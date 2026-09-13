"""Connected-stage flattening and independent, stock-USD comparison receipts."""
import hashlib
from pathlib import Path
import shutil
import sys

from usdaeco_suite.stage_common import ROOT, FORM_A, FORM_B, read, sha, stamp

CRATE_CAP = 10_000_000
METADATA = ('defaultPrim', 'metersPerUnit', 'upAxis', 'fallbackPrimTypes',
            'startTimeCode', 'endTimeCode', 'timeCodesPerSecond', 'framesPerSecond')


def normalized_hash(path):
    sys.path.insert(0, str(ROOT / 'kits/usdaeco-toolchain/tools'))
    from usdaeco_check.example_result import normalized_layer
    return hashlib.sha256(normalized_layer(path)).hexdigest()


def metadata(stage):
    """JSON-safe root metadata, without changing token-array fallbacks in USD."""
    result = {key: stage.GetMetadata(key) for key in METADATA}
    result['fallbackPrimTypes'] = {k: list(v) for k, v in result['fallbackPrimTypes'].items()}
    return result


def study_root_receipts(stage):
    """Retain library path settings when sublayer metadata is flattened away."""
    result = {}
    for layer in stage.GetLayerStack():
        for key, value in layer.customLayerData.items():
            if not key.lower().endswith('studyroot') or key == 'aeco:suite:studyRoot':
                continue
            if key in result and result[key] != value:
                raise ValueError('library study root receipts disagree: ' + key)
            result[key] = value
    return result


def scope_flattened_prototypes(stage, layer):
    """Keep Flatten's generated instance storage inside its source study."""
    from pxr import Sdf
    from usdaeco_suite.stage_common import layer_paths
    from usdaeco_suite.stage_hooks import remap_text
    generated = {p.path for p in layer.rootPrims if p.name.startswith('Flattened_Prototype_')}
    owners = {path: set() for path in generated}
    targets = {path: set() for path in generated}
    for path in layer_paths(layer):
        spec = layer.GetPrimAtPath(path) if path.IsPrimPath() else None
        if not spec or not spec.HasInfo('references'):
            continue
        source = stage.GetPrimAtPath(path)
        if not source:
            continue
        references = source.GetMetadata('references')
        roots = {r.primPath.GetPrefixes()[1] for r in references.GetAppliedItems()
                 if r.primPath.HasPrefix(Sdf.Path('/Studies')) and len(r.primPath.GetPrefixes()) >= 2} if references else set()
        for reference in spec.referenceList.GetAppliedItems():
            if reference.primPath in owners:
                owners[reference.primPath].update(roots)
                targets[reference.primPath].update(str(r.primPath) for r in references.GetAppliedItems())
    if any(len(roots) != 1 for roots in owners.values()):
        raise ValueError('flattened prototype must have one owning study')
    mappings = {}
    for path, roots in owners.items():
        suffix = hashlib.sha256('\n'.join(sorted(targets[path])).encode()).hexdigest()[:16]
        mappings[str(path)] = str(next(iter(roots)).AppendChild('Flattened_Prototype_' + suffix))
    edits = Sdf.BatchNamespaceEdit()
    for old, new in sorted(mappings.items(), key=lambda pair: pair[1]):
        if layer.GetPrimAtPath(new):
            raise ValueError('source occupies the generated prototype namespace')
        edits.Add(old, new)
    if mappings:
        if not layer.Apply(edits):
            raise ValueError('cannot scope flattened instance storage')
        layer.ImportFromString(remap_text(layer.ExportToString(), mappings))


def export_flat(stage, directory, target):
    from pxr import UsdUtils
    from usdaeco_suite.stage_probe import snapshot
    layer = stage.Flatten(addSourceFileComment=False)
    scope_flattened_prototypes(stage, layer)
    layer.customLayerData = {**layer.customLayerData, **study_root_receipts(stage)}
    for key in METADATA:
        layer.pseudoRoot.SetInfo(key, stage.GetMetadata(key))
    stamp(layer, 'flattened', 'suite', 'Usd.Stage.Flatten', 'stage/' + FORM_A,
          sha(directory / FORM_A), 'v' + read(ROOT / 'library.json')['version'])
    if layer.subLayerPaths or layer.GetExternalAssetDependencies() or any(layer.externalReferences):
        raise ValueError('flattened stage has external asset dependencies')
    if not layer.Export(str(target)):
        raise ValueError('crate export failed')
    if any(UsdUtils.ExtractExternalReferences(str(target))):
        target.unlink()
        raise ValueError('flattened stage has external asset dependencies')
    return dict(source=snapshot(stage), metadata=metadata(stage), studyRoots=study_root_receipts(stage))


def compare(left, right, excluded=()):
    """All snapshot fields must agree; only declared mesh fields are excluded."""
    changed = {}
    for path in sorted(left.keys() & right.keys()):
        fields = sorted(k for k in left[path].keys() | right[path].keys()
                        if left[path].get(k) != right[path].get(k)
                        and not (k == 'mesh' and path in excluded))
        if fields:
            changed[path] = fields
    return dict(leftPrims=len(left), rightPrims=len(right),
                added=sorted(right.keys() - left.keys()), removed=sorted(left.keys() - right.keys()),
                changed=changed, comparedMeshes=sum('mesh' in v and p not in excluded for p, v in left.items()),
                meshExclusions=sorted(excluded))


def equal(result):
    return not (result['added'] or result['removed'] or result['changed'])


def scene_fields(rows, *, flattened=False):
    """Compare public scene paths; report Flatten's generated storage separately."""
    result, storage = {}, []
    for path, row in rows.items():
        if any(part.startswith('Flattened_Prototype_') for part in path.split('/')):
            if not flattened:
                raise ValueError('source occupies the generated prototype namespace')
            storage.append(path)
        else:
            result[path] = {k: row[k] for k in ('type', 'identity', 'world', 'transformTimes', 'mesh') if k in row}
    return result, storage


def build_flattened(directory):
    """Always read Form A through the ABI-matched IFC reader, then publish by cap."""
    from usdaeco_suite.stage_check import probe
    from usdaeco_suite.stage_build import inventory
    print('== stage: flatten connected root', flush=True)
    target = ROOT / 'out' / FORM_B
    target.parent.mkdir(parents=True, exist_ok=True)
    probe('flatten', directory, target.with_suffix('.json'), connected=True)
    size = target.stat().st_size
    committed = directory / FORM_B
    if size <= CRATE_CAP:
        shutil.copyfile(target, committed)
    elif committed.exists():
        committed.unlink()
    record = dict(file=FORM_B, bytes=size, sha256=sha(target),
                  normalization='sdf-usda-v1', normalized_sha256=normalized_hash(target),
                  source='stage/' + FORM_A, sourceSha256=sha(directory / FORM_A),
                  tag='v' + read(ROOT / 'library.json')['version'],
                  distribution='committed' if size <= CRATE_CAP else 'release-asset', cap=CRATE_CAP)
    manifest = read(directory / 'manifest.json')
    manifest['flattened'] = record
    inventory(directory, manifest)
    print(f"{size} bytes; {record['distribution']}; sdf-usda-v1 {record['normalized_sha256']}", flush=True)
    return record


def check_flattened(directory, output, manifest):
    from usdaeco_suite.stage_check import probe
    record = manifest['flattened']
    artifact = directory / FORM_B if record['distribution'] == 'committed' else ROOT / 'out' / FORM_B
    if not artifact.is_file():
        raise ValueError('Form B missing; run stage/build.py --flatten or fetch the release asset into out/')
    # Each fresh native process reopens the connected source before Flatten.
    a = probe('flatten', directory, output / 'flat-a.json', connected=True)
    probe('flatten', directory, output / 'flat-a-repeat.json', connected=True)
    c = probe('flatten', directory, output / 'flat-c.json', use_native=True)
    isolated = output / 'flat-isolated'
    isolated.mkdir(exist_ok=True)
    shutil.copyfile(artifact, isolated / FORM_B)
    b = probe('flat-snapshot', isolated, output / 'flat-stock.json')
    flat_c_dir = output / 'flat-c-isolated'
    flat_c_dir.mkdir(exist_ok=True)
    shutil.copyfile(output / 'flat-c.usdc', flat_c_dir / FORM_B)
    fc = probe('flat-snapshot', flat_c_dir, output / 'flat-c-stock.json')
    excluded = {p['path'] for p in read(directory / 'dc.manifest.json')['tessellationControlled']}
    bs, storage = scene_fields(b['snapshot'], flattened=True)
    cs, c_storage = scene_fields(fc['snapshot'], flattened=True)
    original_a, _ = scene_fields(a['source'])
    original_c, _ = scene_fields(c['source'])
    comparisons = dict(flattenedToTwins=compare(bs, original_c, excluded),
                       flattenedTwinsToConnected=compare(cs, original_a, excluded),
                       flattenedTwinsToFlattenedConnected=compare(cs, bs, excluded),
                       flattenedToConnected=compare(bs, original_a))
    hashes = [normalized_hash(p) for p in (artifact, output / 'flat-a.usdc', output / 'flat-a-repeat.usdc')]
    valid = (all(equal(v) for v in comparisons.values()) and len(set(hashes)) == 1
             and hashes[0] == record['normalized_sha256'] and sha(artifact) == record['sha256']
             and artifact.stat().st_size == record['bytes']
             and record['sourceSha256'] == sha(directory / FORM_A)
             and b['metadata'] == a['metadata'] == c['metadata'] == fc['metadata']
             and a['studyRoots'] == c['studyRoots']
             and all(b['provenance'].get(k) == v == fc['provenance'].get(k) for k, v in a['studyRoots'].items())
             and b['provenance']['aeco:layer:role'] == 'flattened'
             and b['provenance']['aeco:layer:source'] == 'stage/' + FORM_A
             and b['provenance']['aeco:layer:sourceSha256'] == record['sourceSha256']
             and b['provenance']['aeco:layer:tag'] == record['tag']
             and record['distribution'] == ('committed' if record['bytes'] <= CRATE_CAP else 'release-asset')
             and (record['bytes'] <= CRATE_CAP or not (directory / FORM_B).exists()))
    data = dict(comparisons=comparisons, metadata=b['metadata'], plugins=b['plugins'],
                layout=b['layout'],
                studyRoots=a['studyRoots'],
                rawPrims=len(b['snapshot']), scenePrims=len(bs), generatedPrototypePrims=len(storage),
                flattenedTwinsPrototypePrims=len(c_storage),
                censusDeviation='Usd.Stage.Flatten adds generated instance-prototype storage prims.',
                stockUSD=b['usdVersion'], bytes=record['bytes'], normalization=record['normalization'],
                normalizedHashes=hashes, deterministic=len(set(hashes)) == 1,
                externalAssets=b['externalAssets'], sublayers=b['sublayers'])
    return data, valid, f"{record['bytes']} bytes; {len(b['snapshot'])} prims; three equal normalized hashes"
