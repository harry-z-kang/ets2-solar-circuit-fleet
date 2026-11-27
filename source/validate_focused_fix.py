"""Check the focused fix, optionally comparing the original truck/coach archives.

--truck-before and --coach-before enable strict preservation checks.
--volvo-tuning-defs points to a privately extracted official tuning DLC root.
--overlays-reviewed records visual review; this does not prove ETS2 runtime results.
"""
from pathlib import Path
import argparse,hashlib,io,json,math,re,struct,xml.etree.ElementTree as ET,zipfile
from PIL import Image,ImageChops,ImageOps,ImageStat
ROOT=Path(__file__).resolve().parent.parent

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--truck-before');p.add_argument('--coach-before');p.add_argument('--volvo-tuning-defs');p.add_argument('--overlays-reviewed',action='store_true');a=p.parse_args()
    checks=[]
    def check(name,passed,detail=''):checks.append({'check':name,'passed':bool(passed),'detail':detail})
    data=json.loads((ROOT/'source/focused-fix-layouts.json').read_text());truck=data['truck'];idx=json.loads((ROOT/'source/texture-index.json').read_text())
    targeted={*data['coaches'],truck['texture'],truck['heavy_texture']}
    check('115 unique texture exports',len(idx)==len({t['name'] for t in idx})==115)
    for t in idx:
        n=t['name'];raw=(ROOT/'textures'/f'{n}.dds').read_bytes();h,w=struct.unpack_from('<II',raw,12);levels=struct.unpack_from('<I',raw,28)[0]
        check('Dimensions '+n,[w,h]==t['size'])
        check('BC3 complete mip header '+n,raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and levels==1+int(math.log2(max(w,h))))
        expected=128;ww,hh=w,h
        for _ in range(levels):expected+=max(1,(ww+3)//4)*max(1,(hh+3)//4)*16;ww=max(1,ww//2);hh=max(1,hh//2)
        check('Complete DDS payload '+n,len(raw)==expected)
        im=Image.open(io.BytesIO(raw));im.load();check('Decoded opaque body alpha '+n,im.getchannel('A').getextrema()==(255,255))
        png=Image.open(ROOT/'textures'/f'{n}.png');png.load();check('Editable source and PNG '+n,png.size==(w,h) and ET.parse(ROOT/'textures'/f'{n}.svg').getroot() is not None)
    proof={}
    for n,l in data['coaches'].items():
        x,y,w=l['logo'];bay=l['safe_bay'];bottom=l['fleet_y']+5
        check('Coach logo inside clear bay '+n,x>=bay[0] and y>=bay[1] and x+w<=bay[2] and y+w*186/922<=bay[3])
        check('Coach fleet line inside clear bay '+n,l['fleet_y']<=bay[3])
        im=Image.open(ROOT/'textures'/f'{n}.png').convert('RGB')
        left=im.crop((x,y,x+w,bottom));right=ImageOps.flip(ImageOps.mirror(im.crop((x,4096-bottom,x+w,4096-y))))
        mean=ImageStat.Stat(ImageChops.difference(left,right)).mean;proof[n]=mean
        check('Rendered opposite-side lettering agrees with left '+n,max(mean)<.25,str(mean))
        check('Distinct correct coach fleet ID '+n,l['fleet'] in (ROOT/'textures'/f'{n}.svg').read_text())
    def overlap(x,y):return min(x[2],y[2])>max(x[0],y[0]) and min(x[3],y[3])>max(x[1],y[1])
    for i,(x,y,w) in enumerate(truck['logos']):
        for field,box in [('logo',[x,y,x+w,y+w*186/922]),('fleet line',[x,truck['fleet_y']-22,x+300,truck['fleet_y']+3])]:
            check('FH6 '+field+' clear of handle/seam '+str(i),not any(overlap(box,b) for b in truck['handle_boxes']+truck['door_seams']))
    check('Distinct heavy role text','TK-05 / HEAVY SUPPORT' in (ROOT/'textures'/f'{truck["heavy_texture"]}.svg').read_text())
    check('Standard role text retained','TK-05 / ALUMNI SUPPORT' in (ROOT/'textures'/f'{truck["texture"]}.svg').read_text())
    mounted={};modules={'truck':ROOT/'mods/gtsr-trucks-v0.4.1.scs','coach':ROOT/'mods/gtsr-coaches-v0.1.1.scs','trailer':ROOT/'mods/gtsr-trailers-v0.1.scs'}
    prefix=truck['mount']+'/def/vehicle/truck/'+truck['vehicle']+'/paint_job/'
    exceptions={'truck':{'manifest.sii','Description.txt',truck['mount']+'/gtsr_solar/'+truck['texture']+'.dds',prefix+'gtsrh8_1.sii',prefix+'accessory/gtsrh8_1.sii'},'coach':{'manifest.sii','Description.txt',*['gtsr_solar/'+n+'.dds' for n in data['coaches']]}}
    additions={truck['mount']+'/gtsr_solar/'+truck['heavy_texture']+'.'+ext for ext in ['dds','tobj']}
    preservation={}
    for kind,path in modules.items():
        with zipfile.ZipFile(path) as z:
            names=z.namelist();check('Archive integrity '+kind,z.testzip() is None);check('Unique members '+kind,len(names)==len(set(names)))
            mounts={n.split('/')[0] for n in names if n.startswith(('base/','dlc_'))} if kind=='truck' else {''}
            virtual={m:{n[len(m)+1:] if m else n:n for n in names if not m or n.startswith(m+'/')} for m in mounts}
            ids=[]
            for m,files in virtual.items():
                available={**virtual.get('base',{}),**files}
                for v,n in files.items():
                    raw=z.read(n)
                    if v.endswith('.tobj'):
                        length=struct.unpack_from('<I',raw,40)[0];target=raw[48:48+length].decode().lstrip('/')
                        check('Mounted TOBJ '+kind+' '+n,target in available,target)
                    if v.endswith(('.sii','.mat')):
                        s=raw.decode();check('Balanced definition '+kind+' '+n,s.count('{')==s.count('}'))
                        for ref in re.findall(r'(?:paint_job_mask|texture)\s*:\s*"/([^"]+)"',s):check('Mounted material '+kind+' '+n,ref in available,ref)
                        ids+=re.findall(r'accessory_paint_job_data\s*:\s*(\S+)',s)
                    if v.startswith('gtsr_solar/') and v.endswith('.dds'):
                        local=ROOT/'textures'/Path(v).name
                        if local.exists():check('Module matches export '+kind+' '+v,raw==local.read_bytes())
            check('Unique paint IDs '+kind,len(ids)==len(set(ids)))
            check('Paint count '+kind,len(ids)=={'truck':78,'coach':5,'trailer':1}[kind])
            if kind=='truck':
                heavy=z.read(prefix+'gtsrh8_1.sii').decode()
                check('Heavy uses dedicated map',f'/{"gtsr_solar"}/{truck["heavy_texture"]}.tobj' in heavy)
                check('Heavy exact restriction retained',set(re.findall(r'suitable_for\[\]:\s*"([^"]+)"',heavy))=={'l2h3_8x4_a.volvo.fh_2024.cabin','8x4.volvo.fh_2024.chassis'})
                check('Alumni uses standard map',truck['texture']+'.tobj' in z.read(prefix+'gtsrsc_3.sii').decode())
                text=z.read(prefix+'accessory/gtsrh8_1.sii').decode();block=re.search(r'simple_paint_job_data: \.focus_fenders\s*\{([^}]+)\}',text).group(1)
                check('Heavy painted-fender override assignments',set(re.findall(r'acc_list\[\]:\s*"([^"]+)"',block))==set(truck['heavy_accessory_overrides']) and 'solid-navy.tobj' in block)
                check('Truck manifest version','package_version: "0.4.1"' in z.read('manifest.sii').decode())
            if kind=='coach':
                manifest=z.read('manifest.sii').decode();check('Coach manifest and DLC retained','package_version: "0.1.1"' in manifest and '"dlc_bus"' in manifest)
            previous={'truck':a.truck_before,'coach':a.coach_before}.get(kind)
            if previous:
                with zipfile.ZipFile(previous) as old:
                    changed={n for n in old.namelist() if n in names and old.read(n)!=z.read(n)}
                    added=set(names)-set(old.namelist());removed=set(old.namelist())-set(names)
                    check('Only focused existing entries changed '+kind,changed==exceptions[kind],str(sorted(changed)))
                    check('Only declared additions '+kind,added==(additions if kind=='truck' else set()),str(sorted(added)))
                    check('No archive entries removed '+kind,not removed)
                    preservation[kind]={'unchanged_entries':len(old.namelist())-len(changed),'changed':sorted(changed),'added':sorted(added)}
                    if kind=='coach':
                        for n in ['man-lions-coach-121','scania-touring-129']:check('Short coach unchanged '+n,z.read('gtsr_solar/'+n+'.dds')==old.read('gtsr_solar/'+n+'.dds'))
    if a.volvo_tuning_defs:
        observed=set()
        for p in (Path(a.volvo_tuning_defs)/'def/vehicle/truck/volvo.fh_2024/accessory').glob('*/*.sii'):
            m=re.search(r'accessory_addon_data\s*:\s*(\S+)',p.read_text())
            if m:observed.add(p.parent.name+'.'+m.group(1).split('.')[0])
        for acc in truck['heavy_accessory_overrides']:check('Verified official painted accessory '+acc,acc in observed)
    report={'version':'0.4.1','checks_passed':sum(c['passed'] for c in checks),'checks_total':len(checks),'failures':[c for c in checks if not c['passed']],'feedback_screenshots_reviewed':25,'focused_template_overlays_reviewed':5 if a.overlays_reviewed else 0,'official_volvo_tuning_units_verified':bool(a.volvo_tuning_defs),'corrected_build_in_game_tested':False,'active_profile_modified':False,'opposite_side_pixel_difference_mean_rgb':proof,'preservation':preservation,'limits':['Right-side flat projection uses the UV orientation established by the supplied game screenshots; it is not a new game capture.','The corrected build still needs in-game confirmation of seams, gloss and accessory combinations.'],'checks':checks}
    (ROOT/'source/focused-fix-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'{report["checks_passed"]}/{len(checks)} focused checks passed')
    if report['failures']:raise SystemExit(json.dumps(report['failures'],indent=2))

if __name__=='__main__':main()
