"""Reproduce the federated USD and IFC roots from the suite's pinned sources."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usdaeco_suite.stage_common import (ROOT, FORM_A, FORM_C, DISCIPLINES, read, write,
                                       sha, repos, configure, stamp, header, layer_paths)


def fallback_union():
    """Collect declared stock fallbacks from committed schemas and example roots."""
    from pxr import Sdf
    result = {}
    evidence = []
    for card in repos().values():
        checkout = ROOT / card['path']
        candidates = set(checkout.glob('*/generatedSchema.usda'))
        candidates.update(checkout.glob('examples/*.usda'))
        candidates.update(checkout.glob('examples/*/result/layers/out/*.usda'))
        candidates.update(checkout.glob('examples/*/result/layers/out/*/*.usda'))
        for path in sorted(candidates):
            if 'fallbackPrimTypes' not in path.read_text():
                continue
            layer = Sdf.Layer.FindOrOpen(str(path))
            values = layer.pseudoRoot.GetInfo('fallbackPrimTypes') or {}
            for key, value in values.items():
                if key in result and result[key] != list(value):
                    raise ValueError('conflicting fallback: ' + key)
                result[key] = list(value)
            if values:
                evidence.append(str(path.relative_to(ROOT)))
    source = Sdf.Layer.FindOrOpen(str(ROOT / 'data/usdaeco-datacentre/dist/full/dc.usda'))
    result.update({k: list(v) for k, v in source.pseudoRoot.GetInfo('fallbackPrimTypes').items()})
    return result, evidence


def new_layer(path, role, package, source, tag, fallbacks=None, producer='usdAECO suite'):
    from pxr import Sdf
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(path))
    stamp(layer, role, package, producer, str(source.relative_to(ROOT)), sha(source), tag)
    if fallbacks is not None:
        header(layer, fallbacks)
    return layer


def packages(destination, fallbacks):
    from pxr import Sdf
    source = ROOT / 'data/usdaeco-datacentre/dist/full'
    data = read(source / 'dc.manifest.json')
    tag = repos()['usdaeco-datacentre']['tag']
    shutil.copyfile(source / 'dc.manifest.json', destination / 'dc.manifest.json')
    copied = {'dc.manifest.json': dict(source=str((source / 'dc.manifest.json').relative_to(ROOT)),
                                      sourceSha256=sha(source / 'dc.manifest.json'), tag=tag)}
    for discipline in DISCIPLINES:
        folder = destination / 'packages' / discipline
        folder.mkdir(parents=True)
        for suffix in ('.ifc', '.usda', '.semantics.usda', '.geometry.usdc'):
            name = discipline + suffix
            path = folder / name
            shutil.copyfile(source / name, path)
            copied[str(path.relative_to(destination))] = dict(source=str((source / name).relative_to(ROOT)),
                                                            sourceSha256=sha(path), tag=tag)
        layer = new_layer(folder / 'presentation.usda', 'presentation', discipline,
                          source / (discipline + '.ifc'), tag)
        layer.Save()
        # The reader materializes a flattened delivery. Restore the twin's
        # catalog inheritance so upper-layer type refinements reach occurrences
        # identically through either form. This layer owns no definitions.
        drivers = new_layer(folder / 'drivers.usda', 'drivers', discipline,
                            source / (discipline + '.semantics.usda'), tag)
        semantics = Sdf.Layer.FindOrOpen(str(source / (discipline + '.semantics.usda')))
        for path in layer_paths(semantics):
            prim = semantics.GetPrimAtPath(path) if path.IsPrimPath() else None
            if prim and prim.HasInfo('inheritPaths'):
                target = Sdf.CreatePrimInLayer(drivers, path)
                target.SetInfo('inheritPaths', prim.GetInfo('inheritPaths'))
        drivers.Save()
        lines = [f'# {discipline} delivery', '',
                 f'Producer: {data["generator"]}. Source release: `{tag}`.', '',
                 'The IFC delivery and its USD twin are copied without changing their bytes.',
                 'The source layer stamps retain their original production tag; the suite manifest',
                 'records the release that supplied these bytes.', '',
                 '| Census | Count |', '|---|---:|']
        lines += [f'| {key} | {value} |' for key, value in data['packages'][discipline].items()]
        lines += ['', '`presentation.usda` contains local display opinions and may be muted separately.',
                  'The shared delivery defines the spatial structure; other deliveries overlay it.', '']
        if discipline == 'cooling':
            lines += ['Two meshes are `tessellationControlled`: the near and tangent clash pipes.',
                      'Their IFC swept solids can tessellate differently from the controlled USD twins.',
                      'See `tessellationControlled` in the adjacent delivery manifest.', '']
        (folder / 'README.md').write_text('\n'.join(lines))
    return copied


def package_stack(names, destination=None):
    result = []
    for d in names:
        result.append(f'packages/{d}/presentation.usda')
        if destination and (destination / f'packages/{d}/derived.usda').exists():
            result.append(f'packages/{d}/derived.usda')
        result += [f'packages/{d}/drivers.usda', f'packages/{d}/{d}.usda']
    return result


def root_layer(destination, name, stack, fallbacks):
    source = ROOT / 'data/usdaeco-datacentre/dist/full/dc.usda'
    layer = new_layer(destination / name, 'root', 'suite', source,
                      'v' + read(ROOT / 'library.json')['version'], fallbacks)
    layer.subLayerPaths = stack
    layer.Save()
    return layer


def run_analysis(name, destination, fallbacks, reuse=False):
    command = [sys.executable, str(ROOT / 'tools/usdaeco_suite/stage_hooks.py'), name, str(destination)]
    if reuse:
        command.append('--reuse')
    subprocess.run(command, check=True, timeout=900)
    return read(destination / 'analysis' / name / 'receipt.json')


def views(destination, fallbacks, analyses):
    mapping = {'shell': ['shared'], 'site': ['site', 'shared'], 'architecture': ['arch', 'shared'],
               'structure': ['structure', 'shared'], 'mep': ['cooling', 'electrical', 'shared'],
               **{d: [d, 'shared'] for d in ('electrical', 'it', 'fitout', 'security')}}
    result = {}
    for name, selected in mapping.items():
        stack = ['../' + p for p in package_stack(selected, destination)]
        root_layer(destination, 'views/' + name + '.usda', stack, fallbacks)
        result[name] = dict(packages=selected, analyses=[])
    for name, receipt in analyses.items():
        stack = ['../presentation/views/' + name + '.usda', '../presentation/' + name + '.usda', '../analysis/' + name + '/root.usda']
        stack += ['../' + p for p in package_stack(DISCIPLINES, destination)]
        root_layer(destination, 'views/' + name + '.usda', stack, fallbacks)
        result[name] = dict(packages=list(DISCIPLINES), analyses=[name])
        if name == 'plan':
            for key in ('A', 'B'):
                view = 'plan-' + key
                stack = [f'../presentation/{view}.usda', f'../analysis/plan/out/{key}/play.usda']
                stack += ['../' + p for p in package_stack(DISCIPLINES, destination)]
                layer = root_layer(destination, 'views/' + view + '.usda', stack, fallbacks)
                layer.endTimeCode = 77
                layer.Save()
                result[view] = dict(packages=list(DISCIPLINES), analyses=['plan'], programme=key)
    root_layer(destination, 'views/all.usda', ['../' + FORM_C], fallbacks)
    result['all'] = dict(packages=list(DISCIPLINES), analyses=list(analyses))
    return result


def inventory(destination, manifest):
    from pxr import Sdf
    files = {}
    for path in sorted(destination.rglob('*')):
        if not path.is_file() or path.name == 'manifest.json' or '__pycache__' in path.parts:
            continue
        relative = str(path.relative_to(destination))
        row = dict(sha256=sha(path), bytes=path.stat().st_size)
        if path.suffix in {'.usda', '.usdc'}:
            layer = Sdf.Layer.FindOrOpen(str(path))
            row.update({k.removeprefix('aeco:layer:'): v for k, v in layer.customLayerData.items()
                        if k.startswith('aeco:layer:')})
            row['primSpecs'] = sum(p.IsPrimPath() for p in layer_paths(layer))
            source = row.get('source', '')
            origin = ROOT / source if (ROOT / source).is_file() else path.parent / source
            row['sourceStampMatches'] = origin.is_file() and sha(origin) == row.get('sourceSha256')
        if relative in manifest.get('copied', {}):
            row['copy'] = manifest['copied'][relative]
        files[relative] = row
    manifest['files'] = files
    manifest['sourceStampDifferences'] = [name for name, row in files.items() if row.get('sourceStampMatches') is False]
    manifest['totalBytes'] = sum(r['bytes'] for r in files.values())
    manifest['folderBytes'] = {str(folder.relative_to(destination)): sum(
        r['bytes'] for name, r in files.items() if name.startswith(str(folder.relative_to(destination)) + '/'))
        for category in ('packages', 'analysis') for folder in sorted((destination / category).iterdir()) if folder.is_dir()}
    for category in ('presentation', 'views'):
        manifest['folderBytes'][category] = sum(r['bytes'] for name, r in files.items() if name.startswith(category + '/'))
    write(destination / 'manifest.json', manifest)


def binary_geometry(destination):
    """Keep bulk geometry in crates; preserve readable drivers and result records."""
    from pxr import Sdf
    selected = []
    for path in sorted((destination / 'analysis').rglob('*.usda')):
        if (path.stem in {'exact', 'twins', 'exploded', 'diagrams', 'CriticalDoors', 'Privacy'}
                or path.stem.startswith(('derived-cameras-', 'wireframe-', 'part-'))):
            selected.append(path)
    mapping = {str(p.resolve()): p.with_suffix('.usdc') for p in selected}
    for path in sorted(destination.rglob('*.usda')):
        layer = Sdf.Layer.FindOrOpen(str(path))
        paths = [os.path.relpath(mapping[str((path.parent / p).resolve())], path.parent)
                 if str((path.parent / p).resolve()) in mapping else p for p in layer.subLayerPaths]
        if paths != list(layer.subLayerPaths):
            layer.subLayerPaths = paths
            layer.Save()
    for path in selected:
        Sdf.Layer.FindOrOpen(str(path)).Export(str(mapping[str(path.resolve())]))
        path.unlink()


def compact_layers(destination, copied):
    """Use compact USDA indentation without changing delivered source bytes."""
    from pxr import Sdf
    for path in destination.rglob('*.usda'):
        if str(path.relative_to(destination)) in copied:
            continue
        lines = []
        multiline = False
        for line in Sdf.Layer.FindOrOpen(str(path)).ExportToString().splitlines():
            if not multiline:
                depth = len(line) - len(line.lstrip(' '))
                line = ' ' * (depth // 4) + line.lstrip(' ')
            lines.append(line)
            if line.count('"""') % 2:
                multiline = not multiline
        path.write_text('\n'.join(lines) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'stage')
    parser.add_argument('--analyses', nargs='+')
    parser.add_argument('--reuse-hooks', action='store_true', help='development only: rearchive existing hook outputs')
    parser.add_argument('--flatten', action='store_true', help='flatten the existing connected stage only')
    args = parser.parse_args(argv)
    if args.flatten:
        from usdaeco_suite.stage_flatten import build_flattened
        build_flattened(args.output.resolve())
        return 0
    configure()
    from pxr import Sdf
    print('== stage: federated packages', flush=True)
    output = args.output.resolve()
    # Build in an isolated directory; never mutate the pinned submodule inputs.
    destination = ROOT / 'out/stage-build'
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    fallbacks, evidence = fallback_union()
    copied = packages(destination, fallbacks)
    from usdaeco_suite.bonsai_delivery import install_delivery
    bonsai = install_delivery(destination, copied)
    base = package_stack(DISCIPLINES)
    root_layer(destination, FORM_C, base, fallbacks)
    names = args.analyses or (['cctv'] if args.smoke else ['cctv', 'clash', 'plan', 'compliance', 'repeat', 'solid', 'wall', 'pipe', 'buildup'])
    analyses = {}
    for name in names:
        print('== stage: analysis ' + name, flush=True)
        analyses[name] = run_analysis(name, destination, fallbacks, args.reuse_hooks)
    stack = [f'presentation/{name}.usda' for name in analyses]
    stack += [f'analysis/{name}/root.usda' for name in analyses]
    stack += package_stack(DISCIPLINES, destination)
    # Reopen the package-only root after worker processes have finished reading it.
    layer = Sdf.Layer.FindOrOpen(str(destination / FORM_C))
    layer.subLayerPaths = stack
    layer.Save()
    connected = [re.sub(r'packages/([^/]+)/\1\.usda$', lambda m:
                       f'packages/{m[1]}/{m[1]}.ifc' + (':SDF_FORMAT_ARGS:spine=over&geometry=1' if m[1] != 'shared' else ''), p)
                 for p in stack]
    root_layer(destination, FORM_A, connected, fallbacks)
    selection = views(destination, fallbacks, analyses)
    binary_geometry(destination)
    print('== stage: refresh composed analysis receipts', flush=True)
    environment = dict(os.environ)
    executable = environment.get('USDAECO_VALIDATION_PYTHON', sys.executable)
    environment.pop('PYTHONPATH', None)
    if environment.get('USDAECO_VALIDATION_PYTHON'):
        environment['PYTHONPATH'] = environment.get('USDAECO_VALIDATION_PYTHONPATH', '')
    subprocess.run([executable, str(ROOT / 'tools/usdaeco_suite/stage_finalize.py'), str(destination)],
                   env=environment, check=True, timeout=900)
    compact_layers(destination, copied)
    manifest = dict(facility='demo-datacentre-01', version=read(ROOT / 'library.json')['version'],
                    source=dict(repo='usdaeco-datacentre', tag=repos()['usdaeco-datacentre']['tag']),
                    copied=copied, fallbackPrimTypes=fallbacks, fallbackSources=evidence,
                    packages=read(destination / 'dc.manifest.json')['packages'], analyses=analyses, views=selection,
                    crossPackageLinks=read(destination / 'dc.manifest.json')['crossPackageLinks'],
                    integration=read(destination / 'integration.json'),
                    axis=dict(run=True, producer='wall and pipe hooks', standaloneHook=False), proofs={})
    from usdaeco_suite.stage_checks import finding_records
    manifest['expectedFindings'] = finding_records(manifest)
    manifest['integrationFindings'] = []
    if bonsai:
        manifest['bonsai'] = bonsai
    output.mkdir(parents=True, exist_ok=True)
    for name in ('packages', 'analysis', 'presentation', 'views'):
        if (output / name).exists():
            shutil.rmtree(output / name)
        shutil.copytree(destination / name, output / name)
    for name in (FORM_C, FORM_A, 'dc.manifest.json', 'integration.json'):
        shutil.copyfile(destination / name, output / name)
    inventory(output, manifest)
    if not args.smoke:
        from usdaeco_suite.stage_flatten import build_flattened
        build_flattened(output)
    print(f"{len(copied)} copied files, {len(analyses)} analyses, {len(selection)} views; {manifest['totalBytes']} bytes", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
