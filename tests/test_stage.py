from pathlib import Path

from pxr import Sdf, Usd

from usdaeco_suite.stage_checks import (analysis_namespace_errors, compare_errors, finding_records,
                                       summarize_mutes, summarize_validation, tidy_stage)
from usdaeco_suite.stage_hooks import prune, remap_data, reroot, study_mappings
from usdaeco_suite.traverse import owner


def test_camera_reroot_keeps_relationships_and_pose():
    layer = Sdf.Layer.CreateAnonymous()
    layer.ImportFromString('''#usda 1.0
    def Scope "Renders" {
        def Camera "overview" {
            double3 xformOp:translate = (1, 2, 3)
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }
    }
    def Scope "Study" {
        rel camera = </Renders/overview>
    }
    ''')
    reroot(layer, 'cctv')
    stage = Usd.Stage.Open(layer)
    camera = stage.GetPrimAtPath('/Renders/cctv/overview')
    assert camera.GetTypeName() == 'Camera'
    assert tuple(camera.GetAttribute('xformOp:translate').Get()) == (1, 2, 3)
    assert stage.GetPrimAtPath('/Study').GetRelationship('camera').GetTargets() == [camera.GetPath()]
    assert not stage.GetPrimAtPath('/Renders/overview')


def test_study_relocation_keeps_discovery_arcs_and_metadata():
    layer = Sdf.Layer.CreateAnonymous()
    layer.ImportFromString('''#usda 1.0
    (customLayerData = { string result = "/Clash/Result" })
    def Scope "Clash" {
        def Scope "Result" {
            rel targets = [</Clash/Result>, </demo_datacentre_01/Wall>]
        }
        def Scope "Instance" (prepend references = </Clash/Result>) {}
    }
    ''')
    moves = study_mappings([layer], 'clash', 'demo_datacentre_01')
    reroot(layer, 'clash', mappings=moves)
    stage = Usd.Stage.Open(layer)
    result = stage.GetPrimAtPath('/Studies/clash/Clash/Result')
    assert result in list(stage.Traverse())
    assert layer.customLayerData['result'] == str(result.GetPath())
    assert result.GetRelationship('targets').GetTargets() == [result.GetPath(), Sdf.Path('/demo_datacentre_01/Wall')]
    assert stage.GetPrimAtPath('/Studies/clash/Clash/Instance').GetRelationship('targets')
    assert not analysis_namespace_errors(layer, 'clash', '/demo_datacentre_01')
    assert remap_data({'targets': ['/Clash/Result', '/ClashSimilar']}, moves) == {
        'targets': [str(result.GetPath()), '/ClashSimilar']}
    before = layer.ExportToString()
    reroot(layer, 'clash', mappings=study_mappings([layer], 'clash', 'demo_datacentre_01'))
    assert layer.ExportToString() == before


def test_namespace_check_rejects_stale_targets_metadata_and_foreign_studies():
    layer = Sdf.Layer.CreateAnonymous()
    layer.ImportFromString('''#usda 1.0
    (customLayerData = { string programme = "/Programme" })
    def Scope "Studies" {
        def Scope "plan" {
            rel old = </Looks/Material>
            def Camera "misplacedCamera" {}
        }
        def Scope "cctv" {}
    }
    ''')
    errors = analysis_namespace_errors(layer, 'plan', '/demo_datacentre_01')
    assert any('/Programme' in e for e in errors)
    assert any('/Looks/Material' in e for e in errors)
    assert any('/Studies/cctv' in e for e in errors)
    assert any('render camera outside' in e for e in errors)


def test_tidy_root_includes_classes_and_inactive_strays():
    layer = Sdf.Layer.CreateAnonymous()
    layer.ImportFromString('''#usda 1.0
    (defaultPrim = "demo_datacentre_01")
    def Xform "demo_datacentre_01" {
        class "_TypeCatalog" {}
    }
    def Scope "Renders" {}
    def Scope "Studies" {
        def Scope "pipe" {}
    }
    ''')
    stage = Usd.Stage.Open(layer)
    assert not tidy_stage(stage, ['pipe'])['errors']
    stray = Sdf.CreatePrimInLayer(layer, '/_TypeCatalog')
    stray.specifier = Sdf.SpecifierClass
    assert 'stage must contain only the project catalog' in tidy_stage(stage, ['pipe'])['errors']
    del layer.rootPrims['_TypeCatalog']
    stray = Sdf.CreatePrimInLayer(layer, '/Hidden')
    stray.active = False
    assert 'stage root prims differ' in tidy_stage(stage, ['pipe'])['errors']


def test_empty_over_pruning_preserves_authored_controls():
    layer = Sdf.Layer.CreateAnonymous()
    layer.ImportFromString('''#usda 1.0
    over "empty" {
        over "nested" {}
    }
    over "hidden" {
        token visibility = "invisible"
    }
    over "disabled" (active = false) {}
    def Scope "defined" {}
    ''')
    prune(layer)
    assert not layer.GetPrimAtPath('/empty')
    assert layer.GetAttributeAtPath('/hidden.visibility').default == 'invisible'
    assert layer.GetPrimAtPath('/disabled').active is False
    assert layer.GetPrimAtPath('/defined').specifier == Sdf.SpecifierDef


def test_ownership_comes_from_delivery_even_with_typed_promotion(tmp_path):
    delivery = tmp_path / 'packages/arch/arch.usda'
    overlay = tmp_path / 'analysis/cctv/root.usda'
    delivery.parent.mkdir(parents=True)
    overlay.parent.mkdir(parents=True)
    delivery.write_text('#usda 1.0\ndef Xform "Wall" {}\n')
    overlay.write_text('#usda 1.0\ndef Xform "Wall" {\n custom string note = "review"\n}\n')
    root = Sdf.Layer.CreateAnonymous()
    root.subLayerPaths = [str(overlay), str(delivery)]
    stage = Usd.Stage.Open(root)
    assert owner(stage.GetPrimAtPath('/Wall')) == 'packages/arch'


def test_expected_illustrative_errors_do_not_admit_structural_errors():
    expected = {'MisplacedDevice': 2}
    rows = [dict(rule='MisplacedDevice', severity='error')] * 2
    assert compare_errors(rows, expected)[0]
    assert not compare_errors(rows[:1], expected)[0]
    assert not compare_errors(rows + [dict(rule='duplicateId', severity='error')], expected)[0]
    assert compare_errors(rows + [dict(rule='proxyClassified', severity='warn')], expected)[0]


def test_mute_diagnostics_require_exact_predicted_port_sites():
    row = dict(layer='packages/cooling/cooling.usda', moved=[], compositionErrors=0,
               newErrors=[dict(rule='danglingPortLink', severity='error', paths=['/Other/Port']),
                          dict(rule='QuantityStale', severity='error', paths=['/Quantity'])])
    manifest = dict(crossPackageLinks=[dict(targetPackage='cooling', relationship='aeco:connectedPorts', source='/Other/Port')])
    data = dict(complete=True, rows=[row])
    summary, valid = summarize_mutes(data, manifest)
    assert valid and not summary['portOnlyRequirementMet']
    assert summary['rows'][0]['dependencyErrorCount'] == 1
    manifest['crossPackageLinks'][0]['source'] = '/Unexpected/Port'
    assert not summarize_mutes(data, manifest)[1]
    manifest['crossPackageLinks'][0]['source'] = '/Other/Port'
    row['newErrors'].append(dict(rule='duplicateId', severity='error', paths=['/Element']))
    assert not summarize_mutes(data, manifest)[1]


def test_expected_findings_cannot_be_expanded_by_editing_the_manifest():
    manifest = dict(integration=dict(repeat=[dict(changes=[dict(declared=False)])]))
    manifest['expectedFindings'] = finding_records(manifest)
    data = dict(findings=[dict(rule='RepeatDrift', severity='error', paths=['/Occurrence'])], validators={})
    assert summarize_validation(data, manifest)[1]
    manifest['expectedFindings'][0]['count'] = 2
    assert not summarize_validation(data, manifest)[1]
    manifest['expectedFindings'] = finding_records(manifest)
    data['findings'].append(dict(rule='ComplianceStale', severity='error', paths=['/Reader']))
    assert not summarize_validation(data, manifest)[1]
