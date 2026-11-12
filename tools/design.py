"""Shared Rev A3 placement, pins and netlist. Units: mm; XY from PCB top left."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W, H = 95, 98
MOUNT = [(4, 4), (91, 4), (4, 94), (91, 94)]
XS = [18.4 + 19.05*i for i in range(4)]
YS = [33.30 + 19.05*i for i in range(4)]
TOUCH, JOY = (XS[0],YS[3]), (XS[3],YS[0])
ENC = (XS[0], YS[0])
MCU = ((XS[1]+XS[2])/2, 0.25)
NAMES = ('SLOT1 SLOT2 NEW_CHAT PTT SLOT3 SLOT4 ACCEPT DECLINE '
         'SLOT5 SLOT6 FIND INTERRUPT PTT_B DIAL_PUSH '
         'JOY_UP JOY_RIGHT JOY_DOWN JOY_LEFT JOY_CENTER').split()
MATRIX = [[0,1,2,3,4], [5,6,7,8,9], [10,11,12,13,-1], [14,15,16,17,18]]
ROWS, COLS = [5,6,7,8], [9,10,11,12,13]
ENC_PINS, TOUCH_PIN, LED_PIN = (1,2), 4, 44
KEY_GRID = [(1,0),(2,0),(0,2),(1,3),(0,1),(1,1),(1,2),
            (2,2),(2,1),(3,1),(3,3),(3,2),(2,3)]
KEYS = [(XS[x],YS[y]) for x,y in KEY_GRID]
LED_KEYS = [0,1,4,5,8,9]
PTT_PRIMARY, PTT_SECONDARY = 3,12
LEDS = [(KEYS[i][0]+(-5.1 if i==0 else 5.1 if i==1 else 0), KEYS[i][1]-9.525) for i in LED_KEYS]

@dataclass
class Part:
    ref: str
    val: str
    kind: str
    xy: tuple
    nets: dict

parts = []
def add(ref,val,kind,xy,**nets):
    parts.append(Part(ref,val,kind,xy,nets))

def pn(*nets):
    return {str(i+1): n for i,n in enumerate(nets)}

m = {'5V':'VBUS','GND':'GND','3V3':'V3V3','1':'ENC_A','2':'ENC_B',
     str(TOUCH_PIN):'TOUCH_MCU',str(LED_PIN):'LED_GPIO'}
m.update({str(pin):f'ROW{i}' for i,pin in enumerate(ROWS)})
m.update({str(pin):f'COL{i}' for i,pin in enumerate(COLS)})
add('U1','ESP32-S3-Zero-M','Zero',MCU,**m)

for row, line in enumerate(MATRIX):
    for col, i in enumerate(line):
        if i < 0:
            continue
        colnet, rownet = f'COL{col}', f'ROW{row}'
        if i < 13:
            x,y = KEYS[i]
            add(f'SW{i+1}',NAMES[i],'MX',(x,y),**pn(colnet,f'K{i+1}'))
            dxy = (x+9.525,y+5.2)
        elif i == 13:
            add('SW14','EC11E15244G1','EC11',ENC,
                **{'A':'ENC_A','B':'ENC_B','C':'GND','S1':colnet,'S2':'K14','MP':'GND'})
            dxy = (ENC[0]+1,ENC[1]-12.8)
        else:
            dxy = (JOY[0]-9.5+(i-14)*4.75,JOY[1]-17.8)
        # Active row low; column input pull-up. K/cathode on pin 1.
        add(f'D{i+1}','BAT46W-7-F','SOD123',dxy,**pn(rownet,f'K{i+1}'))

# Rotating the printed cap 45 degrees marks the physical diagonal directions.
# Drawing #1 terminal names A,B,C,D map to up,right,left,down in firmware.
# Common is on the columns' diode side; wire these diodes anode to column,
# cathode to direction, so the shared joystick common can be driven ROW3.
for i, p in enumerate(parts):
    if p.ref in [f'D{j}' for j in range(15,20)]:
        j = int(p.ref[1:])-15
        parts[i] = Part(p.ref,p.val,p.kind,p.xy,pn(f'K{j+15}',f'COL{j}'))
add('SW15','SKRHAAE010','SKRH',JOY,**pn('K15','K19','K18','K16','ROW3','K17'))

add('U2','SN74LV1T125DBVR','SOT23_5',(24,11),**pn('GND','LED_GPIO','GND','LED_BUF','LED_5V'))
add('U3','TPS22918DBVR','SOT23_6',(32,9),**pn('VBUS','GND','V3V3','LED_CT',None,'LED_5V'))
add('R1','330R','R0603',(24,15),**pn('LED_BUF','PIX0'))
add('R2','1k','R0603',(12,84),**pn('TOUCH_MCU','TOUCH_FOIL'))
for i in range(5):
    add(f'R{i+3}','22k','R0603',(66+i*4.6,10.4),**pn('V3V3',f'COL{i}'))
add('J1','Touch foil wire','Wire',TOUCH,**pn('TOUCH_FOIL'))
for i,(x,y) in enumerate(LEDS):
    add(f'LED{i+1}','WS2812B-MINI-V6','RGB3535',(x,y),**pn('LED_5V',f'PIX{i+1}' if i<5 else None,'GND',f'PIX{i}'))
    add(f'C{i+1}','100n','C0603',(x+(-4.6 if i==0 else 4.6),y-3.6 if i<2 else y+1.4),**pn('LED_5V','GND'))
add('C7','100n','C0603',(28,10),**pn('LED_5V','GND'))
add('C8','47u 10V','C1206',(32,16.0),**pn('LED_5V','GND'))
add('C9','4.7n C0G','C0603',(32,4.5),**pn('LED_CT','GND'))
add('C10','1u 16V','C0603',(36.4,8.5),**pn('VBUS','GND'))
for i, xy in enumerate(MOUNT,1):
    add(f'H{i}','M2','Mount',xy)

BOM = [
    ('U1',1,'Waveshare ESP32-S3-Zero-M (4 MB / 2 MB)','with 2x9 male headers',19,28),
    ('U2',1,'TI SN74LV1T125DBVR','SOT-23-5; 1.8–5.5 V translator',0.7,2.5),
    ('U3',1,'TI TPS22918DBVR','SOT-23-6; 5 V LED rail load switch',1.5,5),
    ('SW1-SW13',13,'MX-compatible 3-pin or 5-pin switches','solder type; match SW4 and SW13 for the shared 2U cap',0.65,1.5),
    ('SW14',1,'ALPS EC11E15244G1','push encoder; confirm drawing / D shaft',5,12),
    ('SW15',1,'ALPS SKRHAAE010','no guide bosses; verify footprint before substituting',5,16),
    ('D1-D19',19,'Diodes Inc. BAT46W-7-F','SOD-123; low forward drop Schottky',0.08,0.30),
    ('LED1-LED6',6,'Worldsemi WS2812B-MINI-V6','3535; verify MINI-V6 (no X1 suffix)',0.3,0.9),
    ('R1',1,'330 ohm','0603',0.02,0.1),
    ('R2',1,'1 kohm','0603',0.02,0.1),
    ('R3-R7',5,'22 kohm ±1%','0603; matrix column pull-ups',0.02,0.1),
    ('C1-C7',7,'100 nF X7R 16 V','0603',0.04,0.12),
    ('C8',1,'47 uF X5R 10 V','1206; ceramic',0.3,1),
    ('C9',1,'4.7 nF C0G 50 V','0603; load-switch slew-rate capacitor',0.04,0.2),
    ('C10',1,'1 uF X7R 16 V','0603; load-switch input bypass',0.05,0.2),
    ('PCB',1,'2-layer FR4 1.6 mm','95 x 98 mm; bare PCB; per board in small batch',5,20),
    ('CAPS-A',6,'MX 1U frosted translucent keycaps','matte clear or milky PC; 17.9 mm reference width',0.7,2.5),
    ('CAPS-C',5,'MX 1U opaque command caps','add optional icon decals',0.35,1.2),
    ('PRINT',1,'PLA/PETG + translucent material','base, plate, knobs, light pipes and dual-stem 2U cap',4.5,11),
    ('SCREWS',4,'M2x10 pan-head screws','self-tap into printed pilot holes',0.1,0.35),
    ('FOIL',1,'Copper adhesive foil + thin wire','14 mm square + 50 mm wire',0.2,1),
    ('USB',1,'USB-C data cable','reuse an existing cable',0,8),
]
