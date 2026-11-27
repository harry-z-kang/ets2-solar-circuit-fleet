"""Build the focused 0.4.1 coach/FH6 correction without changing other maps.

Uses the included SVGs and focused-fix-layouts.json. Optional --templates supplies
the original PJP archive solely for private overlays under --qa-dir.
Use rebuild.py for manual SVG edits; this recipe overwrites the targeted lettering.
"""
from pathlib import Path
import argparse,copy,hashlib,io,json,math,re,xml.etree.ElementTree as ET,zipfile
from PIL import Image,ImageOps
from build_truck_expansion import WHITE,NAVY,GOLD,rect,label,logo,svg,render,cells,trace,tobj
from rebuild import encode_dds

ROOT=Path(__file__).resolve().parent.parent
NS='http://www.w3.org/2000/svg';ET.register_namespace('',NS)

def coach_art(name,layout):
    root=ET.fromstring((ROOT/'textures'/f'{name}.svg').read_bytes())
    sides=[e for e in root if e.tag==f'{{{NS}}}g'][:2]
    assert len(sides)==2
    x,y,w=layout['logo'];ox,oy=layout['side_origin'];lx,ly=x-ox,y-oy
    for i,side in enumerate(sides):
        for child in list(side):
            if child.tag in [f'{{{NS}}}image',f'{{{NS}}}text'] or child.get('id')=='focus-wordmark':side.remove(child)
        s=logo(0,0,w)+label(0,layout['fleet_y']-y,'TEAM TRANSPORT / '+layout['fleet'],layout['fleet_size'])
        transform=f'translate({lx} {ly})' if i==0 else f'translate({lx+w} {ly}) scale(-1 1)'
        group=ET.fromstring(f'<g xmlns="{NS}" id="focus-wordmark" transform="{transform}">{s}</g>')
        side.append(group)
    return ET.tostring(root,encoding='unicode')

def truck_art(layout,heavy=False):
    s=rect(0,0,4096,4096,WHITE)
    for x,y,x1,y1 in layout['bands']+layout['sides']:
        s+=rect(x,y,x1-x,y1-y,NAVY)+rect(x,y,x1-x,20,GOLD)
    role='HEAVY SUPPORT' if heavy else 'ALUMNI SUPPORT'
    for (x,y,w),side in zip(layout['logos'],layout['sides']):
        s+=logo(x,y,w)+label(x,layout['fleet_y'],'TK-05 / '+role,20)
        s+=trace(x+20,side[3]-95,w*.75)
    s+=cells(*layout['roof'])
    return svg(4096,4096,s)

def replace_module(seed,target,changes,additions,version,description):
    temp=target.with_suffix('.scs.tmp')
    with zipfile.ZipFile(seed) as z,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for n in z.namelist():
            data=changes.get(n,z.read(n))
            if n=='manifest.sii':data=re.sub(r'package_version:\s*"[^"]+"','package_version: "'+version+'"',data.decode()).encode()
            if n=='Description.txt':data=description.encode()
            out.writestr(n,data)
        for n,data in additions.items():
            assert n not in z.namelist(),n
            out.writestr(n,data)
    with zipfile.ZipFile(temp) as z:assert z.testzip() is None
    temp.replace(target)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--truck-seed');p.add_argument('--coach-seed');p.add_argument('--templates');p.add_argument('--qa-dir');p.add_argument('--reuse-textures',action='store_true');args=p.parse_args()
    data=json.loads((ROOT/'source/focused-fix-layouts.json').read_text());truck=data['truck']
    seeds={
      'truck':Path(args.truck_seed) if args.truck_seed else ROOT/'mods/gtsr-trucks-v0.4.scs',
      'coach':Path(args.coach_seed) if args.coach_seed else ROOT/'mods/gtsr-coaches-v0.1.scs'}
    outputs={'truck':ROOT/'mods/gtsr-trucks-v0.4.1.scs','coach':ROOT/'mods/gtsr-coaches-v0.1.1.scs'}
    for k in seeds:
        if not seeds[k].exists():seeds[k]=outputs[k]
    index={e['name']:e for e in json.loads((ROOT/'source/texture-index.json').read_text())}
    artwork={n:(coach_art(n,l),l['template'],'coach') for n,l in data['coaches'].items()}
    artwork[truck['texture']]=(truck_art(truck),truck['template'],'truck')
    artwork[truck['heavy_texture']]=(truck_art(truck,True),truck['template'],'truck')
    archive=zipfile.ZipFile(args.templates) if args.templates else None
    if archive:
        h=hashlib.sha256()
        with open(args.templates,'rb') as f:
            for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
        assert h.hexdigest()==json.loads((ROOT/'source/truck-template-catalog.json').read_text())['archive_sha256']
    qa=Path(args.qa_dir) if args.qa_dir else None
    if qa:qa.mkdir(parents=True,exist_ok=True)
    changes={'truck':{},'coach':{}};additions={'truck':{},'coach':{}}
    inventories={}
    for kind,seed in seeds.items():
        with zipfile.ZipFile(seed) as z:inventories[kind]=set(z.namelist())
    template_hashes={}
    for name,(source,template,kind) in artwork.items():
        path=ROOT/'textures'/name
        reuse=args.reuse_textures and all(path.with_suffix('.'+e).exists() for e in ['svg','png','dds']) and path.with_suffix('.svg').read_bytes()==source.encode()
        if not reuse:
            im=render(source);path.with_suffix('.svg').write_bytes(source.encode());im.save(path.with_suffix('.png'));path.with_suffix('.dds').write_bytes(encode_dds(im))
        else:im=Image.open(path.with_suffix('.png')).convert('RGBA')
        old=index.get(name,{})
        index[name]={**old,'name':name,'size':list(im.size),'mip_levels':1+int(math.log2(max(im.size))),'format':'DXT5 / BC3','template':template,'scope':'Focused coach/FH6 correction 0.4.1'}
        if kind=='truck':index[name].update({'vehicle_id':truck['vehicle'],'mount':truck['mount']})
        member=('' if kind=='coach' else truck['mount']+'/')+'gtsr_solar/'+name
        bucket=changes[kind] if member+'.dds' in inventories[kind] else additions[kind]
        bucket[member+'.dds']=path.with_suffix('.dds').read_bytes()
        if name==truck['heavy_texture']:bucket[member+'.tobj']=tobj('gtsr_solar/'+name+'.dds')
        if archive:
            raw=archive.read(template);template_hashes[template]=hashlib.sha256(raw).hexdigest()
            if qa:
                wire=Image.open(io.BytesIO(raw)).convert('L');mask=ImageOps.invert(wire).point(lambda v:int(v*.72))
                overlay=im.copy();overlay.paste(Image.new('RGB',im.size,'#ee5984'),(0,0),mask);overlay.thumbnail((1800,1200));overlay.convert('RGB').save(qa/(name+'.jpg'),quality=94)
        print('Built focused map:',name,flush=True)
    prefix=truck['mount']+'/def/vehicle/truck/'+truck['vehicle']+'/paint_job/'
    with zipfile.ZipFile(seeds['truck']) as z:
        heavy=z.read(prefix+'gtsrh8_1.sii').decode()
        heavy=heavy.replace('/gtsr_solar/'+truck['texture']+'.tobj','/gtsr_solar/'+truck['heavy_texture']+'.tobj')
        changes['truck'][prefix+'gtsrh8_1.sii']=heavy.encode()
        accessory=z.read(prefix+'accessory/gtsrh8_1.sii').decode()
        # Drop this recipe's prior block for idempotent regeneration.
        accessory=re.sub(r'\nsimple_paint_job_data: \.focus_fenders\s*\{[^}]*\}\s*','\n',accessory)
        block='\nsimple_paint_job_data: .focus_fenders\n{\n paint_job_mask: "/gtsr_solar/solid-navy.tobj"\n'+''.join(' acc_list[]: "'+a+'"\n' for a in truck['heavy_accessory_overrides'])+'}\n'
        pos=accessory.rfind('}');accessory=accessory[:pos].rstrip()+'\n'+block+'}\n'
        changes['truck'][prefix+'accessory/gtsrh8_1.sii']=accessory.encode()
    descriptions={
      'truck':'Solar Circuit 0.4.1: focused Volvo FH6 Aero Globetrotter XL correction.\nSmaller cab lettering clear of the marked handle/seam regions, navy lower fender coverage, and dedicated Heavy Support artwork with painted rear-fender overrides.\nAll other truck coverage retained: 25 families, 78 paint definitions.\nBased on user screenshots and UV review; corrected build awaits an in-game confirmation. Personal alumni tribute.\n',
      'coach':'Solar Circuit coaches 0.1.1: focused MAN Lion\'s Coach L 13.9 m, Scania Touring HD 13.7 m and Volvo 9700 DD correction.\nRight-side lettering is compensated for the observed UV mirroring. Smaller double-decker logo sits below the lower-window cutout.\nShort MAN/Scania body maps retained unchanged. Requires SCS Coaches DLC.\nBased on user screenshots and UV review; corrected build awaits an in-game confirmation. Personal alumni tribute.\n'}
    for kind,version in [('truck','0.4.1'),('coach','0.1.1')]:replace_module(seeds[kind],outputs[kind],changes[kind],additions[kind],version,descriptions[kind])
    (ROOT/'source/texture-index.json').write_text(json.dumps(list(index.values()),indent=2)+'\n',encoding='utf-8',newline='\n')
    if template_hashes:(ROOT/'source/focused-fix-template-hashes.json').write_text(json.dumps(template_hashes,indent=2)+'\n',encoding='utf-8',newline='\n')
    if archive:archive.close()
    print('Wrote focused truck 0.4.1 and coach 0.1.1 modules')

if __name__=='__main__':main()
