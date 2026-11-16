"""Generate editable KiCad 9 sources, project-local footprints, BOM and firmware pins."""
import argparse
import csv
import json
import uuid
from collections import Counter
from design import *

PCB = ROOT/'hardware'
LIB = PCB/'Gowuji.pretty'
STEM = PCB/'Gowuji-RevA'
NS = uuid.UUID('0528179e-dd14-4289-89fb-3eeb29ba075a')
def uid(s): return str(uuid.uuid5(NS,s))
def q(s): return json.dumps(str(s),ensure_ascii=False)
def f(x): return ('%.4f' % x).rstrip('0').rstrip('.') or '0'
def xy(x,y): return f'{f(x)} {f(y)}'
def u(s): return f'(uuid "{uid(s)}")'
def put(p,s): p.write_text(s,encoding='utf-8',newline='\n')

# Pad data in top view. THT origins match MX (turned to face south) and ALPS EC11E.
def th(n,x,y,drill,d=None,rect=False):
    return (n,x,y,d or drill,d or drill,drill,'rect' if rect else 'circle')
def sm(n,x,y,w,h): return (n,x,y,w,h,0,'rect')
def pair(pitch,w,h): return [sm(1,-pitch/2,0,w,h),sm(2,pitch/2,0,w,h)]
L=['5V','GND','3V3','1','2','3','4','5','6']
R=['43','44','13','12','11','10','9','8','7']
FP = {
    'Zero': (18,23.5,0,11.75,[th(n,x,1.59+i*2.54,1.05,1.8, n=='5V')
        for x,ns in [(-7.62,L),(7.62,R)] for i,n in enumerate(ns)]),
    'MX': (14,14,0,0,[th(1,-2.54,5.08,1.5,2.2),th(2,3.81,2.54,1.5,2.2),
        th('',0,0,4.1),th('',-5.08,0,1.75),th('',5.08,0,1.75)]),
    'EC11': (12,12,0,0,[th('A',-7.5,-2.5,1,1.9),th('B',-7.5,2.5,1,1.9),
        th('C',-7.5,0,1,1.9),th('S1',7,2.5,1,1.9),th('S2',7,-2.5,1,1.9),
        th('MP',0,-5.6,2.8,3.4),th('MP',0,5.6,2.8,3.4)]),
    'SKRH': (7.35,7.5,0,0,[sm(n,x,y,1.35,1)
        for x,ns in [(-3.575,[1,2,3]),(3.575,[4,5,6])] for y,n in zip([-1.425,0,1.425],ns)]
        +[sm('M1',0,-4.05,2,1.8),sm('M2',0,4.05,2,1.8)]),
    'SOD123': (2.7,1.65,0,0,pair(3.2,1.1,1.3)),
    'RGB3535': (3.5,3.5,0,0,[sm(n,x,y,1.8,1.0)
        for n,x,y in [(1,-1.565,-.89),(2,-1.565,.89),(3,1.565,.89),(4,1.565,-.89)]]),
    'SOT23_5': (2.9,1.6,0,0,[sm(n,x,y,0.64,1.0) for n,x,y in [
        (1,-.95,1.18),(2,0,1.18),(3,.95,1.18),(4,.95,-1.18),(5,-.95,-1.18)]]),
    'SOT23_6': (2.9,1.6,0,0,[sm(n,x,y,0.64,1.0) for n,x,y in [
        (1,-.95,1.18),(2,0,1.18),(3,.95,1.18),(4,.95,-1.18),(5,0,-1.18),(6,-.95,-1.18)]]),
    'R0603': (1.6,.8,0,0,pair(1.55,.9,.95)),
    'R1206': (3.2,1.6,0,0,pair(2.8,1.4,1.75)),
    'C0603': (1.6,.8,0,0,pair(1.55,.9,.95)),
    'C1206': (3.2,1.6,0,0,pair(2.8,1.4,1.75)),
    # ST DS12698 Rev 3, Fig. 12. PCB top view (port is north of centre).
    'MP34DT06J': (3,4,0,0,[sm(n,x,y,.4,.95) for n,x,y in
        [(1,.425,.675),(2,.425,-.675),(3,-.425,-.675),(4,-.425,.675)]]
        +[sm(5,x,0,.35,2.3) for x in (-1.225,1.225)]
        +[sm(5,0,y,1.3,.35) for y in (-1.725,1.725)]),
    'Wire': (2.2,2.2,0,0,[th(1,0,0,0.9,2.2)]),
    'Mount': (5.5,5.5,0,0,[th('',0,0,2.4)]),
}

MODEL_PATHS={
    'Zero':('local','esp32-s3-zero.step',0),
    'MX':('local','mx-neutral.step',0),
    'EC11':('local','ec11.step',0),
    'SKRH':('local','skrh.step',0),
    'SOD123':('stock','Diode_SMD.3dshapes/D_SOD-123.step',0),
    'RGB3535':('stock','LED_SMD.3dshapes/LED_WS2812B-Mini_PLCC4_3.5x3.5mm.step',0),
    'R0603':('stock','Resistor_SMD.3dshapes/R_0603_1608Metric.step',0),
    'C0603':('stock','Capacitor_SMD.3dshapes/C_0603_1608Metric.step',0),
    'C1206':('stock','Capacitor_SMD.3dshapes/C_1206_3216Metric.step',0),
    'SOT23_5':('stock','Package_TO_SOT_SMD.3dshapes/SOT-23-5.step',-90),
    'SOT23_6':('stock','Package_TO_SOT_SMD.3dshapes/SOT-23-6.step',-90),
    'MP34DT06J':('local','mp34dt06j.step',0),
}

def pad(p, tag, nets=None):
    n,x,y,w,h,d,shape=p
    typ='smd' if not d else 'thru_hole' if n!='' else 'np_thru_hole'
    drill=f'(drill {f(d)})' if d else ''
    layers='"*.Cu" "*.Mask"' if d else '"F.Cu" "F.Paste" "F.Mask"'
    net=nets.get(str(n)) if nets else None
    netdef=f'(net {NETS[net]} {q(net)})' if net else ''
    return (f'(pad {q(n)} {typ} {shape} (at {xy(x,y)}) (size {xy(w,h)}) {drill} '
            f'(layers {layers}) {netdef} {u(tag+"/pad/"+str(p))})')

def footprint(kind, part=None):
    w,h,x,y,ps=FP[kind]
    tag=(part.ref if part else 'lib')+'/'+kind
    name='Gowuji:'+kind if part else kind
    ref,val=(part.ref,part.val) if part else ('REF**',kind)
    at=f'(at {xy(*part.xy)}) (path "/{uid("schematic")}/{uid(part.ref)}")' if part else ''
    attr='through_hole' if any(p[5] for p in ps) else 'smd'
    if kind=='Mount': attr='board_only exclude_from_pos_files exclude_from_bom'
    rpos=(0,24.75) if kind=='Zero' else (0,6.1) if kind=='SKRH' else (0,-8.1) if kind in ('MX','EC11') else (0,-h/2-1.45)
    hidden=kind in ('R0603','C0603','C1206','SOD123','RGB3535','MX','Mount')
    # Courtyard encloses all pads; closely spaced parts can share physical edge clearance.
    x0=min([x-w/2]+[p[1]-p[3]/2 for p in ps])-.1
    x1=max([x+w/2]+[p[1]+p[3]/2 for p in ps])+.1
    y0=min([y-h/2]+[p[2]-p[4]/2 for p in ps])-.1
    y1=max([y+h/2]+[p[2]+p[4]/2 for p in ps])+.1
    drawings=[f'(fp_rect (start {xy(x-w/2,y-h/2)}) (end {xy(x+w/2,y+h/2)}) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
              f'(fp_rect (start {xy(x0,y0)}) (end {xy(x1,y1)}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))']
    mark={'SOD123':(-2.05,-.98), 'RGB3535':(1.6,1.9), 'Zero':(-8.55,-.1),
          'SOT23_5':(-2.04,1.8), 'SOT23_6':(-2.04,1.8), 'SKRH':(-5.4,-1.38),
          'MP34DT06J':(.93,2.25)}.get(kind)
    if mark:
        drawings.append(f'(fp_line (start {xy(*mark)}) (end {xy(mark[0]+.55,mark[1])}) (stroke (width 0.15) (type default)) (layer "F.SilkS"))')
    props=[
        f'(property "Reference" {q(ref)} (at {xy(*rpos)} 0) (layer "F.SilkS") {"(hide yes)" if hidden else ""} (effects (font (size 0.8 0.8) (thickness 0.12))))',
        f'(property "Value" {q(val)} (at 0 0 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))']
    model=[]
    if kind in MODEL_PATHS:
        where,path,angle=MODEL_PATHS[kind]
        if kind=='MX' and part:
            path={'PTT':'mx-ptt.step','PTT_B':'mx-bare.step'}.get(part.val,
                'mx-agent.step' if part.val.startswith('SLOT') else
                f'mx-{part.val.lower().replace("_","-")}.step')
        prefix='${KIPRJMOD}/models/' if where=='local' else '${KICAD9_3DMODEL_DIR}/'
        model=[f'(model {q(prefix+path)} (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 {angle})))']
    return (f'(footprint {q(name)} '+('' if part else '(version 20241229) (generator "pcbnew") ')+
            f'(layer "F.Cu") {u(tag)} {at} (attr {attr})\n'+'\n'.join(
        props+drawings+[pad(p,tag,board_nets(part) if part else None) for p in ps]+model)+')')
def board(revision='A4',legacy_antenna=True):
    for kind in FP: put(LIB/(kind+'.kicad_mod'),footprint(kind)+'\n')
    put(PCB/'fp-lib-table','(fp_lib_table (version 7) (lib (name "Gowuji") (type "KiCad") (uri "${KIPRJMOD}/Gowuji.pretty") (options "") (descr "GOWUJI Rev A")))\n')
    nets='\n'.join(f'(net {i} {q(n)})' for n,i in NETS.items())
    shapes=[f'(gr_rect (start 0 0) (end {W} {H}) (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts") {u("edge")})']
    for i,(x,y) in enumerate(KEYS):
        shapes.append(f'(gr_text "{NAMES[i]}" (at {xy(x,y-5.3)}) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .13))))')
    markings=[(f'GOWUJI / REV {revision}',19,4.2),('TOUCH FOIL',18.4,96)]
    if legacy_antenna: markings.append(('USB / BOOT',72,4.2))
    for name,x,y in markings:
        shapes.append(f'(gr_text "{name}" (at {xy(x,y)}) (layer "F.SilkS") (effects (font (size 1 1) (thickness .15))))')
    if legacy_antenna: shapes.append(f'''(zone (net 0) (net_name "") (layers "F.Cu" "B.Cu") (name "Module antenna")
    (hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness .25)
    (keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) (footprints allowed))
    (fill (thermal_gap 0.3) (thermal_bridge_width 0.3))
    (polygon (pts (xy {f(MCU[0]-5)} 20) (xy {f(MCU[0]+5)} 20) (xy {f(MCU[0]+5)} 27) (xy {f(MCU[0]-5)} 27))))''')
    return f'''(kicad_pcb (version 20241229) (generator "pcbnew")
 (general (thickness 1.6)) (paper "A4")
 (title_block (title "GOWUJI Macro Pad") (rev "{revision}"))
 (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (32 "B.Adhes" user) (33 "F.Adhes" user)
  (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user) (37 "F.SilkS" user)
  (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user) (41 "Cmts.User" user)
  (44 "Edge.Cuts" user) (45 "Margin" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user)
  (48 "B.Fab" user) (49 "F.Fab" user))
 (setup (pad_to_mask_clearance 0))
 {nets}
 {chr(10).join(footprint(p.kind,p) for p in parts)}
 {chr(10).join(shapes)}
)
'''

def effect(size=1.27,just='',hide=False):
    return f'(effects (font (size {size} {size})) {f"(justify {just})" if just else ""} {"(hide yes)" if hide else ""})'
def pins(kind):
    nums=list(dict.fromkeys(str(p[0]) for p in FP[kind][4] if p[0]!=''))
    names={'SOD123':['K','A'],'RGB3535':['VDD','DOUT','GND','DIN'],
           'SOT23_5':['OE','A','GND','Y','VCC'],'SOT23_6':['VIN','GND','ON','CT','QOD','VOUT'],
           'SKRH':['A','CENTER','C','B','COM','D','TAB1','TAB2'],
           'MP34DT06J':['VDD','L/R','CLK','DOUT','GND']}
    groups=[nums[:(len(nums)+1)//2],nums[(len(nums)+1)//2:]]
    if kind=='Zero': groups=[L,R]
    if kind in ('MX','R0603','R1206','C0603','C1206','SOD123','Wire'): groups=[nums[:1],nums[1:]]
    width=5.08 if kind in ('Zero','EC11','RGB3535','SOT23_5','SOT23_6','SKRH','MP34DT06J') else 2.54
    out=[]
    for side, group in zip([-1,1],groups):
        for i,num in enumerate(group):
            name=names.get(kind,nums)[nums.index(num)]
            if kind=='Zero' and num not in ('GND','5V','3V3'): name='IO'+num
            ptype='passive'
            out.append((num,name,side*(width+2.54), ((len(group)-1)/2-i)*2.54, 0 if side==-1 else 180,ptype))
    return out,width,max(len(g) for g in groups)*1.27+1.27

def board_nets(part):
    if part.kind=='Mount':
        return {}
    out={}
    for num,name,*_ in pins(part.kind)[0]:
        net=part.nets.get(num)
        if net:
            out[num]='/'+net
        else:
            prefix=part.ref if num==name else part.ref+'-'+name
            out[num]=f'unconnected-({prefix}-Pad{num})'
    return out

NETS={n:i for i,n in enumerate(sorted({n for p in parts for n in board_nets(p).values()}),1)}

def sym(kind,identifier):
    ps,w,h=pins(kind)
    libpins=' '.join(f'(pin {typ} line (at {xy(x,y)} {rot}) (length 2.54) (name {q(name)} {effect(1.0)}) (number {q(num)} {effect(1.0)}))'
                     for num,name,x,y,rot,typ in ps)
    hidepins='(pin_numbers hide) (pin_names (offset 0) hide)' if w==2.54 else '(pin_names (offset 0.5))'
    def line(*points):
        return '(polyline (pts '+' '.join(f'(xy {xy(*v)})' for v in points)+') (stroke (width .254) (type default)) (fill (type none)))'
    if kind=='MX':
        body=line((-w,0),(-1.4,0),(1.3,1.4))+line((1.4,0),(w,0))
    elif kind=='SOD123':
        body=line((-w,0),(w,0))+line((-1.2,-1.45),(-1.2,1.45))+line((-1.2,0),(1.2,1.45),(1.2,-1.45),(-1.2,0))
    elif kind in ('C0603','C1206'):
        body=line((-w,0),(-.65,0))+line((.65,0),(w,0))+line((-.65,-1.5),(-.65,1.5))+line((.65,-1.5),(.65,1.5))
    elif kind in ('R0603','R1206'):
        body=f'(rectangle (start {-w} 1) (end {w} -1) (stroke (width .254) (type default)) (fill (type none)))'
    else:
        body=f'(rectangle (start {-w} {h}) (end {w} {-h}) (stroke (width .254) (type default)) (fill (type background)))'
    return f'''(symbol {q(identifier)} {hidepins} (in_bom yes) (on_board yes)
 (property "Reference" "X" (at 0 {h+2.54} 0) {effect()})
 (property "Value" {q(kind)} (at 0 {-h-2.54} 0) {effect()})
 (symbol "{kind}_0_1" {body})
 (symbol "{kind}_1_1" {libpins}))'''

def schematic(revision='A4',project='Gowuji-RevA',extra_locations=None,footprints=None):
    sch_id=uid('schematic')
    used=sorted({p.kind for p in parts if p.kind!='Mount'})
    put(PCB/'Gowuji.kicad_sym','(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(sym(k,k) for k in used)+')\n')
    put(PCB/'sym-lib-table','(sym_lib_table (version 7) (lib (name "Gowuji") (type "KiCad") (uri "${KIPRJMOD}/Gowuji.kicad_sym") (options "") (descr "GOWUJI Rev A")))\n')
    objs=[]
    def note(s,x,y,size=2):
        objs.append(f'(text {q(s)} (at {xy(x,y)} 0) {effect(size,"left")} {u("text/"+s)})')
    note('01  USB-C controller and touch',22.86,25.4)
    note('02  Six addressable indicators',22.86,116.84)
    note('05  LED rail soft start',172.72,217.17)
    note('03  Mechanical keys and diode matrix',172.72,25.4)
    note('04  Encoder / 5-way navigation',172.72,142.24)
    note('Rows active low; R3–R7 pull columns up to V3V3. Only one row drives at a time.',172.72,195.58,1.524)
    if revision=='A4':
        note('U1 supplies VBUS from USB-C only. No on-board battery charger.',22.86,104.14,1.524)
    else:
        note('USB-C, input protection, 3.3 V power and internal boot test pads',22.86,302.26)
        note('07  ESP32-S3FH4R2 crystal, RF feed and bypass',400.05,145.0)
    note('SW15 shares ROW3; direction diodes face the opposite way from SW1–SW14 on PCB.',172.72,200.66,1.524)
    note(f"PCB outline 95 x 98 mm / {2 if revision=='A4' else 4} layers / 1.6 mm. H1–H4 are PCB-only.",22.86,247.65,1.524)
    note('06  Board microphone / 2.048 MHz PDM',22.86,259.08)
    loc={'U1':(60.96,57.15), 'R2':(60.96,86.36), 'J1':(104.14,86.36),
         'U2':(50.8,137.16),'R1':(109.22,137.16),'SW14':(205.74,165.1),
         'D14':(248.92,165.1),'SW15':(289.56,165.1),'C7':(48.26,226.06),'C8':(104.14,226.06),
         'U3':(205.74,240.03),'C9':(254,233.68),'C10':(254,247.65),
         'U4':(50.8,273.05),'C11':(100.33,273.05),'C12':(137.16,273.05),
         'R8':(191.77,273.05),'R9':(269.24,273.05)}
    for i in range(13):
        x=186.69+((i%4)*53.34)
        y=43.18+(i//4)*25.4
        loc[f'SW{i+1}']=(x,y)
        loc[f'D{i+1}']=(x+25.4,y)
    for i in range(6):
        x=48.26+(i%3)*45.72
        y=161.29+(i//3)*31.75
        loc[f'LED{i+1}']=(x,y)
        loc[f'C{i+1}']=(x,y+12.7)
    for i in range(5):
        loc[f'D{i+15}']=(327.66+(i%2)*38.1,151.13+(i//2)*13.97)
        loc[f'R{i+3}']=(309.88+(i%3)*36.83,226.06+(i//3)*15.24)
    loc.update(extra_locations or {})
    footprints=footprints or {}
    for p in parts:
        if p.kind=='Mount': continue
        x,y=loc[p.ref]
        ps,w,h=pins(p.kind)
        small=w==2.54
        h=1.27 if small else h
        # KiCad coordinates: local positive Y in symbols points up.
        def prop(key,val,py,hide=False):
            return f'(property {q(key)} {q(val)} (at {xy(x,py)} 0) {effect(1.1,hide=hide)})'
        props=' '.join([prop('Reference',p.ref,y-h-1.27),prop('Value',p.val,y+h+1.27),
                        prop('Footprint',footprints.get(p.kind,'Gowuji:'+p.kind),y,True),prop('Datasheet','',y,True)])
        for num,name,px,py,rot,typ in ps:
            a,b=x+px,y-py
            net=p.nets.get(num)
            key=p.ref+'/'+num
            if not net:
                objs.append(f'(no_connect (at {xy(a,b)}) {u("nc/"+key)})')
                continue
            c=a+(-1 if px<0 else 1)*3.81
            # Anchor label at the outer end; label text extends away from symbol.
            objs.append(f'(wire (pts (xy {xy(a,b)}) (xy {xy(c,b)})) (stroke (width 0) (type default)) {u("wire/"+key)})')
            objs.append(f'(label {q(net)} (at {xy(c,b)} {180 if px<0 else 0}) {effect(1.0,"left bottom")} {u("label/"+key)})')
        objs.append(f'''(symbol (lib_id "Gowuji:{p.kind}") (at {xy(x,y)} 0) (unit 1)
 (in_bom yes) (on_board yes) (dnp {'yes' if p.val.startswith('DNP ') else 'no'}) {u(p.ref)} {props}
 {" ".join(f'(pin {q(n)} {u("pin/"+p.ref+"/"+n)})' for n,*_ in ps)}
 (instances (project "{project}" (path "/{sch_id}" (reference {q(p.ref)}) (unit 1)))))''')
    return f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid "{sch_id}")
 (paper "{'A3' if revision=='A4' else 'A2'}") (title_block (title "GOWUJI Macro Pad") (rev "{revision}"))
 (lib_symbols {" ".join(sym(k,"Gowuji:"+k) for k in used)})
 {chr(10).join(objs)}
 (sheet_instances (path "/" (page "1")))
)
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unrouted',type=Path,help='Optional output path for a new unrouted PCB. Use a separate path.')
    args=parser.parse_args()
    LIB.mkdir(exist_ok=True,parents=True)
    pcb=board()
    if args.unrouted:
        if args.unrouted.resolve()==STEM.with_suffix('.kicad_pcb').resolve():
            parser.error('refusing to overwrite the routed board')
        args.unrouted.parent.mkdir(exist_ok=True,parents=True)
        put(args.unrouted,pcb)
    put(STEM.with_suffix('.kicad_sch'),schematic())
    put(STEM.with_suffix('.kicad_pro'),json.dumps({
        "meta":{"filename":"Gowuji-RevA.kicad_pro","version":1},
        "net_settings":{"classes":[{"name":"Default","clearance":.2,"track_width":.3,"via_diameter":.65,
                                    "via_drill":.3,"microvia_diameter":.3,"microvia_drill":.1,
                                    "diff_pair_width":.2,"diff_pair_gap":.25,"diff_pair_via_gap":.25,
                                    "pcb_color":"rgba(0, 0, 0, 0.000)","schematic_color":"rgba(0, 0, 0, 0.000)",
                                    "wire_width":6,"bus_width":12,"line_style":0}],"meta":{"version":4}}
    },indent=2)+'\n')
    with (PCB/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as fh:
        out=csv.writer(fh)
        out.writerow(['Refs','Qty','Part','Notes','Unit CNY low','Unit CNY high','Subtotal low','Subtotal high'])
        for r,n,p,d,a,b in BOM: out.writerow([r,n,p,d,a,b,round(n*a,2),round(n*b,2)])
        out.writerow(['TOTAL', '', 'Planning estimate', 'Excludes labor, shipping and PCBA', '', '',
                      round(sum(n*a for _,n,_,_,a,_ in BOM),2),round(sum(n*b for _,n,_,_,_,b in BOM),2)])
    dst=ROOT/'firmware'/'Gowuji'/'pins.h'
    dst.parent.mkdir(exist_ok=True,parents=True)
    def vals(seq): return '{'+','.join(map(str,seq))+'}'
    put(dst,f'''// Generated by tools/hardware.py from tools/design.py.
#pragma once
#include <stdint.h>
constexpr uint8_t ROWS[] = {vals(ROWS)}, COLS[] = {vals(COLS)};
constexpr uint8_t ENC_A = {ENC_PINS[0]}, ENC_B = {ENC_PINS[1]}, TOUCH_PIN = {TOUCH_PIN}, RGB_PIN = {LED_PIN};
constexpr uint8_t MIC_CLK_PIN = {MIC_CLK}, MIC_DATA_PIN = {MIC_DATA};
constexpr int8_t MATRIX[4][5] = {vals([vals(r) for r in MATRIX])};
constexpr const char *KEY_NAMES[] = {vals([q(n) for n in NAMES])};
constexpr uint8_t LED_COUNT = {len(LEDS)};
constexpr uint8_t PTT_PRIMARY = {PTT_PRIMARY}, PTT_SECONDARY = {PTT_SECONDARY};
''')

if __name__=='__main__':
    main()
