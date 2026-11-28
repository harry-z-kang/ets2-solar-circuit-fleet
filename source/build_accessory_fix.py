"""Build 0.5.3 painted-front fixes, preserving the 0.5.2 logo alignment.

Default uses the authored calibrated Scania base. --calibrate optionally reads
private PIM/PIT models and projects the existing band onto its painted intake.
"""
from pathlib import Path
import argparse,hashlib,json,zipfile
from PIL import Image,ImageDraw,ImageFilter
from align_coach_logos import artwork
from build_feedback_fix import assignments
from build_mercedes_daf import accessory_text
from build_panel_refinement import package
from build_truck_expansion import render
from rebuild import encode_dds
from scs_midformat import read_model,locators,transform

ROOT=Path(__file__).resolve().parent.parent


def clip(poly,fn):
    result=[]
    if not poly:return result
    previous=poly[-1];pv=fn(previous)
    for current in poly:
        cv=fn(current)
        if (pv<=0)!=(cv<=0):
            frac=pv/(pv-cv)
            result.append(tuple(previous[k]+frac*(current[k]-previous[k]) for k in range(5)))
        if cv<=0:result.append(current)
        previous,pv=current,cv
    return result


def calibrate(models,layout):
    spec=layout['scania_front'];name=spec['texture']
    base=ROOT/'artwork/panel-bases'/f'{name}.png'
    im=Image.open(base).convert('RGB');size=im.size
    mount=locators(models/'vehicle/bus/scania_touring_23/cabin/cab_137h6.pim')[spec['locator']]
    materials,pieces=read_model(models/spec['model'])
    masks={k:Image.new('L',size) for k in ['full','navy','gold']}
    draw={k:ImageDraw.Draw(v) for k,v in masks.items()}
    triangles=0
    for piece in pieces:
        if 'truckpaint' not in materials[piece['material']]['effect']:continue
        stream=piece['streams'];uv=stream[piece['aliases'][spec['paint_uv_alias']]]
        pos=[transform(p,mount) for p in stream['_POSITION']]
        for indices in piece['triangles']:
            poly=[(*pos[i],uv[i][0]*size[0],uv[i][1]*size[1]) for i in indices]
            draw['full'].polygon([(v[3],v[4]) for v in poly],fill=255)
            for (z0,h0),(z1,h1) in zip(spec['front_profile'],spec['front_profile'][1:]):
                cut=clip(clip(poly,lambda p:z0-p[2]),lambda p:p[2]-z1)
                slope=(h1-h0)/(z1-z0)
                fn=lambda p:p[1]-(h0+(p[2]-z0)*slope)
                below=clip(cut,fn)
                if len(below)>=3:draw['navy'].polygon([(v[3],v[4]) for v in below],fill=255)
                gold=clip(below,lambda p:-fn(p)-spec['gold_width_m'])
                if len(gold)>=3:draw['gold'].polygon([(v[3],v[4]) for v in gold],fill=255)
            triangles+=1
    assert triangles>1000
    for key,color,width in [('full',(255,255,255),7),('navy',(5,30,57),7),('gold',(179,144,81),3)]:
        mask=masks[key].filter(ImageFilter.MaxFilter(width))
        im.paste(color,(0,0),mask)
    im.save(base)
    report={'version':layout['version'],'model':spec['model'],'paint_triangles':triangles,
            'paint_uv_alias':spec['paint_uv_alias'],'front_profile':spec['front_profile'],
            'gold_width_m':spec['gold_width_m'],'base_sha256':hashlib.sha256(base.read_bytes()).hexdigest()}
    (ROOT/'source/accessory-front-calibration.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calibrate',action='store_true')
    parser.add_argument('--models',type=Path,default=ROOT/'work/panel-refinement/converted')
    parser.add_argument('--truck-seed',type=Path)
    parser.add_argument('--coach-seed',type=Path)
    args=parser.parse_args()
    layout=json.loads((ROOT/'source/accessory-fix-layouts.json').read_text())
    if args.calibrate:calibrate(args.models,layout)
    name=layout['scania_front']['texture']
    alignment=json.loads((ROOT/'source/logo-alignment-layouts.json').read_text())
    content=artwork(name,alignment['coaches'][name]);path=ROOT/'textures'/name
    if path.with_suffix('.svg').read_text()!=content:
        im=render(content)
        path.with_suffix('.svg').write_text(content,encoding='utf-8',newline='\n')
        im.save(path.with_suffix('.png'));path.with_suffix('.dds').write_bytes(encode_dds(im))
    targets={kind:ROOT/'mods'/layout[kind+'_module'] for kind in ['truck','coach']}
    seeds={}
    for kind,previous in [('truck','gtsr-trucks-v0.5.1.scs'),('coach','gtsr-coaches-v0.2.2.scs')]:
        old=ROOT/'mods'/previous
        seeds[kind]=getattr(args,kind+'_seed') or (old if old.exists() else targets[kind])
    member='dlc_volvo_fh_2024/def/vehicle/truck/volvo.fh_2024/paint_job/accessory/gtsrsc_3.sii'
    with zipfile.ZipFile(seeds['truck']) as z:mapping=assignments(z.read(member).decode())
    mapping.update(layout['truck_overrides'])
    package(seeds['truck'],targets['truck'],{member:accessory_text(mapping).encode()},{},set(),'0.5.3',
            'Solar Circuit trucks 0.5.3: FH6 Aero XL Van Leer painted cab wheel arches and Exclusive Aero headlight surrounds navy; all five painted sunshade options white. TK-05 / VAN LEER, body maps and white painted mirrors retained. Other paint jobs unchanged. Blender checked; final ETS2 appearance awaits confirmation.\n')
    package(seeds['coach'],targets['coach'],{'gtsr_solar/'+name+'.dds':path.with_suffix('.dds').read_bytes()},{},set(),'0.2.3',
            'Solar Circuit coaches 0.2.3: Scania Touring HD 13.7 m Standard Painted front intake panel continues the navy/gold band. Select Standard Painted instead of Standard Plastic. MAN/Scania logo alignment retained; other coach maps unchanged. Requires SCS Coaches DLC. Blender checked; final ETS2 appearance awaits confirmation.\n')
    index=json.loads((ROOT/'source/texture-index.json').read_text())
    next(t for t in index if t['name']==name)['scope']='Scania Standard Painted front intake / preserved 0.5.2 logo alignment, 0.5.3'
    (ROOT/'source/texture-index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Built truck 0.5.3 and coach 0.2.3; only Scania front paint and FH6 accessory assignments changed.')


if __name__=='__main__':main()
