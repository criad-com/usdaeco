"""Print spatial containment and defining-delivery ownership in the integrated stage."""
import argparse
from collections import Counter
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usdaeco_suite.stage_common import ROOT, FORM_C


def owner(prim):
    """Prefer the delivering definition, including below a typed promotion."""
    from pxr import Sdf
    for category in ('packages', 'analysis'):
        for spec in prim.GetPrimStack():
            if spec.specifier != Sdf.SpecifierDef:
                continue
            parts = Path(spec.layer.realPath).parts
            if category in parts:
                return category + '/' + parts[parts.index(category) + 1]
    return 'shared structure'


def element(prim):
    schemas = prim.GetMetadata('apiSchemas')
    return bool(schemas and 'AecoElementAPI' in schemas.ApplyOperations([]))


def rows(stage):
    from pxr import Usd
    project = stage.GetDefaultPrim()
    site = next((p for p in Usd.PrimRange(project) if p.GetTypeName() == 'AecoSite'), None)
    if not site:
        raise ValueError('no site in the project spatial structure')
    for prim in Usd.PrimRange(site):
        spatial = prim.GetTypeName() in {'AecoSite', 'AecoFacility', 'AecoFacilityPart', 'AecoLevel', 'AecoSpace'}
        if spatial or element(prim):
            yield dict(path=str(prim.GetPath()), name=prim.GetDisplayName() or prim.GetName(),
                       type=prim.GetTypeName(), owner=owner(prim), element=element(prim),
                       depth=prim.GetPath().pathElementCount - site.GetPath().pathElementCount)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', nargs='?', type=Path, default=ROOT / 'stage' / FORM_C)
    parser.add_argument('--summary', action='store_true')
    parser.add_argument('--package')
    args = parser.parse_args(argv)
    from pxr import Usd
    stage = Usd.Stage.Open(str(args.stage.resolve()))
    if not stage or stage.GetCompositionErrors():
        raise ValueError('stage does not compose')
    counts = Counter()
    for row in rows(stage):
        if args.package and row['owner'] != 'packages/' + args.package:
            continue
        counts[row['owner']] += row['element']
        if not args.summary:
            print('  ' * row['depth'] + row['name'] + ' [' + row['owner'] + ']')
    print('== stage: delivered element census')
    for package, count in sorted(counts.items()):
        print(f'{package}: {count}')
    print('== stage: analysis roots')
    for prim in stage.GetPseudoRoot().GetChildren():
        if prim != stage.GetDefaultPrim():
            print(str(prim.GetPath()) + ' [' + owner(prim) + ']')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
