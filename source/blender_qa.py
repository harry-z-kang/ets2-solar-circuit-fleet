"""Build local Blender inspection scenes and render actual livery DDS textures.

python source/blender_qa.py --vehicle volvo-9700-dd
python source/blender_qa.py --all
Requires private ConverterPIX PIM/PIT exports; see docs/BLENDER-VISUAL-CHECK.md.
"""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    select = parser.add_mutually_exclusive_group(required=True)
    select.add_argument('--vehicle', choices=['man-lions-coach-139', 'scania-touring-137', 'volvo-9700-dd', 'fh6-van-leer'])
    select.add_argument('--all', action='store_true')
    parser.add_argument('--blender', default=shutil.which('blender'))
    parser.add_argument('--models', type=Path, default=ROOT/'work/panel-refinement/converted')
    parser.add_argument('--output', type=Path, default=ROOT/'work/blender-qa')
    parser.add_argument('--texture-dir', type=Path, help='Prefer edited DDS/PNG files here; fall back to module DDS files.')
    parser.add_argument('--truck-module', type=Path)
    parser.add_argument('--coach-module', type=Path)
    parser.add_argument('--views', default='left,right,front,rear,front-left,front-right,rear-right,roof')
    parser.add_argument('--width', type=int, default=1440)
    parser.add_argument('--samples', type=int, default=16)
    parser.add_argument('--flat', action='store_true', help='Unlit paint colors; simplified non-paint materials remain shaded.')
    parser.add_argument('--scene-only', action='store_true')
    args = parser.parse_args()
    if not args.blender:
        parser.error('Blender not on PATH; pass --blender C:/path/to/blender.exe')
    if args.width < 320 or args.samples < 1:
        parser.error('Use width >= 320 and samples >= 1')
    config = json.loads((ROOT/'source/blender-vehicles.json').read_text())
    layout_file = ROOT/'source/logo-alignment-layouts.json'
    if not layout_file.exists():
        layout_file = ROOT/'source/feedback-fix-layouts.json'
    if not layout_file.exists():
        layout_file = ROOT/'source/panel-refinement-layouts.json'
    layouts = json.loads(layout_file.read_text())
    args.output = args.output.resolve()
    # Models and source DDS extracts must remain inside ignored local work/.
    args.output.relative_to((ROOT/'work').resolve())
    args.output.mkdir(parents=True, exist_ok=True)
    textures = args.output/'texture-cache'
    textures.mkdir(exist_ok=True)
    for module in [args.truck_module or ROOT/'mods'/layouts['truck_module'], args.coach_module or ROOT/'mods'/layouts['coach_module']]:
        with zipfile.ZipFile(module) as archive:
            for member in archive.namelist():
                if '/gtsr_solar/' in member or member.startswith('gtsr_solar/'):
                    if member.endswith('.dds'):
                        target = textures/Path(member).name
                        raw = archive.read(member)
                        if not target.exists() or target.read_bytes() != raw:
                            target.write_bytes(raw)
    for vehicle in config if args.all else [args.vehicle]:
        command = [args.blender, '--background', '--factory-startup', '--python-exit-code', '1',
                   '--python', str(ROOT/'source/blender_scene.py'), '--', '--vehicle', vehicle,
                   '--models', str(args.models.resolve()), '--output', str(args.output),
                   '--texture-cache', str(textures), '--views', args.views, '--width', str(args.width), '--samples', str(args.samples)]
        if args.texture_dir:
            command += ['--texture-dir', str(args.texture_dir.resolve())]
        if args.flat:
            command += ['--flat']
        if args.scene_only:
            command += ['--scene-only']
        log = args.output/(vehicle+'-build.log')
        print('Blender QA:', vehicle, '| log:', log, flush=True)
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            print(log.read_text(encoding='utf-8')[-6000:])
            raise SystemExit(result.returncode)
        print('Saved:', args.output/vehicle, flush=True)


if __name__ == '__main__':
    main()
