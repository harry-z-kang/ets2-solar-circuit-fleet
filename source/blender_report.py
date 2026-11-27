"""Create a local contact sheet and HTML gallery from completed Blender QA runs."""
from pathlib import Path
import argparse
import html
import json
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('work/blender-qa'))
    args = parser.parse_args()
    sections = []
    for report in sorted(args.output.glob('*/studio/inspection.json')):
        data = json.loads(report.read_text())
        tiles = []
        sheet = Image.new('RGB',(1280,4*430),'#edf0ef')
        draw = ImageDraw.Draw(sheet)
        for i,view in enumerate(data['renders']):
            path = Path(view['path'])
            image = Image.open(path).convert('RGB')
            image.thumbnail((630,395))
            x,y = i%2*640,i//2*430
            sheet.paste(image,(x,y+28))
            draw.text((x+12,y+8),view['view'],fill='#051e39')
            relative = path.relative_to(args.output.resolve()).as_posix()
            tiles.append(f'<figure><a href="{relative}"><img src="{relative}"></a><figcaption>{html.escape(view["view"])}</figcaption></figure>')
        sheet.save(report.parent/'contact-sheet.jpg',quality=93)
        blend = Path(data['scene_path']).relative_to(args.output.resolve()).as_posix()
        sections.append(f'<section><h2>{html.escape(data["vehicle"])}</h2><p><a href="{blend}">Local Blender scene</a> · {len(data["renders"])} views · {html.escape(data["blender_version"])}</p><div class="grid">'+''.join(tiles)+'</div></section>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Blender livery inspection</title><style>body{font:16px Arial;background:#edf0ef;color:#051e39;max-width:1500px;margin:auto;padding:32px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}figure{margin:0;background:white;padding:8px}img{width:100%}a{color:#075c7d}section{margin:36px 0}figcaption{padding:8px}</style><h1>Blender livery inspection</h1><p>Actual packaged DDS paint on local vehicle geometry. Approximate studio materials and opaque glazing; this is not the ETS2 renderer. Models and scenes remain private.</p>'''+''.join(sections)+'</html>'
    (args.output/'index.html').write_text(page,encoding='utf-8')
    print('Gallery:',args.output/'index.html')


if __name__=='__main__':
    main()
