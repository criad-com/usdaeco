"""Measured composition, ownership, validation, muting and reconstruction proofs."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usdaeco_suite.stage_common import ROOT, FORM_A, FORM_C, read, write, sha
from usdaeco_suite.stage_checks import (digest, inventory_errors, summarize_validation,
                                       summarize_mutes, layout_errors, STAGE_CAP)


def native():
    root = Path(os.environ['USD_DEV'])
    config = (root / 'pxrConfig.cmake').read_text()
    executable = re.search(r'set\(Python3_EXECUTABLE \[\[(.*?)\]\]\)', config)[1]
    paths = sorted((root / 'lib').glob('python*/site-packages'))
    return executable, str(paths[0])


def probe(mode, directory, output, *, plugins=False, connected=False, use_native=False, reuse=False):
    environment = {k: v for k, v in os.environ.items()
                   if k not in ('PYTHONPATH', 'PXR_PLUGINPATH_NAME', 'PXR_AR_DEFAULT_SEARCH_PATH')}
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    executable = sys.executable
    if use_native or connected:
        executable, environment['PYTHONPATH'] = native()
    if plugins and os.environ.get('USDAECO_VALIDATION_PYTHON'):
        executable = os.environ['USDAECO_VALIDATION_PYTHON']
        environment['PYTHONPATH'] = os.environ.get('USDAECO_VALIDATION_PYTHONPATH', '')
    if connected:
        environment.update(USDAECO_IFC_PYTHON=str(ROOT / 'hosts/usdaeco-ifc/tools/ifc-python'),
                           USDAECO_IFC_SOURCE_PYTHON=sys.executable,
                           USDAECO_IFC_CACHE=str(ROOT / 'out/ifc-cache'),
                           CORE_PLUGIN_DIR=str(ROOT / 'core/usdaeco-core/usdAeco'),
                           AXIS_PLUGIN_DIR=str(ROOT / 'section/usdaeco-axis/usdAecoAxis'),
                           AECO_CORE_ROOT=str(ROOT / 'core/usdaeco-core'),
                           AECO_AXIS_ROOT=str(ROOT / 'section/usdaeco-axis'),
                           AECO_SYNC_ROOT=str(ROOT / 'record/usdaeco-sync'),
                           TOOLCHAIN_DIR=str(ROOT / 'kits/usdaeco-toolchain'),
                           PXR_PLUGINPATH_NAME=str(ROOT / 'hosts/usdaeco-ifc/out/plugins/usdIfc/resources'))
    evidence = dict(stage=digest(directory), mode=mode, plugins=plugins, connected=connected,
                    executable=executable, pythonPath=environment.get('PYTHONPATH', ''),
                    nativePlugins=environment.get('USDAECO_NATIVE_PLUGINPATH', ''),
                    probe=sha(ROOT / 'tools/usdaeco_suite/stage_probe.py'),
                    configuration=sha(ROOT / 'tools/usdaeco_suite/stage_common.py'))
    receipt = output.with_suffix('.receipt.json')
    if reuse and output.is_file() and receipt.is_file() and read(receipt) == evidence:
        return read(output) if output.suffix == '.json' else None
    command = [executable, str(ROOT / 'tools/usdaeco_suite/stage_probe.py'), mode, str(directory), str(output)]
    if plugins:
        command.append('--plugins')
    if connected:
        command.append('--connected')
    def execute(command, label):
        with (ROOT / 'out' / ('probe-' + label + '.log')).open('w') as log:
            completed = subprocess.run(command, env=environment, stdout=log, stderr=log, timeout=3600 if mode == 'mute' else 900)
        if completed.returncode:
            raise ValueError('isolated ' + mode + ' probe failed; see out/probe-' + label + '.log')
    if mode == 'mute' and plugins:
        # Independent stages and validator contexts; each layer is tested once.
        count = min(6, os.cpu_count() or 1)
        commands = []
        for shard in range(count):
            part = output.with_name(output.stem + '-' + str(shard) + '.json')
            child = [part.as_posix() if p == str(output) else p for p in command]
            commands.append((child + ['--shard', str(shard), '--shards', str(count)], part))
        with ThreadPoolExecutor(max_workers=count) as workers:
            jobs = [workers.submit(execute, command, 'mute-' + str(i)) for i, (command, _) in enumerate(commands)]
            for job in jobs:
                job.result()
        parts = [read(path) for _, path in commands]
        data = {k: v for k, v in parts[0].items() if k != 'rows'}
        if not all(p['complete'] and p['baseline'] == data['baseline'] and p['validators'] == data['validators'] for p in parts):
            raise ValueError('mute workers disagree on the baseline')
        data['rows'] = sorted([r for p in parts for r in p['rows']], key=lambda r: r['layer'])
        if len({r['layer'] for r in data['rows']}) != len(data['rows']):
            raise ValueError('duplicate mute evidence')
        write(output, data)
    else:
        execute(command, mode + ('-connected' if connected else ''))
    if digest(directory) != evidence['stage']:
        raise ValueError('publication changed during the probe')
    write(receipt, evidence)
    return read(output) if output.suffix == '.json' else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, default=ROOT / 'stage')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--rebuild', action='store_true')
    parser.add_argument('--compare-rebuild', type=Path, help='compare a separately rerun hook build instead of rerunning it again')
    parser.add_argument('--use-evidence', action='store_true', help='reuse successful probes only when input and runtime hashes match')
    args = parser.parse_args(argv)
    sys.path.insert(0, str(ROOT / 'kits/usdaeco-toolchain/tools'))
    from usdaeco_check.report import Report
    report = Report()
    directory = args.stage.resolve()
    manifest = read(directory / 'manifest.json')
    output = ROOT / 'out/stage-check'
    output.mkdir(parents=True, exist_ok=True)
    proofs = {}
    def check(name, function):
        print('== stage: ' + name, flush=True)
        try:
            data, valid, detail = function()
            proofs[name] = data
            report.check(name, valid, detail)
        except Exception as exc:
            report.check(name, False, str(exc).replace(str(ROOT), '<repo>'))
    def vanilla():
        relocated = ROOT / 'out/vanilla-stage'
        if relocated.exists():
            shutil.rmtree(relocated)
        for path in directory.rglob('*'):
            if path.is_file() and path.suffix in ('.usda', '.usdc'):
                target = relocated / path.relative_to(directory)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        shutil.copyfile(directory / 'manifest.json', relocated / 'manifest.json')
        data = probe('vanilla', relocated, output / 'vanilla.json', reuse=args.use_evidence)
        data['relocatedWithoutIFC'] = True
        return data, True, f"{data['census']['prims']} prims; {len(data['views'])} views; zero plugins or composition errors"
    check('vanilla', vanilla)
    def parity():
        a = probe('snapshot', directory, output / 'connected.json', connected=True, reuse=args.use_evidence)
        c = probe('snapshot', directory, output / 'twins.json', use_native=True, reuse=args.use_evidence)
        excluded = {p['path'] for p in read(directory / 'dc.manifest.json')['tessellationControlled']}
        changed = []
        for path in a.keys() & c.keys():
            left, right = dict(a[path]), dict(c[path])
            if path in excluded:
                left.pop('mesh', None); right.pop('mesh', None)
            if left != right:
                changed.append(path)
        data = dict(connectedPrims=len(a), twinPrims=len(c), added=sorted(a.keys() - c.keys()),
                    missing=sorted(c.keys() - a.keys()), changed=changed, meshExclusions=sorted(excluded),
                    comparedMeshes=sum('mesh' in v and p not in excluded for p, v in c.items()))
        return data, not (data['added'] or data['missing'] or changed), f"{len(a)} prims; {data['comparedMeshes']} meshes; {len(changed)} changed"
    check('connected parity', parity)
    def mute():
        data = probe('mute', directory, output / 'mute.json', plugins=not args.smoke, reuse=args.use_evidence)
        if args.smoke:
            valid = not any(r['moved'] or r['compositionErrors'] for r in data['rows'])
            return data, valid, f"{len(data['rows'])} layer drills; placement and composition only"
        summary, valid = summarize_mutes(data, manifest)
        deviations = sum(bool(r['dependencyErrorCount']) for r in summary['rows'])
        return summary, valid, f"{len(data['rows'])} layer drills; {deviations} with recorded dependency errors; port-only requirement not met"
    check('mute', mute)
    def tree():
        errors, size = inventory_errors(directory, manifest)
        data = dict(files=len(manifest['files']), errors=errors, bytes=size)
        return data, not errors and size <= STAGE_CAP, f"{data['files']} files; {len(errors)} inventory/provenance differences"
    check('inventory', tree)
    def layout():
        data = layout_errors(directory, manifest)
        return data, not data['errors'], f"{sum(data['elementsByPackage'].values())} owned elements; {len(data['cameras'])} render cameras; {len(data['errors'])} layout differences"
    check('layout', layout)
    if not args.smoke:
        def validate():
            data = probe('validate', directory, output / 'validation.json', plugins=True, reuse=args.use_evidence)
            summary, valid = summarize_validation(data, manifest, directory)
            expected_rules = {r['rule'] for r in manifest['expectedFindings']}
            manifest['integrationFindings'] = [r for r in data['findings'] if r['severity'] == 'error' and r['rule'] not in expected_rules]
            return summary, valid, f"{sum(map(len, data['validators'].values()))} validators; {summary['rawErrorCount']} expected findings; {summary['unexpectedErrorCount']} unexpected errors"
        check('validators', validate)
        def strict():
            executable = Path(os.environ['USD_DEV']) / 'bin/usdchecker'
            environment = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PXR_PLUGINPATH_NAME')}
            environment['PXR_PLUGINPATH_NAME'] = ''
            with (output / 'usdchecker.log').open('w') as log:
                result = subprocess.run([str(executable), '--strict', str(directory / FORM_C)],
                                        env=environment, stdout=log, stderr=log, timeout=180)
            return dict(exitCode=result.returncode, strict=True), result.returncode == 0, f'plugin-free usdchecker --strict exit {result.returncode}'
        check('strict checker', strict)
        def render():
            from PIL import Image, ImageStat
            executable = os.environ['USDRECORD']
            target = output / 'vanilla.png'
            environment = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PXR_PLUGINPATH_NAME', 'PXR_AR_DEFAULT_SEARCH_PATH')}
            environment.update(PXR_PLUGINPATH_NAME='', LC_ALL='C', HDEMBREE_CAMERA_LIGHT_INTENSITY='100', HDEMBREE_AMBIENT_OCCLUSION_SAMPLES='0')
            with (output / 'usdrecord.log').open('w') as log:
                result = subprocess.run([executable, '--disableGpu', '--renderer', 'Embree', '--purposes', 'proxy,render',
                                         '--camera', '/Renders/cctv/overview', '--imageWidth', '960',
                                         str(ROOT / 'out/vanilla-stage' / FORM_C), str(target)],
                                        env=environment, stdout=log, stderr=log, timeout=300)
            if result.returncode:
                raise ValueError('plugin-free usdrecord failed; see out/stage-check/usdrecord.log')
            with Image.open(target) as image:
                variance = max(ImageStat.Stat(image.convert('RGB')).var)
                data = dict(width=image.width, height=image.height, bytes=target.stat().st_size,
                            sha256=sha(target), nonUniform=variance > 0, renderer='Embree', relocatedWithoutIFC=True)
            valid = data['nonUniform'] and max(data['width'], data['height']) <= 1600 and data['bytes'] <= 400000
            if args.record and valid:
                shutil.copyfile(target, directory / 'vanilla.png')
                data['file'] = 'vanilla.png'
            return data, valid, f"{data['width']}x{data['height']}; {data['bytes']} bytes; non-uniform={data['nonUniform']}"
        check('vanilla render', render)
    if args.rebuild or args.compare_rebuild:
        def reproduce():
            target = args.compare_rebuild.resolve() if args.compare_rebuild else ROOT / 'out/stage-rebuilt'
            if target == directory:
                raise ValueError('reconstruction must be a separate directory')
            if not args.compare_rebuild:
                command = [sys.executable, str(ROOT / 'stage/build.py'), '--output', str(target)]
                if args.smoke:
                    command.append('--smoke')
                with (output / 'rebuild.log').open('w') as log:
                    result = subprocess.run(command, stdout=log, stderr=log, timeout=1800)
                if result.returncode:
                    raise ValueError('fresh hook rebuild failed; see out/stage-check/rebuild.log')
            expected = {str(p.relative_to(directory)): sha(p) for p in directory.rglob('*.usda')}
            actual = {str(p.relative_to(target)): sha(p) for p in target.rglob('*.usda')}
            changed = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
            return dict(textLayers=len(expected), changed=changed), not changed, f'{len(expected)} text layers; {len(changed)} changed after fresh hooks'
        check('rebuild', reproduce)
    if args.record:
        from usdaeco_suite.stage_build import inventory
        manifest['proofs'] = proofs
        # Include the verified render, then account for the ledger's own bytes.
        inventory(directory, manifest)
        proofs['publication size'] = dict(bytes=0, cap=STAGE_CAP)
        for _ in range(4):
            write(directory / 'manifest.json', manifest)
            size = manifest['totalBytes'] + (directory / 'manifest.json').stat().st_size
            if size == proofs['publication size']['bytes']:
                break
            proofs['publication size']['bytes'] = size
            if 'inventory' in proofs:
                proofs['inventory']['bytes'] = size
        print('== stage: publication size', flush=True)
        report.check('publication size', size <= STAGE_CAP, f'{size} bytes including the manifest; cap {STAGE_CAP}')
    return report.finish()


if __name__ == '__main__':
    raise SystemExit(main())
