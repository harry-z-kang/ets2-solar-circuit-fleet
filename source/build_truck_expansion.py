"""Build the 14-model Solar Circuit truck expansion from the author's templates.

Usage: python source/build_truck_expansion.py --templates /path/to/templates.zip
Requires source/requirements.txt. The template archive is not redistributed.
Use rebuild.py instead when updating the exported SVG artwork by hand.
"""
from pathlib import Path
import argparse, base64, hashlib, html, io, json, math, re, struct, zipfile
from PIL import Image, ImageDraw, ImageFont, ImageOps
import pymupdf
from rebuild import encode_dds

ROOT=Path(__file__).resolve().parent.parent
NAVY='#051E39'; GOLD='#B39051'; WHITE='#FFFFFF'
MOUNTS={'volvo.fh_2021':'dlc_volvo_fh_2021','volvo.fh_2024':'dlc_volvo_fh_2024','iveco.sway':'dlc_iveco_sway','man.tgx_2020':'dlc_man_tgx_2020','renault.etech_t':'dlc_renault_etech_t'}
LOGO=base64.b64encode((ROOT/'artwork/gtsr-logo-original.png').read_bytes()).decode()

def rect(x,y,w,h,color):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>'
def label(x,y,value,size=34,color=WHITE):return f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" font-weight="700" fill="{color}">{html.escape(value)}</text>'
def logo(x,y,w):return f'<image x="{x}" y="{y}" width="{w}" height="{w*186/922}" href="data:image/png;base64,{LOGO}"/>'
def svg(w,h,s):return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{s}</svg>'
def render(s):
    doc=pymupdf.open(stream=s.encode(),filetype='svg');pix=doc[0].get_pixmap(alpha=True)
    im=Image.frombytes('RGBA',(pix.width,pix.height),pix.samples);im.putalpha(255)
    return im
def cells(x,y,w,h,cols=7,rows=2):
    s=rect(x,y,w,h,NAVY)
    for row in range(rows):
        for col in range(cols):
            xx=x+8+col*(w-16)/cols;yy=y+8+row*(h-16)/rows
            cw=(w-16)/cols-6;ch=(h-16)/rows-6
            s+=f'<rect x="{xx}" y="{yy}" width="{cw}" height="{ch}" rx="5" fill="#0D2B46" stroke="#426077" stroke-width="2"/>'
            s+=f'<path d="M{xx+cw/2} {yy+4} V{yy+ch-4}" stroke="#426077" stroke-width="1"/>'
    return s
def trace(x,y,w):
    s=f'<path d="M{x} {y} H{x+w*.32} L{x+w*.42} {y-30} H{x+w*.74} L{x+w*.84} {y-60} H{x+w}" fill="none" stroke="{GOLD}" stroke-width="4"/>'
    for a,b in [(x,y),(x+w*.74,y-30),(x+w,y-60)]:s+=f'<circle cx="{a}" cy="{b}" r="6" fill="{NAVY}" stroke="{GOLD}" stroke-width="3"/>'
    return s
def band(bounds):
    x0,y0,x1,y1=bounds
    return rect(x0,y0,x1-x0,y1-y0,NAVY)+rect(x0,y0,x1-x0,20,GOLD)

def cabin_art(model,cabin,layout,fleet):
    s=rect(0,0,4096,4096,WHITE)
    for bounds in layout['bands']+layout['sides']:s+=band(bounds)
    for i,(x,y,w) in enumerate(layout['logos']):
        s+=logo(x,y,w)
        # Add a small fleet identifier only within the clear painted band.
        bottom=y+w*186/922
        s+=label(x,bottom+46,fleet+' / ALUMNI SUPPORT',29)
        bx0,by0,bx1,by1=layout['sides'][i]
        if by1-bottom>170:s+=trace(x+20,by1-45,w*.75)
    # Decorative roof cells occupy only the selected clear UV panel.
    x,y,w,h=layout['roof'];s+=cells(x,y,w,h)
    return svg(4096,4096,s)

def auxiliary_art(name,w,h):
    if 'Deflector' in name:
        # Deflector maps use tall narrow islands. Reserve white above the skirt.
        s=rect(0,0,w,h,WHITE)+rect(0,h*.70,w,h*.30,NAVY)+rect(0,h*.69,w,h*.02,GOLD)
    else:
        s=rect(0,0,w,h,NAVY)
        # Two horizontally arranged skirt islands are common in the source maps.
        for y in [h*.08,h*.57]:
            s+=rect(0,y,w,max(12,h*.025),GOLD)
            if w>=1024:s+=trace(w*.10,y+h*.19,w*.40)
    return svg(w,h,s)

def tobj(path):
    head=bytes.fromhex('010AB170000000000000000000000000000000000100020002000303030002020001000000010000')
    b=('/'+path).encode('ascii');return head+struct.pack('<II',len(b),0)+b
def unit(kind,name,body):return f'SiiNunit\n{{\n{kind}: {name}\n{{\n{body}\n}}\n}}\n'
def texture_name(model,filename):
    if filename.startswith('Cabin ') and not filename.startswith('Cabin Deflectors'):
        code=filename.split(' (')[0].lower().replace(' ','_')
    else:code=re.sub('[^a-z0-9]+','_',filename[:-4].lower()).strip('_')
    return 'trk_'+model.replace('.','_')+'_'+code

def build(args):
    catalog=json.loads((ROOT/'source/truck-template-catalog.json').read_text())
    metadata=json.loads((ROOT/'source/expanded-truck-vehicles.json').read_text())
    layouts=json.loads((ROOT/'source/truck-livery-layouts.json').read_text())
    archive=Path(args.templates)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=catalog['archive_sha256']:
        raise ValueError('Template archive does not match the verified v2.1.3 archive. Update the catalog before changing sources.')
    seed=Path(args.base_mod) if args.base_mod else next((p for p in [ROOT/'mods/gtsr-trucks-v0.1.scs',ROOT/'mods/gtsr-trucks-v0.2.scs'] if p.exists()),None)
    if not seed:raise ValueError('No existing Scania truck module found; provide --base-mod.')
    # Preserve the original Scania module, stripping any previous expansion on reruns.
    with zipfile.ZipFile(seed) as z:
        original={}
        for name in z.namelist():
            virtual=name[5:] if name.startswith('base/') else name
            if name.startswith('dlc_') or '/trk_' in virtual:continue
            if virtual.startswith('def/vehicle/truck/') and virtual.split('/')[3] in metadata:continue
            original[virtual]=z.read(name)
    (ROOT/'textures').mkdir(exist_ok=True)
    qa=Path(args.qa_dir) if args.qa_dir else None
    if qa:qa.mkdir(parents=True,exist_ok=True)
    index=json.loads((ROOT/'source/texture-index.json').read_text())
    index=[x for x in index if not x['name'].startswith('trk_')]
    export=[];vehicle_info=[];representatives=[]
    with zipfile.ZipFile(archive) as z:
        for number,model in enumerate(catalog['models'],2):
            key=model['internal_vehicle_id'];meta=metadata[key];layout=layouts[key]
            mount=MOUNTS.get(key,'base');fleet=f'TK-{number:02}'
            by_file={};cabin_defs=[]
            for t in model['templates']:
                fn=t['archive_path'].rsplit('/',1)[-1]
                name=texture_name(key,fn);by_file[fn[:-4]]=name
                if t['kind']=='main_cabin':
                    source=cabin_art(key,t['cabin'],layout,fleet)
                    runtime_ids=next(c['internal_name'] for c in meta['cabins'] if c['name']==t['cabin'])
                    cabin_defs.append(({**t,'internal_cabin_ids':runtime_ids},name))
                else:source=auxiliary_art(fn,t['width'],t['height'])
                cached=args.reuse_textures and all((ROOT/'textures'/f'{name}.{ext}').exists() for ext in ['svg','png','dds']) and (ROOT/'textures'/f'{name}.svg').read_bytes()==source.encode()
                im=Image.open(ROOT/'textures'/f'{name}.png').convert('RGBA') if cached else render(source)
                if im.size!=(t['width'],t['height']):raise ValueError('Unexpected rendered dimensions '+name)
                if not cached:
                    (ROOT/'textures'/f'{name}.svg').write_bytes(source.encode())
                    im.save(ROOT/'textures'/f'{name}.png')
                    (ROOT/'textures'/f'{name}.dds').write_bytes(encode_dds(im))
                index.append({'name':name,'size':list(im.size),'mip_levels':1+int(math.log2(max(im.size))),'format':'DXT5 / BC3','template':t['archive_path'],'vehicle_id':key,'cabin':t.get('cabin'),'mount':mount})
                export.append((mount,name))
                if qa:
                    # Development-only overlay: never copy the author's wireframe to the release.
                    wire=Image.open(io.BytesIO(z.read(t['archive_path']))).convert('L')
                    mask=ImageOps.invert(wire).point(lambda x:int(x*.68))
                    overlay=im.copy();overlay.paste(Image.new('RGB',im.size,'#EE5984'),(0,0),mask)
                    overlay.thumbnail((840,840));overlay.convert('RGB').save(qa/f'{name}.jpg',quality=90)
                if t['kind']=='main_cabin' and len(cabin_defs)==1:
                    preview=im.copy();preview.thumbnail((1000,1000))
                    preview.convert('RGB').save(ROOT/'previews'/f'{key.replace(".","-")}-texture.jpg',quality=92)
                    representatives.append({'model':meta['name'],'vehicle':key,'texture':name,'crop':layout['side_crop']})
            vehicle_info.append({'vehicle_id':key,'name':meta['name'],'mount':mount,'fleet_number':fleet,'cabin_count':len(cabin_defs),'template_count':len(model['templates']),'cabins':[{'name':t['cabin'],'ids':t['internal_cabin_ids'],'texture':name} for t,name in cabin_defs],'auxiliary_map_count':len(model['templates'])-len(cabin_defs)})
            print(f"Built {meta['name']}: {len(cabin_defs)} cabins, {len(model['templates'])-len(cabin_defs)} auxiliary maps",flush=True)

    target=ROOT/'mods/gtsr-trucks-v0.2.scs'
    temp=target.with_suffix('.scs.tmp')
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for name,data in original.items():
            if name in ['manifest.sii','Description.txt','Image.jpg']:continue
            out.writestr('base/'+name,data)
        out.writestr('manifest.sii',unit('mod_package','.gtsr_package',' package_version: "0.2.0"\n display_name: "Solar Circuit / 15 Trucks [visual check needed]"\n author: "Personal alumni fleet / Codex"\n category[]: "paint_job"\n mp_mod_optional: true\n icon: "Image.jpg"\n description_file: "Description.txt"'))
        thumbnail=render(svg(552,324,rect(0,0,552,324,NAVY)+rect(0,0,552,12,GOLD)+logo(35,50,480)+label(35,220,'SOLAR CIRCUIT',35)+label(35,280,'15 TRUCK MODELS',25,GOLD)))
        thumb_bytes=io.BytesIO();thumbnail.convert('RGB').resize((276,162)).save(thumb_bytes,format='JPEG',quality=95)
        out.writestr('Image.jpg',thumb_bytes.getvalue())
        if 'gtsr_solar/solid-white.dds' not in original:
            out.write(ROOT/'textures/solid-white.dds','base/gtsr_solar/solid-white.dds')
            out.writestr('base/gtsr_solar/solid-white.tobj',tobj('gtsr_solar/solid-white.dds'))
        out.writestr('Description.txt','Solar Circuit 0.2: 15 SCS truck models, 39 cabin layouts.\nScania S 2016, Volvo FH3/FH4/FH5/FH6 including Aero, Iveco Stralis/Hi-Way/S-Way, MAN TGX Euro 5/Euro 6/GX-GM-GN, Renault Magnum/Premium/T/E-Tech T.\nTruck DLC parts load only when the matching truck DLC is present.\nPersonal alumni tribute. Static validation and template overlays checked; no in-game test.\n')
        for mount,name in export:
            path='gtsr_solar/'+name
            out.write(ROOT/'textures'/f'{name}.dds',mount+'/'+path+'.dds')
            out.writestr(mount+'/'+path+'.tobj',tobj(path+'.dds'))
        for info in vehicle_info:
            key=info['vehicle_id'];meta=metadata[key];mount=info['mount']
            mapped={t['archive_path'].rsplit('/',1)[-1][:-4]:texture_name(key,t['archive_path'].rsplit('/',1)[-1]) for t in next(m for m in catalog['models'] if m['internal_vehicle_id']==key)['templates']}
            for i,cabin in enumerate(info['cabins']):
                ident='gtsrsc_'+str(i)
                virtual=f'def/vehicle/truck/{key}/paint_job/{ident}.sii'
                body=f' name: "Solar Circuit - Alumni Support"\n price: 1000\n unlock: 0\n icon: "gtsrsc_icon"\n airbrush: true\n base_color: (1.0, 1.0, 1.0)\n base_color_locked: true\n stock: false\n paint_job_mask: "/gtsr_solar/{cabin["texture"]}.tobj"'
                if meta['alt_uv']:body+='\n alternate_uvset: true'
                # Restrict even single-cabin definitions to their known cabin unit.
                for cid in cabin['ids']:body+=f'\n suitable_for[]: "{cid}.{key}.cabin"'
                out.writestr(mount+'/'+virtual,unit('accessory_paint_job_data',f'{ident}.{key}.paint_job',body))
                if meta['uses_accessories']:
                    accessory='SiiNunit\n{\n'
                    for n,(group,accessories) in enumerate(meta['accessories'].items()):
                        # The Renault tuning pack's short skirts share the standard short map.
                        lookup='Sideskirts (6x Short)' if group=='Sideskirts (6x Short, Tuning Pack)' else group
                        texture=mapped.get(lookup,'solid-white' if 'Deflector' in group else 'solid-navy')
                        accessory+=f'simple_paint_job_data: .ovr{n}\n{{\n paint_job_mask: "/gtsr_solar/{texture}.tobj"\n'
                        for acc in accessories:accessory+=f' acc_list[]: "{acc}"\n'
                        accessory+='}\n'
                    accessory+='}\n'
                    out.writestr(mount+f'/def/vehicle/truck/{key}/paint_job/accessory/{ident}.sii',accessory)
    with zipfile.ZipFile(temp) as z:
        if z.testzip():raise ValueError('Truck archive failed integrity check')
    temp.replace(target)
    (ROOT/'source/texture-index.json').write_bytes(json.dumps(index,indent=2).encode())
    (ROOT/'source/expanded-truck-support.json').write_bytes(json.dumps({'version':'0.2.0','additional_models':14,'additional_cabins':37,'additional_textures':len(export),'truck_models_total':15,'truck_cabins_total':39,'conditional_mounts':MOUNTS,'vehicles':vehicle_info},indent=2).encode())
    (ROOT/'source/truck-preview-index.json').write_bytes(json.dumps(representatives,indent=2).encode())
    print('New truck module:',target,'compressed bytes:',target.stat().st_size,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--templates',required=True)
    parser.add_argument('--base-mod')
    parser.add_argument('--reuse-textures',action='store_true',help='Reuse matching SVG/PNG/DDS exports while rebuilding definitions.')
    parser.add_argument('--qa-dir',help='Optional development overlays. Keep outside the public package.')
    build(parser.parse_args())
