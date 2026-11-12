"""Validate and render the photo-based Rev A4 enclosure option."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"mechanical"))
import appearance as look
import generate as a4


def clear(a,b):
    assert sum(s.Volume() for s in a.intersect(b).solids().vals()) < 1e-6


def validate(out):
    t,f,d,c=look.tray(),look.face(),look.fitted_disk(),look.cover()
    pcb=a4.block(a4.W/2,a4.H/2,a4.W,a4.H,4.8,1.6)
    clear(t,pcb)
    clear(f,pcb)
    clear(t,d)
    clear(t,f)
    clear(f,c)
    module=a4.block(a4.MCU[0],a4.MCU[1]+11.75,18.3,23.8,8.4,4.85)
    plug=a4.block(a4.MCU[0],-2.25,12.5,6,6.55,6.6)
    clear(c,module)
    clear(c,plug)
    clear(f,plug)
    clear(t,plug)
    clear(f,a4.block(*a4.MIC,3.1,4.1,6.4,1.12))
    clear(f,a4.cyl(*a4.MIC_PORT,a4.MIC_BORE/2-.01,7.6,4))
    assert 1.35-look.SEAT_DEPTH>=1.0
    for x,y in a4.MOUNT:
        clear(f,a4.cyl(x,y,1.05,4.9,6.48))
    key=look.cap("agent")
    for i,(x,y) in enumerate(a4.KEYS):
        clear(f,a4.block(x,y,13.8,13.8,9.88,1.55))
        if i not in (a4.PTT_PRIMARY,a4.PTT_SECONDARY):
            moving=key.translate((x,-y,6.4+9.2-4))
            clear(f,moving)
            clear(c,moving)
    x,y=a4.KEYS[a4.PTT_PRIMARY]
    clear(f,look.cap("ptt").translate((x+a4.PTT_PITCH/2,-y,6.4+9.2-4)))
    clear(f,a4.cyl(*a4.ENC,8.8,6.4+13.3,9))
    for path in out.glob("*.stl"):
        blob=path.read_bytes()
        count=struct.unpack_from("<I",blob,80)[0]
        assert len(blob)==84+50*count
        edges=Counter()
        for i in range(count):
            flat=struct.unpack_from("<9f",blob,96+50*i)
            pts=[tuple(round(v,5) for v in flat[j:j+3]) for j in (0,3,6)]
            edges.update(tuple(sorted((a,b))) for a,b in zip(pts,pts[1:]+pts[:1]))
        assert set(edges.values())=={2},path
    count=len(list(out.glob("*.stl")))
    assert count==12
    print(f"Verified {count} closed meshes, rear seat, cover/USB, microphone and 4 mm key travel.")


def render(out,cli):
    src=(ROOT/"hardware/Gowuji-RevA.kicad_pcb").read_text(encoding="utf-8").rstrip()
    for n in look.NAMES+("bare",):
        src=src.replace(f'${{KIPRJMOD}}/models/mx-{n}.step',(out/f"preview-mx-{n}.step").as_posix())
    src=src.replace("${KIPRJMOD}/models/ec11.step",(out/"preview-encoder.step").as_posix())
    src=src.replace("${KIPRJMOD}",(ROOT/"hardware").as_posix())
    preview=out/"appearance-preview.kicad_pcb"
    case=json.dumps((out/"enclosure.step").as_posix(),ensure_ascii=False)
    preview.write_text(src[:-1]+f'''(footprint "Preview:Enclosure" (layer "F.Cu") (at 0 0)
      (attr board_only exclude_from_bom exclude_from_pos_files)
      (model {case} (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0))))
    )\n''',encoding="utf-8")
    for name,side,angle in (("front","top","330,0,18"),("rear","bottom","28,0,160")):
        subprocess.run([cli,"pcb","render","--width","1300","--height","960","--background","opaque",
                        "--quality","high","--side",side,"--rotate",angle,"--zoom",".76",
                        "--output",str(out/f"{name}.png"),str(preview)],cwd=ROOT,check=True)


def package(out):
    with zipfile.ZipFile(out/"GOWUJI-A4-appearance.zip","w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.iterdir()):
            if (p.suffix==".stl" or p.suffix==".png" or
                p.suffix==".step" and not p.name.startswith("preview-")):
                z.write(p,p.name)
        z.write(ROOT/"docs/appearance.md","appearance.md")
        for name in ("light-pipes.stl","joystick-cap.stl","mx-fit-coupon.stl"):
            z.write(ROOT/"mechanical"/name,"reuse-a4/"+name)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=ROOT/"build/appearance")
    parser.add_argument("--kicad-cli",default="kicad-cli")
    args=parser.parse_args()
    out=args.out.resolve()
    validate(out)
    render(out,args.kicad_cli)
    package(out)
