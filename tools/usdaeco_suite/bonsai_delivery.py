"""Compare, publish and reproduce the cooling producer delivery from source."""
from collections import Counter
import os
from pathlib import Path
import shutil
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usdaeco_suite.stage_common import ROOT, configure, read, write, sha, stamp, repos
from usdaeco_suite.stage_flatten import compare, equal, normalized_hash

PRODUCER = 'Bonsai 0.8.5 (Blender 5.1.2) export of the generator delivery'
SOURCE = ROOT / 'data/usdaeco-datacentre/dist/full'
SUFFIXES = ('.ifc', '.usda', '.semantics.usda', '.geometry.usdc')


def ifc_records(path):
    import ifcopenshell
    model = ifcopenshell.open(str(path))
    def document(d):
        return (d.Description, d.Location, d.Identification, d.Name)
    return dict(entities=Counter(e.is_a() for e in model),
                identities=Counter((e.GlobalId, e.is_a()) for e in model.by_type('IfcRoot')),
                documents=Counter(document(d) for d in model.by_type('IfcDocumentReference')),
                associations=Counter((r.GlobalId, document(r.RelatingDocument),
                                      tuple(sorted(e.GlobalId for e in r.RelatedObjects)))
                                     for r in model.by_type('IfcRelAssociatesDocument')))


def compare_ifc(before, after):
    return {key: dict(before=sum(before[key].values()), after=sum(after[key].values()),
                      removed=sum((before[key] - after[key]).values()),
                      added=sum((after[key] - before[key]).values())) for key in before}


def package_snapshot(path):
    from pxr import Sdf, Usd
    from usdaeco_suite.stage_probe import snapshot
    shared = Sdf.Layer.FindOrOpen(str(SOURCE / 'shared.usda'))
    root = Sdf.Layer.CreateAnonymous()
    root.TransferContent(shared)
    root.subLayerPaths = [str(path.resolve()), shared.identifier]
    stage = Usd.Stage.Open(root)
    if not stage or stage.GetCompositionErrors():
        raise ValueError('cooling comparison stage does not compose')
    return snapshot(stage)


def convert_delivery(source, destination):
    from usdaeco_ifc.convert import convert
    destination.mkdir(parents=True, exist_ok=True)
    return convert(str(source), str(destination / 'cooling.usda'), overlay_spine=True)


def stamp_twin(folder, *, tag=None):
    """Keep the two declared display fixtures; all other geometry is converted."""
    from pxr import Sdf
    controlled = read(SOURCE / 'dc.manifest.json')['tessellationControlled']
    old = Sdf.Layer.FindOrOpen(str(SOURCE / 'cooling.geometry.usdc'))
    geometry = Sdf.Layer.FindOrOpen(str(folder / 'cooling.geometry.usdc'))
    for row in controlled:
        path = Sdf.Path(row['path'])
        if not old.GetPrimAtPath(path):
            raise ValueError('controlled mesh missing from the pinned delivery')
        Sdf.CopySpec(old, path, geometry, path)
    for suffix, role in [('.usda', 'package'), ('.semantics.usda', 'semantics'), ('.geometry.usdc', 'geometry')]:
        layer = Sdf.Layer.FindOrOpen(str(folder / ('cooling' + suffix)))
        stamp(layer, role, 'cooling', PRODUCER, 'cooling.ifc', sha(folder / 'cooling.ifc'),
              tag or 'v' + read(ROOT / 'library.json')['version'])
        layer.customLayerData = {**layer.customLayerData,
                                 'aeco:layer:generatorSourceSha256': sha(SOURCE / 'cooling.ifc')}
        layer.Save()


def delivery_readme(folder, receipt):
    lines = ['# cooling delivery', '', 'Producer: ' + PRODUCER + '.', '',
             'Bonsai loaded the pinned generator IFC and saved it without model edits.',
             'The export header timestamp is normalized to the generator timestamp.',
             'The adjacent USD twin is regenerated with the pinned converter (`spine=over`).',
             'The two declared `tessellationControlled` display meshes are retained from',
             'the pinned publication; their IFC swept solids remain unchanged.', '',
             '| Verified census | Count |', '|---|---:|']
    lines += [f'| {key} | {value} |' for key, value in read(SOURCE / 'dc.manifest.json')['packages']['cooling'].items()]
    lines += ['', 'All 16,163 IFC GlobalIds, 184 document references and 184 document associations',
              'survive. Description, Location, Identification, related objects and relationship',
              'GlobalIds are compared with multiplicity. Classification, relationship targets,',
              f"world transforms and {receipt['usd']['comparedMeshes']} meshes (including shared space extents) match.",
              'Two controlled meshes are excluded from the export comparison.', '',
              'The measured receipt is [bonsai-export.json](bonsai-export.json).',
              '`presentation.usda`, `drivers.usda` and `derived.usda` remain independently mutable.',
              'The shared delivery alone defines the spatial structure.', '']
    (folder / 'README.md').write_text('\n'.join(lines))


def install_delivery(destination, copied):
    """Rebuild from the accepted producer IFC; Blender is only needed to redeliver."""
    accepted = ROOT / 'stage/packages/cooling'
    receipt_path = accepted / 'bonsai-export.json'
    if not receipt_path.is_file():
        return None
    receipt = read(receipt_path)
    if not receipt['accepted']:
        shutil.copyfile(receipt_path, destination / 'packages/cooling/bonsai-export.json')
        return receipt
    if sha(accepted / 'cooling.ifc') != receipt['export']['sha256']:
        raise ValueError('accepted Bonsai source hash differs')
    folder = destination / 'packages/cooling'
    shutil.copyfile(accepted / 'cooling.ifc', folder / 'cooling.ifc')
    convert_delivery(folder / 'cooling.ifc', folder)
    from pxr import Sdf
    production_tag = Sdf.Layer.FindOrOpen(str(accepted / 'cooling.usda')).customLayerData['aeco:layer:tag']
    stamp_twin(folder, tag=production_tag)
    if any(normalized_hash(folder / name) != value for name, value in receipt['twins'].items()):
        raise ValueError('regenerated Bonsai twin differs from the accepted delivery')
    shutil.copyfile(receipt_path, folder / 'bonsai-export.json')
    delivery_readme(folder, receipt)
    for suffix in SUFFIXES:
        copied.pop('packages/cooling/cooling' + suffix, None)
    return receipt


def accepted_delivery_file(folder, name):
    receipt = read(folder / 'bonsai-export.json')
    if not receipt['accepted'] or receipt['generator']['sha256'] != sha(SOURCE / 'cooling.ifc'):
        return False
    if name == 'cooling.ifc':
        return sha(folder / name) == receipt['export']['sha256']
    return (name in receipt['twins'] and
            normalized_hash(folder / name) == receipt['twins'][name])


def check_delivery(directory, output):
    receipt = read(directory / 'packages/cooling/bonsai-export.json')
    source = directory / 'packages/cooling/cooling.ifc'
    if sha(SOURCE / 'cooling.ifc') != receipt['generator']['sha256']:
        raise ValueError('Bonsai baseline differs from the pinned source')
    if not receipt['accepted']:
        valid = sha(source) == receipt['generator']['sha256']
        return receipt, valid, 'export rejected; generator source retained'
    configure()
    generated = output / 'bonsai-converted'
    if generated.exists():
        shutil.rmtree(generated)
    convert_delivery(source, generated)
    baseline = package_snapshot(SOURCE / 'cooling.usda')
    candidate = package_snapshot(generated / 'cooling.usda')
    committed = package_snapshot(source.with_suffix('.usda'))
    excluded = {p['path'] for p in read(SOURCE / 'dc.manifest.json')['tessellationControlled']}
    usd = compare(baseline, candidate, excluded)
    twin = compare(candidate, committed, excluded)
    ifc = compare_ifc(ifc_records(SOURCE / 'cooling.ifc'), ifc_records(source))
    valid = (equal(usd) and equal(twin) and ifc == receipt['ifc'] and usd == receipt['usd']
             and all(not (r['added'] or r['removed']) for r in ifc.values())
             and sha(source) == receipt['export']['sha256']
             and receipt['converter']['tag'] == repos()['usdaeco-ifc']['tag'])
    from pxr import Sdf
    for suffix in SUFFIXES[1:]:
        data = Sdf.Layer.FindOrOpen(str(source.parent / ('cooling' + suffix))).customLayerData
        valid &= (data['aeco:layer:producer'] == PRODUCER and data['aeco:layer:sourceSha256'] == sha(source))
        valid &= accepted_delivery_file(source.parent, 'cooling' + suffix)
    return dict(ifc=ifc, usd=usd, committedTwin=twin, accepted=True), valid, \
        f"{ifc['identities']['after']} GlobalIds; {ifc['documents']['after']} references; {ifc['associations']['after']} associations; {usd['comparedMeshes']} meshes"


def main():
    configure()
    print('== stage: Bonsai delivery', flush=True)
    work = ROOT / 'out/bonsai-delivery'
    work.mkdir(parents=True, exist_ok=True)
    raw = work / 'cooling.raw.ifc'
    runtime = work / 'runtime.json'
    environment = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    with (work / 'blender.log').open('w') as log:
        subprocess.run([os.environ['AECO_BLENDER'], '-b', '--python-exit-code', '1', '--python',
                        str(ROOT / 'tools/usdaeco_suite/bonsai_export.py'), '--',
                        str(SOURCE / 'cooling.ifc'), str(raw), str(runtime)],
                       env=environment, stdout=log, stderr=log, timeout=900, check=True)
    host = read(runtime)
    if host['blender'] != '5.1.2' or host['bonsai'] != 'Bonsai 0.8.5' or not host['exported']:
        raise ValueError('Bonsai runtime does not match the production contract')
    # Normalize only volatile export header fields, keeping the Bonsai producer.
    import ifcopenshell
    exported = ifcopenshell.open(str(raw))
    baseline = ifcopenshell.open(str(SOURCE / 'cooling.ifc'))
    exported.header.file_name.time_stamp = baseline.header.file_name.time_stamp
    exported.header.file_name.name = 'cooling.ifc'
    candidate = work / 'cooling.ifc'
    exported.write(str(candidate))
    print('== stage: compare cooling export', flush=True)
    convert_delivery(candidate, work)
    excluded = {p['path'] for p in read(SOURCE / 'dc.manifest.json')['tessellationControlled']}
    usd = compare(package_snapshot(SOURCE / 'cooling.usda'), package_snapshot(work / 'cooling.usda'), excluded)
    ifc = compare_ifc(ifc_records(SOURCE / 'cooling.ifc'), ifc_records(candidate))
    accepted = equal(usd) and all(not (r['added'] or r['removed']) for r in ifc.values())
    receipt = dict(accepted=accepted, producer=PRODUCER, runtime=host,
                   generator=dict(source='data/usdaeco-datacentre/dist/full/cooling.ifc',
                                  sha256=sha(SOURCE / 'cooling.ifc'), tag=repos()['usdaeco-datacentre']['tag']),
                   export=dict(sha256=sha(candidate), bytes=candidate.stat().st_size, rawSha256=sha(raw),
                               normalizedHeaderFields=['name', 'time_stamp']),
                   converter=dict(repo='usdaeco-ifc', tag=repos()['usdaeco-ifc']['tag'], spine='over'),
                   ifc=ifc, usd=usd, deviations=[] if accepted else ['Export comparison differs; generator delivery retained.'])
    target = ROOT / 'stage/packages/cooling'
    manifest = read(ROOT / 'stage/manifest.json')
    if accepted:
        stamp_twin(work)
        receipt['twins'] = {'cooling' + suffix: normalized_hash(work / ('cooling' + suffix)) for suffix in SUFFIXES[1:]}
        for suffix in SUFFIXES:
            shutil.copyfile(work / ('cooling' + suffix), target / ('cooling' + suffix))
            manifest['copied'].pop('packages/cooling/cooling' + suffix, None)
        delivery_readme(target, receipt)
    else:
        for suffix in SUFFIXES:
            name = 'cooling' + suffix
            shutil.copyfile(SOURCE / name, target / name)
            manifest['copied']['packages/cooling/' + name] = dict(
                source=str((SOURCE / name).relative_to(ROOT)), sourceSha256=sha(SOURCE / name),
                tag=repos()['usdaeco-datacentre']['tag'])
        (target / 'README.md').write_text(
            '# cooling delivery\n\nThe pinned generator delivery and its USD twin are retained.\n'
            'The Bonsai export did not preserve the comparison contract.\n'
            'See [bonsai-export.json](bonsai-export.json) for the exact comparison counts.\n')
    write(target / 'bonsai-export.json', receipt)
    manifest['bonsai'] = receipt
    from usdaeco_suite.stage_build import inventory
    inventory(ROOT / 'stage', manifest)
    print(f"accepted={accepted}; {ifc['documents']['after']} document references; {usd['comparedMeshes']} compared meshes", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
