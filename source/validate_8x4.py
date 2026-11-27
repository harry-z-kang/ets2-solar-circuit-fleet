"""Validate the 0.3 fleet. Optional --game-defs roots enable stock-unit checks.

Each root should contain def/vehicle/truck from the official SCS extractor.
--previous-mod verifies preservation against the 0.2 truck module.
No game data is copied into the report. This does not launch ETS2.
"""
from pathlib import Path
import argparse, io, json, math, re, struct, zipfile
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game-defs',action='append',default=[])
    p.add_argument('--previous-mod');p.add_argument('--overlays-reviewed',action='store_true')
    args=p.parse_args();checks=[]
    def check(name,ok,detail=''):
        checks.append({'check':name,'passed':bool(ok),'detail':detail})
    scope=json.loads((ROOT/'source/8x4-support.json').read_text())
    index=json.loads((ROOT/'source/texture-index.json').read_text())
    check('85 unique exported texture sets',len(index)==len({t['name'] for t in index})==85)
    check('10 new authored maps',sum(t['name'].startswith('h8_') for t in index)==10)
    for t in index:
        name=t['name'];raw=(ROOT/'textures'/f'{name}.dds').read_bytes()
        h,w=struct.unpack_from('<II',raw,12);levels=struct.unpack_from('<I',raw,28)[0]
        check('DDS dimensions '+name,[w,h]==t['size'])
        check('DXT5 mip header '+name,raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and levels==1+int(math.log2(max(w,h))))
        expected=128;ww,hh=w,h
        for _ in range(levels):
            expected+=max(1,(ww+3)//4)*max(1,(hh+3)//4)*16;ww=max(1,ww//2);hh=max(1,hh//2)
        check('Complete mip payload '+name,len(raw)==expected)
        im=Image.open(io.BytesIO(raw));im.load()
        check('Opaque DDS '+name,im.size==(w,h) and im.getchannel('A').getextrema()==(255,255))
        png=Image.open(ROOT/'textures'/f'{name}.png');png.load()
        check('PNG and editable source '+name,png.size==(w,h) and (ROOT/'textures'/f'{name}.svg').is_file())

    stock={};cabins={};chassis={};accessories={}
    for root in args.game_defs:
        for path in (Path(root)/'def/vehicle/truck').glob('*/*/*.sii'):
            if path.parent.name not in ['cabin','chassis']:continue
            text=path.read_text(errors='replace');m=re.search(r'accessory_(cabin|chassis)_data\s*:\s*(\S+)',text)
            if m:
                unit=m.group(2);stock[unit]=text
                (cabins if m.group(1)=='cabin' else chassis)[unit]=(path.parent.parent.name,text)
        for path in (Path(root)/'def/vehicle/truck').glob('*/accessory/*/*.sii'):
            text=path.read_text(errors='replace');m=re.search(r'accessory_\w+_data\s*:\s*(\S+)',text)
            if m:accessories.setdefault(path.parent.parent.parent.name,set()).add(path.parent.name+'.'+m.group(1).split('.')[0])

    expected_pairs={(c['unit'],ch) for f in scope['families'] for c in f['cabins'] for ch in c['chassis_units']}
    expected_chassis={ch for f in scope['families'] for ch in f['chassis_units']}
    check('11 heavy truck families',len(scope['families'])==11)
    check('12 stock chassis definitions',len(expected_chassis)==12)
    check('20 unique cabin/chassis pairs',len(expected_pairs)==20)
    if args.game_defs:
        four_axles={u:(v,t) for u,(v,t) in chassis.items() if len(re.findall(r'powered_axle\[\]\s*:',t))==4 and len(re.findall(r'powered_axle\[\]\s*:\s*true',t))==2}
        check('Complete stock four-axle/two-driven-axle inventory',set(four_axles)==expected_chassis,str(sorted(four_axles)))
        def rules(text,field,kind):return {u for u in re.findall(field+r'\[\d*\]\s*:\s*"?([\w.]+)',text) if u.endswith('.'+kind)}
        derived=set()
        for ch,(v,ctext) in four_axles.items():
            for cab,(cv,btext) in cabins.items():
                if cv!=v:continue
                cs=rules(ctext,'suitable_for','cabin');bs=rules(btext,'suitable_for','chassis')
                if cs and cab not in cs:continue
                if bs and ch not in bs:continue
                if cab in rules(ctext,'conflict_with','cabin') or ch in rules(btext,'conflict_with','chassis'):continue
                derived.add((cab,ch))
        check('Complete legal stock cabin/chassis pairs',derived==expected_pairs,str(sorted(derived^expected_pairs)))

    path=ROOT/'mods/gtsr-trucks-v0.3.scs'
    with zipfile.ZipFile(path) as z:
        names=z.namelist();check('Archive integrity',z.testzip() is None)
        check('Unique archive paths',len(names)==len(set(names)))
        mounts={n.split('/')[0] for n in names if n.startswith(('base/','dlc_'))}
        check('Conditional truck DLC mounts',mounts=={'base','dlc_daf_2021','dlc_volvo_fh_2021','dlc_volvo_fh_2024','dlc_iveco_sway','dlc_man_tgx_2020','dlc_renault_etech_t'})
        lookup={m:{n[len(m)+1:]:n for n in names if n.startswith(m+'/')} for m in mounts}
        unit_ids=[]
        for mount,files in lookup.items():
            available={**lookup['base'],**files}
            for virtual,actual in sorted(files.items()):
                if virtual.endswith('.tobj'):
                    b=z.read(actual);length=struct.unpack_from('<I',b,40)[0];target=b[48:48+length].decode().lstrip('/')
                    check('Mounted TOBJ '+actual,target in available,target)
                elif virtual.endswith(('.sii','.mat')):
                    text=z.read(actual).decode();check('Balanced definition '+actual,text.count('{')==text.count('}'))
                    for ref in re.findall(r'paint_job_mask:\s*"/([^"]+)"',text):check('Mounted mask '+actual,ref in available,ref)
                    if '/paint_job/' in actual and '/accessory/' not in actual:
                        unit_ids+=re.findall(r'accessory_paint_job_data\s*:\s*(\S+)',text)
                    if args.game_defs:
                        for u in re.findall(r'suitable_for\[\]:\s*"([^"]+)"',text):check('Installed unit '+u,u in stock)
        defs=[n for n in names if '/paint_job/' in n and '/accessory/' not in n and n.endswith('.sii')]
        check('59 paint-job definitions',len(defs)==59)
        check('Unique named paint-job units',len(unit_ids)==len(set(unit_ids))==59)
        heavy=[n for n in defs if '/gtsrh8_' in n]
        check('20 Heavy Support definitions',len(heavy)==20)
        actual_pairs=set()
        for f in scope['families']:
            key=f['vehicle_id'];prefix=f['mount']+f'/def/vehicle/truck/{key}/paint_job/'
            for i,c in enumerate(f['cabins']):
                fn=prefix+f'gtsrh8_{i}.sii';text=z.read(fn).decode()
                refs=re.findall(r'suitable_for\[\]:\s*"([^"]+)"',text)
                check('Exact cabin/chassis restrictions '+fn,set(refs)=={c['unit'],*c['chassis_units']})
                check('Exact cabin mask '+fn,f'/gtsr_solar/{c["texture"]}.tobj' in text)
                actual_pairs.update((cab,ch) for cab in refs if cab.endswith('.cabin') for ch in refs if ch.endswith('.chassis'))
                if f['accessory_assignments']:
                    afn=prefix+f'accessory/gtsrh8_{i}.sii';at=z.read(afn).decode()
                    mapped={}
                    for block in re.findall(r'simple_paint_job_data:[^{]+\{([^}]+)\}',at):
                        texture=re.search(r'paint_job_mask:\s*"/gtsr_solar/([^"]+)\.tobj"',block).group(1)
                        for a in re.findall(r'acc_list\[\]:\s*"([^"]+)"',block):mapped[a]=texture
                    check('Exact heavy accessory mappings '+afn,mapped==f['accessory_assignments'])
            if args.game_defs:
                known=accessories.get(key,set())|{'chassis.'+u.split('.')[0] for u in f['chassis_units']}
                check('Stock accessory IDs '+key,set(f['accessory_assignments'])<=known,str(sorted(set(f['accessory_assignments'])-known)))
        check('Exact heavy support coverage',actual_pairs==expected_pairs)
        check('Manifest version','package_version: "0.3.0"' in z.read('manifest.sii').decode())
        check('Mod thumbnail',Image.open(io.BytesIO(z.read('Image.jpg'))).size==(276,162))
        for name,t in scope['new_textures'].items():
            mount=next(f['mount'] for f in scope['families'] if f['vehicle_id']==t['vehicle_id'])
            check('New DDS matches export '+name,z.read(mount+'/gtsr_solar/'+name+'.dds')==(ROOT/'textures'/f'{name}.dds').read_bytes())
        if args.previous_mod:
            with zipfile.ZipFile(args.previous_mod) as old:
                keep=[n for n in old.namelist() if n not in ['manifest.sii','Image.jpg','Description.txt']]
                check('All previous gameplay files preserved byte-for-byte',all(n in names and old.read(n)==z.read(n) for n in keep),str(len(keep))+' files')
    for filename in ['gtsr-trailers-v0.1.scs','gtsr-coaches-v0.1.scs']:
        with zipfile.ZipFile(ROOT/'mods'/filename) as z:check('Unchanged module integrity '+filename,z.testzip() is None)
    report={'version':'0.3.0','local_game_version_observed':'1.62.3.3','checks_passed':sum(c['passed'] for c in checks),'checks_total':len(checks),'failures':[c for c in checks if not c['passed']],'game_session_launched':False,'installed_in_active_profile':False,'local_stock_definitions_checked':bool(args.game_defs),'template_overlays_reviewed':10 if args.overlays_reviewed else 0,'limits':['Runtime loading, seams, material finish, opposite-side reading direction and interactions with other mods require an in-game check.','Stock SCS chassis only. Non-paintable plastic/metal retains factory materials.'],'checks':checks}
    (ROOT/'source/8x4-validation.json').write_bytes(json.dumps(report,indent=2).encode())
    print(f'{report["checks_passed"]}/{len(checks)} checks passed')
    if report['failures']:raise SystemExit(json.dumps(report['failures'],indent=2))

if __name__=='__main__':main()
