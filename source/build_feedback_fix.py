"""Build v0.5.1 from v0.5.0 feedback; preserve unrelated module members."""
from pathlib import Path
import argparse
import base64
import json
import math
import re
import zipfile
from build_panel_refinement import art, image_base, opposite, package
from build_truck_expansion import label, logo, render, svg, WHITE
from build_mercedes_daf import accessory_text
from rebuild import encode_dds

ROOT = Path(__file__).resolve().parent.parent


def dd_art(layout):
    size, body = image_base('volvo-9700-dd')
    x,y,w = layout['logo']
    mark = logo(x,y,w)
    # Original proportional mark directly on white, with no rectangular plaque.
    body += mark+opposite(f'<g transform="translate({2*x+w} 0) scale(-1 1)">{mark}</g>')
    cx,cy,cw = layout['car']
    source = ROOT/'artwork'/layout['car_asset']
    from PIL import Image
    iw,ih = Image.open(source).size
    encoded = base64.b64encode(source.read_bytes()).decode()
    car = f'<g transform="translate({2*cx+cw} 0) scale(-1 1)"><image x="{cx}" y="{cy}" width="{cw}" height="{cw*ih/iw}" href="data:image/png;base64,{encoded}"/></g>'
    body += car+opposite(car)
    tx,ty,value = layout['caption']
    caption = label(tx,ty,value,36,WHITE)
    body += caption+opposite(f'<g transform="translate({2*tx+950} 0) scale(-1 1)">{caption}</g>')
    return svg(*size,body)


def assignments(text):
    result = {}
    for block in re.findall(r'simple_paint_job_data:[^{]+\{([^}]+)\}',text):
        texture = re.search(r'paint_job_mask:\s*"/gtsr_solar/([^"]+)\.tobj"',block)[1]
        for ident in re.findall(r'acc_list\[\]:\s*"([^"]+)"',block):
            result[ident] = texture
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--truck-seed',type=Path)
    parser.add_argument('--coach-seed',type=Path)
    parser.add_argument('--reuse-textures',action='store_true')
    args = parser.parse_args()
    data = json.loads((ROOT/'source/feedback-fix-layouts.json').read_text())
    truck = data['truck']
    modules = {'truck':ROOT/'mods'/data['truck_module'],'coach':ROOT/'mods'/data['coach_module']}
    seeds = {}
    for kind,previous in [('truck','gtsr-trucks-v0.5.scs'),('coach','gtsr-coaches-v0.2.scs')]:
        seeds[kind] = getattr(args,kind+'_seed') or (ROOT/'mods'/previous if (ROOT/'mods'/previous).exists() else modules[kind])
    changes = {'truck':{},'coach':{}}
    index = json.loads((ROOT/'source/texture-index.json').read_text())
    for name,layout in {**data['coaches'],truck['texture']:truck}.items():
        content = dd_art(layout) if name=='volvo-9700-dd' else art(name,layout)
        path = ROOT/'textures'/name
        if not (args.reuse_textures and path.with_suffix('.svg').exists() and path.with_suffix('.svg').read_text()==content):
            image = render(content)
            path.with_suffix('.svg').write_text(content,encoding='utf-8',newline='\n')
            image.save(path.with_suffix('.png'))
            path.with_suffix('.dds').write_bytes(encode_dds(image))
        kind = 'coach' if name in data['coaches'] else 'truck'
        prefix = '' if kind=='coach' else truck['mount']+'/'
        changes[kind][prefix+'gtsr_solar/'+name+'.dds'] = path.with_suffix('.dds').read_bytes()
        next(t for t in index if t['name']==name)['scope'] = 'Native v0.5.0 feedback / Blender refinement 0.5.1'
        print('Built',name,flush=True)
    prefix = truck['mount']+'/def/vehicle/truck/'+truck['vehicle']+'/paint_job/accessory/gtsrsc_3.sii'
    with zipfile.ZipFile(seeds['truck']) as archive:
        mapping = assignments(archive.read(prefix).decode())
    mapping.update(truck['solid_overrides'])
    changes['truck'][prefix] = accessory_text(mapping).encode()
    package(seeds['truck'],modules['truck'],changes['truck'],{},set(),'0.5.1',
            'Solar Circuit truck 0.5.1: TK-05 / VAN LEER restored on Aero XL. Painted lower front accessories navy; painted upper mirrors white. Other fleet entries preserved. Blender geometry check completed; corrected in-game appearance awaits confirmation.\n')
    package(seeds['coach'],modules['coach'],changes['coach'],{},set(),'0.2.1',
            'Solar Circuit coaches 0.2.1: MAN/Scania bands raised to marked luggage-panel lines. DD team mark directly on white; team-provided SR-4 illustration replaces sketch. Short bodies preserved. Blender geometry check completed; corrected in-game appearance awaits confirmation.\n')
    (ROOT/'source/texture-index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':
    main()
