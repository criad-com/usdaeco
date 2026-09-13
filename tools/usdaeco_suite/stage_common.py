"""Portable source configuration and stage provenance shared by the suite tools."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
FORM_C = 'demo-datacentre-01.usd-only.usda'
FORM_A = 'demo-datacentre-01.usda'
DISCIPLINES = ('site', 'arch', 'structure', 'cooling', 'electrical', 'it', 'fitout', 'security', 'shared')


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repos():
    return {p['name']: p for p in read(ROOT / 'suite.json')['repos']}


def configure(*, plugins=True, native_plugins=False):
    """Source imports only; resources are registered before creating a USD stage."""
    cards = repos()
    for card in cards.values():
        path = ROOT / card['path']
        sys.path[:0] = [str(path / 'tools'), str(path)]
    environment = {
        'AECO_CORE_ROOT': 'core/usdaeco-core', 'CORE_PLUGIN_DIR': 'core/usdaeco-core/usdAeco',
        'AECO_AXIS_ROOT': 'section/usdaeco-axis', 'AXIS_PLUGIN_DIR': 'section/usdaeco-axis/usdAecoAxis',
        'AECO_BUILDUP_ROOT': 'section/usdaeco-buildup', 'BUILDUP_PLUGIN_DIR': 'section/usdaeco-buildup/usdAecoBuildUp',
        'AECO_SYNC_ROOT': 'record/usdaeco-sync', 'AECO_DATACENTRE_ROOT': 'data/usdaeco-datacentre',
        'TOOLCHAIN_DIR': 'kits/usdaeco-toolchain', 'AECO_IFC_ROOT': 'hosts/usdaeco-ifc',
        'AECO_CCTV_ROOT': 'kind/usdaeco-cctv', 'CCTV_EXEC_ROOT': 'kits/usdaeco-cctv-exec',
    }
    for key, path in environment.items():
        os.environ[key] = str(ROOT / path)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    if not plugins:
        return []
    from pxr import Plug
    resources = [ROOT / 'core/usdaeco-core/usdAeco']
    for card in cards.values():
        checkout = ROOT / card['path']
        for path in sorted(checkout.glob('*/plugInfo.json')):
            if path.parent.name.startswith(('usdAeco', 'usdSolid')) and path.parent not in resources:
                resources.append(path.parent)
    # usdSolid's schema is in the native kit's source package.
    for path in (ROOT / 'kits/usdSolid').glob('**/generatedSchema.usda'):
        if (path.parent / 'plugInfo.json').is_file() and path.parent not in resources:
            resources.append(path.parent)
    if native_plugins:
        resources += [Path(p) for p in os.environ.get('USDAECO_NATIVE_PLUGINPATH', '').split(os.pathsep) if p]
    for path in resources:
        Plug.Registry().RegisterPlugins(str(path))
    os.environ['PXR_PLUGINPATH_NAME'] = os.pathsep.join(map(str, resources))
    return resources


def stamp(layer, role, package, producer, source, source_sha, tag):
    layer.customLayerData = {**layer.customLayerData, **{
        'aeco:layer:' + key: value for key, value in dict(
            role=role, package=package, producer=producer, source=source,
            sourceSha256=source_sha, tag=tag).items()}}


def header(layer, fallbacks):
    from pxr import Vt
    layer.defaultPrim = 'demo_datacentre_01'
    layer.pseudoRoot.SetInfo('metersPerUnit', 1.0)
    layer.pseudoRoot.SetInfo('upAxis', 'Z')
    layer.pseudoRoot.SetInfo('fallbackPrimTypes', {k: Vt.TokenArray(v) for k, v in sorted(fallbacks.items())})
    layer.startTimeCode, layer.endTimeCode = 0, 288
    layer.timeCodesPerSecond = 24
    layer.framesPerSecond = 24


def layer_paths(layer):
    paths = []
    layer.Traverse('/', lambda p: paths.append(p))
    return paths
