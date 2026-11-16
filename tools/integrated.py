"""Generate the Rev B schematic and PCB placement using KiCad 9's Python."""
import argparse
import csv
from dataclasses import replace
import json
from pathlib import Path

import pcbnew as k
import design as a
import hardware as gen
from integrated_layout import CHIP, USB

STOCK = {"S3":"Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP5.6x5.6mm",
         "USB_C":"Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
         "LDO":"Package_TO_SOT_SMD:SOT-223-3_TabPin2",
         "R1206":"Resistor_SMD:R_1206_3216Metric",
         "Xtal":"Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
         "UFL":"Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical"}
# ESP32-S3FH4R2 QFN pinout; SPI signals are used inside the package.
GPIO = {g:g+5 for g in range(15)} | {17:23,18:24,19:25,20:26,21:27,
        33:38,34:39,35:40,36:41,37:42,38:43,39:44,40:45,41:47,
        42:48,43:49,44:50,45:51,46:52}
S3_LABELS = {str(p):f"GPIO{g}" for g,p in GPIO.items()}
S3_LABELS.update({str(i):n for i,n in enumerate(
    ("LNA_IN","VDD3P3","VDD3P3","CHIP_PU"),1)})
S3_LABELS.update({str(i):n for i,n in enumerate(
    ("VDD3P3_RTC","XTAL_32K_P","XTAL_32K_N"),20)})
S3_LABELS.update({str(i):n for i,n in enumerate(
    ("SPICS1","VDD_SPI","SPIHD","SPIWP","SPICS0","SPICLK","SPIQ","SPID","SPICLK_N","SPICLK_P"),28)})
S3_LABELS.update({"46":"VDD3P3_CPU","53":"XTAL_N","54":"XTAL_P","55":"VDDA","56":"VDDA","57":"GND_EP"})
LABELS = {"S3":dict(sorted(S3_LABELS.items(),key=lambda pair:int(pair[0]))),
          "USB_C":{"A5":"CC1","B5":"CC2","A6":"D+","B6":"D+",
                   "A7":"D-","B7":"D-","A8":"SBU1","B8":"SBU2","S1":"SHELL"} |
                   {n:"GND" for n in ("A1","A12","B1","B12")} |
                   {n:"VBUS" for n in ("A4","A9","B4","B9")},
          "LDO":{"1":"GND","2":"OUT","3":"IN"},
          "Xtal":{"1":"XI","2":"GND","3":"XO","4":"GND"},
          "UFL":{"1":"RF","2":"GND"}}
NEW_LOC = {"U1":(76.2,58.42),"R2":(50.8,97.79),"J1":(104.14,97.79),
           "J2":(48.26,332.74),"U5":(191.77,317.5),"U6":(116.84,318.77),
           "R10":(108,350.52),"R11":(162.56,350.52),"R12":(108,364.49),"R13":(162.56,364.49),
           "R14":(234.95,345.44),"C13":(279.4,345.44),
           "C14":(235,317.5),"C15":(279.4,317.5),"C16":(325.12,317.5),
           "TP1":(234.95,364.49),"TP2":(279.4,364.49),"TP3":(325.12,364.49)}
NEW_LOC.update({k: (round(x/1.27)*1.27,y) for k,(x,y) in NEW_LOC.items()})
NEW_LOC.update({"X1":(416.56,165.1),"J3":(520.7,165.1),"L1":(469.9,165.1),
                "L2":(469.9,217.17),"R15":(368.3,364.49),"TP4":(411.48,364.49),
                "TP5":(462.28,364.49)})
NEW_LOC.update({"R16":(386.08,317.5),"R17":(386.08,345.44)})
for i in range(17,28):
    NEW_LOC[f"C{i}"]=(411.48+53.34*((i-17)%3),190.5+25.4*((i-17)//3))


def parts():
    moved = {"U2":(22,9.5),"U3":(24,18),"R1":(24,13),
             "C7":(28,15),"C8":(25,22),"C9":(20.8,18),"C10":(30,19),
             "R8":(39.0,12.5),"R9":(56.7,5.6)}
    old = next(p for p in a.parts if p.ref=="U1")
    m={str(GPIO[int(g)]):n for g,n in old.nets.items() if g.isdigit()}
    m.update({"1":"RF_CHIP","2":"RF_3V3","3":"RF_3V3","4":"CHIP_EN",
              "20":"V3V3","29":"VDD_SPI","46":"V3V3","53":"XTAL_N","54":"XTAL_P",
              "55":"RF_3V3","56":"RF_3V3","57":"GND",
              str(GPIO[0]):"BOOT0",str(GPIO[19]):"USB_N_MCU",str(GPIO[20]):"USB_P_MCU"})
    usb={n:label for n,label in LABELS["USB_C"].items() if label in ("GND","VBUS","CC1","CC2")}
    usb={n:("VBUS_RAW" if label=="VBUS" else label) for n,label in usb.items()}
    usb.update({"A6":"USB_P","B6":"USB_P","A7":"USB_N","B7":"USB_N","S1":"GND"})
    def part(ref,val,kind,pos,*pins):
        return a.Part(ref,val,kind,pos,a.pn(*pins))
    return [a.Part("U1","ESP32-S3FH4R2","S3",CHIP,m)]+[
        replace(p,xy=moved.get(p.ref,p.xy),val="2.2u 25V" if p.ref=="C10" else p.val)
        for p in a.parts if p.ref!="U1"]+[
        a.Part("J2","HRO TYPE-C-31-M-12","USB_C",USB,usb),
        part("U5","TLV76133DCYR","LDO",(38,18.3),"GND","V3V3","VBUS"),
        part("U6","USBLC6-2SC6","SOT23_6",(32,11.3),"USB_N","GND","USB_P","USB_P","VBUS","USB_N"),
        part("R10","22R","R0603",(46.2,18.6),"USB_N","USB_N_MCU"),
        part("R11","22R","R0603",(49.1,18.6),"USB_P","USB_P_MCU"),
        part("R12","5.1k","R0603",(26,9),"CC1","GND"),
        part("R13","5.1k","R0603",(36.2,10),"CC2","GND"),
        part("R14","10k","R0603",(42.5,11.4),"V3V3","CHIP_EN"),
        part("C13","1u 16V","C0603",(42.5,13.7),"CHIP_EN","GND"),
        part("C14","4.7u 16V","C1206",(29.6,16.7),"VBUS","VBUS_DAMP"),
        part("R16","0.82R","R1206",(24.25,11.5),"VBUS_RAW","VBUS"),
        part("R17","1.5R","R0603",(27.3,17.3),"VBUS_DAMP","GND"),
        part("C15","22u 10V","C1206",(41,23.8),"V3V3","GND"),
        part("C16","100n","C0603",(53.5,19.2),"V3V3","GND"),
        part("TP1","BOOT","Probe",(59,3.4),"BOOT0"),
        part("TP2","RESET","Probe",(57,2),"CHIP_EN"),
        part("TP3","GND","Probe",(48,3),"GND"),
        part("TP4","UART_RX","Probe",(51,3),"LED_GPIO"),
        part("TP5","UART_TX","Probe",(54,3),"PDM_DATA_MCU"),
        part("X1","40 MHz / 10 pF","Xtal",(48.2,6.4),"XTAL_P","GND","XTAL_N","GND"),
        part("C17","15p C0G tune","C0603",(44.4,6.3),"XTAL_P","GND"),
        part("C18","15p C0G tune","C0603",(52.1,7.0),"XTAL_N","GND"),
        part("L1","2.2nH RF tune","R0603",(43,8.7),"RF_CHIP","RF_FEED"),
        part("C19","DNP RF tune","C0603",(43.9,4.3),"RF_CHIP","GND"),
        part("C20","DNP RF tune","C0603",(40.0,8.1),"RF_FEED","GND"),
        part("J3","U.FL-R-SMT-1","UFL",(40.0,3.6),"RF_FEED","GND"),
        part("L2","BLM18PG221SN1","R0603",(56,10.8),"V3V3","RF_3V3"),
        part("C21","10u 10V","C0603",(58,13.4),"RF_3V3","GND"),
        part("C22","100n","C0603",(56.5,8.0),"RF_3V3","GND"),
        part("C23","100n","C0603",(43.0,10),"RF_3V3","GND"),
        part("C24","1u 10V","C0603",(54.5,16),"VDD_SPI","GND"),
        part("C25","1u 10V","C0603",(54.6,13.5),"V3V3","GND"),
        part("C26","100n","C0603",(50.5,21.1),"V3V3","GND"),
        part("C27","1u 10V","C0603",(54,21.8),"V3V3","GND"),
        part("R15","10k","R0603",(60.4,6),"V3V3","BOOT0")]


def placeholder_fp():
    # Temporary outlines only. The PCB receives the exact KiCad library parts below.
    return {kind:(4,4,0,0,[gen.sm(n,0,0,.4,.4) for n in names]) for kind,names in LABELS.items()}


def make(libs,out):
    out.mkdir(parents=True,exist_ok=True)
    stem=out/"Gowuji-RevB"
    path=stem.with_suffix(".kicad_pcb")
    if path.exists():
        raise FileExistsError(f"Generate in a new directory to preserve the current board: {path}")
    gen.PCB,gen.LIB=out,out/"Gowuji.pretty"
    gen.LIB.mkdir(exist_ok=True)
    gen.parts=parts()
    gen.FP={k:v for k,v in gen.FP.items() if k!="Zero"}
    gen.FP |= placeholder_fp() | {"Probe":(1.4,1.4,0,0,[gen.sm(1,0,0,1.4,1.4)])}
    original=gen.pins
    def pins(kind):
        if kind not in LABELS:
            return original(kind)
        labels=list(LABELS[kind].items())
        cut=(len(labels)+1)//2
        width=10.16 if kind=="S3" else 5.08
        groups=[labels[:cut],labels[cut:]]
        return [(n,name,side*(width+2.54),((len(g)-1)/2-i)*2.54,0 if side==-1 else 180,"passive")
                for side,g in zip((-1,1),groups) for i,(n,name) in enumerate(g)],width,cut*1.27+1.27
    gen.pins=pins
    gen.NETS={n:i for i,n in enumerate(sorted({n for p in gen.parts for n in gen.board_nets(p).values()}),1)}
    custom={"USB_C","LDO","S3"}
    sch_fp={kind:("Gowuji:"+kind if kind in custom else name) for kind,name in STOCK.items()}
    gen.put(stem.with_suffix(".kicad_sch"),gen.schematic("B","Gowuji-RevB",NEW_LOC,sch_fp))
    tmp=out/"placement.tmp.kicad_pcb"
    gen.put(tmp,gen.board("B",legacy_antenna=False).replace("${KIPRJMOD}/models/","${KIPRJMOD}/../models/"))
    for footprint in gen.LIB.glob("*.kicad_mod"):
        source=footprint.read_text(encoding="utf-8")
        revised=source.replace("${KIPRJMOD}/models/","${KIPRJMOD}/../models/")
        if revised!=source:
            gen.put(footprint,revised)
    b=k.LoadBoard(str(tmp))
    b.SetCopperLayerCount(4)
    for old in list(b.GetFootprints()):
        part=next(p for p in gen.parts if p.ref==old.GetReference())
        if part.kind not in STOCK:
            if part.ref=="U6" or part.kind=="Probe":
                old.Reference().SetVisible(False)
            if part.val.startswith("DNP "):
                old.SetAttributes(old.GetAttributes() | k.FP_DNP)
            continue
        lib,name=STOCK[part.kind].split(":")
        fp=k.FootprintLoad(str(libs/f"{lib}.pretty"),name)
        if fp is None:
            raise ValueError(STOCK[part.kind])
        if part.kind=="S3":
            # Maintain a solder-paste gap to the nine exposed-pad via bores.
            windows=[p for p in fp.Pads() if not p.GetNumber() and p.IsOnLayer(k.F_Paste)]
            assert len(windows)==16
            for pad in windows:
                pad.SetSize(k.VECTOR2I(k.FromMM(1.04),k.FromMM(1.04)))
        if part.kind in custom:
            fp.SetFPID(k.LIB_ID("Gowuji",part.kind))
            for item in fp.GraphicalItems():
                if part.kind!="S3" and item.GetLayer()==k.F_SilkS and isinstance(item,k.PCB_SHAPE):
                    item.SetLayer(k.F_Fab)
            (gen.LIB/f"{part.kind}.kicad_mod").unlink()
            k.FootprintSave(str(gen.LIB),fp)
        else:
            fp.SetFPID(k.LIB_ID(lib,name))
            (gen.LIB/f"{part.kind}.kicad_mod").unlink()
        fp.SetReference(part.ref)
        fp.SetValue(part.val)
        fp.SetPath(old.GetPath())
        fp.SetPosition(old.GetPosition())
        if part.ref=="J2":
            fp.SetOrientationDegrees(180)
        if part.ref in ("J2","U1","X1","J3"):
            fp.Reference().SetVisible(False)
        b.Add(fp)
        nets=gen.board_nets(part)
        pad_numbers={pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()}
        if pad_numbers!=set(nets):
            raise ValueError((part.ref,pad_numbers^set(nets)))
        for pad in fp.Pads():
            if pad.GetNumber():
                pad.SetNet(b.GetNetsByName()[nets[pad.GetNumber()]])
        b.Remove(old)
    k.SaveBoard(str(path),b)
    tmp.unlink()
    project=json.loads((a.ROOT/"hardware/Gowuji-RevA.kicad_pro").read_text())
    project["meta"]["filename"]="Gowuji-RevB.kicad_pro"
    gen.put(stem.with_suffix(".kicad_pro"),json.dumps(project,indent=2)+"\n")
    with (out/"BOM.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f)
        w.writerow(("Refs","Qty","Part","Notes","CNY low","CNY high"))
        w.writerows(row for row in a.BOM if row[0] not in {"U1","PCB","C10"})
        w.writerows([
            ("PCB",1,"4-layer FR4 1.6 mm","95 x 98 mm; quote exact controlled impedance stackup",None,None),
            ("U1",1,"ESP32-S3FH4R2","QFN56, 4 MB QSPI flash, 2 MB PSRAM",None,None),
            ("J2",1,"HRO TYPE-C-31-M-12","USB 2.0 16-pin; shell soldered",.8,2.8),
            ("U5",1,"TLV76133DCYR","3.3 V 1 A LDO; SOT-223; verify temperature",1.8,4.5),
            ("U6",1,"USBLC6-2SC6","USB data ESD; SOT-23-6",.35,1.5),
            ("R10-R11",2,"22 ohm","0603 USB source damping",.02,.1),
            ("R12-R13",2,"5.1 kohm 1%","0603 Type-C sink Rd",.02,.1),
            ("R14",1,"10 kohm","0603 enable pull-up",.02,.1),
            ("C13",1,"1 uF 16 V X7R","0603 enable delay",.05,.2),
            ("C10",1,"2.2 uF 25 V X7R","0603 direct VBUS bypass; >=1 uF effective at 5.25 V including tolerance",None,None),
            ("C14",1,"4.7 uF 16 V X7R","1206 VBUS damping branch, paired with R17",.1,.35),
            ("R16",1,"0.82 ohm 5% 0.5 W","1206 pulse-rated; check hot-plug waveform (4.50 A peak and 64.7 uJ maximum in separate model cases)",None,None),
            ("R17",1,"1.5 ohm 5%","0603 VBUS damping branch; check pulse curve",None,None),
            ("C15",1,"22 uF 10 V X7R","1206 3.3 V bulk, check DC bias",.2,.8),
            ("C16",1,"100 nF 16 V X7R","0603 module bypass",.04,.12),
            ("X1",1,"40 MHz 3225 4-pin crystal","10 pF CL; confirm exact part and trim",None,None),
            ("L1",1,"2.2 nH RF inductor","starting value; tune with VNA",None,None),
            ("L2",1,"Murata BLM18PG221SN1","RF supply ferrite",None,None),
            ("C17-C18",2,"15 pF C0G","starting crystal load values; trim",None,None),
            ("C19-C20",0,"RF matching positions","DNP until tuned",0,0),
            ("C21",1,"10 uF 10 V","RF rail bulk",None,None),
            ("C22-C23,C26",3,"100 nF","supply bypass",None,None),
            ("C24-C25,C27",3,"1 uF 10 V","supply bypass",None,None),
            ("R15",1,"10 kohm","BOOT pull-up",None,None),
            ("J3",1,"Hirose U.FL-R-SMT-1","50 ohm, internal antenna",None,None),
            ("ANT1",1,"2.4 GHz 50 ohm adhesive FPC antenna","u.FL compatible; select and tune in enclosure",None,None),
            ("TP1-TP5",5,"Bare pads","internal service",0,0)])
    print(path)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--libraries",type=Path,required=True)
    p.add_argument("--out",type=Path,default=a.ROOT/"hardware"/"rev-b")
    opts=p.parse_args()
    make(opts.libraries.resolve(),opts.out.resolve())
