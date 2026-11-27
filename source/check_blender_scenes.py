"""Run inside Blender to verify saved inspection scenes and their external paint."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import bpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('root',type=Path)
parser.add_argument('--views',default='left,right,front,rear,front-left,front-right,rear-right,roof')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
root = args.root.resolve()
expected_views = set(args.views.split(','))
checks = []
for path in sorted(root.glob('*/studio/inspection.json')):
    info = json.loads(path.read_text())
    bpy.ops.wm.open_mainfile(filepath=info['scene_path'])
    cameras = {obj.name for obj in bpy.data.objects if obj.type=='CAMERA'}
    checks.append({'check':info['vehicle']+' saved cameras','passed':set(info['camera_names'])<=cameras})
    textures = {Path(t['path']).resolve():t['sha256'] for t in info['paint_textures'].values()}
    observed = set()
    for obj in bpy.data.objects:
        if obj.type!='MESH':
            continue
        for material in obj.data.materials:
            if not material.node_tree:
                continue
            for node in material.node_tree.nodes:
                if node.type=='TEX_IMAGE' and node.image:
                    source = Path(bpy.path.abspath(node.image.filepath)).resolve()
                    if source in textures:
                        observed.add(source)
                        checks.append({'check':info['vehicle']+' paint UV '+obj.name,'passed':'_TEXCOORD1' in obj.data.uv_layers})
    checks.append({'check':info['vehicle']+' paint images loaded','passed':observed==set(textures)})
    checks.append({'check':info['vehicle']+' external paint hashes','passed':all(p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in textures.items())})
    checks.append({'check':info['vehicle']+' complete renders','passed':len(info['renders'])==len(expected_views) and {r['view'] for r in info['renders']}==expected_views and all(Path(r['path']).exists() for r in info['renders'])})
report = {'blender_version':bpy.app.version_string,'checks_passed':sum(c['passed'] for c in checks),'checks_total':len(checks),'failures':[c for c in checks if not c['passed']],'checks':checks}
(root/'saved-scene-checks.json').write_text(json.dumps(report,indent=2)+'\n')
assert not report['failures'],report['failures']
print('SAVED_SCENES_VERIFIED',report['checks_passed'],flush=True)
