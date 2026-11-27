"""Build v0.5 panel continuity, Aurora coach and Van Leer FH6 artwork.

The included paint-color bases are calibrated from locally inspected geometry.
They contain only our colors; original models, templates and reference photos
are not included. Rebuild.py preserves manual SVG edits; this recipe regenerates
the eight selected maps from artwork/panel-bases and panel-refinement-layouts.json.
"""
from pathlib import Path
import argparse,base64,hashlib,json,math,re,zipfile
from PIL import Image
from build_truck_expansion import svg,render,rect,label,logo,tobj,NAVY,GOLD,WHITE
from build_mercedes_daf import accessory_text

ROOT=Path(__file__).resolve().parent.parent

def image_base(name):
    p=ROOT/'artwork/panel-bases'/f'{name}.png';im=Image.open(p)
    b=base64.b64encode(p.read_bytes()).decode()
    return im.size,f'<image x="0" y="0" width="{im.width}" height="{im.height}" href="data:image/png;base64,{b}"/>'

def opposite(content):return '<g transform="translate(0 4096) scale(1 -1)">'+content+'</g>'
def mirrored_word(content,x,w):return f'<g transform="translate({2*x+w} 0) scale(-1 1)">'+content+'</g>'

def art(name,layout):
    size,s=image_base(name)
    if 'logo' in layout:
        x,y,w=layout['logo'];mark=logo(x,y,w)
        if 'logo_plaque' in layout:mark=rect(*layout['logo_plaque'],NAVY)+mark
        else:mark+=label(x,layout['fleet_y'],'TEAM TRANSPORT / '+layout['fleet'],40)
        s+=mark+opposite(mirrored_word(mark,x,w))
        if name=='volvo-9700-dd':
            # The silhouette points toward the coach's front on both shells.
            raw=(ROOT/'artwork/sr4-aurora-silhouette.svg').read_text()
            car=raw[raw.find('>')+1:raw.rfind('</svg>')]
            cx,cy,cw=layout['car'];scale=cw/1200
            car=f'<g transform="translate({cx+cw} {cy}) scale({-scale} {scale})">'+car+'</g>'
            s+=car+opposite(car)
            tx,ty,caption=layout['caption'];caption_svg=label(tx,ty,caption,36,WHITE)
            s+=caption_svg+opposite(mirrored_word(caption_svg,tx,950))
    elif 'logos' in layout:
        for x,y,w in layout['logos']:s+=logo(x,y,w)+label(x,layout['label_y'],layout['label'],29)
    return svg(*size,s)

def package(seed,target,replacements,additions,remove,version,description):
    temp=target.with_suffix('.scs.tmp')
    with zipfile.ZipFile(seed) as z,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        seen=set()
        for name in z.namelist():
            if name in remove:continue
            raw=replacements.get(name,additions.get(name,z.read(name)))
            if name=='manifest.sii':raw=re.sub(r'package_version:\s*"[^"]+"',f'package_version: "{version}"',raw.decode()).encode()
            if name=='Description.txt':raw=description.encode()
            out.writestr(name,raw);seen.add(name)
        for name,raw in additions.items():
            if name not in seen:out.writestr(name,raw)
    with zipfile.ZipFile(temp) as z:assert z.testzip() is None
    temp.replace(target)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--truck-seed');p.add_argument('--coach-seed');p.add_argument('--reuse-textures',action='store_true');a=p.parse_args()
    data=json.loads((ROOT/'source/panel-refinement-layouts.json').read_text());truck=data['truck']
    truck_target=ROOT/'mods'/data['truck_module'];coach_target=ROOT/'mods'/data['coach_module']
    def seed(given,previous,current):return Path(given) if given else (previous if previous.exists() else current)
    truck_seed=seed(a.truck_seed,ROOT/'mods/gtsr-trucks-v0.4.1.scs',truck_target)
    coach_seed=seed(a.coach_seed,ROOT/'mods/gtsr-coaches-v0.1.1.scs',coach_target)
    index={t['name']:t for t in json.loads((ROOT/'source/texture-index.json').read_text())}
    layouts={**data['coaches'],truck['texture']:truck,**{n:{} for n in truck['accessories'].values()}}
    changes={'truck':{},'coach':{}};added={'truck':{},'coach':{}}
    inventories={}
    for k,src in [('truck',truck_seed),('coach',coach_seed)]:
        with zipfile.ZipFile(src) as z:inventories[k]=set(z.namelist())
    for name,l in layouts.items():
        source=art(name,l);stem=ROOT/'textures'/name
        cached=a.reuse_textures and all(stem.with_suffix('.'+ext).exists() for ext in ['svg','png','dds']) and stem.with_suffix('.svg').read_bytes()==source.encode()
        if not cached:
            im=render(source);stem.with_suffix('.svg').write_bytes(source.encode());im.save(stem.with_suffix('.png'));stem.with_suffix('.dds').write_bytes(__import__('rebuild').encode_dds(im))
        else:im=Image.open(stem.with_suffix('.png'))
        coach=name in data['coaches'];mount='' if coach else truck['mount'];kind='coach' if coach else 'truck'
        index[name]={**index.get(name,{}),'name':name,'size':list(im.size),'mip_levels':1+int(math.log2(max(im.size))),'format':'DXT5 / BC3','scope':'Panel continuity / Aurora / Van Leer 0.5'}
        if not coach:index[name].update({'mount':mount,'vehicle_id':truck['vehicle']})
        prefix=(mount+'/' if mount else '')+'gtsr_solar/'+name
        bucket=changes[kind] if prefix+'.dds' in inventories[kind] else added[kind]
        bucket[prefix+'.dds']=stem.with_suffix('.dds').read_bytes()
        if prefix+'.tobj' not in inventories[kind]:added[kind][prefix+'.tobj']=tobj('gtsr_solar/'+name+'.dds')
        print('Built panel map',name,flush=True)
    prefix=truck['mount']+'/def/vehicle/truck/'+truck['vehicle']+'/paint_job/'
    with zipfile.ZipFile(truck_seed) as z:
        name=prefix+truck['keep_paint']+'.sii'
        changes['truck'][name]=z.read(name).decode().replace('Solar Circuit - Alumni Support','Solar Circuit - Van Leer').encode()
        mapping={}
        acc_name=prefix+'accessory/'+truck['keep_paint']+'.sii';acc=z.read(acc_name).decode()
        for block in re.findall(r'simple_paint_job_data:[^{]+\{([^}]+)\}',acc):
            tex=re.search(r'paint_job_mask:\s*"/gtsr_solar/([^"]+)\.tobj"',block)[1]
            for ident in re.findall(r'acc_list\[\]:\s*"([^"]+)"',block):mapping[ident]=tex
        mapping.update(truck['accessories']);changes['truck'][acc_name]=accessory_text(mapping).encode()
    retired=truck['retired_texture']
    remove={prefix+truck['remove_paint']+'.sii',prefix+'accessory/'+truck['remove_paint']+'.sii',truck['mount']+'/gtsr_solar/'+retired+'.dds',truck['mount']+'/gtsr_solar/'+retired+'.tobj'}
    package(truck_seed,truck_target,changes['truck'],added['truck'],remove,'0.5.0','Solar Circuit 0.5: Van Leer FH6 Aero Globetrotter XL with geometry-calibrated cab/deflector stripe.\nThe single Van Leer choice retains stock 8x4 compatibility; the duplicate Heavy Support entry for this cab is removed.\nOther fleet vehicles retained: 25 families, 77 truck paint definitions.\nCustom paint artwork only. Corrected appearance awaits in-game confirmation.\n')
    package(coach_seed,coach_target,changes['coach'],added['coach'],set(),'0.2.0','Solar Circuit coaches 0.2: painted doors and end panels share geometry-calibrated navy/gold bands.\nMAN 13.9 m, Scania 13.7 m and Volvo 9700 DD; shorter bodies unchanged.\nSpecial SR-4 Aurora silhouette and road on the DD, with team logo between window rows.\nRequires SCS Coaches DLC. Corrected appearance awaits in-game confirmation.\n')
    index.pop(retired,None)
    for ext in ['svg','png','dds']:
        old=ROOT/'textures'/f'{retired}.{ext}'
        if old.exists():old.unlink()
    assert len(index)==118
    (ROOT/'source/texture-index.json').write_text(json.dumps(list(index.values()),indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Wrote truck 0.5 / coach 0.2; 118 texture sets, 77 truck definitions')

if __name__=='__main__':main()
