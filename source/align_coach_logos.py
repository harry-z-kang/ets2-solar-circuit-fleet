"""Align both sides of the MAN/Scania logos in physical space, then package coaches.

Default rebuild uses the distributed calibration; --calibrate reads private local
PIM/PIT geometry and derives separate UV placements for each side.
"""
from pathlib import Path
from functools import lru_cache
import argparse
import json
import re
from build_panel_refinement import image_base, opposite, package
from build_truck_expansion import label, logo, render, svg
from rebuild import encode_dds
from scs_midformat import read_model, locators, transform

ROOT = Path(__file__).resolve().parent.parent
LAYOUT = ROOT/'source/logo-alignment-layouts.json'
VEHICLES = ['man-lions-coach-139','scania-touring-137']


@lru_cache(None)
def model(path,variant='default',look='default'):
    return read_model(path,variant,look)


def surface_height(path,x,q,side):
    """Model Y at a logo coordinate; q is the upright virtual side coordinate."""
    v = q if side=='left' else 4096-q
    materials,pieces = model(path)
    hits = []
    for piece in pieces:
        if 'truckpaint' not in materials[piece['material']]['effect']:
            continue
        streams = piece['streams']
        uv = streams[piece['aliases']['_TEXCOORD1']]
        positions = streams['_POSITION']
        for tri in piece['triangles']:
            a,b,c = [(uv[i][0]*8192,uv[i][1]*4096) for i in tri]
            if not min(a[0],b[0],c[0])-1e-7<=x<=max(a[0],b[0],c[0])+1e-7:
                continue
            if not min(a[1],b[1],c[1])-1e-7<=v<=max(a[1],b[1],c[1])+1e-7:
                continue
            denominator = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(denominator)<1e-9:
                continue
            aa = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(v-c[1]))/denominator
            bb = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(v-c[1]))/denominator
            weights = (aa,bb,1-aa-bb)
            if min(weights)<-1e-6:
                continue
            xyz = tuple(sum(w*positions[i][j] for w,i in zip(weights,tri)) for j in range(3))
            if abs(xyz[0])>1.1:
                hits.append(xyz)
    if not hits:
        raise ValueError(f'No painted side surface at {path.name} {side} {x},{q}')
    return max(hits,key=lambda p:abs(p[0]))[1]


def invert_height(path,x,height,side):
    y0,y1 = 3600.,3800.
    h0,h1 = [surface_height(path,x,y,side) for y in [y0,y1]]
    y = y0+(height-h0)*(y1-y0)/(h1-h0)
    for _ in range(4):
        h = surface_height(path,x,y,side)
        if abs(h-height)<1e-7:
            break
        slope = (surface_height(path,x,y+.1,side)-h)/.1
        y += (height-h)/slope
    return y


def wheel_ground(models,chassis):
    values = []
    for name,locator in locators(models/chassis).items():
        match = re.fullmatch(r'wheel_([ab])_\d+',name)
        if not match:
            continue
        axle = 'front' if match[1]=='a' else 'rear'
        variant = 'left' if locator['position'][0]<0 else 'right'
        materials,pieces = model(models/f'vehicle/truck/upgrade/wheel/tire/{axle}_1.pim',variant,'trailmaster')
        for piece in pieces:
            if 'shadow' not in materials[piece['material']]['effect']:
                values += [transform(p,locator)[1] for p in piece['streams']['_POSITION']]
    return min(values)


def calibrate(models):
    baseline = json.loads((ROOT/'source/feedback-fix-layouts.json').read_text())
    config = json.loads((ROOT/'source/blender-vehicles.json').read_text())
    data = {'version':'0.5.2','truck_module':baseline['truck_module'],'coach_module':'gtsr-coaches-v0.2.2.scs',
            'center_above_ground_m':1.0,'logo_height_m':.5,'coaches':{}}
    for name in VEHICLES:
        layout = baseline['coaches'][name]
        main = models/config[name]['main']
        chassis = next(p['model'] for p in config[name]['parts'] if p.get('wheel_root'))
        ground = wheel_ground(models,chassis)
        cx = layout['logo'][0]+layout['logo'][2]/2
        sides = []
        for side in ['left','right']:
            center = ground+data['center_above_ground_m']
            top = invert_height(main,cx,center+data['logo_height_m']/2,side)
            bottom = invert_height(main,cx,center-data['logo_height_m']/2,side)
            width = (bottom-top)*922/186
            x = cx-width/2
            fleet = invert_height(main,cx,ground+.62,side)
            before = layout['logo'][1]+layout['logo'][2]*186/922/2
            after = surface_height(main,cx,(top+bottom)/2,side)-ground
            assert abs(after-1.0)<.001
            sides.append({'side':side,'logo':[x,top,width],'fleet_y':fleet,'fleet_size':40*width/1100,
                          'before_center_above_ground_m':surface_height(main,cx,before,side)-ground,
                          'measured_top_above_ground_m':surface_height(main,cx,top,side)-ground,
                          'measured_center_above_ground_m':after,
                          'measured_bottom_above_ground_m':surface_height(main,cx,bottom,side)-ground})
        data['coaches'][name] = {'fleet':layout['fleet'],'ground_model_y_m':ground,'model':config[name]['main'],'sides':sides}
    LAYOUT.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    return data


def artwork(name,layout):
    size,body = image_base(name)
    for side in layout['sides']:
        x,y,w = side['logo']
        mark = logo(x,y,w)+label(x,side['fleet_y'],'TEAM TRANSPORT / '+layout['fleet'],side['fleet_size'])
        if side['side']=='right':
            mark = opposite(f'<g transform="translate({2*x+w} 0) scale(-1 1)">{mark}</g>')
        body += mark
    return svg(*size,body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calibrate',action='store_true')
    parser.add_argument('--models',type=Path,default=ROOT/'work/panel-refinement/converted')
    parser.add_argument('--coach-seed',type=Path)
    args = parser.parse_args()
    data = calibrate(args.models) if args.calibrate else json.loads(LAYOUT.read_text())
    changes = {}
    for name,layout in data['coaches'].items():
        content = artwork(name,layout)
        path = ROOT/'textures'/name
        if not path.with_suffix('.svg').exists() or path.with_suffix('.svg').read_text()!=content:
            image = render(content)
            path.with_suffix('.svg').write_text(content,encoding='utf-8',newline='\n')
            image.save(path.with_suffix('.png'))
            path.with_suffix('.dds').write_bytes(encode_dds(image))
        changes['gtsr_solar/'+name+'.dds'] = path.with_suffix('.dds').read_bytes()
        print(name,[(s['side'],s['measured_center_above_ground_m']) for s in layout['sides']],flush=True)
    target = ROOT/'mods'/data['coach_module']
    previous = ROOT/'mods/gtsr-coaches-v0.2.1.scs'
    seed = args.coach_seed or (previous if previous.exists() else target)
    package(seed,target,changes,{},set(),'0.2.2','Solar Circuit coaches 0.2.2: MAN 13.9 m and Scania 13.7 m logos share a 1.00 m center above reference tire contact and 0.50 m physical height on both sides. Other coach artwork is unchanged. Checked on local geometry and in Blender; exact game ride heights/materials may vary.\n')
    index = json.loads((ROOT/'source/texture-index.json').read_text())
    for item in index:
        if item['name'] in VEHICLES:
            item['scope'] = 'MAN/Scania physical logo alignment 0.5.2'
    (ROOT/'source/texture-index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':
    main()
