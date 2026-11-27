"""Build the 0.4 Mercedes-Benz / DAF fleet expansion from Carsmaniac's pack.

Download the original PNG/PSD pack linked in mercedes-daf-support.json.
Use --templates ARCHIVE.zip and optionally --base-mod gtsr-trucks-v0.3.scs.
Use rebuild.py to retain manual edits to the exported SVG artwork.
Original wireframes and game data are never added to the module.
"""
from pathlib import Path
import argparse,collections,hashlib,io,json,math,zipfile
from PIL import Image,ImageOps
from build_truck_expansion import NAVY,GOLD,WHITE,rect,label,logo,svg,render,cells,trace,tobj,unit
from rebuild import encode_dds

ROOT=Path(__file__).resolve().parent.parent

def stripe(bounds):
    x,y,x1,y1=bounds
    return rect(x,y,x1-x,y1-y,NAVY)+rect(x,y,x1-x,16,GOLD)

def cabin_art(layout):
    s=rect(0,0,4096,4096,WHITE)
    for bounds in layout['bands']+layout['sides']:s+=stripe(bounds)
    for (x,y,w),bounds in zip(layout['logos'],layout['sides']):
        s+=logo(x,y,w)
        s+=label(x,layout['fleet_y'],layout['fleet_number']+' / SOLAR SUPPORT',21)
        s+=trace(x,bounds[3]-85,w*.88)
    if layout['roof']:s+=cells(*layout['roof'])
    for region in layout.get('tower_cells',[]):s+=cells(*region,5,2)
    return svg(4096,4096,s)

def auxiliary_art(info):
    w,h=info['size'];part=info['part']
    if 'Mirrors' in part:
        # Uniform white avoids lettering or stripes wrapping unpredictably on
        # small mirror islands, while retaining a model-specific editable map.
        return svg(w,h,rect(0,0,w,h,WHITE))
    s=rect(0,0,w,h,NAVY)
    if 'Sideskirts' in part:
        for y in [h*.12,h*.88]:s+=rect(0,y,w,max(8,h*.014),GOLD)
        if info['vehicle_id']=='daf.xf_electric':
            # The battery skirts are split into narrow islands: decoration only.
            for x in [w*.08,w*.56]:s+=trace(x,h*.44,w*.31)
        else:
            s+=trace(w*.12,h*.30,w*.55)
            s+='<g transform="translate(0 '+str(h)+') scale(1 -1)">'+trace(w*.12,h*.30,w*.55)+'</g>'
    return svg(w,h,s)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def accessory_text(assignments):
    grouped=collections.defaultdict(list)
    for acc,texture in assignments.items():grouped[texture].append(acc)
    s='SiiNunit\n{\n'
    for i,(texture,accs) in enumerate(sorted(grouped.items())):
        s+=f'simple_paint_job_data: .ovr{i}\n{{\n paint_job_mask: "/gtsr_solar/{texture}.tobj"\n'
        for acc in sorted(accs):s+=f' acc_list[]: "{acc}"\n'
        s+='}\n'
    return s+'}\n'

def build(args):
    support=json.loads((ROOT/'source/mercedes-daf-support.json').read_text())
    layouts=json.loads((ROOT/'source/mercedes-daf-layouts.json').read_text())
    archive=Path(args.templates)
    if digest(archive)!=support['template_pack']['sha256']:raise ValueError('Unexpected source template archive')
    seed=Path(args.base_mod) if args.base_mod else next((p for p in [ROOT/'mods/gtsr-trucks-v0.3.scs',ROOT/'mods/gtsr-trucks-v0.4.scs'] if p.exists()),None)
    if not seed:raise ValueError('An existing 0.3/0.4 truck module is required as the seed')
    qa=Path(args.qa_dir) if args.qa_dir else None
    if qa:qa.mkdir(parents=True,exist_ok=True)
    index={t['name']:t for t in json.loads((ROOT/'source/texture-index.json').read_text())}
    for name in list(index):
        if name.startswith('md_'):del index[name]
    with zipfile.ZipFile(archive) as z:
        for name,info in support['textures'].items():
            template=z.read(info['archive_path'])
            if hashlib.sha256(template).hexdigest()!=info['template_sha256']:raise ValueError('Template member mismatch '+name)
            source=cabin_art(layouts[name]) if info['kind']=='cabin' else auxiliary_art(info)
            stem=ROOT/'textures'/name
            cached=args.reuse_textures and all(stem.with_suffix('.'+e).exists() for e in ['svg','png','dds']) and stem.with_suffix('.svg').read_bytes()==source.encode()
            if cached:im=Image.open(stem.with_suffix('.png')).convert('RGBA')
            else:
                im=render(source);stem.with_suffix('.svg').write_bytes(source.encode());im.save(stem.with_suffix('.png'))
                stem.with_suffix('.dds').write_bytes(encode_dds(im))
            assert list(im.size)==info['size']
            index[name]={'name':name,'size':list(im.size),'mip_levels':1+int(math.log2(max(im.size))),'format':'DXT5 / BC3','template':info['archive_path'],'vehicle_id':info['vehicle_id'],'mount':info['mount'],'scope':'Mercedes-Benz / DAF 0.4'}
            if qa:
                wire=Image.open(io.BytesIO(template)).convert('RGBA')
                wire=Image.alpha_composite(Image.new('RGBA',wire.size,'white'),wire).convert('L')
                mask=ImageOps.invert(wire).point(lambda p:int(p*.65))
                overlay=im.copy();overlay.paste(Image.new('RGB',im.size,'#EE5984'),(0,0),mask)
                overlay.thumbnail((1100,1100));overlay.convert('RGB').save(qa/(name+'.jpg'),quality=93)
            print('Built',name,im.size,flush=True)
    for alias,name in support['heavy_aliases'].items():
        for ext in ['svg','png','dds']:(ROOT/'textures'/f'{alias}.{ext}').write_bytes((ROOT/'textures'/f'{name}.{ext}').read_bytes())
        index[alias]={**index[name],'name':alias,'scope':'8x4 alias refreshed by Mercedes-Benz / DAF 0.4'}
    exports={name:info['mount'] for name,info in support['textures'].items()}
    for alias,name in support['heavy_aliases'].items():exports[alias]=support['textures'][name]['mount']
    replacements={mount+'/gtsr_solar/'+name+'.'+ext for name,mount in exports.items() for ext in ['dds','tobj']}
    refreshed_accessories=set()
    heavy=json.loads((ROOT/'source/8x4-support.json').read_text())
    families={f['vehicle_id']:f for f in support['families']}
    for f in heavy['families']:
        if f['vehicle_id'] not in families:continue
        for i,c in enumerate(f['cabins']):refreshed_accessories.add(f['mount']+f'/def/vehicle/truck/{f["vehicle_id"]}/paint_job/accessory/gtsrh8_{i}.sii')
    target=ROOT/'mods/gtsr-trucks-v0.4.scs';temp=target.with_suffix('.scs.tmp')
    with zipfile.ZipFile(seed) as zin,zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for n in zin.namelist():
            if n in ['manifest.sii','Image.jpg','Description.txt'] or n in replacements or n in refreshed_accessories or '/gtsrmd_' in n:continue
            out.writestr(n,zin.read(n))
        out.writestr('manifest.sii',unit('mod_package','.gtsr_package',' package_version: "0.4.0"\n display_name: "Solar Circuit / 25 Trucks + Stock 8x4"\n author: "Personal alumni fleet / Codex"\n category[]: "paint_job"\n mp_mod_optional: true\n icon: "Image.jpg"\n description_file: "Description.txt"'))
        thumb=render(svg(552,324,rect(0,0,552,324,NAVY)+rect(0,0,552,12,GOLD)+logo(35,48,480)+label(35,220,'SOLAR CIRCUIT',35)+label(35,280,'MERCEDES-BENZ / DAF',25,GOLD)))
        b=io.BytesIO();thumb.convert('RGB').resize((276,162)).save(b,format='JPEG',quality=95);out.writestr('Image.jpg',b.getvalue())
        out.writestr('Description.txt','Solar Circuit 0.4: 25 truck families, 78 paint definitions.\nAdds all seven standard SCS Mercedes-Benz and DAF families and retains all stock 8x4 options.\nSmaller cab logos; model-specific available DAF mirrors, visors and skirts.\nMatching truck DLC required for conditional sections. Personal alumni tribute.\nNew maps statically checked and reviewed against templates; no new in-game test.\n')
        for name,mount in exports.items():
            prefix=mount+'/gtsr_solar/'+name
            out.write(ROOT/'textures'/f'{name}.dds',prefix+'.dds')
            out.writestr(prefix+'.tobj',tobj('gtsr_solar/'+name+'.dds'))
        for key,f in families.items():
            prefix=f['mount']+f'/def/vehicle/truck/{key}/paint_job/'
            for i,c in enumerate(c for c in f['cabins'] if not c['heavy']):
                ident='gtsrmd_'+str(i)
                body=' name: "Solar Circuit - Alumni Support"\n price: 1000\n unlock: 0\n icon: "gtsrsc_icon"\n airbrush: true\n base_color: (1.0, 1.0, 1.0)\n base_color_locked: true\n stock: false'
                body+=f'\n paint_job_mask: "/gtsr_solar/{c["texture"]}.tobj"'
                for cid in c['ids']:body+=f'\n suitable_for[]: "{cid}.{key}.cabin"'
                out.writestr(prefix+ident+'.sii',unit('accessory_paint_job_data',ident+'.'+key+'.paint_job',body))
                out.writestr(prefix+'accessory/'+ident+'.sii',accessory_text(f['accessory_assignments']))
        for f in heavy['families']:
            key=f['vehicle_id']
            if key not in families:continue
            for i,c in enumerate(f['cabins']):out.writestr(f['mount']+f'/def/vehicle/truck/{key}/paint_job/accessory/gtsrh8_{i}.sii',accessory_text(families[key]['accessory_assignments']))
    with zipfile.ZipFile(temp) as z:
        if z.testzip():raise ValueError('Module archive integrity failure')
    temp.replace(target)
    assert len(index)==support['texture_sets_total']
    (ROOT/'source/texture-index.json').write_bytes(json.dumps(list(index.values()),indent=2).encode())
    print('Wrote',target,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--templates',required=True);p.add_argument('--base-mod');p.add_argument('--qa-dir');p.add_argument('--reuse-textures',action='store_true')
    build(p.parse_args())
