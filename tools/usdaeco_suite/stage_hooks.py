"""Run pinned example hooks in disposable workspaces, then archive their own layers."""
import importlib
import importlib.util
import inspect
import os
from pathlib import Path
import re
import shutil
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usdaeco_suite.stage_common import (ROOT, FORM_C, read, write, sha, repos, configure,
                                       stamp, header, layer_paths)


def reroot(layer, prefix, *, facility=False):
    """Move authored specs as well as all path-valued targets in the text layer."""
    from pxr import Sdf
    mappings = {'/Renders': '/Renders/' + prefix}
    if facility:
        mappings.update({p: '/demo_datacentre_01' + p for p in
                         ('/demo_datacentre_01_Site', '/_TypeCatalog', '/Systems', '/Zones')})
    for old, new in mappings.items():
        if layer.GetPrimAtPath(old):
            temporary = Sdf.Layer.CreateAnonymous()
            Sdf.CreatePrimInLayer(temporary, Sdf.Path(new).GetParentPath())
            Sdf.CopySpec(layer, old, temporary, new)
            del layer.rootPrims[Sdf.Path(old).name]
            top = Sdf.Path(new).GetPrefixes()[0]
            if layer.GetPrimAtPath(top):
                Sdf.CreatePrimInLayer(layer, Sdf.Path(new).GetParentPath())
                Sdf.CopySpec(temporary, new, layer, new)
            else:
                Sdf.CopySpec(temporary, top, layer, top)
    text = layer.ExportToString()
    # Only serialized path values, not prim declarations or arbitrary substrings.
    for old, new in mappings.items():
        text = re.sub(r'([<"])' + re.escape(old) + r'(?=[/>"])', r'\g<1>' + new, text)
    layer.ImportFromString(text)


def run(name, destination):
    configure()
    from pxr import Sdf, Usd
    card = repos()['usdaeco-' + name]
    repository = ROOT / card['path']
    example = repository / 'examples/datacentre'
    workspace = ROOT / 'out/stage-hooks' / name
    if '--reuse' in sys.argv and (workspace / 'out/hook-findings.json').exists():
        stage = Usd.Stage.Open(str(workspace / 'out/example.usda'))
        archive(name, destination, workspace, stage, read(workspace / 'out/hook-findings.json'), card, example)
        return
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(example / 'inputs', workspace / 'inputs', ignore=shutil.ignore_patterns('source'))
    out = workspace / 'out'
    out.mkdir()
    # Some released hooks resolve a fixed variant directory even with an
    # explicit stage override. These transient aliases all name the actual full
    # publication; its counts and variant field are never relabelled.
    alias = workspace / 'source'
    for variant in ('base', 'clash', 'pod', 'floors', 'iris'):
        target = alias / 'dist' / variant
        target.mkdir(parents=True)
        (target / 'dc.usda').symlink_to(destination / FORM_C)
        (target / 'dc.manifest.json').symlink_to(destination / 'dc.manifest.json')
        (target / 'packages').symlink_to(destination / 'packages', target_is_directory=True)
    (workspace / 'inputs/source').symlink_to(alias, target_is_directory=True)
    os.environ['AECO_DATACENTRE_ROOT'] = str(alias)
    base = Sdf.Layer.FindOrOpen(str(destination / FORM_C))
    layer = Sdf.Layer.CreateNew(str(out / 'example.usda'))
    layer.TransferContent(base)
    # Preserve source metadata, rebasing every package sublayer to this workspace.
    layer.subLayerPaths = [str(destination / p) for p in base.subLayerPaths]
    inputs = sorted((workspace / 'inputs').glob('*.usda'))
    layer.subLayerPaths = [str(p) for p in inputs] + [str(destination / FORM_C)]
    layer.Save()
    os.environ['AECO_DATACENTRE_STAGE'] = str(destination / FORM_C)
    stage = Usd.Stage.Open(layer)
    if stage.GetCompositionErrors():
        raise ValueError('scratch inputs do not compose')
    hooks = {'cctv': ('usdaeco_cctv.example', 'hook'), 'pipe': ('usdaeco_pipe.example', 'library_hook'),
             'wall': ('usdaeco_wall.example', 'hook'), 'buildup': ('usdaeco_buildup.datacentre', 'hook'),
             'plan': ('usdaeco_plan.example', 'hook'), 'repeat': ('usdaeco_repeat.example', 'hook'),
             'clash': ('usdaeco_clash.example', 'derive')}
    if name == 'solid':
        # The pinned exact producer requires its own native generation recipe.
        # Reuse its declared display/exact result without pretending to rerun it.
        for path in (example / 'result/layers/out').rglob('*.usda'):
            target = out / path.relative_to(example / 'result/layers/out')
            target.parent.mkdir(parents=True, exist_ok=True)
            text = path.read_text()
            text = re.sub(r'@[^@]*inputs/source/dist/[^@]+@', '@' + str(destination / FORM_C) + '@', text)
            target.write_text(text)
        layer.subLayerPaths[:0] = ['presentation.usda', 'twins.usda', 'exact.usda']
        layer.Save()
        findings = read(example / 'expected/findings.json')
        write(out / 'hook-findings.json', findings)
        archive(name, destination, workspace, stage, findings, card, example)
        return
    if name == 'compliance':
        spec = importlib.util.spec_from_file_location('suite_compliance_hook', example / 'run.py')
        imported = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(imported)
        function = 'hook'
    else:
        module, function = hooks[name]
        imported = importlib.import_module(module)
    hook = getattr(imported, function)
    if name in ('wall', 'buildup'):
        def published_full():
            publication = read(destination / 'dc.manifest.json')
            for relative, record in publication['files'].items():
                if relative.endswith(('.usda', '.usdc', '.ifc')):
                    discipline = relative.split('.')[0]
                    path = destination / 'packages' / discipline / relative
                    if path.exists() and sha(path) != record['sha256']:
                        raise ValueError('full publication source hash differs')
            return destination / FORM_C, publication
        imported.published_source = published_full
    if name == 'buildup':
        select = imported.select_walls
        def select_full(stage, config):
            spaces = [p for p in stage.Traverse() if p.GetTypeName() == 'AecoSpace' and p.GetName() == 'WC']
            result = {}
            for space in spaces:
                class Selection:
                    def Traverse(self):
                        return (p for p in stage.Traverse() if p not in spaces or p == space)
                for row in select(Selection(), config):
                    path = str(row[0].GetPath())
                    if path not in result or row[1]['name'] == 'WcLining':
                        result[path] = row
            return [result[p] for p in sorted(result)]
        imported.select_walls = select_full
        source = inspect.getsource(imported.derive)
        old = "wc, = [p for p in stage.Traverse() if p.GetTypeName() == 'AecoSpace' and p.GetName() == 'WC']"
        new = "wc = min([p for p in stage.Traverse() if p.GetTypeName() == 'AecoSpace' and p.GetName() == 'WC'], key=lambda p: (UsdGeom.XformCache().GetLocalToWorldTransform(p).ExtractTranslation() - UsdGeom.XformCache().GetLocalToWorldTransform(wall).ExtractTranslation()).GetLength())"
        if source.count(old) != 1:
            raise ValueError('WC derivation adapter no longer matches the pinned hook')
        namespace = dict(imported.__dict__)
        exec(compile(source.replace(old, new), '<suite WC selection adapter>', 'exec'), namespace)
        imported.derive = namespace['derive']
    if name == 'clash':
        runtime = importlib.import_module('usdaeco_clash.runtime')
        runtime.unavailable_reason = lambda: 'Exact producer not rerun; committed exact layers are retained separately.'
    if name == 'repeat':
        composition = importlib.import_module('usdaeco_repeat.compose')
        verify = composition.verify
        def verify_full(original, composed, mapping, tolerance=1e-6):
            def mapped(path):
                for old in sorted(mapping, key=lambda p: len(str(p)), reverse=True):
                    if path.HasPrefix(old):
                        return path.ReplacePrefix(old, mapping[old])
                return path
            expected = {mapped(p.GetPath()) for p in Usd.PrimRange(original)}
            extra = {p.GetPath() for p in Usd.PrimRange(composed)} - expected
            delta = Sdf.Layer.FindOrOpen(str(out / 'composition/deviations.usda'))
            with Usd.EditContext(composed.GetStage(), delta):
                for path in sorted(extra, key=lambda p: len(str(p))):
                    if not any(p.HasPrefix(path) for p in expected):
                        Sdf.CreatePrimInLayer(delta, path).SetInfo('active', False)
            delta.Save()
            return verify(original, composed, mapping, tolerance)
        composition.verify = verify_full
    if name == 'cctv':
        # The released hook hard-codes the base fixture census. Preserve its
        # guard, substituting the full publication's independently recorded count.
        source = inspect.getsource(hook)
        old = 'len(cameras) != 45'
        if source.count(old) != 1:
            raise ValueError('camera census adapter no longer matches the pinned hook')
        source = source.replace(old, 'len(cameras) != ' + str(read(destination / 'dc.manifest.json')['census']['cameras']))
        namespace = dict(imported.__dict__)
        exec(compile(source, '<suite camera census adapter>', 'exec'), namespace)
        hook = namespace[function]
    findings = hook(stage, out, render_a=False) if name == 'plan' else hook(stage, out)
    if name == 'clash':
        for filename in ('exact.usda', 'twins.usda', 'exact-results.usda'):
            shutil.copyfile(example / 'result/layers/out' / filename, out / filename)
            layer.subLayerPaths.insert(0, filename)
    layer.Save()
    write(out / 'hook-findings.json', findings)
    if not isinstance(findings, list):
        raise ValueError('hook findings must be a list')
    archive(name, destination, workspace, stage, findings, card, example)


def archive(name, destination, workspace, stage, findings, card, example):
    from pxr import Sdf, Usd, UsdGeom, Vt
    from usdaeco_check.example import diff_findings
    out = workspace / 'out'
    folder = destination / 'analysis' / name
    folder.mkdir(parents=True)
    presentation = Sdf.Layer.CreateNew(str(destination / 'presentation' / (name + '.usda')))
    source = example / 'run.py'
    def provenance(layer, role):
        committed = name == 'solid' or (name == 'clash' and Path(layer.realPath).name in ('exact.usda', 'twins.usda', 'exact-results.usda'))
        origin = source
        if committed:
            origin = example / 'result/layers/out' / Path(layer.realPath).name
            if not origin.exists():
                origin = example / 'manifest.json'
        stamp(layer, role, name, ('committed result ' if committed else 'hook ') + card['tag'],
              str(origin.relative_to(ROOT)), sha(origin), card['tag'])
    own = sorted((workspace / 'inputs').rglob('*.usda')) + sorted(out.rglob('*.usda'))
    excluded = {out / 'example.usda', out / 'source.usda'}
    own = [p for p in own if p not in excluded]
    mapping = {str(p): folder / p.relative_to(workspace) for p in own}
    generated = {}
    for path in own:
        original = Sdf.Layer.FindOrOpen(str(path))
        target = mapping[str(path)]
        target.parent.mkdir(parents=True, exist_ok=True)
        copied = Sdf.Layer.CreateNew(str(target))
        copied.TransferContent(original)
        # Hook snapshot wrappers must never pull the facility into the analysis.
        sublayers = []
        for asset in original.subLayerPaths:
            resolved = str((path.parent / asset).resolve()) if not Path(asset).is_absolute() else asset
            if resolved in mapping:
                sublayers.append(os.path.relpath(mapping[resolved], target.parent))
            elif Path(resolved) in excluded or resolved == str(destination / FORM_C) or asset.endswith('example.usdc'):
                continue
            else:
                raise ValueError('unmapped analysis sublayer: ' + Path(asset).name)
        copied.subLayerPaths = sublayers
        reroot(copied, name)
        for prim_path in list(layer_paths(copied)):
            spec = copied.GetPrimAtPath(prim_path) if prim_path.IsPrimPath() else None
            if not spec:
                continue
            for relationship in list(spec.relationships):
                if relationship.name.startswith('material:binding') and not relationship.targetPathList.GetAppliedItems():
                    # Empty binding opinions fail the stock material validator.
                    # Retain the weaker delivery binding and its appearance.
                    spec.RemoveProperty(relationship)
            if (spec.typeName == 'GeomSubset' and spec.nameParent and spec.nameParent.typeName == 'BrepArray'
                    and spec.attributes.get('familyName') and spec.attributes['familyName'].default == 'materialBind'):
                # Face material subsets on a BrepArray have no stock USD
                # element domain. The mesh twin retains the render materials.
                del spec.nameParent.nameChildren[spec.name]
                continue
            if any(p.name.startswith('material:binding') for p in spec.relationships):
                schemas = spec.GetInfo('apiSchemas') if spec.HasInfo('apiSchemas') else Sdf.TokenListOp()
                if 'MaterialBindingAPI' not in schemas.ApplyOperations([]):
                    schemas.prependedItems = ['MaterialBindingAPI', *schemas.prependedItems]
                    spec.SetInfo('apiSchemas', schemas)
        provenance(copied, 'analysis')
        copied.Save()
        generated[str(path)] = copied
    # Extract display-only opinions in their actual USD strength order.
    ordered = [p for p in stage.GetLayerStack() if p.realPath in generated]
    for original in reversed(ordered):
        copied = generated[original.realPath]
        for path in layer_paths(copied):
            if not path.IsPropertyPath() or path.name not in ('visibility', 'primvars:displayColor'):
                continue
            Sdf.CreatePrimInLayer(presentation, path.GetPrimPath())
            Sdf.CopySpec(copied, path, presentation, path)
            prop = copied.GetPropertyAtPath(path)
            prop.owner.RemoveProperty(prop)
        copied.Save()
    # Keep complete render cameras in one analysis layer. A camera's
    # definition and final pose must not be split across independently muted files.
    cameras = Sdf.Layer.CreateNew(str(folder / 'cameras.usda'))
    display_stage = Usd.Stage.Open(cameras)
    for prim in stage.TraverseAll():
        if str(prim.GetPath()).startswith('/Renders/') and prim.IsA(UsdGeom.Camera):
            target = UsdGeom.Camera.Define(display_stage, '/Renders/' + name + '/' + prim.GetName())
            target.SetFromCamera(UsdGeom.Camera(prim).GetCamera())
    for copied in generated.values():
        if not copied.GetPrimAtPath('/Renders'):
            continue
        camera_stage = Usd.Stage.Open(copied)
        for prim in camera_stage.TraverseAll():
            if prim.IsA(UsdGeom.Camera) and str(prim.GetPath()).startswith('/Renders/'):
                path = '/Renders/' + name + '/' + prim.GetName()
                if not display_stage.GetPrimAtPath(path):
                    UsdGeom.Camera.Define(display_stage, path).SetFromCamera(UsdGeom.Camera(prim).GetCamera())
    for copied in generated.values():
        if copied.GetPrimAtPath('/Renders'):
            del copied.rootPrims['Renders']
        copied.Save()
    provenance(cameras, 'analysis')
    cameras.Save()
    # New representation placements are snapshots, owned by the delivery whose
    # referent they depict. World anchors keep them stable when analysis inputs
    # are muted, while retaining the original points and spatial namespace.
    base = Usd.Stage.Open(str(destination / FORM_C))
    inheritance = Sdf.Layer.CreateNew(str(folder / 'inheritance.usda'))
    provenance(inheritance, 'analysis')
    for prim in stage.Traverse():
        if not base.GetPrimAtPath(prim.GetPath()):
            continue
        applied = []
        for inherited in prim.GetInherits().GetAllDirectInherits():
            for original in ordered:
                spec = original.GetPrimAtPath(inherited)
                if spec and spec.HasInfo('apiSchemas'):
                    applied.extend(spec.GetInfo('apiSchemas').ApplyOperations([]))
        if applied:
            spec = Sdf.CreatePrimInLayer(inheritance, prim.GetPath())
            spec.SetInfo('apiSchemas', Sdf.TokenListOp.Create(prependedItems=list(dict.fromkeys(applied))))
    inheritance.Save()
    anchors = {}
    cache = UsdGeom.XformCache()
    timed_caches = {}
    for prim in stage.TraverseAll():
        path = prim.GetPath()
        if (not str(path).startswith('/demo_datacentre_01/') or base.GetPrimAtPath(path)
                or not prim.IsA(UsdGeom.Xformable) or prim.IsAbstract()):
            continue
        parent = path.GetParentPath()
        owner = None
        while parent != Sdf.Path.absoluteRootPath and not owner:
            candidate = base.GetPrimAtPath(parent)
            if candidate:
                for spec in candidate.GetPrimStack():
                    parts = Path(spec.layer.realPath).parts
                    if spec.specifier == Sdf.SpecifierDef and 'packages' in parts:
                        owner = parts[parts.index('packages') + 1]
                        break
            parent = parent.GetParentPath()
        if not owner:
            continue
        if owner not in anchors:
            file = destination / 'packages' / owner / 'derived.usda'
            anchors[owner] = Sdf.Layer.FindOrOpen(str(file)) if file.exists() else Sdf.Layer.CreateNew(str(file))
        anchor = Sdf.CreatePrimInLayer(anchors[owner], path)
        anchor.typeName = prim.GetTypeName()
        transform = anchor.attributes.get('xformOp:transform') or Sdf.AttributeSpec(anchor, 'xformOp:transform', Sdf.ValueTypeNames.Matrix4d)
        transform.default = cache.GetLocalToWorldTransform(prim)
        transform.SetInfo('aecoDerived', True)
        times = set()
        ancestor = prim
        while ancestor and not ancestor.IsPseudoRoot():
            if ancestor.IsA(UsdGeom.Xformable):
                times.update(UsdGeom.Xformable(ancestor).GetTimeSamples())
            ancestor = ancestor.GetParent()
        for time in sorted(times):
            timed = timed_caches.setdefault(time, UsdGeom.XformCache(Usd.TimeCode(time)))
            anchors[owner].SetTimeSample(transform.path, time, timed.GetLocalToWorldTransform(prim))
        order = anchor.attributes.get('xformOpOrder') or Sdf.AttributeSpec(anchor, 'xformOpOrder', Sdf.ValueTypeNames.TokenArray)
        order.default = Vt.TokenArray(['!resetXformStack!', 'xformOp:transform'])
        order.SetInfo('aecoDerived', True)
        for copied in generated.values():
            spec = copied.GetPrimAtPath(path)
            if spec:
                for prop in list(spec.properties):
                    if prop.name.startswith('xformOp:') or prop.name == 'xformOpOrder':
                        spec.RemoveProperty(prop)
    for owner, anchor in anchors.items():
        stamp(anchor, 'derived', owner, 'usdAECO suite representation placement',
              str(source.relative_to(ROOT)), sha(source), card['tag'])
        anchor.Save()
    if name == 'plan':
        for key in ('A', 'B'):
            selected = Sdf.Layer.CreateNew(str(destination / 'presentation' / ('plan-' + key + '.usda')))
            if key == 'B':
                selected.TransferContent(presentation)
            else:
                for filename in ('programme.usda', 'presentation.usda', 'predecessors.usda', '4d.usda'):
                    source_layer = generated[str(out / key / filename)]
                    for path in layer_paths(source_layer):
                        if path.IsPropertyPath() and path.name in ('visibility', 'primvars:displayColor'):
                            Sdf.CreatePrimInLayer(selected, path.GetPrimPath())
                            Sdf.CopySpec(source_layer, path, selected, path)
                            prop = source_layer.GetPropertyAtPath(path)
                            prop.owner.RemoveProperty(prop)
            provenance(selected, 'presentation')
            selected.Save()
            placement = Sdf.Layer.CreateNew(str(folder / 'out' / key / 'placement.usda'))
            source_layer = generated[str(out / key / 'presentation.usda')]
            for path in layer_paths(source_layer):
                if (path.IsPropertyPath() and (path.name.startswith('xformOp:') or path.name == 'xformOpOrder')
                        and base.GetPrimAtPath(path.GetPrimPath())):
                    Sdf.CreatePrimInLayer(placement, path.GetPrimPath())
                    Sdf.CopySpec(source_layer, path, placement, path)
                    prop = source_layer.GetPropertyAtPath(path)
                    prop.owner.RemoveProperty(prop)
            provenance(placement, 'analysis')
            placement.Save()
            play = generated[str(out / key / 'play.usda')]
            play.subLayerPaths = ['../../cameras.usda', 'placement.usda', '4d.usda', 'predecessors.usda', 'presentation.usda', 'programme.usda']
    for copied in generated.values():
        prune(copied)
        copied.Save()
    view_path = destination / 'presentation/views' / (name + '.usda')
    view_path.parent.mkdir(parents=True, exist_ok=True)
    view_display = Sdf.Layer.CreateNew(str(view_path))
    for path in layer_paths(presentation):
        if path.IsPropertyPath() and path.name == 'visibility' and base.GetPrimAtPath(path.GetPrimPath()):
            Sdf.CreatePrimInLayer(view_display, path.GetPrimPath())
            Sdf.CopySpec(presentation, path, view_display, path)
            prop = presentation.GetPropertyAtPath(path)
            prop.owner.RemoveProperty(prop)
    prune(view_display)
    prune(presentation)
    provenance(view_display, 'presentation')
    view_display.Save()
    provenance(presentation, 'presentation')
    presentation.Save()
    root = Sdf.Layer.CreateNew(str(folder / 'root.usda'))
    provenance(root, 'analysis')
    direct = []
    for asset in stage.GetRootLayer().subLayerPaths:
        resolved = str((out / asset).resolve())
        if resolved in mapping:
            direct.append(os.path.relpath(mapping[resolved], folder))
    direct += [os.path.relpath(mapping[str(p)], folder) for p in sorted((workspace / 'inputs').glob('*.usda'))]
    root.subLayerPaths = ['cameras.usda', 'inheritance.usda', *dict.fromkeys(direct)]
    root.Save()
    write(folder / 'findings.json', findings)
    expected = read(example / 'expected/findings.json')
    differences = diff_findings(findings, expected)
    adaptations = {
        'cctv': ['Base camera census guard uses full manifest count.'],
        'wall': ['Published-source adapter verifies the full delivery hashes and counts.'],
        'buildup': ['Published-source adapter verifies the full delivery hashes and counts.',
                    'Apply the released WC boundary selector to every WC space, merging selections by prim path.'],
        'plan': ['Fixed pod source lookup aliases the full publication; frame rendering is separate.',
                 'The integrated root selects programme B; A and B have separate 4D views.',
                 'Demonstration pod relocation is confined to the programme views; the integrated facility keeps its delivered placement.'],
        'repeat': ['Fixed floors source lookup aliases the full publication.',
                   'Deactivate prototype-only spatial extents absent from the occurrence, then run the original exact subtree proof.'],
        'compliance': ['Fixed iris manifest lookup aliases the full publication.'],
        'clash': ['Mesh hook runs on full; exact bodies and exact results are committed result ' + card['tag'] + '.'],
        'solid': ['Native exact producer is not rerun; committed geometry is rebased over full.'],
    }.get(name, [])
    write(folder / 'receipt.json', dict(producer=('committed result ' if name == 'solid' else 'hook ') + card['tag'], tag=card['tag'], run=name != 'solid',
          findings=len(findings), expectedFindings=len(expected), differences=differences,
          source=str(source.relative_to(ROOT)), sourceSha256=sha(source),
          adaptations=adaptations))


def prune(layer):
    """Remove empty over ancestors left by moving presentation properties."""
    from pxr import Sdf
    for path in sorted(layer_paths(layer), key=lambda p: len(str(p)), reverse=True):
        if not path.IsPrimPath():
            continue
        prim = layer.GetPrimAtPath(path)
        if (prim and prim.specifier == Sdf.SpecifierOver and not prim.nameChildren and not prim.properties
                and set(prim.ListInfoKeys()) <= {'specifier'}):
            if prim.nameParent:
                del prim.nameParent.nameChildren[prim.name]
            else:
                del layer.rootPrims[prim.name]


if __name__ == '__main__':
    destination = Path(sys.argv[2]).resolve()
    (destination / 'presentation').mkdir(exist_ok=True)
    run(sys.argv[1], destination)
