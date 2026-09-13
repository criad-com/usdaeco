"""Run inside Blender to deliver an unchanged IFC through Bonsai's exporter."""
import json
from pathlib import Path
import sys


def main():
    import bpy
    import bonsai.tool as tool
    source, target, receipt = sys.argv[sys.argv.index('--') + 1:]
    print('== stage: Bonsai import', flush=True)
    bpy.ops.bim.load_project(filepath=source)
    print('== stage: Bonsai export', flush=True)
    bpy.ops.bim.save_project(filepath=target, should_save_as=True)
    Path(receipt).write_text(json.dumps(dict(
        blender=bpy.app.version_string,
        bonsai=tool.Ifc.get().header.file_name.originating_system,
        exported=Path(target).is_file())) + '\n')


if __name__ == '__main__':
    main()
