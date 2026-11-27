"""Optional private-model calibration for v0.5.1. Exports only authored color masks."""
from pathlib import Path
import json,re,math
from PIL import Image,ImageDraw,ImageFilter
import argparse
from scs_midformat import read_model,sections,number

def parse(path):
    mats,pieces=read_model(path)
    return [{**p,'paint_uv':p['aliases']['_TEXCOORD1']} for p in pieces if 'truckpaint' in mats[p['material']]['effect']]
root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--models',type=Path,default=root/'work/panel-refinement/converted');a=p.parse_args()
conv=a.models;out=root/'artwork/panel-bases';out.mkdir(parents=True,exist_ok=True)
layouts=__import__('json').loads((root/'source/feedback-fix-layouts.json').read_text())
NAVY=(5,30,57);GOLD=(179,144,81)

def locators(path):
    d={}
    for s in sections(path.read_text(),'Locator'):
        name=re.search(r'Name: "([^"]+)"',s)[1]
        d[name]={'position':[number(v) for v in re.search(r'Position: \(([^)]+)',s)[1].split()],'rotation':[number(v) for v in re.search(r'Rotation: \(([^)]+)',s)[1].split()]}
    return d

def transform(p,t):
    if not t:return p
    w,x,y,z=t['rotation'];vx,vy,vz=p
    tx=2*(y*vz-z*vy);ty=2*(z*vx-x*vz);tz=2*(x*vy-y*vx)
    return (vx+w*tx+y*tz-z*ty+t['position'][0],vy+w*ty+z*tx-x*tz+t['position'][1],vz+w*tz+x*ty-y*tx+t['position'][2])

def clip(poly,func,less=True):
    result=[]
    if not poly:return result
    previous=poly[-1];pv=func(previous);pi=pv<=0 if less else pv>=0
    for cur in poly:
        cv=func(cur);ci=cv<=0 if less else cv>=0
        if ci!=pi:
            frac=pv/(pv-cv);result.append(tuple(previous[k]+frac*(cur[k]-previous[k]) for k in range(5)))
        if ci:result.append(cur)
        previous,pv,pi=cur,cv,ci
    return result

models={
'man-lions-coach-139':('vehicle/bus/man_lions_24/cabin/cab_139h6.pim',(8192,4096),1.44),
'scania-touring-137':('vehicle/bus/scania_touring_23/cabin/cab_137h6.pim',(8192,4096),1.54),
'volvo-9700-dd':('vehicle/bus/volvo_9700_23/cabin/cab_143d6.pim',(8192,4096),1.80),
'trk_volvo_fh_2024_cabin_b_aero':('vehicle/truck/volvo_fh_2024/cabin/globe_xl_aero_2024.pim',(4096,4096),2.152)}
fh_loc=locators(conv/models['trk_volvo_fh_2024_cabin_b_aero'][0])
models.update({
'vl_fh6_aero_side':('vehicle/truck/volvo_fh_2024/accessory/s_deflector/aero.pim',(2048,2048),2.152),
'vl_fh6_standard_side':('vehicle/truck/volvo_fh16_2012/accessory/s_deflector/stock.pim',(2048,2048),2.152),
'vl_fh6_8x4_roof':('vehicle/truck/volvo_fh16_2012/accessory/r_deflector/stock_8x.pim',(1024,1024),2.152),
'vl_fh6_8x4_chassis':('vehicle/truck/volvo_fh_2024/chassis/chs_8x4.pim',(2048,2048),2.152)})
report={}
for name,(model,size,height) in models.items():
    path=conv/model;parts=[(path,None)];loc=locators(path)
    if 'coach' in name or name in ['scania-touring-137','volvo-9700-dd']:
        folder=path.parent;doors=folder/('doors_139h6.pim' if name.startswith('man') else 'doors.pim')
        parts.append((doors,None))
        for category in ['f_bumper','r_bumper','r_panel']:
            for p in (folder.parent/'accessory'/category).glob('*.pim'):
                if category in loc:parts.append((p,loc[category]))
    if name in ['vl_fh6_aero_side','vl_fh6_standard_side']:parts=[(path,fh_loc['s_deflector'])]
    if name=='vl_fh6_8x4_roof':parts=[(path,fh_loc['r_deflector'])]
    navy=Image.new('L',size);gold=Image.new('L',size);nd=ImageDraw.Draw(navy);gd=ImageDraw.Draw(gold);triangles=0;component_stats=[]
    for part,t in parts:
        paint=parse(part);partcount=0
        for piece in paint:
            ss=piece['streams'];pos=[transform(p,t) for p in ss['_POSITION']];uv=ss[piece['paint_uv']]
            for indices in piece['triangles']:
                poly=[(*pos[i],uv[i][0]*size[0],uv[i][1]*size[1]) for i in indices]
                points=layouts['coaches'].get(name,{}).get('front_profile',[[-100,height],[100,height]])
                profile=[(aa[0],bb[0],aa[1],bb[1]) for aa,bb in zip(points,points[1:])]
                for z0,z1,h0,h1 in profile:
                    below=clip(clip(poly,lambda p:p[2]-z0,False),lambda p:p[2]-z1,True)
                    slope=(h1-h0)/(z1-z0)
                    below=clip(below,lambda p:p[1]-(h0+(p[2]-z0)*slope))
                    if len(below)>=3:nd.polygon([(v[3],v[4]) for v in below],fill=255)
                # The DD uses a raised road through the rear bay, below its windows.
                road= name=='volvo-9700-dd'
                segments=[(-100,2,.75,.75),(2,5,.75,1.30),(5,100,1.30,1.30)] if road else profile
                width=.035 if road else .045
                for z0,z1,h0,h1 in segments:
                    cut=clip(clip(poly,lambda p:p[2]-z0,False),lambda p:p[2]-z1,True)
                    slope=(h1-h0)/(z1-z0)
                    fn=lambda p:p[1]-(h0+(p[2]-z0)*slope)
                    cut=clip(cut,fn,True);cut=clip(cut,lambda p:fn(p)+width,False)
                    if len(cut)>=3:gd.polygon([(v[3],v[4]) for v in cut],fill=255)
                partcount+=1
        triangles+=partcount;component_stats.append({'model':part.relative_to(conv).as_posix(),'paint_triangles':partcount,'attachment_y':t['position'][1] if t else 0})
    # A few pixels of color bleed prevent white mip seams along UV island edges.
    navy=navy.filter(ImageFilter.MaxFilter(7));gold=gold.filter(ImageFilter.MaxFilter(3))
    im=Image.new('RGB',size,'white');im.paste(NAVY,(0,0),navy);im.paste(GOLD,(0,0),gold);im.save(out/(name+'.png'))
    preview=im.copy();preview.thumbnail((1600,1000));preview.save(root/'work/panel-refinement'/(name+'-base.jpg'))
    report[name]={'size':list(size),'navy_top_m':height,'gold_width_m':.035 if name=='volvo-9700-dd' else .045,'paint_triangles':triangles,'components':component_stats,'uv_layer':'Stream aliased as _TEXCOORD1; exported V is texture-top-down','mask_bleed_pixels':3}
    print(name,triangles,component_stats,flush=True)
(root/'work/panel-refinement/feedback-projection-report.json').write_text(json.dumps(report,indent=2))
