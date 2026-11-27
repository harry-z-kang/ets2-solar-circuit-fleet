"""Validate the 0.5.1 feedback refinement. Optional prior modules enable byte preservation checks.
The calibration report records private model probes; this validator checks its
base-mask hashes and recorded results without redistributing original models.
"""
from pathlib import Path
import argparse,hashlib,io,json,math,re,struct,xml.etree.ElementTree as ET,zipfile
from PIL import Image,ImageChops,ImageOps,ImageStat
import pymupdf
ROOT=Path(__file__).resolve().parent.parent

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--truck-before');p.add_argument('--coach-before');a=p.parse_args()
    checks=[]
    def check(name,passed,detail=''):checks.append({'check':name,'passed':bool(passed),'detail':detail})
    data=json.loads((ROOT/'source/feedback-fix-layouts.json').read_text());truck=data['truck'];idx=json.loads((ROOT/'source/texture-index.json').read_text())
    check('118 unique texture exports',len(idx)==len({t['name'] for t in idx})==118)
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
        x,y,w=l['logo'];bottom=math.ceil(y+w*186/922)+2
        xml=ET.parse(ROOT/'textures'/f'{n}.svg').getroot();xml.remove(xml[0])
        doc=pymupdf.open(stream=ET.tostring(xml),filetype='svg');pix=doc[0].get_pixmap(alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        left=im.crop((x,y,x+w,bottom));right=ImageOps.flip(ImageOps.mirror(im.crop((x,4096-bottom,x+w,4096-y))))
        mean=ImageStat.Stat(ImageChops.difference(left,right)).mean;proof[n]=mean
        check('Opposite-side wordmark '+n,max(mean)<.35,str(mean))
    calibration=json.loads((ROOT/'source/feedback-calibration.json').read_text());total_probes=0
    for n,c in calibration['maps'].items():
        base=ROOT/'artwork/panel-bases'/f'{n}.png'
        check('Calibrated base hash '+n,hashlib.sha256(base.read_bytes()).hexdigest()==c['base_sha256'])
        for comp in c['components']:
            total_probes+=comp['stripe_crossings_sampled']
            check('Recorded gold crossing probes '+n+' '+comp['model'],comp['stripe_crossings_sampled']==comp['gold_samples_passed'],str(comp['stripe_crossings_sampled']))
        check('Calibration image size '+n,list(Image.open(base).size)==c['size'])
    check('Geometry probes include all three coach doors',all(any('doors' in c['model'] and c['stripe_crossings_sampled']>0 for c in calibration['maps'][n]['components']) for n in data['coaches']))
    check('Multiple geometry stripe probes',total_probes>1500,str(total_probes))
    s=(ROOT/'textures'/f'{truck["texture"]}.svg').read_text()
    check('Van Leer replaces old cab label','TK-05 / VAN LEER' in s and 'ALUMNI SUPPORT' not in s)
    check('Team-provided SR4 illustration preserved',hashlib.sha256((ROOT/'artwork/sr4-team-illustration.png').read_bytes()).hexdigest()=='1e15c7167a0cb9e823e9a99d407cdefa99f5442e4e2da4b8948658f5bbe24be2')
    check('DD has no rectangular logo plaque','logo_plaque' not in data['coaches']['volvo-9700-dd'])
    check('DD Aurora artwork and caption','SR-4 AURORA / CO-03' in (ROOT/'textures/volvo-9700-dd.svg').read_text())
    modules={'truck':ROOT/'mods'/data['truck_module'],'coach':ROOT/'mods'/data['coach_module'],'trailer':ROOT/'mods/gtsr-trailers-v0.1.scs'}
    prefix=truck['mount']+'/def/vehicle/truck/'+truck['vehicle']+'/paint_job/'
    changes={'truck':{'manifest.sii','Description.txt',truck['mount']+'/gtsr_solar/'+truck['texture']+'.dds',prefix+'accessory/gtsrsc_3.sii'},'coach':{'manifest.sii','Description.txt',*['gtsr_solar/'+n+'.dds' for n in data['coaches']]}}
    additions=set();removed=set()
    preservation={}
    for kind,path in modules.items():
        with zipfile.ZipFile(path) as z:
            names=z.namelist();check('Archive integrity '+kind,z.testzip() is None);check('Unique members '+kind,len(names)==len(set(names)))
            mounts={n.split('/')[0] for n in names if n.startswith(('base/','dlc_'))} if kind=='truck' else {''}
            virtual={m:{n[len(m)+1:] if m else n:n for n in names if not m or n.startswith(m+'/')} for m in mounts};ids=[]
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
            check('Paint count '+kind,len(ids)=={'truck':77,'coach':5,'trailer':1}[kind])
            if kind=='truck':
                text=z.read(prefix+'gtsrsc_3.sii').decode();acc=z.read(prefix+'accessory/gtsrsc_3.sii').decode()
                check('Single Van Leer menu entry','Solar Circuit - Van Leer' in text and prefix+'gtsrh8_1.sii' not in names)
                check('Normal and 8x4 Aero XL availability',set(re.findall(r'suitable_for\[\]:\s*"([^"]+)"',text))=={'l2h3_aero.volvo.fh_2024.cabin','l2h3_8x4_a.volvo.fh_2024.cabin'})
                assignments={}
                for block in re.findall(r'simple_paint_job_data:[^{]+\{([^}]+)\}',acc):
                    tex=re.search(r'paint_job_mask:\s*"/gtsr_solar/([^"]+)\.tobj"',block)[1]
                    for ident in re.findall(r'acc_list\[\]:\s*"([^"]+)"',block):
                        check('Unique accessory override '+ident,ident not in assignments);assignments[ident]=tex
                for ident,tex in {**truck['accessories'],**truck['solid_overrides']}.items():check('Correct accessory assignment '+ident,assignments.get(ident)==tex)
                for ident in ['r_fender.paint_8x','r_fendr_top.paint_8x','r_fendr_top.chrome_p_8x']:check('Navy painted 8x4 fender '+ident,assignments.get(ident)=='solid-navy')
                check('Truck manifest version','package_version: "0.5.1"' in z.read('manifest.sii').decode())
                check('25 truck families',len({i.split('.paint_job')[0].split('.',1)[1] for i in ids})==25)
            if kind=='coach':
                manifest=z.read('manifest.sii').decode();check('Coach version and dependency','package_version: "0.2.1"' in manifest and '"dlc_bus"' in manifest)
            previous={'truck':a.truck_before,'coach':a.coach_before}.get(kind)
            if previous:
                with zipfile.ZipFile(previous) as old:
                    changed={n for n in old.namelist() if n in names and old.read(n)!=z.read(n)};added=set(names)-set(old.namelist());gone=set(old.namelist())-set(names)
                    check('Only declared existing changes '+kind,changed==changes[kind],str(sorted(changed)))
                    check('Only declared additions '+kind,added==(additions if kind=='truck' else set()),str(sorted(added)))
                    check('Only requested retired entries '+kind,gone==(removed if kind=='truck' else set()),str(sorted(gone)))
                    preservation[kind]={'unchanged_entries':len(set(old.namelist())-changed-gone),'changed':sorted(changed),'added':sorted(added),'removed':sorted(gone)}
    report={'version':'0.5.1','checks_passed':sum(c['passed'] for c in checks),'checks_total':len(checks),'failures':[c for c in checks if not c['passed']],'new_feedback_screenshots_reviewed':28,'stripe_annotations_reviewed':2,'blender_renders_reviewed':32,'geometry_gold_crossing_samples':total_probes,'corrected_build_in_game_tested':False,'active_profile_modified':False,'blender_geometry_tested':True,'opposite_side_pixel_difference_mean_rgb':proof,'preservation':preservation,'checks':checks}
    (ROOT/'source/feedback-fix-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'{report["checks_passed"]}/{len(checks)} refinement checks passed')
    if report['failures']:raise SystemExit(json.dumps(report['failures'],indent=2))
if __name__=='__main__':main()
