"""Photo-based enclosure option for Rev A4. Uses the original PCB coordinates."""
from pathlib import Path
import argparse
import math
import cadquery as cq
import generate as a4

ROOT = Path(__file__).resolve().parents[1]
W, H, M = a4.W, a4.H, a4.M
CX, CY = W/2, H/2
SEAT_DEPTH, DISK_RADIUS, DISK_HEIGHT = .35, 38, 2.7
ENGRAVE = .65
FACE = 11.4
LOWER_MARGIN = 1.8  # Clear the bottom row at full travel with a printable rim.


def rounded(x, y, w, h, z, depth, r):
    return a4.block(x, y, w, h, z, depth).edges("|Z").fillet(r)


def frame_shape(inset, z, depth, bottom_inset=None):
    bottom_inset=inset if bottom_inset is None else bottom_inset
    return rounded(CX, CY+(LOWER_MARGIN+inset-bottom_inset)/2, W+2*M-2*inset,
                   H+2*M+LOWER_MARGIN-inset-bottom_inset, z, depth, 5-inset/2)


def lower_edge(z,height):
    return a4.block(CX,H+M+LOWER_MARGIN/2-.5,W+2*M,LOWER_MARGIN+1,z,height)


def tray():
    body=a4.base().union(lower_edge(0,9.9)).intersect(frame_shape(0,-.1,10.2))
    outline=frame_shape(2.9,-.1,.40).cut(frame_shape(3.55,-.15,.55))
    return body.cut(outline).cut(a4.cyl(CX,CY,DISK_RADIUS+.25,-.1,SEAT_DEPTH+.1))


def face():
    # Original 1.5 mm switch plate and microphone path are preserved. The outer
    # frame sits above the panel, away from the switches, to form a shallow well.
    plate=a4.panel().union(lower_edge(9.9,1.5)).intersect(frame_shape(0,6.2,5.3))
    lip=frame_shape(0,FACE-.1,1.0).edges(">Z").chamfer(.42)
    lip=lip.cut(frame_shape(2.65,FACE-.25,1.6,bottom_inset=2.05))
    # The raised rim breaks at the USB notch, including its removable cover.
    lip=lip.cut(a4.block(a4.MCU[0],-.9,22.2,5.2,FACE-.25,1.65))
    return plate.union(lip)


def stroke(x0,y0,x1,y1,width,z,height):
    # x/y are native CAD coordinates, not PCB coordinates.
    x,y=(x0+x1)/2,(y0+y1)/2
    a=a4.block(x,-y,math.hypot(x1-x0,y1-y0),width,z,height).rotate(
        (x,y,z),(x,y,z+1),math.degrees(math.atan2(y1-y0,x1-x0)))
    return a.union(a4.cyl(x0,-y0,width/2,z,height)).union(a4.cyl(x1,-y1,width/2,z,height))


def cloud(scale, z, height, wall):
    # Smooth six-lobed outline inferred from the photo, not a measured outline.
    def profile(offset):
        points=[]
        for i in range(72):
            angle=math.tau*i/72
            r=scale*(1+.095*math.cos(6*(angle-math.pi/2)))+offset
            points.append((r*math.cos(angle),r*math.sin(angle)))
        return cq.Workplane("XY",origin=(0,0,z)).spline(points,periodic=True).close().extrude(height)
    return profile(0).cut(profile(-wall))


def disk():
    # Inner flat face down on the print bed; decoration is cut into the visible face.
    outer=a4.cyl(0,0,DISK_RADIUS,0,DISK_HEIGHT).edges(">Z").chamfer(.48)
    center=outer.cut(a4.cyl(0,0,DISK_RADIUS-3.4,DISK_HEIGHT-.45,.7))
    top=DISK_HEIGHT-.45
    z=top-ENGRAVE
    mark=cloud(15.5,z,ENGRAVE+.2,1.7)
    mark=mark.union(stroke(-3,4,1,0,1.65,z,.85)).union(stroke(1,0,-3,-4,1.65,z,.85))
    mark=mark.union(stroke(4,-4,8,-4,1.65,z,.85))
    return center.cut(mark)


def fitted_disk():
    return disk().rotate((0,0,0),(1,0,0),180).translate((CX,-CY,SEAT_DEPTH))


def dish(w,h,z):
    return rounded(0,0,w-4.2,h-4.2,z-.43,1.0,2.5).edges("<Z").fillet(.48)


def icon(name,z,h):
    def lines(points):
        out=stroke(*points[0],*points[1],.46,z,h)
        for i in range(1,len(points)-1):
            out=out.union(stroke(*points[i],*points[i+1],.46,z,h))
        return out
    ring=a4.cyl(0,0,2.65,z,h).cut(a4.cyl(0,0,2.22,z-.1,h+.2))
    if name=="agent":
        return ring.union(lines([(-1.1,0),(1.1,0)])).union(lines([(0,-1.1),(0,1.1)]))
    if name=="new-chat":
        return lines([(1.3,2.3),(-1.9,-.3),(-.1,-.3),(-1.3,-2.3),(2,.4),(.2,.4),(1.3,2.3)])
    if name=="accept":
        return ring.union(lines([(-1.25,0),(-.35,-.85),(1.25,.95)]))
    if name=="decline":
        return ring.union(lines([(-.9,-.9),(.9,.9)])).union(lines([(-.9,.9),(.9,-.9)]))
    if name=="interrupt":
        return lines([(-1.8,-1.6),(.25,.45),(1.7,1.9),(.2,1.9)]).union(
            lines([(1.7,.4),(1.7,1.9)])).union(lines([(-1.85,.4),(-.7,1.55)]))
    if name=="find":
        return cloud(2.4,z,h,.40).union(lines([(-.85,-.6),(0,.2),(-.65,.85)])).union(
            lines([(.55,-.75),(1.25,-.75)]))
    if name=="ptt":
        return a4.mic_symbol(z,h)
    raise ValueError(name)


def cap(name):
    if name=="ptt":
        part=a4.ptt_cap().cut(dish(36.9,17.9,5.3))
    else:
        part=rounded(0,0,17.9,17.9,0,5.3,2.0).edges(">Z").chamfer(.72)
        part=part.cut(rounded(0,0,14.8,14.8,-.1,3.85,1.5)).union(a4.cyl(0,0,3.0,0,4.15))
        part=part.cut(a4.block(0,0,4.18,1.37,-.1,3.75).union(a4.block(0,0,1.37,4.18,-.1,3.75)))
        part=part.cut(dish(17.9,17.9,5.3))
    # Put the artwork below the dish floor so it shows even without a contrast fill.
    return part.cut(icon(name,4.62,.65))


def cover():
    shell=rounded(a4.MCU[0],10.7,22,23.4,FACE,2.8,1.15).edges(">Z").chamfer(.55)
    return shell.cut(a4.block(a4.MCU[0],10.7,19.6,24.2,FACE-.1,2.25))


def knob():
    shape=a4.cyl(0,0,8.8,0,9).edges("<Z").chamfer(.9)
    socket=a4.cyl(0,0,3.09,1.6,8).cut(a4.block(4.05,0,5,8,1.5,8.2))
    return shape.cut(socket)


NAMES=("agent","new-chat","accept","decline","interrupt","find","ptt")


def export(out):
    out.mkdir(parents=True,exist_ok=True)
    t,p,d,c=tray(),face(),disk(),cover()
    models={"base":t,"face":p.rotate((0,0,0),(1,0,0),180).translate((0,0,12.3)),
            "rear-disk":d,"usb-cover":c.rotate((0,0,0),(1,0,0),180).translate((-a4.MCU[0],-10.7,14.2)),
            "encoder-knob":knob()}
    models.update({f"key-{n}":cap(n) for n in NAMES})
    for n,shape in models.items():
        if len(shape.solids().vals())!=1 or not shape.val().isValid():
            raise ValueError(f"Expected one valid printable solid: {n}")
        cq.exporters.export(shape,str(out/f"{n}.stl"),tolerance=.025,angularTolerance=.12)
        cq.exporters.export(shape,str(out/f"{n}.step"))

    def step(name, parts):
        assembly=cq.Assembly(name=name)
        for n,shape,col in parts:
            assembly.add(shape,name=n,color=cq.Color(*col))
        assembly.export(str(out/f"{name}.step"))

    parts=[("base",t,(.65,.67,.68)),("face",p,(.91,.92,.91)),
           ("cover",c,(.89,.90,.89)),("back",fitted_disk(),(.81,.83,.85))]
    x,y=a4.TOUCH
    parts.append(("touch-mark",a4.cyl(x,y,3.4,FACE+.002,.028),(.29,.32,.34)))
    for i,(x,y) in enumerate(a4.MOUNT):
        parts.append((f"screw-{i+1}",a4.cyl(x,y,2.05,FACE,1.15).cut(
            a4.block(x,y,1.0,1.0,FACE+.85,.35)),(.14,.15,.17)))
    for i,(x,y) in enumerate(a4.LEDS):
        parts.append((f"diffuser-{i+1}",a4.block(x,y,3.9,2.25,9.85,1.55),(.84,.92,.98,.80)))
    step("enclosure",[(n,s.translate((0,0,-6.4)),col) for n,s,col in parts])

    switch=a4.block(0,0,14,14,0,8.1)
    for n in NAMES+("bare",):
        items=[("switch",switch,(.12,.13,.15))]
        if n!="bare":
            x=a4.PTT_PITCH/2 if n=="ptt" else 0
            items.append(("cap",cap(n).translate((x,0,9.2)),(.82,.89,.94,.84) if n=="agent" else (.93,.93,.91)))
            items.append(("ink",icon(n,13.823,.03).translate((x,0,0)),(.33,.43,.76) if n=="agent" else (.17,.19,.22)))
        step("preview-mx-"+n,items)
    step("preview-encoder",[("body",a4.block(0,0,11.7,12,0,6.5),(.35,.37,.39)),
         ("neck",a4.cyl(0,0,3.4,6.5,6.8),(.7,.72,.73)),
         ("knob",knob().rotate((0,0,0),(1,0,0),180).translate((0,0,22.3)),(.92,.92,.89))])


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=ROOT/"build"/"appearance")
    export(parser.parse_args().out.resolve())
