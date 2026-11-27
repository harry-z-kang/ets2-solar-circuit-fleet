"""Convert privately installed ETS2 models for local Blender inspection.

Requires the locally downloaded ConverterPIX executable. Does not install addons,
change game files or distribute models. All exports stay under ignored work/.
"""
from pathlib import Path
import argparse
import json
import subprocess

ROOT = Path(__file__).resolve().parent.parent
WHEELS = ['vehicle/truck/upgrade/wheel/'+kind+'/'+axle+'_1.pim' for kind in ['tire', 'rim'] for axle in ['front', 'rear']]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, default=Path('C:/Program Files (x86)/Steam/steamapps/common/Euro Truck Simulator 2'))
    parser.add_argument('--converter', type=Path, default=ROOT/'work/panel-refinement/converter_pix.exe')
    parser.add_argument('--models', type=Path, default=ROOT/'work/panel-refinement/converted')
    parser.add_argument('--vehicle', help='One key from blender-vehicles.json; default all four.')
    args = parser.parse_args()
    args.models = args.models.resolve()
    args.models.relative_to((ROOT/'work').resolve())
    config = json.loads((ROOT/'source/blender-vehicles.json').read_text())
    chosen = [config[args.vehicle]] if args.vehicle else config.values()
    models = {p['model'] for vehicle in chosen for p in vehicle['parts']} | set(WHEELS)
    models.add('vehicle/truck/volvo_fh16_2012/accessory/s_deflector/stock.pim')
    args.models.mkdir(parents=True, exist_ok=True)
    for name in sorted(models):
        archives = ['base_share.scs', 'base_vehicle.scs', 'dlc_volvo_fh_2024.scs']
        if '/bus/' in name:
            archives += ['dlc_bus.scs']
        command = [str(args.converter.resolve())]
        for archive in archives:
            path = args.game_dir/archive
            if not path.exists():
                raise FileNotFoundError(path)
            command += ['-b', str(path)]
        command += ['-e', str(args.models), '-m', '/'+name[:-4]]
        result = subprocess.run(command, capture_output=True, text=True)
        (args.models/(Path(name).stem+'-conversion.log')).write_text(result.stdout+result.stderr)
        target = args.models/name
        if result.returncode or not target.exists() or not target.with_suffix('.pit').exists():
            raise RuntimeError('Conversion failed: '+name+'\n'+(result.stdout+result.stderr)[-3000:])
        print('Converted', name, flush=True)


if __name__ == '__main__':
    main()
