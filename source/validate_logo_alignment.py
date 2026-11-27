"""Validate coach logo exports. Optional local geometry and prior archive checks.

python source/validate_logo_alignment.py --models work/panel-refinement/converted
    --coach-before work/logo-alignment/gtsr-coaches-v0.2.1.scs
"""
from pathlib import Path
import argparse,base64,hashlib,io,json,struct,xml.etree.ElementTree as ET,zipfile
from PIL import Image
from align_coach_logos import ROOT,artwork,surface_height


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models',type=Path)
    parser.add_argument('--coach-before',type=Path)
    args = parser.parse_args()
    data = json.loads((ROOT/'source/logo-alignment-layouts.json').read_text())
    baseline = json.loads((ROOT/'SHA256SUMS.json').read_text())
    checks,measurements = [],[]
    def check(name,passed):
        checks.append({'check':name,'passed':bool(passed)})
        assert passed,name
    digest = lambda raw:hashlib.sha256(raw).hexdigest()
    names = set(data['coaches'])
    check('Two requested coach bodies',names=={'man-lions-coach-139','scania-touring-137'})
    for name,layout in data['coaches'].items():
        svg = (ROOT/'textures'/f'{name}.svg').read_text()
        check('Reproducible layout '+name,svg==artwork(name,layout))
        xml = ET.fromstring(svg)
        images = list(xml.iter('{http://www.w3.org/2000/svg}image'))
        check('Preserved stripe and panel base '+name,base64.b64decode(images[0].get('href').split(',',1)[1])==(ROOT/'artwork/panel-bases'/f'{name}.png').read_bytes())
        check('Two side logos '+name,len(images)==3)
        for side,mark in zip(layout['sides'],images[1:]):
            x,y,w,h = [float(mark.get(k)) for k in ['x','y','width','height']]
            check('Unaltered proportional source mark '+name+' '+side['side'],abs(w/h-922/186)<1e-10 and base64.b64decode(mark.get('href').split(',',1)[1])==(ROOT/'artwork/gtsr-logo-original.png').read_bytes())
            values = [side['measured_top_above_ground_m'],side['measured_center_above_ground_m'],side['measured_bottom_above_ground_m']]
            if args.models:
                values = [surface_height(args.models/layout['model'],x+w/2,q,side['side'])-layout['ground_model_y_m'] for q in [y,y+h/2,y+h]]
            check('Shared physical bounds '+name+' '+side['side'],all(abs(a-b)<.001 for a,b in zip(values,[1.25,1.,.75])))
            measurements.append({'vehicle':name,'side':side['side'],'top_center_bottom_m':values,'remeasured_from_geometry':bool(args.models)})
        raw = (ROOT/'textures'/f'{name}.dds').read_bytes()
        hh,ww = struct.unpack_from('<II',raw,12)
        levels = struct.unpack_from('<I',raw,28)[0]
        check('BC3 complete mip header '+name,raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and (ww,hh)==(8192,4096) and levels==14)
        expected = 128
        for _ in range(levels):
            expected += max(1,(ww+3)//4)*max(1,(hh+3)//4)*16
            ww,hh = max(1,ww//2),max(1,hh//2)
        check('Complete mip payload '+name,len(raw)==expected)
        image = Image.open(io.BytesIO(raw));image.load()
        check('Opaque decoded DDS '+name,image.getchannel('A').getextrema()==(255,255))
        for ext in ['png','dds']:
            check('SVG rebuild matches '+name+'.'+ext,(ROOT/'textures'/f'{name}.{ext}').read_bytes()==(ROOT/'rebuilt/textures'/f'{name}.{ext}').read_bytes())
    for path in (ROOT/'textures').iterdir():
        if path.stem not in names and path.suffix in {'.svg','.png','.dds'}:
            check('Preserved unrelated texture '+path.name,digest(path.read_bytes())==baseline[path.relative_to(ROOT).as_posix()])
    current = ROOT/'mods'/data['coach_module']
    with zipfile.ZipFile(current) as z:
        check('Coach archive integrity',z.testzip() is None and len(z.namelist())==len(set(z.namelist())))
        for name in names:
            check('Packaged final texture '+name,z.read('gtsr_solar/'+name+'.dds')==(ROOT/'textures'/f'{name}.dds').read_bytes())
        if args.coach_before:
            with zipfile.ZipFile(args.coach_before) as old:
                check('Coach inventory preserved',set(z.namelist())==set(old.namelist()))
                changed = {n for n in z.namelist() if z.read(n)!=old.read(n)}
                check('Only requested maps and metadata changed',changed=={'manifest.sii','Description.txt',*['gtsr_solar/'+n+'.dds' for n in names]})
        with zipfile.ZipFile(ROOT/'rebuilt/mods'/current.name) as rebuilt:
            check('Coach rebuild preserves every payload',set(z.namelist())==set(rebuilt.namelist()) and all(z.read(n)==rebuilt.read(n) for n in z.namelist()))
    for module in ['gtsr-trucks-v0.5.1.scs','gtsr-trailers-v0.1.scs']:
        check('Unchanged module '+module,digest((ROOT/'mods'/module).read_bytes())==baseline['mods/'+module])
    report = {'version':'0.5.2','checks_passed':len(checks),'checks_total':len(checks),'failures':[],
              'tolerance_m':.001,'reference':'Standard reference tires in the Blender inspection configuration.',
              'measurements':measurements,'checks':checks,'game_runtime_tested':False}
    (ROOT/'source/logo-alignment-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('LOGO_ALIGNMENT_VERIFIED',len(checks))


if __name__=='__main__':main()
