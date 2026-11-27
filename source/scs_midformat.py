"""Small read-only importer for ConverterPIX text exports; no game data bundled."""
from pathlib import Path
import re
import struct


def sections(text, kind):
    start = 0
    while match := re.search(r'\b' + kind + r'\s*\{', text[start:]):
        begin = start + match.end()
        end, depth = begin, 1
        while depth:
            depth += (text[end] == '{') - (text[end] == '}')
            end += 1
        yield text[begin:end - 1]
        start = end


def number(value):
    return struct.unpack('!f', bytes.fromhex(value[1:]))[0] if value.startswith('&') else float(value)


def named(block):
    return re.search(r'Name:\s*"([^"]+)"', block)[1]


def locators(path):
    result = {}
    for block in sections(Path(path).read_text(), 'Locator'):
        result[named(block)] = {
            key.lower(): [number(v) for v in re.search(key + r':\s*\(([^)]+)', block)[1].split()]
            for key in ['Position', 'Rotation']
        }
    return result


def transform(point, locator, direction=False):
    if not locator:
        return point
    w, x, y, z = locator['rotation']
    vx, vy, vz = point
    tx, ty, tz = 2*(y*vz-z*vy), 2*(z*vx-x*vz), 2*(x*vy-y*vx)
    offset = (0, 0, 0) if direction else locator['position']
    return (vx+w*tx+y*tz-z*ty+offset[0], vy+w*ty+z*tx-x*tz+offset[1], vz+w*tz+x*ty-y*tx+offset[2])


def read_model(path, variant='default', look='default'):
    path = Path(path)
    text = path.read_text()
    traits = path.with_suffix('.pit').read_text()
    looks = list(sections(traits, 'Look'))
    selected = next((b for b in looks if named(b).lower() == look.lower()), looks[0])
    materials = []
    for block in sections(selected, 'Material'):
        attributes = {}
        for attr in sections(block, 'Attribute'):
            tag = re.search(r'Tag:\s*"([^"]+)"', attr)[1]
            values = re.search(r'Value:\s*\(([^)]+)', attr)
            if values:
                attributes[tag] = tuple(number(v) for v in values[1].split())
        textures = {}
        for tex in sections(block, 'Texture'):
            tag = re.search(r'Tag:\s*"([^"]+)"', tex)[1].split(':')[-1]
            textures[tag] = re.search(r'Value:\s*"([^"]+)"', tex)[1]
        materials.append({'alias': re.search(r'Alias:\s*"([^"]+)"', block)[1],
                          'effect': re.search(r'Effect:\s*"([^"]+)"', block)[1],
                          'attributes': attributes, 'textures': textures})
    variants = list(sections(traits, 'Variant'))
    chosen = next((b for b in variants if named(b).lower() == variant.lower()), None)
    if chosen is None:
        raise ValueError(f'{path.name}: variant {variant!r} unavailable')
    visible = {named(p) for p in sections(chosen, 'Part') if re.search(r'Value:\s*\(\s*1\s*\)', p)}
    indices = set()
    for part in sections(text, 'Part'):
        if named(part) in visible:
            match = re.search(r'^\s*Pieces:\s*([^\n]+)', part, re.M)
            if match:
                indices.update(map(int, match[1].split()))
    pieces = []
    for block in sections(text, 'Piece'):
        index = int(re.search(r'\bIndex:\s*(\d+)', block)[1])
        if index not in indices:
            continue
        streams, aliases = {}, {}
        for stream in sections(block, 'Stream'):
            tag = re.search(r'Tag:\s*"([^"]+)"', stream)[1]
            if tag not in ['_POSITION', '_NORMAL'] and not tag.startswith('_UV'):
                continue
            streams[tag] = [tuple(number(v) for v in line.split()) for line in re.findall(r'^\s*\d+\s*\(([^)]+)\)', stream, re.M)]
            alias = re.search(r'Aliases:\s*([^\n]+)', stream)
            if alias:
                for value in re.findall(r'"([^"]+)"', alias[1]):
                    aliases[value] = tag
        triangles = next(sections(block, 'Triangles'))
        pieces.append({'index': index, 'material': int(re.search(r'\bMaterial:\s*(\d+)', block)[1]),
                       'streams': streams, 'aliases': aliases,
                       'triangles': [tuple(map(int, line.split())) for line in re.findall(r'^\s*\d+\s*\(([^)]+)\)', triangles, re.M)]})
    return materials, pieces
