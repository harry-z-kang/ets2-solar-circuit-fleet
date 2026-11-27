"""Validate the 0.4 package; optional extracted SCS roots enable unit checks.

Use --game-defs ROOT repeatedly for base, truck DLC and tuning DLC roots.
Use --previous-mod gtsr-trucks-v0.3.scs for the preservation comparison.
These checks do not launch ETS2 or establish in-game visual correctness.
"""
from pathlib import Path
import argparse,io,json,math,re,struct,zipfile
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-defs',action='append',default=[]);p.add_argument('--previous-mod');p.add_argument('--overlays-reviewed',action='store_true');args=p.parse_args()
    results=[]
    def check(name,passed,detail=''):results.append({'check':name,'passed':bool(passed),'detail':detail})
    support=json.loads((ROOT/'source/mercedes-daf-support.json').read_text());layouts=json.loads((ROOT/'source/mercedes-daf-layouts.json').read_text());index=json.loads((ROOT/'source/texture-index.json').read_text())
    expected_models={'mercedes.actros','mercedes.actros2014','daf.xf','daf.xf_euro6','daf.2021','daf.xd','daf.xf_electric'}
    check('All seven requested SCS families',{f['vehicle_id'] for f in support['families']}==expected_models)
    check('114 distinct exported texture sets',len(index)==len({t['name'] for t in index})==114)
    check('29 new exported maps',sum(t['name'].startswith('md_') for t in index)==29)
    check('20 unique cabin atlases',len(layouts)==20)
    for t in index:
        name=t['name'];b=(ROOT/'textures'/f'{name}.dds').read_bytes();h,w=struct.unpack_from('<II',b,12);levels=struct.unpack_from('<I',b,28)[0]
        check('DDS dimensions '+name,[w,h]==t['size'])
        check('BC3 full mip header '+name,b[:4]==b'DDS ' and b[84:88]==b'DXT5' and levels==1+int(math.log2(max(w,h))))
        expected=128;ww,hh=w,h
        for _ in range(levels):expected+=max(1,(ww+3)//4)*max(1,(hh+3)//4)*16;ww=max(1,ww//2);hh=max(1,hh//2)
        check('Complete mip payload '+name,len(b)==expected)
        im=Image.open(io.BytesIO(b));im.load();check('Opaque decoded DDS '+name,im.size==(w,h) and im.getchannel('A').getextrema()==(255,255))
        png=Image.open(ROOT/'textures'/f'{name}.png');png.load();check('PNG and SVG source '+name,png.size==(w,h) and (ROOT/'textures'/f'{name}.svg').is_file())
    for alias,source in support['heavy_aliases'].items():
        for ext in ['svg','png','dds']:check('Heavy alias '+alias+'.'+ext,(ROOT/'textures'/f'{alias}.{ext}').read_bytes()==(ROOT/'textures'/f'{source}.{ext}').read_bytes())
    def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
    for name,l in layouts.items():
        for i,(x,y,w) in enumerate(l['logos']):
            bounds=[x,y,x+w,y+w*186/922];side=l['sides'][i]
            check('Logo within planned side band '+name+' '+str(i),bounds[0]>=side[0] and bounds[1]>=side[1]+16 and bounds[2]<=side[2] and bounds[3]<=side[3])
            check('Logo clear of marked door handles '+name+' '+str(i),not any(overlap(bounds,h) for h in l['handle_boxes']))
    units={};cabins={};stock={}
    for root in args.game_defs:
        for p in (Path(root)/'def/vehicle/truck').glob('*/*/*.sii'):
            if p.parent.name not in ['cabin','chassis']:continue
            text=p.read_text(errors='replace');m=re.search(r'accessory_(cabin|chassis)_data\s*:\s*(\S+)',text)
            if m:
                units[m.group(2)]=text
                if m.group(1)=='cabin':cabins.setdefault(p.parent.parent.name,set()).add(m.group(2))
        for p in (Path(root)/'def/vehicle/truck').glob('*/accessory/*/*.sii'):
            text=p.read_text(errors='replace');m=re.search(r'accessory_\w+_data\s*:\s*(\S+)',text)
            if m:stock.setdefault(p.parent.parent.parent.name,set()).add(p.parent.name+'.'+m.group(1).split('.')[0])
    if args.game_defs:
        for f in support['families']:
            key=f['vehicle_id'];check('Complete installed cabin inventory '+key,cabins[key]==set(f['observed_cabin_units']))
            check('Current stock and SCS tuning accessory IDs '+key,set(f['accessory_assignments'])<=stock[key],str(sorted(set(f['accessory_assignments'])-stock[key])))
    with zipfile.ZipFile(ROOT/'mods/gtsr-trucks-v0.4.scs') as z:
        names=z.namelist();check('Archive integrity',z.testzip() is None);check('Unique archive paths',len(names)==len(set(names)))
        mounts={n.split('/')[0] for n in names if n.startswith(('base/','dlc_'))}
        check('Expected conditional mounts',mounts=={'base','dlc_daf_2021','dlc_daf_xd','dlc_daf_xf_electric','dlc_volvo_fh_2021','dlc_volvo_fh_2024','dlc_iveco_sway','dlc_man_tgx_2020','dlc_renault_etech_t'})
        lookup={m:{n[len(m)+1:]:n for n in names if n.startswith(m+'/')} for m in mounts}
        unit_ids=[]
        for mount,files in sorted(lookup.items()):
            available={**lookup['base'],**files}
            for virtual,actual in sorted(files.items()):
                if virtual.endswith('.tobj'):
                    b=z.read(actual);length=struct.unpack_from('<I',b,40)[0];target=b[48:48+length].decode().lstrip('/')
                    check('Mounted TOBJ '+actual,target in available,target)
                elif virtual.endswith(('.sii','.mat')):
                    text=z.read(actual).decode();check('Balanced definition '+actual,text.count('{')==text.count('}'))
                    for ref in re.findall(r'paint_job_mask:\s*"/([^"]+)"',text):check('Mounted mask '+actual,ref in available,ref)
                    if '/paint_job/' in actual and '/accessory/' not in actual:unit_ids+=re.findall(r'accessory_paint_job_data\s*:\s*(\S+)',text)
                    if args.game_defs:
                        for u in re.findall(r'suitable_for\[\]:\s*"([^"]+)"',text):check('Installed unit '+u,u in units)
        defs=[n for n in names if '/paint_job/' in n and '/accessory/' not in n and n.endswith('.sii')]
        check('78 unique paint-job definitions',len(defs)==len(unit_ids)==len(set(unit_ids))==78)
        check('25 truck families',len({n.split('/def/vehicle/truck/')[1].split('/')[0] for n in defs})==25)
        check('19 new standard definitions',sum('/gtsrmd_' in n for n in defs)==19)
        check('20 retained heavy definitions',sum('/gtsrh8_' in n for n in defs)==20)
        for f in support['families']:
            key=f['vehicle_id'];prefix=f['mount']+f'/def/vehicle/truck/{key}/paint_job/'
            for i,c in enumerate(c for c in f['cabins'] if not c['heavy']):
                fn=prefix+f'gtsrmd_{i}.sii';text=z.read(fn).decode();refs=re.findall(r'suitable_for\[\]:\s*"([^"]+)"',text)
                check('Exact cabin restriction '+fn,set(refs)=={cid+'.'+key+'.cabin' for cid in c['ids']})
                check('Exact cabin mask '+fn,f'/gtsr_solar/{c["texture"]}.tobj' in text)
                at=z.read(prefix+f'accessory/gtsrmd_{i}.sii').decode();mapped={}
                for block in re.findall(r'simple_paint_job_data:[^{]+\{([^}]+)\}',at):
                    texture=re.search(r'paint_job_mask:\s*"/gtsr_solar/([^"]+)\.tobj"',block).group(1)
                    for acc in re.findall(r'acc_list\[\]:\s*"([^"]+)"',block):mapped[acc]=texture
                check('Exact accessory mappings '+fn,mapped==f['accessory_assignments'])
        heavy=json.loads((ROOT/'source/8x4-support.json').read_text())
        for f in heavy['families']:
            for i,c in enumerate(f['cabins']):
                fn=f['mount']+f'/def/vehicle/truck/{f["vehicle_id"]}/paint_job/gtsrh8_{i}.sii';text=z.read(fn).decode()
                check('Preserved 8x4 restriction '+fn,set(re.findall(r'suitable_for\[\]:\s*"([^"]+)"',text))=={c['unit'],*c['chassis_units']})
        check('Manifest version','package_version: "0.4.0"' in z.read('manifest.sii').decode())
        check('Mod image dimensions',Image.open(io.BytesIO(z.read('Image.jpg'))).size==(276,162))
        exports={name:t['mount'] for name,t in support['textures'].items()}
        for alias,name in support['heavy_aliases'].items():exports[alias]=support['textures'][name]['mount']
        for name,mount in exports.items():check('Exact exported DDS '+name,z.read(mount+'/gtsr_solar/'+name+'.dds')==(ROOT/'textures'/f'{name}.dds').read_bytes())
        if args.previous_mod:
            exceptions={'manifest.sii','Image.jpg','Description.txt',*[mount+'/gtsr_solar/'+name+'.dds' for name,mount in exports.items()]}
            refreshed={f['vehicle_id'] for f in support['families']}
            for f in heavy['families']:
                if f['vehicle_id'] not in refreshed:continue
                for i,c in enumerate(f['cabins']):exceptions.add(f['mount']+f'/def/vehicle/truck/{f["vehicle_id"]}/paint_job/accessory/gtsrh8_{i}.sii')
            with zipfile.ZipFile(args.previous_mod) as old:
                keep=[n for n in old.namelist() if n not in exceptions]
                check('Unrelated previous gameplay entries preserved',all(n in names and old.read(n)==z.read(n) for n in keep),str(len(keep))+' byte-identical entries')
                changed=[n for n in old.namelist() if n in names and old.read(n)!=z.read(n)]
                check('Only declared previous entries changed',set(changed)<=exceptions,str(changed))
    for filename in ['gtsr-trailers-v0.1.scs','gtsr-coaches-v0.1.scs']:
        with zipfile.ZipFile(ROOT/'mods'/filename) as z:check('Retained module integrity '+filename,z.testzip() is None)
    report={'version':'0.4.0','checks_passed':sum(c['passed'] for c in results),'checks_total':len(results),'failures':[c for c in results if not c['passed']],'local_game_version_observed':'1.62.3.3','stock_and_tuning_units_checked':bool(args.game_defs),'new_template_overlays_reviewed':30 if args.overlays_reviewed else 0,'user_screenshots_reviewed':27,'new_liveries_in_game_tested':False,'active_profile_modified':False,'limits':['New Mercedes/DAF alignment, material finish, opposite-side reading direction and accessory combinations require an in-game check.','The supplied screenshots document issues in earlier versions, including mirrored coach text; this Mercedes/DAF expansion does not claim those other vehicle issues are fixed.'],'checks':results}
    (ROOT/'source/mercedes-daf-validation.json').write_bytes(json.dumps(report,indent=2).encode())
    print(f'{report["checks_passed"]}/{len(results)} checks passed')
    if report['failures']:raise SystemExit(json.dumps(report['failures'],indent=2))

if __name__=='__main__':main()
