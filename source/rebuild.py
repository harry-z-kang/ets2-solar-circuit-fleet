"""Rebuild edited Solar Circuit SVG maps. Requires: pip install pillow pymupdf.
Output is written to rebuilt/, leaving the original installable modules intact.
"""
from pathlib import Path
import argparse, io, struct, zipfile
from PIL import Image
import pymupdf

def encode_dds(im):
    im=im.convert('RGBA');im.putalpha(255);width,height=im.size;parts=[]
    while True:
        stream=io.BytesIO();im.save(stream,format='DDS',pixel_format='DXT5')
        raw=stream.getvalue();parts.append(raw[128:])
        if im.size==(1,1):break
        im=im.resize((max(1,im.width//2),max(1,im.height//2)),Image.Resampling.LANCZOS)
    header=bytearray(raw[:128]);struct.pack_into('<I',header,8,0xA1007)
    struct.pack_into('<II',header,12,height,width)
    struct.pack_into('<I',header,20,((width+3)//4)*((height+3)//4)*16)
    struct.pack_into('<I',header,28,len(parts));struct.pack_into('<I',header,108,0x401008)
    return bytes(header)+b''.join(parts)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--texture',action='append',help='Texture basename; repeat to select several. Defaults to all.')
    args=parser.parse_args();root=Path(__file__).resolve().parent.parent
    sources=sorted((root/'textures').glob('*.svg'))
    if args.texture:
        wanted=set(args.texture);available={f.stem for f in sources}
        if wanted-available:parser.error('Unknown textures: '+', '.join(sorted(wanted-available)))
        sources=[f for f in sources if f.stem in wanted]
    output=root/'rebuilt';(output/'textures').mkdir(parents=True,exist_ok=True)
    (output/'mods').mkdir(exist_ok=True);replacements={}
    for f in sources:
        doc=pymupdf.open(stream=f.read_bytes(),filetype='svg');pix=doc[0].get_pixmap(alpha=True)
        im=Image.frombytes('RGBA',(pix.width,pix.height),pix.samples);w,h=im.size
        if w&(w-1) or h&(h-1):raise ValueError(f'{f.name}: DDS dimensions must be powers of two')
        im.putalpha(255);im.save(output/'textures'/f'{f.stem}.png')
        raw=encode_dds(im);(output/'textures'/f'{f.stem}.dds').write_bytes(raw)
        replacements[f'gtsr_solar/{f.stem}.dds']=raw
        print('Rebuilt',f.stem,w,h)
    for src in sorted((root/'mods').glob('*.scs')):
        with zipfile.ZipFile(src) as zin,zipfile.ZipFile(output/'mods'/src.name,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zout:
            for n in zin.namelist():
                first,_,rest=n.partition('/')
                virtual=rest if first=='base' or first.startswith('dlc_') else n
                data=replacements[virtual] if virtual in replacements else zin.read(n)
                zout.writestr(n,data)
    print('Updated modules:',output/'mods')
    print('Install one copy of each module: originals OR rebuilt files. Check the result in game.')

if __name__=='__main__':main()
