"""Sweep board-level models and write reproducible data. Requires NumPy and ngspice shared library."""
import argparse
from collections import Counter
import ctypes as c
import itertools
import json
import os
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

import numpy as np
from design import (ROOT, MATRIX, KEYS, KEY_GRID, LED_KEYS, LEDS, MOUNT, MCU, W, H,
                    ENC, JOY, TOUCH, XS, YS, PTT_PRIMARY, PTT_SECONDARY,
                    MIC, MIC_PORT, MIC_BORE, MIC_BOSS_Z)

CURRENT = "A4"


class Vector(c.Structure):
    _fields_ = [("name",c.c_char_p),("type",c.c_int),("flags",c.c_short),
                ("data",c.POINTER(c.c_double)),("complex",c.c_void_p),("length",c.c_int)]


class Spice:
    """Thin wrapper around the KiCad-bundled ngspice API."""
    def __init__(self,path):
        path=path.resolve()
        self.dll_dir=os.add_dll_directory(str(path.parent)) if os.name=="nt" else None
        self.dll=c.CDLL(str(path))
        cb=c.CFUNCTYPE(c.c_int,c.c_char_p,c.c_int,c.c_void_p)
        self.log=[]
        self.text=cb(lambda s,*_: self.log.append(s.decode("utf-8","replace")) or 0)
        self.dll.ngSpice_Init.argtypes=[cb,cb,*([c.c_void_p]*5)]
        self.dll.ngSpice_Init(self.text,self.text,None,None,None,None,None)
        self.dll.ngSpice_Circ.argtypes=[c.POINTER(c.c_char_p)]
        self.dll.ngSpice_Command.argtypes=[c.c_char_p]
        self.dll.ngGet_Vec_Info.argtypes=[c.c_char_p]
        self.dll.ngGet_Vec_Info.restype=c.POINTER(Vector)

    def run(self,deck,*names):
        self.log.clear()
        lines=[line.encode("ascii") for line in deck.strip().splitlines()]
        buf=(c.c_char_p*(len(lines)+1))(*lines,None)
        if self.dll.ngSpice_Circ(buf) or self.dll.ngSpice_Command(b"run"):
            raise RuntimeError("\n".join(self.log))
        out=[]
        for name in names:
            ptr=self.dll.ngGet_Vec_Info(name.encode("ascii"))
            if not ptr or not ptr.contents.data or not ptr.contents.length:
                raise RuntimeError(f"Missing {name}: "+"\n".join(self.log))
            out.append(np.ctypeslib.as_array(ptr.contents.data,shape=(ptr.contents.length,)).copy())
        self.dll.ngSpice_Command(b"destroy all")
        return out


def sweep_power(sp, out, pcb_loop):
    results=[]
    representative={}
    # Nominal 12.3 uF includes the Waveshare C1/C8/C9. Effective values vary with DC bias.
    # LEDs: 6 * 3 * 12 mA, tested as coincident pulses plus 6 mA static.
    corners=list(itertools.product((4.75,5.25),(.22,.55),(.5,1.5),(6,13),(18,55),(7,19),(.222,.276)))
    corners.insert(0,(5.0,.35,.9,9,32,12,.222))
    for i,(v,r,l,cm,cl,slew,pulse) in enumerate(corners):
        for rev in ("A1",CURRENT):
            if rev==CURRENT:
                supply=f"""Vtarget target 0 PWL(0 0 2m 0 {2+slew}m {v})
Bswitch bus led I=max(0,(min(v(bus),v(target))-v(led))/0.09)
Rbleed led 0 100k
Cinput bus 0 1u"""
            else:
                supply="Rdirect bus led 0.01"
            # Allow 2 mA equivalent VBUS demand for the 3.3 V mic during capture;
            # approximate 1.1 uF on the module regulator as an extra input load.
            mic = "CmicBudget bus 0 1.1u\nImicBudget bus 0 PWL(0 0 44m 0 44.4m 0.002)" if rev==CURRENT else ""
            deck=f"""GOWUJI {rev} USB hot-plug and LED load step
Vhost host 0 PWL(0 0 20u {v})
Rcable host inductor {r}
Lcable inductor bus {l}u
Cmodule bus 0 {cm}u
{supply}
{mic}
Rledlayout led last {pcb_loop}
Cled led 0 {cl}u
Imcu bus 0 PWL(0 0 0.35m 0 0.8m 0.035 44m 0.035 44.4m 0.14)
Iled last 0 PULSE(0 {pulse} 45m 2u 2u 0.25m 1.5m)
.tran 2u 53m 0 2u
.end"""
            t,bus,led,current=sp.run(deck,"time","v(bus)","v(last)","vhost#branch")
            current=-current
            start=t<=.0015
            active=t>=.045
            idle=(t>=.002)&(t<=.022)
            result=dict(revision=rev,corner=i,host_V=v,cable_ohm=r,cable_uH=l,module_uF=cm,
                        led_uF=cl,rise_ms=slew,led_pulse_A=pulse,copper_loop_ohm=pcb_loop,
                        attach_charge_uC=float(np.trapezoid(np.maximum(current[start]-np.interp(
                            t[start],[0,.00035,.0008,.0015],[0,0,.035,.035]),0),t[start])*1e6),
                        attach_peak_A=float(current[start].max()),
                        late_start_peak_mA=float(current[idle].max()*1000),
                        active_peak_mA=float(current[active].max()*1000),
                        led_min_V=float(led[active].min()), vbus_max_V=float(bus.max()))
            results.append(result)
            if i==0:
                representative[rev]=(t,led,current)
                (out/f"power-{rev}.cir").write_text(deck+"\n",encoding="ascii")
    a1=[r for r in results if r["revision"]=="A1"]
    revised=[r for r in results if r["revision"]==CURRENT]
    assert all(a["attach_charge_uC"]>b["attach_charge_uC"] for a,b in zip(a1,revised))
    assert min(r["led_min_V"] for r in revised)>4.25
    assert max(r["active_peak_mA"] for r in revised)<500
    assert max(r["late_start_peak_mA"] for r in revised)<100
    return results,representative


def sweep_logic(sp,out):
    result=[]
    # The old case stresses uncertain internal pull-ups (25–75 kΩ).
    # New hardware uses external ±1% resistors. Open input uses a 10 uA
    # leakage sink as a guardband, not a full network temperature model.
    for rev,vals in (("A1", (25e3,75e3)),(CURRENT,(21.78e3,22.22e3))):
        for v,r,cap,leak,temp in itertools.product((3.0,3.6),vals,(30,200),(0,10e-6),(-10,60)):
            model="D(IS=2n N=1.75 RS=1.2 EG=1.11)" if rev=="A1" else "D(IS=8n N=1 RS=4 EG=0.69 XTI=2)"
            wait=12 if rev=="A1" else 25
            deck=f"""GOWUJI {rev} five simultaneous keys and inter-row release
V3 v3 0 {v}
Rcol v3 col {r}
Rfour v3 group {r/4}
Dother group row DM
Rrow row 0 60
Db col sw DM
Skey sw row ctl 0 SW1
Vctl ctl 0 PULSE(1 0 20u 0.05u 0.05u 70u 150u)
Ileak col 0 {leak}
Ccol col 0 {cap}p
.model DM {model}
.model SW1 SW(Ron=5 Roff=1e11 Vt=.5 Vh=.1)
.temp {temp}
.tran 0.05u 60u
.end"""
            t,col=sp.run(deck,"time","v(col)")
            low=float(np.interp(10e-6,t,col))
            high=float(np.interp((20+wait)*1e-6,t,col))
            result.append(dict(revision=rev,VDD=v,Rpull_ohm=r,Ccolumn_pF=cap,leak_A=leak,temp_C=temp,
                               low_V=low,high_V=high,low_margin_V=.25*v-low,high_margin_V=high-.75*v))
            if rev==CURRENT and (v,r,cap,leak,temp)==(3.0,22.22e3,200,10e-6,-10):
                (out/f"matrix-{CURRENT}-corner.cir").write_text(deck+"\n",encoding="ascii")
    revised=[r for r in result if r["revision"]==CURRENT]
    assert min(r["low_margin_V"] for r in revised)>.15
    assert min(r["high_margin_V"] for r in revised)>.2
    return result


def read_nets(xml):
    nets={}
    for net in ET.parse(xml).findall("./nets/net"):
        for n in net.findall("node"):
            nets[n.get("ref"),n.get("pin")]=net.get("name").lstrip("/")
    return nets


def mic_topology(nets):
    expected = {
        "U4": ("V3V3","GND","PDM_CLK","PDM_DATA","GND"),
        "R8": ("PDM_CLK","PDM_CLK_MCU"), "R9": ("PDM_DATA_MCU","PDM_DATA"),
        "C11": ("V3V3","GND"), "C12": ("V3V3","GND"),
    }
    for ref, pins in expected.items():
        for i, name in enumerate(pins,1):
            assert nets[ref,str(i)] == name, (ref,i)
    assert nets["U1","3"] == "PDM_CLK_MCU" and nets["U1","43"] == "PDM_DATA_MCU"
    return dict(expected, module_clock_gpio=3, module_data_gpio=43)


def matrix_topology(nets):
    # Derive edges from exported schematic connectivity, not from the ideal key map.
    def pair(ref,a,b): return nets[ref,a],nets[ref,b]
    diodes=[pair(f"D{i+1}","2","1") for i in range(19)]
    contacts=[pair(f"SW{i+1}","1","2") for i in range(13)]+[pair("SW14","S1","S2")]
    contacts += [pair("SW15",j,"5") for j in ("1","4","6","3","2")]
    index={net:i for i,net in enumerate(sorted({n for edge in diodes+contacts for n in edge}))}
    closed=np.arange(1<<19,dtype=np.uint32)
    on=[(closed & (1<<i))!=0 for i in range(19)]
    steps=[]
    for row,keys in enumerate(MATRIX):
        can=np.zeros((len(index),len(closed)),dtype=bool)
        can[index[f"ROW{row}"]]=True
        links=[(index[a],index[b],None) for a,b in diodes]
        links += [(index[a],index[b],on[i]) for i,(l,r) in enumerate(contacts) for a,b in ((l,r),(r,l))]
        for step in range(len(index)):
            prev=can.copy()
            for a,b,state in links:
                can[a] |= can[b] if state is None else (can[b]&state)
            if np.array_equal(prev,can): break
        else: raise AssertionError("matrix reachability failed to converge")
        for col,key in enumerate(keys):
            assert np.array_equal(can[index[f"COL{col}"]],on[key] if key>=0 else np.zeros_like(on[0])),(row,col)
        steps.append(step+1)
    return dict(key_states=len(closed),row_scans=4*len(closed),iterations_by_row=steps)


def mechanical_geometry():
    sys.path.insert(0,str(ROOT/"mechanical"))
    import generate as geom
    tray,plate=geom.base(),geom.panel()
    assert {KEY_GRID[i] for i in LED_KEYS} == {(1,0),(2,0),(0,1),(1,1),(2,1),(3,1)}
    assert ENC == (XS[0],YS[0]) and JOY == (XS[3],YS[0]) and TOUCH == (XS[0],YS[3])
    assert KEY_GRID[PTT_PRIMARY] == (1,3) and KEY_GRID[PTT_SECONDARY] == (2,3)
    pcb=geom.block(W/2,H/2,W,H,4.8,1.6)
    assert tray.intersect(pcb).solids().size()==0
    assert plate.intersect(pcb).solids().size()==0
    module=geom.block(MCU[0],MCU[1]+11.75,18.3,23.8,8.4,4.5)
    assert plate.intersect(module).solids().size()==0
    assert tray.intersect(module).solids().size()==0
    mic=geom.block(*MIC,3.1,4.1,6.4,1.12)
    assert plate.intersect(mic).solids().size()==0
    assert plate.intersect(geom.cyl(*MIC_PORT,MIC_BORE/2-.01,7.6,4)).solids().size()==0
    mic_gap=MIC_BOSS_Z-6.4-1.0
    assert .45 <= mic_gap <= .7
    for x,y in KEYS:
        pin_body=geom.block(x,y,13.8,13.8,9.88,1.55)
        assert plate.intersect(pin_body).solids().size()==0
    for x,y in MOUNT:
        screw=geom.cyl(x,y,1.05,4.9,6.48)
        assert plate.intersect(screw).solids().size()==0
    web=YS[0]-geom.MX_OPENING/2-geom.MODULE_NOTCH_END
    # Two independently printed edges can each shift by 0.20 mm.
    assert web-.40>=1.2
    sleeve=geom.block(MCU[0],-2.25,12.5,6,6.55,6.6)
    assert tray.intersect(sleeve).solids().size()==0
    assert plate.intersect(sleeve).solids().size()==0
    cover=geom.usb_cover()
    assert cover.intersect(sleeve).solids().size()==0 and cover.intersect(module).solids().size()==0
    cover_key_gap=YS[0]-17.9/2-(10.7+23.4/2)
    assert cover_key_gap>=1.2
    # PCB underside 4.8; factory pin tail must be trimmed to 3.0 mm max.
    clearance=4.8-1.35-3.0
    enc_clear=min(ENC[1],H-ENC[1])-5.6-3.4/2
    assert clearance>=.4 and enc_clear>=1.0
    window_web=min(KEYS[i][1]-y for i,(_,y) in zip(LED_KEYS,LEDS))-geom.MX_OPENING/2-2.4/2
    assert window_web>.8
    x,y=KEYS[PTT_PRIMARY]
    ptt_full_travel=geom.ptt_cap().translate((x+geom.PTT_PITCH/2,-y,15.6-4.0))
    assert ptt_full_travel.intersect(plate).solids().size()==0
    ptt_side_gap=1.5*geom.PTT_PITCH-36.9/2-17.9/2
    assert ptt_side_gap>=1.0
    meshes={}
    for name in ("base","plate","dial","joystick-cap","light-pipes","mx-fit-coupon","ptt-keycap-2u","usb-cover"):
        blob=(ROOT/"mechanical"/f"{name}.stl").read_bytes()
        triangles=struct.unpack_from("<I",blob,80)[0]
        assert len(blob)==84+50*triangles
        edges=Counter()
        for i in range(triangles):
            flat=struct.unpack_from("<9f",blob,96+50*i)
            pts=[tuple(round(x,4) for x in flat[j:j+3]) for j in (0,3,6)]
            edges.update(tuple(sorted((a,b))) for a,b in zip(pts,pts[1:]+pts[:1]))
        assert set(edges.values())=={2},name
        meshes[name]=triangles
    return dict(nominal_usb_web_mm=web,usb_web_after_0p2mm_per_edge_mm=web-.4,
                microphone_bore_mm=MIC_BORE,microphone_nominal_gasket_gap_mm=round(mic_gap,2),
                led_window_web_mm=window_web,ptt_adjacent_cap_gap_mm=ptt_side_gap,
                usb_cover_to_keycap_gap_mm=cover_key_gap,
                min_header_tail_clearance_mm=clearance,
                encoder_pad_to_board_edge_mm=enc_clear,checked_key_openings=len(KEYS),closed_stl_triangles=meshes)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ngspice",type=Path,required=True)
    p.add_argument("--netlist",type=Path,required=True,help="KiCad schematic export, format kicadxml")
    p.add_argument("--pcb-metrics",type=Path,required=True)
    p.add_argument("--out",type=Path,default=ROOT/"build"/"simulation")
    p.add_argument("--plot",action="store_true")
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    spice=Spice(args.ngspice)
    metrics=json.loads(args.pcb_metrics.read_text(encoding="utf-8"))
    # Apply total pulse current to the entire worst LED loop as an upper bound on drop.
    copper=np.ceil(metrics["max_path_loop_ohm"]*20)/20
    power,curves=sweep_power(spice,args.out,copper)
    logic=sweep_logic(spice,args.out)
    nets=read_nets(args.netlist)
    data=dict(power=power,logic=logic,topology=matrix_topology(nets),microphone_wiring=mic_topology(nets),
              mechanical=mechanical_geometry(),
              production_gate="HOLD: verify USB hot-plug and suspend, first-article fit and board audio in hardware")
    (args.out/"results.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    if args.plot:
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,2,figsize=(10.2,4.1),layout="constrained")
        for rev,(t,led,current) in curves.items():
            name="A1 direct capacitor" if rev=="A1" else f"{CURRENT} soft start"
            axes[0].plot(t*1e3,current,label=name)
            axes[1].plot(t*1e3,led,label=name)
        for ax,y,xmax in zip(axes,("USB input current (A)","LED rail (V)"),(.6,20)):
            ax.set(xlim=(0,xmax),xlabel="Time after attach (ms)",ylabel=y)
            ax.grid(alpha=.25)
            ax.legend()
        fig.suptitle("USB attach — nominal circuit model (not lab data)")
        fig.savefig(args.out/"usb-attach.png",dpi=160)
    for rev in ("A1",CURRENT):
        a=[r for r in power if r["revision"]==rev]
        b=[r for r in logic if r["revision"]==rev]
        print(f"{rev}: attach charge {min(x['attach_charge_uC'] for x in a):.1f}–"
              f"{max(x['attach_charge_uC'] for x in a):.1f} uC; "
              f"min LED rail {min(x['led_min_V'] for x in a):.3f} V; "
              f"worst logic LOW/HIGH margins {min(x['low_margin_V'] for x in b):.3f}/"
              f"{min(x['high_margin_V'] for x in b):.3f} V")
    print(data["topology"],data["mechanical"])


if __name__=="__main__":
    main()
