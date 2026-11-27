"""Build Solar Circuit Heavy Support for stock SCS 8x4 chassis.

Obtain the two author archives linked in 8x4-support.json; no wireframes are
redistributed. Run with --templates DDS.zip --complete-templates PNG.zip.
Use rebuild.py to preserve manual edits to the exported h8_*.svg artwork.
"""
from pathlib import Path
import argparse, collections, hashlib, io, json, math, zipfile
from PIL import Image, ImageOps
from build_truck_expansion import NAVY, GOLD, WHITE, rect, label, logo, svg, render, cells, trace, band, tobj, unit
from rebuild import encode_dds

ROOT=Path(__file__).resolve().parent.parent

def artwork(info):
    w,h=info['width'],info['height'];layout=info['layout'];fleet=info['fleet_number']
    s=rect(0,0,w,h,WHITE)
    if layout=='scania_skirts':
        s=rect(0,0,w,h,NAVY)
        for y in [110,340,1700,1920]:s+=rect(0,y,w,20,GOLD)
        s+=trace(150,550,700)
        s+='<g transform="translate(0 2048) scale(1 -1)">'+trace(150,550,700)+'</g>'
    elif layout=='scan16':
        for x in [430,2470]:s+=band((x,2610,x+1180,3220))
        for x in [650,2770]:
            s+=logo(x,2670,610)+label(x,2990,fleet+' / HEAVY SUPPORT',27)
            s+=trace(x,3090,590)
        s+=band((1610,2700,2470,3160))+band((1200,3600,2900,4096))
        for x in [440,2840]:
            s+=band((x,450,x+790,1400))
            s+=logo(x+90,550,620)+label(x+90,740,'HEAVY SUPPORT 8x4',28,GOLD)
            s+=cells(x+80,800,650,350)
    elif layout=='scan09':
        for x in [50,3000]:s+=band((x,790,x+1020,1240))
        for x in [260,3190]:s+=logo(x,840,680)+label(x,1170,fleet+' / HEAVY SUPPORT',26)
        s+=band((1350,1210,2750,1760))
        for y in [3250,3750]:s+=band((50,y,1150,min(y+340,4096)))
        s+=cells(3000,3480,600,180)
    elif layout=='actros':
        for x in [100,3000]:s+=band((x,800,x+1000,1350))
        for x in [270,3220]:s+=logo(x,850,630)+label(x,1190,fleet+' / HEAVY SUPPORT',26)
        s+=band((1400,3200,2690,4096))
        for x in [1400,2100]:s+=band((x,2200,x+570,2800))+cells(x+100,2400,400,220,5,2)
        s+=band((2800,3550,4070,4096))
    elif layout=='daf':
        for x in [150,2650]:s+=band((x,2530,x+1250,3030))
        for x in [450,3000]:
            s+=logo(x,2580,620)+label(x,2960,fleet+' / HEAVY SUPPORT',26)
            s+=trace(x,2890,620)
        s+=band((1450,2640,2700,2950))+band((1000,3500,3000,4010))
        s+=cells(1650,1240,700,150)
    else:raise ValueError('Unknown layout '+layout)
    return svg(w,h,s)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def build(args):
    data=json.loads((ROOT/'source/8x4-support.json').read_text())
    paths={'dds':Path(args.templates),'png':Path(args.complete_templates)}
    for k,p in paths.items():
        if digest(p)!=data['archives'][k]['sha256']:raise ValueError('Unexpected template archive: '+str(p))
    archives={k:zipfile.ZipFile(p) for k,p in paths.items()}
    seed=Path(args.base_mod) if args.base_mod else next((p for p in [ROOT/'mods/gtsr-trucks-v0.2.scs',ROOT/'mods/gtsr-trucks-v0.3.scs'] if p.exists()),None)
    if not seed:raise ValueError('Provide the existing truck module using --base-mod.')
    qa=Path(args.qa_dir) if args.qa_dir else None
    if qa:qa.mkdir(parents=True,exist_ok=True)
    index=[t for t in json.loads((ROOT/'source/texture-index.json').read_text()) if not t['name'].startswith('h8_')]
    mounts={f['vehicle_id']:f['mount'] for f in data['families']}
    for name,info in data['new_textures'].items():
        template=archives[info['archive']].read(info['archive_path'])
        if hashlib.sha256(template).hexdigest()!=info['sha256']:raise ValueError('Template member hash mismatch '+name)
        source=artwork(info);stem=ROOT/'textures'/name
        cached=args.reuse_textures and all(stem.with_suffix('.'+e).exists() for e in ['svg','png','dds']) and stem.with_suffix('.svg').read_bytes()==source.encode()
        if cached:im=Image.open(stem.with_suffix('.png')).convert('RGBA')
        else:
            im=render(source);stem.with_suffix('.svg').write_bytes(source.encode())
            im.save(stem.with_suffix('.png'));stem.with_suffix('.dds').write_bytes(encode_dds(im))
        assert im.size==(info['width'],info['height'])
        index.append({'name':name,'size':list(im.size),'mip_levels':1+int(math.log2(max(im.size))),'format':'DXT5 / BC3','template':info['archive_path'],'vehicle_id':info['vehicle_id'],'mount':mounts[info['vehicle_id']],'scope':'stock 8x4'})
        if qa:
            wire=Image.open(io.BytesIO(template)).convert('RGBA')
            wire=Image.alpha_composite(Image.new('RGBA',wire.size,'white'),wire).convert('L')
            mask=ImageOps.invert(wire).point(lambda p:int(p*.72))
            overlay=im.copy();overlay.paste(Image.new('RGB',im.size,'#EE5984'),(0,0),mask)
            overlay.thumbnail((1100,1100));overlay.convert('RGB').save(qa/(name+'.jpg'),quality=93)
        print('Built',name,im.size,flush=True)
    for z in archives.values():z.close()
    target=ROOT/'mods/gtsr-trucks-v0.3.scs';temp=target.with_suffix('.scs.tmp')
    with zipfile.ZipFile(seed) as zin,zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for n in zin.namelist():
            if n in ['manifest.sii','Image.jpg','Description.txt'] or '/h8_' in n or '/gtsrh8_' in n:continue
            out.writestr(n,zin.read(n))
        out.writestr('manifest.sii',unit('mod_package','.gtsr_package',' package_version: "0.3.0"\n display_name: "Solar Circuit / 20 Trucks + Stock 8x4"\n author: "Personal alumni fleet / Codex"\n category[]: "paint_job"\n mp_mod_optional: true\n icon: "Image.jpg"\n description_file: "Description.txt"'))
        thumb=render(svg(552,324,rect(0,0,552,324,NAVY)+rect(0,0,552,12,GOLD)+logo(35,50,480)+label(35,220,'SOLAR CIRCUIT',35)+label(35,280,'20 TRUCKS / STOCK 8x4',25,GOLD)))
        b=io.BytesIO();thumb.convert('RGB').resize((276,162)).save(b,format='JPEG',quality=95);out.writestr('Image.jpg',b.getvalue())
        out.writestr('Description.txt','Solar Circuit 0.3: 20 SCS truck families; 39 existing paint definitions plus 20 Heavy Support 8x4 options.\nAll 12 stock 8x4 chassis definitions observed in ETS2 1.62.3.3, across 11 families.\nMatching truck DLC required for conditional sections. Personal alumni tribute.\nStatic checks and template overlays reviewed. In-game appearance untested.\n')
        for name,info in data['new_textures'].items():
            prefix=mounts[info['vehicle_id']]+'/gtsr_solar/'+name
            out.write(ROOT/'textures'/f'{name}.dds',prefix+'.dds')
            out.writestr(prefix+'.tobj',tobj('gtsr_solar/'+name+'.dds'))
        for f in data['families']:
            key=f['vehicle_id'];prefix=f['mount']+f'/def/vehicle/truck/{key}/paint_job/'
            for i,c in enumerate(f['cabins']):
                ident='gtsrh8_'+str(i)
                body=' name: "Solar Circuit - Heavy Support 8x4"\n price: 1000\n unlock: 0\n icon: "gtsrsc_icon"\n airbrush: true\n base_color: (1.0, 1.0, 1.0)\n base_color_locked: true\n stock: false'
                body+=f'\n paint_job_mask: "/gtsr_solar/{c["texture"]}.tobj"\n suitable_for[]: "{c["unit"]}"'
                for chassis in c['chassis_units']:body+=f'\n suitable_for[]: "{chassis}"'
                out.writestr(prefix+ident+'.sii',unit('accessory_paint_job_data',ident+'.'+key+'.paint_job',body))
                grouped=collections.defaultdict(list)
                for acc,texture in f['accessory_assignments'].items():grouped[texture].append(acc)
                if grouped:
                    s='SiiNunit\n{\n'
                    for n,(texture,accs) in enumerate(sorted(grouped.items())):
                        s+=f'simple_paint_job_data: .ovr{n}\n{{\n paint_job_mask: "/gtsr_solar/{texture}.tobj"\n'
                        for acc in sorted(accs):s+=f' acc_list[]: "{acc}"\n'
                        s+='}\n'
                    s+='}\n';out.writestr(prefix+'accessory/'+ident+'.sii',s)
    with zipfile.ZipFile(temp) as z:
        if z.testzip():raise ValueError('Archive integrity failure')
    temp.replace(target)
    (ROOT/'source/texture-index.json').write_bytes(json.dumps(index,indent=2).encode())
    print('Wrote',target,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--templates',required=True);p.add_argument('--complete-templates',required=True)
    p.add_argument('--base-mod');p.add_argument('--qa-dir');p.add_argument('--reuse-textures',action='store_true')
    build(p.parse_args())
