"""Generate print-ready STL and editable STEP. Requires CadQuery 2.8."""
from pathlib import Path
import sys
import cadquery as cq

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from design import W,H,MOUNT,KEYS,LEDS,TOUCH,JOY,ENC,MCU

OUT=Path(__file__).resolve().parent
M=2.4
MX_OPENING=14.20
MODULE_NOTCH_WIDTH=19.2
MODULE_NOTCH_END=24.4
JOYSTICK_STEM_HEIGHT=5.0
JOYSTICK_SOCKET_DEPTH=2.85

def block(x,y,dx,dy,z,height):
    return cq.Workplane('XY').box(dx,dy,height,centered=(True,True,False)).translate((x,-y,z))

def cyl(x,y,r,z,height):
    return cq.Workplane('XY').circle(r).extrude(height).translate((x,-y,z))

def outline(m,z,height):
    return block(W/2,H/2,W+2*m,H+2*m,z,height).edges('|Z').fillet(2)

def base():
    body=outline(M,0,9.9)
    body=body.cut(block(W/2,H/2,W+.7,H+.7,2,9))
    # USB plug access; the module's connector is above the bare carrier PCB.
    body=body.cut(block(MCU[0],-.9,13.4,4.5,5.8,5.2))
    # Lower the floor locally under the factory headers (3.45 mm below PCB).
    for x in [MCU[0]-7.62,MCU[0]+7.62]:
        body=body.cut(block(x,11.9,3.1,22.6,1.35,1.0))
    for x,y in MOUNT:
        body=body.union(cyl(x,y,2.85,1.9,2.9)).cut(cyl(x,y,.82,1.95,4))
    # Four low ridges support the PCB mid-span; keep clear of solder joints.
    for x,y in [(9,20),(86,20),(9,75),(86,75)]:
        body=body.union(block(x,y,4,3,1.9,2.9))
    return body

def panel():
    panel=outline(M,9.9,1.5)
    for x,y in KEYS:
        panel=panel.cut(block(x,y,MX_OPENING,MX_OPENING,9.7,2))
    for x,y in LEDS:
        panel=panel.cut(block(x,y,4.05,2.4,9.7,2))
    # Open module notch gives direct access to USB and the boot/reset buttons.
    y0=-2.9
    panel=panel.cut(block(MCU[0],(MODULE_NOTCH_END+y0)/2,MODULE_NOTCH_WIDTH,MODULE_NOTCH_END-y0,9.7,2))
    panel=panel.cut(block(*ENC,13.5,13.3,9.7,2))
    panel=panel.cut(cyl(*JOY,4.55,9.7,2))
    # Marks the touch target; foil adheres to the 1.15 mm membrane underneath.
    x,y=TOUCH
    ring=cyl(x,y,4.8,11.05,.5).cut(cyl(x,y,4.25,10.9,.9))
    panel=panel.cut(ring)
    for x,y in MOUNT:
        panel=panel.union(cyl(x,y,2.7,6.4,3.6)).cut(cyl(x,y,1.18,6.2,5.4))
    return panel

def dial():
    # Flat on a 6 mm shaft is nominally 4.5 mm from the opposite arc.
    # Print face down. Socket starts at the open end opposite the build plate.
    shell=cyl(0,0,8.8,0,9)
    for i in range(16):
        import math
        ang=i*math.tau/16
        shell=shell.cut(cyl(9*math.cos(ang),9*math.sin(ang),.65,-.1,9.2))
    socket=cyl(0,0,3.09,1.6,8).intersect(block(-1,0,7.25,8,1.5,8.2))
    # Limit the flat side to +1.55 mm relative to centre.
    socket=socket.cut(block(4.05,0,5,8,1.5,8.2))
    return shell.cut(socket)

def joy_cap():
    head=cyl(0,0,6.4,0,2.1).union(cyl(0,0,2.6,2,4.0))
    socket=block(0,0,2.08,2.08,6.0-JOYSTICK_SOCKET_DEPTH,3.1).rotate((0,0,0),(0,0,1),45)
    return head.cut(socket)

def light_pipes():
    arr=None  # One solid per insert, with spacing for a slicer.
    for i in range(6):
        insert=block(i*6,0,3.9,2.25,0,1.55)
        arr=insert if arr is None else arr.union(insert)
    return arr

def fit_coupon():
    # Left to right: 14.00, 14.20, 14.40; same print thickness and face orientation.
    coupon=block(20,0,60,21,0,1.5)
    for i,opening in enumerate((14.0,MX_OPENING,14.4)):
        coupon=coupon.cut(block(20*i,0,opening,opening,-.1,1.7))
        for j in range(i+1):
            coupon=coupon.cut(cyl(20*i+(j-i/2)*2,8.8,.55,-.1,1.7))
    return coupon

def main():
    tray,top=base(),panel()
    models={'base':tray,
            'plate':top.rotate((0,0,0),(1,0,0),180).translate((0,0,11.4)),
            'dial':dial(),'joystick-cap':joy_cap(),'light-pipes':light_pipes(),
            'mx-fit-coupon':fit_coupon()}
    for name,obj in models.items():
        if not obj.val().isValid(): raise ValueError(f'Invalid model: {name}')
        cq.exporters.export(obj,str(OUT/(name+'.stl')),tolerance=.03,angularTolerance=.1)
        cq.exporters.export(obj,str(OUT/(name+'.step')))
    assembly=cq.Assembly(name='GOWUJI Rev A2')
    assembly.add(tray,name='base')
    assembly.add(top,name='plate')
    assembly.add(block(W/2,H/2,W,H,4.8,1.6),name='pcb-envelope')
    assembly.export(str(OUT/'fit-reference.step'))

if __name__=='__main__':
    main()
