"""Refresh derived receipts against the final composed analysis stack."""
import os
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usdaeco_suite.stage_common import ROOT, FORM_C, configure, read, write, stamp, sha, repos


def finalize(directory):
    configure(native_plugins=True)
    from pxr import Sdf, Usd
    from usdaeco_ifc.exact_common import fingerprint
    stage = Usd.Stage.Open(str(directory / FORM_C))
    if not stage or stage.GetCompositionErrors():
        raise ValueError('cannot refresh an invalid analysis stack')
    changed = set()
    correlations = 0
    for prim in stage.Traverse():
        if prim.GetName() != 'Body':
            continue
        exact = prim.GetParent().GetChild('BodyExact')
        if not exact or exact.GetTypeName() != 'BrepArray':
            continue
        attribute = prim.GetAttribute('aeco:derived:stamp')
        text = attribute.Get() or ''
        if 'source=' not in text:
            continue
        # Placement anchoring preserves world-space geometry; correlate the
        # same mesh to the equivalent re-expressed exact representation.
        target = attribute.GetPropertyStack()[0].layer
        with Usd.EditContext(stage, target):
            attribute.Set(re.sub(r'source=[a-f0-9]{64}', 'source=' + fingerprint(exact), text))
        changed.add(target)
        correlations += 1
    for layer in changed:
        layer.Save()
    receipt = dict(exactPlacementCorrelations=correlations)
    quantity_file = directory / 'analysis/repeat/out/quantities.usda'
    if quantity_file.exists():
        from usdaeco_repeat.quantity import derive
        from usdaeco_repeat.diff import compare
        quantity = Sdf.Layer.FindOrOpen(str(quantity_file))
        prims = [p for p in stage.Traverse() if p.HasAPI('AecoQuantityAPI')]
        derive(stage, prims, quantity)
        receipt['quantitiesRecomputed'] = len(prims)
        receipt['repeat'] = [compare(p) for p in stage.Traverse() if p.HasAPI('AecoRepeatAPI')]
        write(directory / 'analysis/repeat/integrated-findings.json', receipt['repeat'])
    compliance_file = directory / 'analysis/compliance/out/compliance.usda'
    if compliance_file.exists():
        from usdaeco_compliance.evaluator import write_results
        original = Sdf.Layer.FindOrOpen(str(compliance_file)).customLayerData
        result = write_results(stage, compliance_file)
        layer = Sdf.Layer.FindOrOpen(str(compliance_file))
        layer.customLayerData = {**original, **layer.customLayerData}
        layer.Save()
        receipt['compliance'] = result
        write(directory / 'analysis/compliance/integrated-findings.json', result)
    source = Path(__file__)
    receipt['producer'] = 'usdAECO suite composed-input refresh'
    receipt['source'] = str(source.relative_to(ROOT))
    receipt['sourceSha256'] = sha(source)
    write(directory / 'integration.json', receipt)


if __name__ == '__main__':
    finalize(Path(sys.argv[1]).resolve())
