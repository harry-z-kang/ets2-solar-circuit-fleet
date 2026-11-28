"""Check the 0.5.3 exports and archives, with optional private geometry probes.

--before DIR enables byte-preservation checks against copies of the prior modules
and before-SHA256SUMS.json. --models DIR verifies the painted intake on its mesh.
"""
from pathlib import Path
import argparse,hashlib,io,json,struct,zipfile
from PIL import Image,ImageChops
from align_coach_logos import artwork
from build_feedback_fix import assignments
from scs_midformat import read_model,locators,transform

ROOT=Path(__file__).resolve().parent.parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path)
    parser.add_argument('--models',type=Path)
    args=parser.parse_args()
    layout=json.loads((ROOT/'source/accessory-fix-layouts.json').read_text())
    checks=[]
    def check(name,passed):
        checks.append({'check':name,'passed':bool(passed)})
        assert passed,name
    sha=lambda raw:hashlib.sha256(raw).hexdigest()
    name=layout['scania_front']['texture']
    alignment=json.loads((ROOT/'source/logo-alignment-layouts.json').read_text())
    check('Scania side logo placements retained',(ROOT/'textures'/f'{name}.svg').read_text()==artwork(name,alignment['coaches'][name]))
    calibration=json.loads((ROOT/'source/accessory-front-calibration.json').read_text())
    base=ROOT/'artwork/panel-bases'/f'{name}.png'
    check('Calibrated front color base',sha(base.read_bytes())==calibration['base_sha256'])
    check('Same front stripe profile as body',layout['scania_front']['front_profile']==json.loads((ROOT/'source/feedback-fix-layouts.json').read_text())['coaches'][name]['front_profile'])
    raw=(ROOT/'textures'/f'{name}.dds').read_bytes()
    h,w=struct.unpack_from('<II',raw,12);levels=struct.unpack_from('<I',raw,28)[0]
    check('Complete BC3 mip header',raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and (w,h,levels)==(8192,4096,14))
    expected=128
    for _ in range(levels):
        expected+=max(1,(w+3)//4)*max(1,(h+3)//4)*16;w,h=max(1,w//2),max(1,h//2)
    check('Complete DDS payload',len(raw)==expected)
    im=Image.open(io.BytesIO(raw));im.load()
    check('Opaque body paint alpha',im.getchannel('A').getextrema()==(255,255))
    for ext in ['png','dds']:
        check('SVG rebuild '+ext,(ROOT/'textures'/f'{name}.{ext}').read_bytes()==(ROOT/'rebuilt/textures'/f'{name}.{ext}').read_bytes())
    truck_member='dlc_volvo_fh_2024/def/vehicle/truck/volvo.fh_2024/paint_job/accessory/gtsrsc_3.sii'
    preserved={}
    for kind,previous in [('truck','gtsr-trucks-v0.5.1.scs'),('coach','gtsr-coaches-v0.2.2.scs')]:
        target=ROOT/'mods'/layout[kind+'_module']
        with zipfile.ZipFile(target) as z:
            check('Integrity and unique members '+kind,z.testzip() is None and len(z.namelist())==len(set(z.namelist())))
            if kind=='truck':
                mapping=assignments(z.read(truck_member).decode())
                for ident,texture in layout['truck_overrides'].items():
                    check('FH6 painted accessory '+ident,mapping[ident]==texture)
                check('White digital mirrors retained',mapping['mirror.cam_digi_a']=='solid-white')
                for texture in set(layout['truck_overrides'].values()):
                    check('Solid override texture exists '+texture,any(prefix+'gtsr_solar/'+texture+'.tobj' in z.namelist() for prefix in ['base/','dlc_volvo_fh_2024/']))
                check('TK-05 / VAN LEER retained','TK-05 / VAN LEER' in (ROOT/'textures/trk_volvo_fh_2024_cabin_b_aero.svg').read_text())
            else:
                check('Packaged final Scania DDS',z.read('gtsr_solar/'+name+'.dds')==raw)
            with zipfile.ZipFile(ROOT/'rebuilt/mods'/target.name) as rebuilt:
                check('Rebuild preserves all module payloads '+kind,set(z.namelist())==set(rebuilt.namelist()) and all(z.read(n)==rebuilt.read(n) for n in z.namelist()))
            if args.before:
                with zipfile.ZipFile(args.before/previous) as old:
                    check('Archive inventory retained '+kind,set(z.namelist())==set(old.namelist()))
                    changed={n for n in z.namelist() if z.read(n)!=old.read(n)}
                    expected={'manifest.sii','Description.txt',truck_member if kind=='truck' else 'gtsr_solar/'+name+'.dds'}
                    check('Only scoped members changed '+kind,changed==expected)
                    preserved[kind]={'changed':sorted(changed),'unchanged_members':len(z.namelist())-len(changed)}
                    if kind=='truck':
                        before_mapping=assignments(old.read(truck_member).decode())
                        check('Only requested accessory mapping changed',mapping=={**before_mapping,**layout['truck_overrides']})
    if args.before:
        baseline=json.loads((args.before/'before-SHA256SUMS.json').read_text())
        for path in (ROOT/'textures').iterdir():
            if path.stem!=name and path.suffix in {'.svg','.png','.dds'}:
                check('Unchanged texture '+path.name,sha(path.read_bytes())==baseline[path.relative_to(ROOT).as_posix()])
        check('Preserved logo calibration JSON',sha((ROOT/'source/logo-alignment-layouts.json').read_bytes())==baseline['source/logo-alignment-layouts.json'])
        check('Trailer byte preservation',sha((ROOT/'mods/gtsr-trailers-v0.1.scs').read_bytes())==baseline['mods/gtsr-trailers-v0.1.scs'])
        old_image=Image.open(args.before/(name+'.png')).convert('RGB')
        new_image=Image.open(ROOT/'textures'/f'{name}.png').convert('RGB')
        bbox=ImageChops.difference(old_image,new_image).getbbox()
        check('Scania changes confined to reserved front intake UV island',bbox is not None and bbox[0]>=6100 and bbox[1]>=2000 and bbox[2]<=7140 and bbox[3]<=2380)
        for side in alignment['coaches'][name]['sides']:
            x,y,w=side['logo'];h=w*186/922
            if side['side']=='right':y=4096-y-h
            box=(int(x)-5,int(y)-5,int(x+w)+5,int(y+h)+5)
            check('Unchanged Scania logo pixels '+side['side'],ImageChops.difference(old_image.crop(box),new_image.crop(box)).getbbox() is None)
        preserved['scania_changed_pixel_bounds']=bbox
    probes={}
    if args.models:
        spec=layout['scania_front'];mat,pieces=read_model(args.models/spec['model'])
        mount=locators(args.models/'vehicle/bus/scania_touring_23/cabin/cab_137h6.pim')[spec['locator']]
        pixels=Image.open(base).convert('RGB');counts={'navy':0,'gold':0,'white':0}
        expected_colors={'navy':(5,30,57),'gold':(179,144,81),'white':(255,255,255)}
        for p in pieces:
            if 'truckpaint' not in mat[p['material']]['effect']:continue
            ss=p['streams'];positions=[transform(v,mount) for v in ss['_POSITION']];uv=ss[p['aliases']['_TEXCOORD1']]
            for tri in p['triangles']:
                xyz=[sum(positions[i][j] for i in tri)/3 for j in range(3)]
                u,v=[sum(uv[i][j] for i in tri)/3 for j in range(2)]
                profile=spec['front_profile'];height=next(h0+(xyz[2]-z0)*(h1-h0)/(z1-z0) for (z0,h0),(z1,h1) in zip(profile,profile[1:]) if z0<=xyz[2]<=z1)
                d=xyz[1]-height
                color='navy' if d<-.06 else 'gold' if -.033<d<-.012 else 'white' if d>.018 else None
                if color:
                    actual=pixels.getpixel((int(u*pixels.width),int(v*pixels.height)))
                    check('Scania front '+color+' probe '+str(sum(counts.values())),actual==expected_colors[color])
                    counts[color]+=1
        check('Front coverage sampled in all three colors',counts['navy']>100 and counts['gold']>5 and counts['white']>5)
        probes=counts
        for ident,path in layout['painted_sunshields'].items():
            mats,parts=read_model(args.models/path)
            check('Paintable sunshade verified '+ident,any('truckpaint' in mats[p['material']]['effect'] for p in parts))
    report={'version':'0.5.3','checks_passed':len(checks),'checks_total':len(checks),'failures':[],
            'front_geometry_samples':probes,'archive_preservation':preserved,'checks':checks,'game_runtime_tested':False}
    (ROOT/'source/accessory-fix-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('ACCESSORY_FIX_VERIFIED',len(checks),'front samples:',probes)


if __name__=='__main__':main()
