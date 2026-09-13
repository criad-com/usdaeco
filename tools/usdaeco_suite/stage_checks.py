"""Small, independently testable checks for the integrated publication."""
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
from usdaeco_suite.stage_common import ROOT, read, sha, layer_paths

STAGE_CAP = 80_000_000

# These diagnostics describe persisted analyses whose inputs were muted. They
# remain errors and are a recorded deviation from the port-only requirement.
MUTE_DEPENDENCIES = {
    'ClashResultWithoutElements': 'Clash result lost a referenced element.',
    'ComplianceStale': 'Composed compliance inputs changed.',
    'MissingBinding': 'A compliance measurement lost its binding target.',
    'MissingDevice': 'A specification lost its applicable devices.',
    'QuantityStale': 'Quantity inputs changed.',
    'RequirementUnmeasurable': 'A requirement lost a measurable dependency.',
    'WallMissingAxis': 'Wall promotion survived removal of its axis.',
    'PipeMissingAxis': 'Pipe promotion survived removal of its axis.',
    'ProxyTwinMissing': 'Exact geometry survived removal of its proxy twin.',
    'TwinStale': 'Exact or twin inputs changed.',
    'RepeatDrift': 'A repeated occurrence lost part of its comparison inputs.',
    'cctvSensorMissing': 'A camera API survived removal of its sensor definition or sensor link.',
}


def digest(directory):
    """Hash the complete USD/IFC input tree and suite pins, independent of location."""
    rows = [(str(p.relative_to(directory)), sha(p)) for p in sorted(directory.rglob('*'))
            if p.is_file() and p.suffix in ('.usda', '.usdc', '.ifc')]
    rows.append(('suite.json', sha(ROOT / 'suite.json')))
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()


def inventory_errors(directory, manifest):
    from pxr import Sdf
    actual = {str(p.relative_to(directory)): p for p in directory.rglob('*')
              if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts}
    errors = ['inventory: ' + p for p in sorted(actual.keys() ^ manifest['files'].keys())]
    for name, path in actual.items():
        record = manifest['files'].get(name)
        if record is None:
            continue
        if record['sha256'] != sha(path) or record['bytes'] != path.stat().st_size:
            errors.append('file changed: ' + name)
        if path.suffix in ('.usda', '.usdc'):
            layer = Sdf.Layer.FindOrOpen(str(path))
            metadata = layer.customLayerData
            for key in ('role', 'package', 'producer', 'source', 'sourceSha256', 'tag'):
                if not metadata.get('aeco:layer:' + key) or record.get(key) != metadata['aeco:layer:' + key]:
                    errors.append('provenance ' + key + ': ' + name)
            source = metadata.get('aeco:layer:source', '')
            origin = ROOT / source if (ROOT / source).is_file() else path.parent / source
            source_matches = origin.is_file() and sha(origin) == metadata.get('aeco:layer:sourceSha256')
            if record.get('sourceStampMatches') != source_matches:
                errors.append('source provenance census: ' + name)
            if not source_matches and name not in manifest.get('copied', {}):
                errors.append('authored source provenance hash: ' + name)
            if record['primSpecs'] != sum(p.IsPrimPath() for p in layer_paths(layer)):
                errors.append('spec census: ' + name)
        copied = manifest.get('copied', {}).get(name)
        if copied and (sha(path) != copied['sourceSha256'] or sha(ROOT / copied['source']) != copied['sourceSha256']):
            errors.append('copy differs: ' + name)
    return errors, sum(p.stat().st_size for p in actual.values()) + (directory / 'manifest.json').stat().st_size


def expected_errors(manifest):
    """Declared illustrative failures, derived from the recorded analysis findings."""
    integration = manifest.get('integration', {})
    counts = Counter()
    for study in integration.get('repeat', []):
        counts['RepeatDrift'] += sum(not c['declared'] for c in study['changes'])
    for finding in integration.get('compliance', {}).get('findings', []):
        if finding.get('severity') == 'error' and finding['kind'] == 'misplacedDevice':
            counts['MisplacedDevice'] += 1
    return +counts


def compare_errors(findings, expected):
    actual = Counter(r['rule'] for r in findings if r['severity'] == 'error')
    return actual == expected, dict(actual)


def finding_records(manifest):
    libraries = {'MisplacedDevice': 'compliance', 'RepeatDrift': 'repeat'}
    return [dict(rule=rule, count=count, library='usdaeco-' + libraries[rule],
                 source='analysis/' + libraries[rule] + '/integrated-findings.json')
            for rule, count in sorted(expected_errors(manifest).items())]


def summarize_validation(data, manifest, directory=None):
    valid, errors = compare_errors(data['findings'], expected_errors(manifest))
    valid = valid and manifest.get('expectedFindings') == finding_records(manifest)
    if directory is not None:
        own_findings = {name: read(directory / f'analysis/{name}/integrated-findings.json')
                        for name in ('repeat', 'compliance') if name in manifest['analyses']}
        valid = valid and expected_errors(dict(integration=own_findings)) == expected_errors(manifest)
    summary = {k: v for k, v in data.items() if k != 'findings'}
    summary.update(errors=[r for r in data['findings'] if r['severity'] == 'error'],
                   rawErrorCount=sum(errors.values()), zeroErrors=not errors,
                   expectedFindings=manifest.get('expectedFindings', []),
                   unexpectedErrorCount=sum((Counter(errors) - expected_errors(manifest)).values()),
                   findingsMatch=bool(valid))
    return summary, valid


def tidy_stage(stage, analyses):
    """Check all roots, including classes and inactive prims hidden by traversal."""
    from pxr import Sdf
    errors = []
    project = stage.GetDefaultPrim().GetPath()
    if project != Sdf.Path('/demo_datacentre_01'):
        errors.append('default project prim differs')
    roots = sorted(str(p.GetPath()) for p in stage.GetPseudoRoot().GetAllChildren())
    if set(roots) != {str(project), '/Renders', '/Studies'}:
        errors.append('stage root prims differ')
    catalog = project.AppendChild('_TypeCatalog')
    catalogs = sorted(str(p.GetPath()) for p in stage.TraverseAll() if p.GetName() == '_TypeCatalog')
    if catalogs != [str(catalog)] or stage.GetPrimAtPath('/_TypeCatalog'):
        errors.append('stage must contain only the project catalog')
    studies = stage.GetPrimAtPath('/Studies')
    if not studies or studies.GetTypeName() != 'Scope':
        errors.append('Studies must be a plain Scope')
    if studies and {p.GetName() for p in studies.GetAllChildren()} != set(analyses):
        errors.append('study libraries differ')
    return dict(rootPrims=roots, catalogs=catalogs, studiesType=studies.GetTypeName() if studies else '', errors=errors)


def analysis_namespace_errors(layer, library, project):
    """Inspect every spec and path opinion, including unused layers and metadata."""
    from pxr import Sdf
    study = Sdf.Path('/Studies/' + library)
    renders = Sdf.Path('/Renders/' + library)
    project = Sdf.Path(project)
    errors = []

    def allowed(path):
        return (path.HasPrefix(project) or path.HasPrefix(study) or path.HasPrefix(renders)
                or path in (Sdf.Path('/Studies'), Sdf.Path('/Renders')))

    def inspect(value):
        if isinstance(value, dict):
            for item in value.values():
                inspect(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                inspect(item)
        elif isinstance(value, Sdf.Reference):
            if not value.assetPath:
                inspect(value.primPath)
        elif isinstance(value, Sdf.Payload):
            if not value.assetPath:
                inspect(value.primPath)
        elif isinstance(value, Sdf.Path):
            if value.IsAbsolutePath() and not allowed(value):
                errors.append('outside study path opinion: ' + str(value))
        elif isinstance(value, str) and value.startswith('/') and Sdf.Path.IsValidPathString(value):
            inspect(Sdf.Path(value))

    inspect(layer.customLayerData)
    for path in layer_paths(layer):
        if path == Sdf.Path.absoluteRootPath:
            continue
        if not allowed(path.GetPrimPath()):
            errors.append('outside study spec: ' + str(path))
        spec = layer.GetObjectAtPath(path)
        if spec is None:
            continue
        if (path.IsPrimPath() and spec.typeName == 'Camera' and not path.HasPrefix(project)
                and (not path.HasPrefix(renders) or path.pathElementCount != 3)):
            errors.append('render camera outside library camera namespace: ' + str(path))
        for key in spec.ListInfoKeys():
            value = spec.GetInfo(key)
            if hasattr(value, 'GetAppliedItems'):
                # Deleted and ordered paths also carry namespace opinions.
                for field in ('explicitItems', 'addedItems', 'prependedItems', 'appendedItems', 'deletedItems', 'orderedItems'):
                    inspect(list(getattr(value, field)))
            else:
                inspect(value)
    return sorted(set(errors))


def layout_errors(directory, manifest):
    from pxr import Sdf, Usd, UsdGeom
    from usdaeco_suite.stage_common import FORM_C
    from usdaeco_suite.traverse import rows
    errors = []
    sizes = {}
    for folder in sorted((directory / 'analysis').iterdir()):
        sizes[folder.name] = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        if sizes[folder.name] > 10_000_000:
            errors.append('analysis size: ' + folder.name)
        for path in folder.rglob('*.usda'):
            if path.stat().st_size > 2_000_000:
                errors.append('text layer size: ' + str(path.relative_to(directory)))
    for path in directory.rglob('*.usda'):
        for asset in re.findall(r'@([^@]+)@', path.read_text()):
            filename, _ = Sdf.Layer.SplitIdentifier(asset)
            if Path(filename).is_absolute() or not (path.parent / filename).is_file():
                errors.append('nonportable or missing asset: ' + str(path.relative_to(directory)) + ': ' + asset)
    for path in (directory / 'presentation').rglob('*.usda'):
        layer = Sdf.Layer.FindOrOpen(str(path))
        for spec_path in layer_paths(layer):
            if spec_path.IsPropertyPath() and spec_path.name not in ('visibility', 'primvars:displayColor'):
                errors.append('non-display presentation property: ' + str(path.relative_to(directory)))
            if spec_path.IsPrimPath():
                spec = layer.GetPrimAtPath(spec_path)
                if spec.specifier != Sdf.SpecifierOver or spec.typeName:
                    errors.append('presentation owns a definition: ' + str(path.relative_to(directory)))
    stage = Usd.Stage.Open(str(directory / FORM_C))
    tidy = tidy_stage(stage, manifest['analyses'])
    errors.extend(tidy['errors'])
    project = stage.GetDefaultPrim().GetPath()
    for name in manifest['analyses']:
        expected = '/Studies/' + name
        if manifest.get('layout', {}).get('studies', {}).get(name) != expected or manifest['analyses'][name].get('studyRoot') != expected:
            errors.append('manifest study root differs: ' + name)
        for path in (directory / 'analysis' / name).rglob('*'):
            if path.suffix not in ('.usda', '.usdc'):
                continue
            layer = Sdf.Layer.FindOrOpen(str(path))
            errors.extend(str(path.relative_to(directory)) + ': ' + error
                          for error in analysis_namespace_errors(layer, name, project))
        presentation_paths = [directory / 'presentation' / (name + '.usda'),
                              directory / 'presentation/views' / (name + '.usda')]
        if name == 'plan':
            presentation_paths += [directory / 'presentation' / ('plan-' + key + '.usda') for key in ('A', 'B')]
        for path in presentation_paths:
            errors.extend(str(path.relative_to(directory)) + ': ' + error
                          for error in analysis_namespace_errors(Sdf.Layer.FindOrOpen(str(path)), name, project))
    counts = Counter(row['owner'].removeprefix('packages/') for row in rows(stage) if row['element'])
    for package, count in manifest['packages'].items():
        if counts[package] != count['elements']:
            errors.append('delivering element census: ' + package)
    cameras = []
    for prim in stage.TraverseAll():
        if prim.IsA(UsdGeom.Camera) and str(prim.GetPath()).startswith('/Renders/'):
            parts = str(prim.GetPath()).split('/')
            cameras.append(str(prim.GetPath()))
            if len(parts) != 4 or parts[2] not in manifest['analyses']:
                errors.append('render camera namespace: ' + str(prim.GetPath()))
    return dict(errors=sorted(set(errors)), analysisBytes=sizes, elementsByPackage=dict(counts), cameras=cameras,
                rootPrims=tidy['rootPrims'], catalogs=tidy['catalogs'], studiesType=tidy['studiesType'],
                studies={name: '/Studies/' + name for name in manifest['analyses']})


def summarize_mutes(data, manifest):
    rows = []
    valid = data.get('complete', False)
    for raw in data['rows']:
        row = {k: v for k, v in raw.items() if k != 'newErrors'}
        package = raw['layer'].split('/')[1] if raw['layer'].startswith('packages/') else None
        predicted = {link['source'] for link in manifest['crossPackageLinks']
                     if link['targetPackage'] == package and link['relationship'] == 'aeco:connectedPorts'}
        ports = {path for finding in raw['newErrors'] if finding['rule'] == 'danglingPortLink' for path in finding['paths']}
        unknown = [r for r in raw['newErrors'] if r['rule'] not in MUTE_DEPENDENCIES and r['rule'] != 'danglingPortLink']
        dependencies = Counter(r['rule'] for r in raw['newErrors'] if r['rule'] in MUTE_DEPENDENCIES)
        row.update(predictedPortErrors=len(predicted), observedPortErrors=len(ports),
                   portPredictionDifferences=sorted(predicted ^ ports), dependencyErrors=dict(dependencies),
                   dependencyErrorCount=sum(dependencies.values()), unexpectedErrors=unknown,
                   newDiagnosticSha256=hashlib.sha256(json.dumps(raw['newErrors'], sort_keys=True).encode()).hexdigest())
        if row['moved'] or row['compositionErrors'] or row['portPredictionDifferences'] or unknown:
            valid = False
        rows.append(row)
    summary = {k: v for k, v in data.items() if k not in ('rows', 'baseline')}
    summary.update(rows=rows, dependencyRules=MUTE_DEPENDENCIES,
                   portOnlyRequirementMet=not any(r['dependencyErrorCount'] for r in rows),
                   diagnosticIdentity='rule, severity and site paths; existing baseline sites are excluded')
    return summary, valid
