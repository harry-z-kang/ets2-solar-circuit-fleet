"""Build the FH6 Aero XL Van Leer sloping front stripe and lowered, larger logo.

The proportional mark spans the door and adjacent cab panel on each side.
Default uses the authored base; --calibrate projects the stripe from private PIMs.
"""
from pathlib import Path
import argparse,hashlib,json
from PIL import Image,ImageDraw,ImageFilter
from build_accessory_fix import clip
from build_panel_refinement import art,package
from build_truck_expansion import render
from rebuild import encode_dds
from scs_midformat import read_model

ROOT=Path(__file__).resolve().parent.parent


def calibrate_front(models,layout):
    model='vehicle/truck/volvo_fh_2024/cabin/globe_xl_aero_2024.pim'
    mats,parts=read_model(models/model)
    size=(4096,4096);masks={key:Image.new('L',size) for key in ['navy','gold']}
    draw={key:ImageDraw.Draw(mask) for key,mask in masks.items()}
    count=0
    for part in parts:
        if 'truckpaint' not in mats[part['material']]['effect']:continue
        ss=part['streams'];uv=ss[part['aliases']['_TEXCOORD1']]
        for tri in part['triangles']:
            poly=[(*ss['_POSITION'][i],uv[i][0]*4096,uv[i][1]*4096) for i in tri]
            for (z0,h0),(z1,h1) in zip(layout['stripe_profile'],layout['stripe_profile'][1:]):
                cut=clip(clip(poly,lambda p:z0-p[2]),lambda p:p[2]-z1)
                fn=lambda p:p[1]-(h0+(p[2]-z0)*(h1-h0)/(z1-z0))
                below=clip(cut,fn)
                if len(below)>=3:draw['navy'].polygon([(v[3],v[4]) for v in below],fill=255)
                band=clip(below,lambda p:-fn(p)-layout['gold_width_m'])
                if len(band)>=3:draw['gold'].polygon([(v[3],v[4]) for v in band],fill=255)
            count+=1
    im=Image.new('RGB',size,'white')
    for key,color,kernel in [('navy',(5,30,57),7),('gold',(179,144,81),3)]:
        im.paste(color,(0,0),masks[key].filter(ImageFilter.MaxFilter(kernel)))
    path=ROOT/'artwork/panel-bases'/f'{layout["texture"]}.png';im.save(path)
    report={'version':layout['version'],'model':model,'paint_triangles':count,
            'profile_z_height_m':layout['stripe_profile'],'gold_width_m':layout['gold_width_m'],
            'base_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (ROOT/'source/fh6-stripe-calibration.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--truck-seed',type=Path)
    parser.add_argument('--calibrate',action='store_true')
    parser.add_argument('--models',type=Path,default=ROOT/'work/panel-refinement/converted')
    args=parser.parse_args()
    layout=json.loads((ROOT/'source/fh6-logo-layout.json').read_text())
    if args.calibrate:calibrate_front(args.models,layout)
    name=layout['texture'];content=art(name,layout)
    path=ROOT/'textures'/name
    if path.with_suffix('.svg').read_text()!=content:
        im=render(content)
        path.with_suffix('.svg').write_text(content,encoding='utf-8',newline='\n')
        im.save(path.with_suffix('.png'))
        path.with_suffix('.dds').write_bytes(encode_dds(im))
    target=ROOT/'mods'/layout['truck_module']
    previous=ROOT/'mods/gtsr-trucks-v0.5.3.scs'
    seed=args.truck_seed or (previous if previous.exists() else target)
    package(seed,target,{layout['mount']+'/gtsr_solar/'+name+'.dds':path.with_suffix('.dds').read_bytes()},{},set(),'0.5.3',
            'Solar Circuit trucks 0.5.3: FH6 Aero XL Van Leer gold stripe slopes down with the front panel line and continues across the nose. Enlarged 936-pixel logos lowered approximately 15 cm on both cab sides, clear of the front corners. Original logo proportions and TK-05 / VAN LEER retained. Painted accessory fixes and all other paint jobs preserved. Blender checked; final ETS2 appearance awaits confirmation.\n')
    index=json.loads((ROOT/'source/texture-index.json').read_text())
    next(t for t in index if t['name']==name)['scope']='FH6 Aero XL sloping front stripe and lowered multi-panel Van Leer logos 0.5.3'
    (ROOT/'source/texture-index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('FH6 logo width 1040 -> 936 px (10 percent reduction), rear edge anchored; truck module 0.5.3.')


if __name__=='__main__':main()
