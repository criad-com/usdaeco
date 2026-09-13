from pathlib import Path

from pxr import Sdf, Usd

from usdaeco_suite.stage_checks import compare_errors, finding_records, summarize_mutes, summarize_validation
from usdaeco_suite.stage_hooks import prune, reroot
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
