"""Fresh-process USD proofs. This module imports no suite plugins by default."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usdaeco_suite.stage_common import FORM_C, FORM_A, FORM_B, read, write, configure


def clean_plugins():
    from pxr import Plug
    found = [p.name for p in Plug.Registry().GetAllPlugins()
             if p.name.startswith(('usdAeco', 'usdSolid')) or p.name == 'usdIfc']
    if found:
        raise ValueError('unexpected suite plugins: ' + ', '.join(found))


def census(stage):
    from pxr import UsdGeom
    counts = Counter()
    for prim in stage.TraverseAll():
        counts['prims'] += 1
        counts[prim.GetTypeName() or 'untyped'] += 1
        if prim.GetAttribute('aeco:id').Get():
            counts['identified'] += 1
        if prim.IsA(UsdGeom.Mesh):
            counts['meshes'] += 1
    return dict(sorted(counts.items()))


def open_stage(path):
    from pxr import Usd
    stage = Usd.Stage.Open(str(path))
    if stage is None or stage.GetCompositionErrors():
        raise ValueError('stage has composition errors')
    return stage


def transform_times(stage):
    from pxr import UsdGeom
    result = {}
    for prim in stage.TraverseAll():
        if not prim.IsA(UsdGeom.Xformable):
            continue
        xform = UsdGeom.Xformable(prim)
        times = set(xform.GetTimeSamples())
        if not xform.GetResetXformStack():
            times.update(result.get(str(prim.GetParent().GetPath()), []))
        if times:
            result[str(prim.GetPath())] = sorted(times)
    return result


def worlds(stage, times=None):
    from pxr import Usd, UsdGeom
    times = transform_times(stage) if times is None else times
    caches = {None: UsdGeom.XformCache(Usd.TimeCode.Default())}
    result = {}
    for prim in stage.TraverseAll():
        if not prim.IsA(UsdGeom.Xformable):
            continue
        path = str(prim.GetPath())
        values = []
        for time in [None, *times.get(path, [])]:
            if time not in caches:
                caches[time] = UsdGeom.XformCache(Usd.TimeCode(time))
            values.extend(float(v) for row in caches[time].GetLocalToWorldTransform(prim) for v in row)
        result[path] = values
    return result


def snapshot(stage):
    from pxr import UsdGeom
    result = {}
    times = transform_times(stage)
    matrices = worlds(stage, times)
    for prim in stage.TraverseAll():
        path = str(prim.GetPath())
        schemas = prim.GetMetadata('apiSchemas')
        row = dict(type=prim.GetTypeName(), schemas=sorted(prim.GetAppliedSchemas()),
                   authoredSchemas=sorted(schemas.ApplyOperations([])) if schemas else [],
                   identity=prim.GetAttribute('aeco:id').Get(),
                   classification={a.GetName(): a.Get() for a in prim.GetAttributes() if a.GetName().startswith('aeco:class:')},
                   relationships={r.GetName(): [str(p) for p in r.GetTargets()] for r in prim.GetRelationships()},
                   world=matrices.get(path), transformTimes=times.get(path, []))
        if prim.IsA(UsdGeom.Mesh):
            row['mesh'] = {name: hashlib.sha256(repr(prim.GetAttribute(name).Get()).encode()).hexdigest()
                           for name in ('points', 'faceVertexCounts', 'faceVertexIndices')}
        result[path] = row
    return result


def validators():
    from pxr import Plug, UsdValidation
    registry = UsdValidation.ValidationRegistry()
    declared = {}
    for plugin in Plug.Registry().GetAllPlugins():
        info = plugin.metadata.get('Validators', {})
        names = [plugin.name + ':' + name for name in info if name not in ('keywords',)]
        if names:
            declared[plugin.name] = sorted(names)
    names = sorted(n for group in declared.values() for n in group)
    loaded = registry.GetOrLoadValidatorsByName(names)
    if not names or len(loaded) != len(names) or not all(loaded):
        raise ValueError('declared validators did not all load')
    return UsdValidation.ValidationContext(loaded), declared


def validation_errors(context, stage):
    results = []
    for error in context.Validate(stage):
        sites = []
        for site in error.GetSites():
            if hasattr(site, 'GetPath'):
                sites.append(str(site.GetPath()))
            elif site.IsPrim():
                sites.append(str(site.GetPrim().GetPath()))
            elif site.IsProperty():
                sites.append(str(site.GetProperty().GetPath()))
            else:
                sites.append('/')
        results.append(dict(rule=error.GetName(), severity=str(error.GetType()).split('.')[-1].lower(), paths=sites))
    return sorted(results, key=lambda r: (r['rule'], r['paths']))


def mute_drill(directory, *, validate=False, progress=None, shard=0, shards=1):
    from pxr import Sdf
    stage = open_stage(directory / FORM_C)
    times = transform_times(stage)
    original = worlds(stage, times)
    context, declared = validators() if validate else (None, {})
    baseline = validation_errors(context, stage) if context else []
    baseline_set = {json.dumps(e, sort_keys=True) for e in baseline if e['severity'] == 'error'}
    layers = [directory / f'packages/{d}/{d}.usda' for d in read(directory / 'manifest.json')['packages']]
    layers += sorted(p for p in (directory / 'analysis').rglob('*') if p.suffix in ('.usda', '.usdc'))
    layers = layers[shard::shards]
    rows = []
    prim_count = len(list(stage.TraverseAll()))
    for path in layers:
        layer = Sdf.Layer.FindOrOpen(str(path))
        if layer not in stage.GetUsedLayers():
            rows.append(dict(layer=str(path.relative_to(directory)), remainingPrims=prim_count,
                             comparedTransforms=len(original), moved=[], compositionErrors=0,
                             newErrors=[], viewOnly=True))
            continue
        relative = str(path.relative_to(directory))
        print('== stage: mute ' + relative, file=sys.stderr, flush=True)
        stage.MuteLayer(layer.identifier)
        if not layer.rootPrims and not layer.subLayerPaths:
            rows.append(dict(layer=relative, remainingPrims=prim_count, comparedTransforms=len(original),
                             moved=[], compositionErrors=len(stage.GetCompositionErrors()), newErrors=[], emptyLayer=True))
            stage.UnmuteLayer(layer.identifier)
            continue
        now = worlds(stage, times)
        moved = [p for p in original.keys() & now.keys()
                 if any(abs(a - b) > 1e-8 for a, b in zip(original[p], now[p]))]
        errors = validation_errors(context, stage) if context else []
        added = [e for e in errors if e['severity'] == 'error' and json.dumps(e, sort_keys=True) not in baseline_set]
        rows.append(dict(layer=relative, remainingPrims=len(list(stage.TraverseAll())),
                         comparedTransforms=len(original.keys() & now.keys()), moved=moved,
                         compositionErrors=len(stage.GetCompositionErrors()), newErrors=added))
        stage.UnmuteLayer(layer.identifier)
        if progress:
            write(progress, dict(rows=rows, complete=False))
    return dict(rows=rows, complete=True, animatedPrims=len(times), transformSamples=sum(map(len, times.values())),
                baseline=[r for r in baseline if r['severity'] == 'error'],
                baselineCounts=dict(Counter(r['severity'] + ':' + r['rule'] for r in baseline)), validators=declared)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['vanilla', 'snapshot', 'mute', 'validate', 'render', 'flatten', 'flat-snapshot'])
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--plugins', action='store_true')
    parser.add_argument('--connected', action='store_true')
    parser.add_argument('--shard', type=int, default=0)
    parser.add_argument('--shards', type=int, default=1)
    args = parser.parse_args()
    if args.mode == 'flatten':
        # Register core's property metadatum before Flatten copies authored data.
        from pxr import Plug
        from usdaeco_suite.stage_common import ROOT
        Plug.Registry().RegisterPlugins(str(ROOT / 'core/usdaeco-core/usdAeco'))
    if args.plugins:
        configure(native_plugins=True)
    elif not args.connected and args.mode != 'flatten':
        clean_plugins()
    from pxr import Plug, Usd, UsdGeom
    directory = args.directory.resolve()
    if args.mode == 'mute':
        data = mute_drill(directory, validate=args.plugins, progress=args.output, shard=args.shard, shards=args.shards)
    else:
        stage = open_stage(directory / (FORM_B if args.mode == 'flat-snapshot' else FORM_A if args.connected else FORM_C))
        if args.mode == 'flatten':
            from usdaeco_suite.stage_flatten import export_flat
            data = export_flat(stage, directory, args.output.with_suffix('.usdc'))
        elif args.mode == 'flat-snapshot':
            from pxr import UsdUtils
            from usdaeco_suite.stage_flatten import metadata
            layer = stage.GetRootLayer()
            if layer.subLayerPaths or any(UsdUtils.ExtractExternalReferences(layer.identifier)):
                raise ValueError('Form B is not self-contained')
            if any(p.GetTypeName().startswith('Aeco') and p.GetPrimTypeInfo().GetSchemaType().isUnknown
                   for p in stage.TraverseAll()):
                raise ValueError('missing effective stock fallback')
            data = dict(snapshot=snapshot(stage), metadata=metadata(stage), plugins=[],
                        usdVersion=list(Usd.GetVersion()), provenance=dict(layer.customLayerData),
                        sublayers=[], externalAssets=[])
            clean_plugins()
        elif args.mode == 'snapshot':
            data = snapshot(stage)
        elif args.mode == 'vanilla':
            if not stage.GetDefaultPrim() or UsdGeom.GetStageMetersPerUnit(stage) != 1 or UsdGeom.GetStageUpAxis(stage) != 'Z':
                raise ValueError('default prim or stage units differ')
            fallbacks = dict(stage.GetMetadata('fallbackPrimTypes'))
            unresolved = sorted({p.GetTypeName() for p in stage.TraverseAll()
                                 if (p.GetTypeName().startswith('Aeco') or p.GetTypeName() == 'BrepArray') and
                                 (p.GetTypeName() not in fallbacks or p.GetPrimTypeInfo().GetSchemaType().isUnknown)})
            if unresolved:
                raise ValueError('missing effective stock fallback: ' + ', '.join(unresolved))
            view_data = {}
            selection = read(directory / 'manifest.json')['views']
            for path in sorted((directory / 'views').glob('*.usda')):
                view = open_stage(path)
                allowed = selection[path.stem]
                for used in view.GetUsedLayers():
                    parts = Path(used.realPath).parts
                    for category, key in [('packages', 'packages'), ('analysis', 'analyses')]:
                        if category in parts and parts[parts.index(category) + 1] not in allowed[key]:
                            raise ValueError('view contains an unselected delivery or analysis: ' + path.stem)
                view_data[path.stem] = dict(census=census(view), packages=allowed['packages'], analyses=allowed['analyses'],
                                           start=view.GetStartTimeCode(), end=view.GetEndTimeCode())
            data = dict(census=census(stage), plugins=[], compositionErrors=0, views=view_data)
            clean_plugins()
        elif args.mode == 'validate':
            context, declared = validators()
            errors = validation_errors(context, stage)
            data = dict(validators=declared, findings=errors,
                        counts=dict(Counter((e['severity'] + ':' + e['rule']) for e in errors)))
        else:
            from pxr import UsdAppUtils, Gf
            # CPU Embree, the same FrameRecorder used by usdrecord.
            camera = UsdGeom.Camera(stage.GetPrimAtPath('/Renders/cctv/overview'))
            recorder = UsdAppUtils.FrameRecorder('Embree', False)
            recorder.SetImageWidth(960)
            recorder.SetIncludedPurposes(['proxy', 'render'])
            recorder.SetColorCorrectionMode('sRGB')
            if not recorder.Record(stage, camera, Usd.TimeCode.Default(), str(args.output)):
                raise ValueError('stock frame recorder failed')
            clean_plugins()
            return
    write(args.output, data)


if __name__ == '__main__':
    main()
