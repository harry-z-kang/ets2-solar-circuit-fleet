"""Validate FH6 logo enlargement; --before enables prior-release preservation.
Optional --models adds paint-UV coverage checks using private converted geometry.
"""
from pathlib import Path
import argparse,base64,hashlib,io,json,struct,xml.etree.ElementTree as ET,zipfile
from PIL import Image,ImageChops,ImageDraw,ImageFilter
from build_panel_refinement import art
from build_feedback_fix import assignments
from scs_midformat import read_model
from build_accessory_fix import clip

ROOT=Path(__file__).resolve().parent.parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path)
    parser.add_argument('--models',type=Path)
    args=parser.parse_args()
    layout=json.loads((ROOT/'source/fh6-logo-layout.json').read_text())
    name=layout['texture'];checks=[];proof={}
    def check(name,passed):
        checks.append({'check':name,'passed':bool(passed)})
        assert passed,name
    sha=lambda raw:hashlib.sha256(raw).hexdigest()
    source=(ROOT/'textures'/f'{name}.svg').read_text()
    check('Source matches calibrated layout',source==art(name,layout))
    images=list(ET.fromstring(source).iter('{http://www.w3.org/2000/svg}image'))
    check('Two enlarged side marks',len(images)==3)
    original=(ROOT/'artwork/gtsr-logo-original.png').read_bytes()
    for n,image in enumerate(images[1:]):
        width,height=float(image.get('width')),float(image.get('height'))
        check('Proportional original mark '+str(n),base64.b64decode(image.get('href').split(',',1)[1])==original and abs(width/height-922/186)<1e-10)
        check('Final 10 percent reduction '+str(n),width==936 and width==layout['first_draft_logo_width']*layout['requested_scale_from_draft']*layout['final_reduction'])
    check('Both TK-05 / VAN LEER captions retained',source.count('TK-05 / VAN LEER')==2)
    check('Unchanged navy/gold/white base',base64.b64decode(images[0].get('href').split(',',1)[1])==(ROOT/'artwork/panel-bases'/f'{name}.png').read_bytes())
    raw=(ROOT/'textures'/f'{name}.dds').read_bytes()
    h,w=struct.unpack_from('<II',raw,12);levels=struct.unpack_from('<I',raw,28)[0]
    check('Opaque BC3 with complete mip header',raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and (w,h,levels)==(4096,4096,13))
    expected=128
    for _ in range(levels):
        expected+=max(1,(w+3)//4)*max(1,(h+3)//4)*16;w,h=max(1,w//2),max(1,h//2)
    check('Complete DDS payload',len(raw)==expected)
    decoded=Image.open(io.BytesIO(raw));decoded.load()
    check('Decoded body alpha',decoded.getchannel('A').getextrema()==(255,255))
    for ext in ['png','dds']:
        check('SVG rebuild matches '+ext,(ROOT/'textures'/f'{name}.{ext}').read_bytes()==(ROOT/'rebuilt/textures'/f'{name}.{ext}').read_bytes())
    target=ROOT/'mods'/layout['truck_module']
    member=layout['mount']+'/gtsr_solar/'+name+'.dds'
    acc=layout['mount']+'/def/vehicle/truck/volvo.fh_2024/paint_job/accessory/gtsrsc_3.sii'
    with zipfile.ZipFile(target) as z:
        check('Module integrity and unique members',z.testzip() is None and len(z.namelist())==len(set(z.namelist())))
        check('Final DDS packaged',z.read(member)==raw)
        required=json.loads((ROOT/'source/accessory-fix-layouts.json').read_text())['truck_overrides']
        mapping=assignments(z.read(acc).decode())
        check('All previous painted accessory fixes retained',all(mapping[k]==v for k,v in required.items()) and mapping['mirror.cam_digi_a']=='solid-white')
        with zipfile.ZipFile(ROOT/'rebuilt/mods'/target.name) as rebuilt:
            check('Rebuilt truck preserves every payload',set(z.namelist())==set(rebuilt.namelist()) and all(z.read(n)==rebuilt.read(n) for n in z.namelist()))
        if args.before:
            with zipfile.ZipFile(args.before/'gtsr-trucks-v0.5.3.scs') as old:
                check('Archive inventory retained',set(z.namelist())==set(old.namelist()))
                changed={n for n in z.namelist() if z.read(n)!=old.read(n)}
                check('Only main cab DDS and metadata changed',{member,'Description.txt'}<=changed<={member,'manifest.sii','Description.txt'})
                proof['changed_archive_members']=sorted(changed)
                proof['preserved_archive_members']=len(z.namelist())-len(changed)
    if args.before:
        baseline=json.loads((args.before/'before-SHA256SUMS.json').read_text())
        for path in (ROOT/'textures').iterdir():
            if path.stem!=name and path.suffix in {'.svg','.png','.dds'}:
                check('Unchanged texture '+path.name,sha(path.read_bytes())==baseline[path.relative_to(ROOT).as_posix()])
        for module,baseline_module in [('gtsr-coaches-v0.5.3.scs','gtsr-coaches-v0.2.3.scs'),('gtsr-trailers-v0.5.3.scs','gtsr-trailers-v0.1.scs')]:
            with zipfile.ZipFile(ROOT/'mods'/module) as current, zipfile.ZipFile(args.before/baseline_module) as previous:
                check('Unchanged gameplay payloads '+module,set(current.namelist())==set(previous.namelist()) and all(current.read(n)==previous.read(n) for n in current.namelist() if n not in {'manifest.sii','Description.txt'}))
        diff=ImageChops.difference(Image.open(args.before/'before.png').convert('RGB'),Image.open(ROOT/'textures'/f'{name}.png').convert('RGB'))
        current_base=Image.open(ROOT/'artwork/panel-bases'/f'{name}.png').convert('RGB')
        base_diff=ImageChops.difference(Image.open(args.before/'before-base.png').convert('RGB'),current_base)
        rr,gg,bb=base_diff.split()
        base_mask=ImageChops.lighter(ImageChops.lighter(rr,gg),bb).point(lambda p:255 if p else 0)
        diff.paste((0,0,0),(0,0),base_mask)
        draw=ImageDraw.Draw(diff)
        for box in [(335,2815,1390,3180),(2715,2815,3770,3180)]:draw.rectangle(box,fill=(0,0,0))
        check('Pixels outside the stripe and logo/caption areas unchanged',diff.getbbox() is None)
        calibration=json.loads((ROOT/'source/fh6-stripe-calibration.json').read_text())
        check('Calibrated sloping stripe base',sha((ROOT/'artwork/panel-bases'/f'{name}.png').read_bytes())==calibration['base_sha256'])
    if args.models:
        model=args.models/'vehicle/truck/volvo_fh_2024/cabin/globe_xl_aero_2024.pim'
        mats,parts=read_model(model)
        coverage=Image.new('L',(4096,4096));draw=ImageDraw.Draw(coverage)
        stripe_counts={side:0 for side in ['left','right','front']}
        stripe_errors={side:0 for side in stripe_counts}
        base_pixels=Image.open(ROOT/'artwork/panel-bases'/f'{name}.png').convert('RGB')
        for p in parts:
            if 'truckpaint' not in mats[p['material']]['effect']:continue
            uv=p['streams'][p['aliases']['_TEXCOORD1']]
            for tri in p['triangles']:
                draw.polygon([(uv[i][0]*4096,uv[i][1]*4096) for i in tri],fill=255)
                polygon=[(*p['streams']['_POSITION'][i],uv[i][0]*4096,uv[i][1]*4096) for i in tri]
                for (z0,h0),(z1,h1) in zip(layout['stripe_profile'],layout['stripe_profile'][1:]):
                    band=clip(clip(polygon,lambda q:z0-q[2]),lambda q:q[2]-z1)
                    fn=lambda q:q[1]-(h0+(q[2]-z0)*(h1-h0)/(z1-z0))
                    band=clip(clip(band,fn),lambda q:-fn(q)-layout['gold_width_m'])
                    if len(band)<3:continue
                    area=abs(sum(a[3]*b[4]-b[3]*a[4] for a,b in zip(band,band[1:]+band[:1])))/2
                    if area<4:continue
                    point=[sum(q[j] for q in band)/len(band) for j in range(5)]
                    side='front' if abs(point[0])<1 and point[2]<-3.2 else 'left' if point[0]<-1 else 'right' if point[0]>1 else None
                    if side:
                        pixel=base_pixels.getpixel((int(point[3]),int(point[4])))
                        stripe_counts[side]+=1
                        if pixel!=(179,144,81):stripe_errors[side]+=1
        coverage=coverage.filter(ImageFilter.MaxFilter(3))
        width=layout['logos'][0][2]
        mask=Image.open(io.BytesIO(original)).getchannel('A').resize((width,round(width*186/922)),Image.Resampling.LANCZOS).point(lambda a:255 if a>127 else 0)
        area=sum(mask.histogram()[1:])
        for n,(x,y,width) in enumerate(layout['logos']):
            local=coverage.crop((round(x),round(y),round(x)+mask.width,round(y)+mask.height))
            missing=ImageChops.multiply(mask,ImageChops.invert(local))
            ratio=sum(missing.histogram()[1:])/area
            check('Logo opaque pixels remain on painted cab '+str(n),ratio<.005)
            proof['logo_'+str(n)+'_paint_coverage_fraction']=1-ratio
        for side,count in stripe_counts.items():
            check('Continuous geometry-projected gold stripe '+side,count>=5 and stripe_errors[side]==0)
        proof['gold_stripe_samples']=stripe_counts
        proof['gold_stripe_errors']=stripe_errors
    report={'version':layout['version'],'checks_passed':len(checks),'checks_total':len(checks),'failures':[],
            'linear_logo_scale':936/410,'linear_scale_from_first_draft':936/650,'final_reduction':.9,'proof':proof,'checks':checks,'game_runtime_tested':False}
    (ROOT/'source/fh6-logo-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('FH6_LOGO_VERIFIED',len(checks),proof)


if __name__=='__main__':main()
