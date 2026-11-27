"""Run inside Blender via blender_qa.py. Read-only livery inspection, not game export."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scs_midformat import locators, read_model, transform

ROOT = Path(__file__).resolve().parent.parent
IMAGES = {}
MATERIALS = {}
MODELS = {}
REPORT = {'warnings': [], 'models': [], 'paint_textures': {}, 'renders': []}


def coordinates(p):
    # SCS right/up/back -> Blender right/forward/up, a proper rotation.
    return (p[0], -p[2], p[1])


def image(path):
    path = Path(path).resolve()
    if path not in IMAGES:
        IMAGES[path] = bpy.data.images.load(str(path), check_existing=True)
    return IMAGES[path]


def resolve_base(args, value):
    if not value:
        return None
    tobj = args.models/value.lstrip('/')
    tobj = tobj.with_suffix('.tobj')
    if tobj.exists():
        match = re.search(r'^\s*(/[^\s]+\.dds)', tobj.read_text(), re.M)
        if match:
            path = args.models/match[1].lstrip('/')
            if path.exists():
                return path
    return None


def paint_file(args, name):
    if not name:
        return None
    candidates = []
    if args.texture_dir:
        candidates += [args.texture_dir/(name+ext) for ext in ['.dds', '.png']]
    candidates += [args.texture_cache/(name+'.dds')]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        raise FileNotFoundError('Paint texture unavailable: '+name)
    REPORT['paint_textures'][name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return path


def material(args, definition, paint):
    key = (json.dumps(definition, sort_keys=True), str(paint), args.flat)
    if key in MATERIALS:
        return MATERIALS[key]
    effect, alias = definition['effect'], definition['alias']
    mat = bpy.data.materials.new(alias+' | '+(paint.stem if paint else 'base'))
    mat.use_nodes = True
    mat.use_backface_culling = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    if 'Weight' in shader.inputs:
        shader.inputs['Weight'].default_value = 1.0
    output = nodes.get('Material Output')
    shader.inputs['Roughness'].default_value = .38 if 'truckpaint' in effect else .65
    shader.inputs['Metallic'].default_value = .7 if 'chrome' in alias else 0
    if 'glass' in effect:
        # Stable opaque glazing shows the exterior paint boundaries without inventing an interior.
        shader.inputs['Base Color'].default_value = (.018, .032, .042, 1)
        shader.inputs['Roughness'].default_value = .2
    else:
        paint = paint if 'truckpaint' in effect else None
        base = paint or resolve_base(args, definition['textures'].get('texture_base'))
        color = definition['attributes'].get('diffuse', (.35, .35, .35))
        shader.inputs['Base Color'].default_value = (*color[:3], 1)
        if base:
            tex = nodes.new('ShaderNodeTexImage')
            tex.image = image(base)
            tex.interpolation = 'Linear'
            uv = nodes.new('ShaderNodeUVMap')
            uv.uv_map = '_TEXCOORD1' if paint else '_TEXCOORD0'
            links.new(uv.outputs['UV'], tex.inputs['Vector'])
            links.new(tex.outputs['Color'], shader.inputs['Base Color'])
            if re.search(r'\.a(?:\.|$)', effect):
                links.new(tex.outputs['Alpha'], shader.inputs['Alpha'])
                mat.surface_render_method = 'DITHERED'
            if paint and args.flat:
                emission = nodes.new('ShaderNodeEmission')
                links.new(tex.outputs['Color'], emission.inputs['Color'])
                links.new(emission.outputs[0], output.inputs['Surface'])
        elif definition['textures'].get('texture_base'):
            REPORT['warnings'].append('Missing base texture; diffuse fallback: '+definition['textures']['texture_base'])
    MATERIALS[key] = mat
    return mat


def import_model(args, part, attachment=None, label=None):
    path = args.models/part['model']
    if not path.exists():
        raise FileNotFoundError(str(path)+'; run prepare_blender_models.py first')
    key = (path, part.get('variant', 'default'), part.get('look', 'default'))
    if key not in MODELS:
        MODELS[key] = read_model(*key)
    definitions, pieces = MODELS[key]
    texture = paint_file(args, part.get('texture'))
    collection = bpy.data.collections.new(label or part['model'])
    bpy.context.scene.collection.children.link(collection)
    count, triangles = 0, 0
    for piece in pieces:
        definition = definitions[piece['material']]
        if 'shadow' in definition['effect'] or 'glass_int' in definition['alias']:
            continue
        streams, aliases = piece['streams'], piece['aliases']
        if texture and 'truckpaint' in definition['effect'] and '_TEXCOORD1' not in aliases:
            raise ValueError('Paint UV alias missing: '+str(path))
        vertices = [coordinates(transform(p, attachment)) for p in streams['_POSITION']]
        mesh = bpy.data.meshes.new(path.stem+'_'+str(piece['index']))
        # SCS triangles wind clockwise; Blender expects counter-clockwise faces.
        # Keeping SCS winding makes Cycles treat exterior faces as interiors.
        mesh.from_pydata(vertices, [], [(c,b,a) for a,b,c in piece['triangles']])
        mesh.update()
        for alias in ['_TEXCOORD0', '_TEXCOORD1', '_TEXCOORD2']:
            if alias not in aliases:
                continue
            values = streams[aliases[alias]]
            layer = mesh.uv_layers.new(name=alias)
            flat_uv = [component for loop in mesh.loops for component in (values[loop.vertex_index][0], 1-values[loop.vertex_index][1])]
            layer.data.foreach_set('uv', flat_uv)
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        if '_NORMAL' in streams:
            mesh.normals_split_custom_set_from_vertices([coordinates(transform(n, attachment, direction=True)) for n in streams['_NORMAL']])
        obj = bpy.data.objects.new(mesh.name, mesh)
        collection.objects.link(obj)
        obj.data.materials.append(material(args, definition, texture))
        obj['scs_model'] = part['model']
        obj['scs_piece'] = piece['index']
        count += 1
        triangles += len(piece['triangles'])
    REPORT['models'].append({'model': part['model'], 'variant': key[1], 'look': key[2], 'objects': count, 'triangles': triangles, 'attached': attachment is not None})


def area(name, location, energy, size, target):
    light = bpy.data.lights.new(name, 'AREA')
    light.energy, light.shape, light.size = energy, 'DISK', size
    obj = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (target-obj.location).to_track_quat('-Z', 'Y').to_euler()


def camera(name, direction, center, corners, aspect):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    radius = max((p-center).length for p in corners)
    obj.location = center+Vector(direction).normalized()*radius*4
    obj.rotation_euler = (center-obj.location).to_track_quat('-Z', 'Y').to_euler()
    inverse = obj.rotation_euler.to_matrix().transposed()
    projected = [inverse@(p-center) for p in corners]
    # ortho_scale is horizontal camera width when landscape rendering.
    data.type = 'ORTHO'
    data.ortho_scale = max(max(abs(p.x) for p in projected)*2, max(abs(p.y) for p in projected)*2*aspect)*1.13
    data.clip_start, data.clip_end = .01, radius*20
    return obj


def main():
    parser = argparse.ArgumentParser()
    for name in ['vehicle', 'models', 'output', 'texture-cache', 'texture-dir', 'views']:
        parser.add_argument('--'+name)
    parser.add_argument('--width', type=int, default=1440)
    parser.add_argument('--samples', type=int, default=16)
    parser.add_argument('--flat', action='store_true')
    parser.add_argument('--scene-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.context.preferences.filepaths.file_preview_type = 'NONE'
    bpy.context.preferences.filepaths.save_version = 0
    for name in ['models', 'output', 'texture_cache', 'texture_dir']:
        if getattr(args, name):
            setattr(args, name, Path(getattr(args, name)))
    destination = args.output/args.vehicle/('flat' if args.flat else 'studio')
    destination.mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT/'source/blender-vehicles.json').read_text())[args.vehicle]
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    main_locators = locators(args.models/config['main'])
    chassis_part = next((p for p in config['parts'] if p.get('wheel_root')), None)
    chassis_locators = locators(args.models/chassis_part['model']) if chassis_part else {}
    for part in config['parts']:
        attachment = None
        if part.get('locator'):
            source_locators = chassis_locators if part.get('locator_root') == 'chassis' else main_locators
            attachment = source_locators[part['locator']]
        import_model(args, part, attachment)
        if part.get('wheel_root'):
            for name, locator in locators(args.models/part['model']).items():
                match = re.fullmatch(r'wheel_([frab])_\d+(?:_\d+)?', name)
                if match:
                    axle = 'front' if match[1] in ['f', 'a'] else 'rear'
                    for kind in ['tire', 'rim']:
                        wheel = {'model': f'vehicle/truck/upgrade/wheel/{kind}/{axle}_1.pim', 'texture': None,
                                 'variant': 'left' if locator['position'][0] < 0 else 'right'}
                        if kind == 'tire':
                            wheel['look'] = 'trailmaster'
                        import_model(args, wheel, locator, name+' '+kind)
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    points = [obj.matrix_world@Vector(p) for obj in objects for p in obj.bound_box]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low+high)/2
    corners = [Vector((x,y,z)) for x in [low.x,high.x] for y in [low.y,high.y] for z in [low.z,high.z]]
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = args.width, round(args.width*.625)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.55,.60,.65,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .5
    area('Softbox left', center+Vector((-6,5,9)), 1500, 8, center)
    area('Softbox right', center+Vector((7,2,7)), 1200, 8, center)
    area('Softbox rear', center+Vector((1,-8,8)), 1700, 8, center)
    bpy.ops.mesh.primitive_plane_add(size=100, location=(center.x,center.y,low.z-.025))
    floor = bpy.context.object
    floor.name = 'Studio floor (QA only)'
    mat = bpy.data.materials.new('Neutral studio floor')
    mat.diffuse_color = (.24,.26,.28,1)
    floor.data.materials.append(mat)
    directions = {'left':(-1,0,.015), 'right':(1,0,.015), 'front':(0,1,.01), 'rear':(0,-1,.01),
                  'front-left':(-1,1,.38), 'front-right':(1,1,.38), 'rear-right':(1,-1,.4), 'roof':(0,0,1)}
    cameras = {n: camera(n,d,center,corners,1.6) for n,d in directions.items()}
    scene.camera = cameras['front-right']
    scene['QA_README'] = 'Local geometry + actual paint DDS. Approximate Blender materials, not ETS2 renderer. Textures are external: rerun the workflow or reload images after rebuilding.'
    for screen in bpy.data.screens:
        for area_ui in screen.areas:
            if area_ui.type == 'VIEW_3D':
                area_ui.spaces.active.region_3d.view_perspective = 'CAMERA'
                area_ui.spaces.active.shading.type = 'MATERIAL'
    bpy.ops.wm.save_as_mainfile(filepath=str(destination/(args.vehicle+'.blend')))
    if not args.scene_only:
        for view in args.views.split(','):
            if view not in cameras:
                raise ValueError('Unknown camera: '+view)
            scene.camera = cameras[view]
            scene.render.filepath = str(destination/(view+'.png'))
            bpy.ops.render.render(write_still=True)
            REPORT['renders'].append({'view': view, 'path': scene.render.filepath})
    REPORT.update({'blender_version': bpy.app.version_string, 'vehicle': args.vehicle, 'bounds_m': [list(low),list(high)],
                   'engine': 'CYCLES CPU', 'mode': 'flat paint' if args.flat else 'studio', 'camera_names': list(cameras),
                   'scene_path': str(destination/(args.vehicle+'.blend')), 'game_runtime_tested': False,
                   'material_limits': ['SCS shader approximated in Blender.', 'Glazing is opaque; interior not imported.', 'Wheels use standard reference rims/tires, not the saved profile configuration.']})
    REPORT['warnings'] = sorted(set(REPORT['warnings']))
    (destination/'inspection.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    print('QA_COMPLETE',args.vehicle,len(REPORT['models']),len(REPORT['renders']),flush=True)


if __name__ == '__main__':
    main()
