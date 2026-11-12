"""Generate local, simplified component models for KiCad 3D preview."""
from pathlib import Path
import math
import cadquery as cq
from generate import PTT_PITCH, mic_symbol, ptt_cap

OUT=Path(__file__).resolve().parents[1]/"hardware"/"models"
BLACK=(.15,.17,.20)
STEEL=(.76,.79,.82)
GOLD=(.78,.58,.25)
PCB=(.07,.22,.33)
WHITE=(.82,.85,.83)
KEY=(.88,.88,.86)
FROSTED=(.88,.94,.94,.64)

def box(x,y,z,w,d,h):
    return cq.Workplane("XY").box(w,d,h,centered=(True,True,False)).translate((x,y,z))

def cylinder(x,y,z,r,h):
    return cq.Workplane("XY").circle(r).extrude(h).translate((x,y,z))

def save(name, items):
    a=cq.Assembly(name=name)
    for i,(solid,color) in enumerate(items):
        a.add(solid,name=f"part{i+1}",color=cq.Color(*color))
    a.export(str(OUT/f"{name}.step"))

def ink_line(x0,y0,x1,y1):
    x,y=(x0+x1)/2,(y0+y1)/2
    return box(x,y,14.5,math.hypot(x1-x0,y1-y0),.52,.03).rotate(
        (x,y,0),(x,y,1),math.degrees(math.atan2(y1-y0,x1-x0)))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    switch=[(box(0,0,0,14,14,5),BLACK),(box(0,0,5,13,13,3.1),(.28,.30,.34)),
            (box(0,0,8.1,5.5,5.5,2.5),WHITE)]
    for name,color in [("mx-neutral",KEY),("mx-agent",FROSTED)]:
        cap=box(0,0,9.2,17.9,17.9,5.3).edges("|Z").fillet(1.1).edges(">Z").chamfer(.6)
        save(name,switch+[(cap,color)])
    icons={"new-chat":[ink_line(-2,0,2,0),ink_line(0,-2,0,2)],
           "accept":[ink_line(-2.3,0,-.7,-1.4),ink_line(-.9,-1.55,2.3,1.6)],
           "decline":[ink_line(-1.65,-1.65,1.65,1.65),ink_line(-1.65,1.65,1.65,-1.65)],
           "interrupt":[box(0,0,14.5,2.9,2.9,.03)],
           "find":[cylinder(-.5,.5,14.5,1.45,.03).cut(cylinder(-.5,.5,14.49,.95,.05)),
                   ink_line(.4,-.4,2.2,-2.2)]}
    for name,solids in icons.items():
        save(f"mx-{name}",switch+[(cap,KEY)]+[(shape,BLACK) for shape in solids])
    save("mx-bare",switch)
    save("mx-ptt",switch+[(ptt_cap().translate((PTT_PITCH/2,0,9.2)),KEY),
                         (mic_symbol(14.17,.02).translate((PTT_PITCH/2,0,0)),BLACK)])
    zero=[(box(0,-11.75,2.5,18,23.5,1.1),PCB),
          (box(0,-2.4,3.6,8.9,7.5,3.25).edges("|Z").fillet(.45),STEEL),
          (box(0,-.8,4.17,7.3,4.9,1.35),BLACK),
          (box(0,-13,3.6,7,7,.9).rotate((0,-13,0),(0,-13,1),45),BLACK),
          (box(0,-22.3,3.6,7.8,1.9,1.3),(.73,.25,.20))]
    for x in [-7.62,7.62]:
        zero.append((box(x,-11.75,0,2.0,22.2,2.5),BLACK))
        for i in range(9):
            zero.append((box(x,-1.59-2.54*i,3.6,1.45,1.45,.32),GOLD))
    for x in [-4.6,4.6]:
        zero.append((box(x,-8.2,3.6,3.8,2.9,.9),STEEL))
        zero.append((cylinder(x,-8.2,4.5,.85,.5),BLACK))
    save("esp32-s3-zero",zero)
    save("ec11",[(box(0,0,0,11.7,12,4.5),BLACK),(box(0,0,4.5,11.7,12,2),STEEL),
                 (cylinder(0,0,6.5,3.45,4),STEEL),(cylinder(0,0,10.5,2.9,9.5),STEEL),
                 (cylinder(0,0,13.3,8.8,8.8).edges(">Z").chamfer(.7),STEEL)])
    save("skrh",[(box(0,0,0,7.35,7.5,1.8),STEEL),(cylinder(0,0,1.8,2.2,1.3),BLACK),
                 (box(0,0,2.9,2.0,2.0,2.1).rotate((0,0,0),(0,0,1),45),WHITE),
                 (cylinder(0,0,5,2.6,1.05),BLACK),(cylinder(0,0,6.05,6.4,2.1),(.31,.34,.37))])

if __name__=="__main__":
    main()
