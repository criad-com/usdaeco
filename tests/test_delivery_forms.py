import copy

import pytest
from pxr import Sdf, Usd, UsdGeom

from usdaeco_suite.bonsai_delivery import compare_ifc
from usdaeco_suite.stage_common import FORM_A, header
from usdaeco_suite.stage_flatten import compare, equal, export_flat, metadata, scene_fields


def test_flatten_preserves_metadata_animation_and_resolves_references(tmp_path):
    delivery = Usd.Stage.CreateNew(str(tmp_path / 'delivery.usda'))
    prim = UsdGeom.Xform.Define(delivery, '/Source')
    prim.AddTranslateOp().Set((1, 2, 3), 7)
    delivery.GetRootLayer().Save()
    stage = Usd.Stage.CreateNew(str(tmp_path / FORM_A))
    header(stage.GetRootLayer(), {'AecoSpace': ['Xform']})
    root = stage.DefinePrim('/demo_datacentre_01', 'Xform')
    root.GetReferences().AddReference('delivery.usda', '/Source')
    stage.GetRootLayer().Save()
    target = tmp_path / 'flat.usdc'
    export_flat(stage, tmp_path, target)
    flat = Usd.Stage.Open(str(target))
    assert metadata(flat) == metadata(stage)
    assert not flat.GetRootLayer().subLayerPaths
    assert not any(flat.GetRootLayer().externalReferences)
    assert flat.GetDefaultPrim().GetAttribute('xformOp:translate').Get(7) == (1, 2, 3)
    assert flat.GetRootLayer().customLayerData['aeco:layer:role'] == 'flattened'


def test_flatten_rejects_asset_attributes(tmp_path):
    stage = Usd.Stage.CreateNew(str(tmp_path / FORM_A))
    header(stage.GetRootLayer(), {'AecoSpace': ['Xform']})
    stage.DefinePrim('/demo_datacentre_01', 'Xform').CreateAttribute('texture', Sdf.ValueTypeNames.Asset).Set('texture.png')
    stage.GetRootLayer().Save()
    with pytest.raises(ValueError, match='external asset'):
        export_flat(stage, tmp_path, tmp_path / 'flat.usdc')


def test_controlled_mesh_exclusion_cannot_hide_identity_or_placement_change():
    before = {'/Pipe': dict(type='Mesh', identity='pipe-1', world=[1], mesh={'points': 'old'})}
    after = copy.deepcopy(before)
    after['/Pipe']['mesh']['points'] = 'new'
    assert equal(compare(before, after, ['/Pipe']))
    for field, value in [('identity', 'pipe-2'), ('world', [2]), ('type', 'Xform')]:
        changed = copy.deepcopy(after)
        changed['/Pipe'][field] = value
        assert not equal(compare(before, changed, ['/Pipe']))
    assert not equal(compare(before, {**after, '/Added': after['/Pipe']}, ['/Pipe']))


def test_generated_prototype_census_is_separate_and_source_collision_rejected():
    data = {'/Element': dict(type='Xform', identity='one'),
            '/Flattened_Prototype_1': dict(type='', identity=None)}
    scene, storage = scene_fields(data, flattened=True)
    assert list(scene) == ['/Element'] and storage == ['/Flattened_Prototype_1']
    with pytest.raises(ValueError, match='generated prototype namespace'):
        scene_fields(data)


def test_ifc_reference_comparison_preserves_fields_targets_and_multiplicity():
    from collections import Counter
    reference = ('/Other/Port', 'other.ifc', 'port-id', 'aeco:connectedPorts')
    before = {'documents': Counter({reference: 2}),
              'associations': Counter({('rel-id', reference, ('element-id',)): 1})}
    after = copy.deepcopy(before)
    assert all(not (r['added'] or r['removed']) for r in compare_ifc(before, after).values())
    after['documents'][reference] -= 1
    after['associations'] = Counter({('rel-id', reference, ('changed-id',)): 1})
    result = compare_ifc(before, after)
    assert result['documents']['removed'] == 1
    assert result['associations']['removed'] == result['associations']['added'] == 1
