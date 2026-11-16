"""Export a checked Rev B engineering-PCBA package (KiCad 9 Python required).

No upload, order, payment or remote publication is performed. Factory CAM,
stock and placement approval remain necessary for every assembly order.
"""
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

import pcbnew as k
from gerbonara import LayerStack

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / 'hardware/rev-b'
STEM = DESIGN / 'Gowuji-RevB'


def refs(text):
    out = []
    for term in text.split(','):
        match = re.fullmatch(r'([A-Z]+)(\d+)-\1(\d+)', term)
        if match:
            prefix, start, end = match.groups()
            out.extend(f'{prefix}{n}' for n in range(int(start), int(end)+1))
        elif re.fullmatch(r'[A-Z]+\d+', term):
            out.append(term)
        else:
            raise ValueError(f'Invalid reference group: {term}')
    return out


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def assembly(board, out):
    with (DESIGN/'assembly-parts.csv').open(encoding='utf-8-sig', newline='') as handle:
        catalog = list(csv.DictReader(handle))
    by_ref = {}
    for row in catalog:
        for ref in refs(row['Refs']):
            if ref in by_ref:
                raise ValueError(f'Duplicate BOM ref {ref}')
            by_ref[ref] = row
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    if set(by_ref) != set(fps):
        raise ValueError(f'BOM/PCB mismatch: {set(by_ref) ^ set(fps)}')
    expected_dnp = {'C19', 'C20'}
    if {r for r, f in fps.items() if f.IsDNP()} != expected_dnp:
        raise ValueError('DNP flags differ from approved C19/C20 list')
    if {r for r,f in fps.items() if f.GetLayer()==k.B_Cu} != {'U5','R16','R17'}:
        raise ValueError('Unexpected bottom components')
    with (out/'positions/kicad.csv').open(newline='') as handle:
        pos = {r['Ref']: r for r in csv.DictReader(handle)}
    bom, cpl, secondary, pins, audit = [], [], [], [], []
    for ref, f in sorted(fps.items(), key=lambda item: (re.sub(r'\d+', '', item[0]),int(re.search(r'\d+',item[0])[0]))):
        row = by_ref[ref]
        process = row['Process']
        if process == 'DNP' and ref not in expected_dnp:
            raise ValueError(f'Unexpected DNP {ref}')
        package = str(f.GetFPID().GetLibItemName())
        record = {'Comment':row['MPN'], 'Designator':ref, 'Footprint':package,
                  'Manufacturer':row['Manufacturer'], 'MPN':row['MPN'],
                  'Quantity':1, 'Specification':row['Specification']}
        if process in ('SMT','HYBRID','SECONDARY'):
            if not row['MPN'] or ref not in pos:
                raise ValueError(f'Missing procurement/position data: {ref}')
            placement = pos[ref]
            # Preserve KiCad's board coordinates and angles. These are assembly
            # references, not guessed offsets for an unknown factory library.
            item = {'Designator':ref, 'Mid X':placement['PosX']+'mm',
                    'Mid Y':placement['PosY']+'mm', 'Rotation':placement['Rot'],
                    'Layer':placement['Side'].capitalize()}
            if process == 'SECONDARY':
                secondary.append(record | item)
            else:
                bom.append(record)
                cpl.append(item)
        for pad in f.Pads():
            if not pad.GetNumber():
                continue
            p = pad.GetPosition()
            pins.append(dict(Designator=ref,Pad=pad.GetNumber(),Net=pad.GetNetname(),
                             X_mm=f'{k.ToMM(p.x):.5f}',Y_mm=f'{-k.ToMM(p.y):.5f}',
                             Layer='Bottom' if f.GetLayer()==k.B_Cu else 'Top'))
        audit.append(dict(Designator=ref,Process=process,Value=f.GetValue(),MPN=row['MPN'],
                          Layer='Bottom' if f.GetLayer()==k.B_Cu else 'Top'))
    if len(bom)!=79 or len(secondary)!=14 or {r['Designator'] for r in bom}!={r['Designator'] for r in cpl}:
        raise ValueError('Expected 78 SMT + 1 hybrid and 14 secondary components')
    write_csv(out/'assembly/BOM.csv',list(bom[0]),bom)
    write_csv(out/'assembly/CPL.csv',list(cpl[0]),cpl)
    write_csv(out/'assembly/secondary-assembly.csv',list(secondary[0]),secondary)
    write_csv(out/'assembly/pad-coordinates.csv',list(pins[0]),pins)
    write_csv(out/'assembly/process.csv',list(audit[0]),audit)
    shutil.copy2(DESIGN/'assembly-parts.csv',out/'assembly/parts-and-sources.csv')
    # Pin-location drawings use the actual PCB; bottom is viewed from below.
    # Each polarized part gets a local enlarged view, including its pad numbers.
    selected = ['U1','U2','U3','U4','U5','U6','J2','J3','X1','LED1','D1','SW15']
    cards=[]
    for ref in selected:
        f=fps[ref]; bottom=f.GetLayer()==k.B_Cu
        cx,cy=k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y)
        pads=list(f.Pads()); chunks=[]
        extent=max(max(abs(k.ToMM(p.GetPosition().x)-cx)+k.ToMM(p.GetSize().x)/2,
                       abs(k.ToMM(p.GetPosition().y)-cy)+k.ToMM(p.GetSize().y)/2) for p in pads)+1
        for p in pads:
            x=(k.ToMM(p.GetPosition().x)-cx)*(-1 if bottom else 1)
            y=k.ToMM(p.GetPosition().y)-cy
            angle=p.GetOrientationDegrees()
            w,h=k.ToMM(p.GetSize().x),k.ToMM(p.GetSize().y)
            color='#ffb546' if p.GetNumber() in ('1','A1') else '#81b6cc'
            chunks.append(f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" fill="{color}" transform="rotate({angle if bottom else -angle} {x} {y})"/>')
            if p.GetNumber():
                size=.16 if ref=='U1' else .28
                chunks.append(f'<text x="{x}" y="{y+.05}" font-size="{size}" text-anchor="middle">{escape(p.GetNumber())}</text>')
        label='BOTTOM, viewed from below' if bottom else 'TOP, viewed from above'
        cards.append(f'<section><h3>{ref} · {escape(by_ref[ref]["MPN"])}</h3><p>{label}</p><svg viewBox="{-extent} {-extent} {2*extent} {2*extent}" xmlns="http://www.w3.org/2000/svg">'+''.join(chunks)+'</svg></section>')
    (out/'assembly/orientation.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Rev B assembly orientation</title>
<style>body{font:16px sans-serif;max-width:1250px;margin:32px auto;background:#f6f8fa;color:#172b36}main{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}section{background:white;padding:16px;border:1px solid #cad7df}h3{font-size:15px}svg{width:100%;height:280px}p{line-height:1.5}</style>
<h1>GOWUJI Rev B · pad orientation reference</h1><p>Use the package pin diagram and these numbered copper pads to confirm factory placement. Orange = pin 1/A1. The drawing is a copper-pad reference, not a rendered component. Bottom U5 is mirrored to its physical underside view. R16/R17 are nonpolar. All diodes: pad 1 = cathode stripe. All LEDs: pad 3 = marked GND corner, not pad 1. U4 pad 2 is LR tied to ground; pad 5 is the ground ring. U5 tab = pin 2 OUT. C19/C20: do not populate.</p><p>CPL is KiCad-native rotation; factory library zero angles are not known. Approve each polarized component against this drawing before placement. Coordinates in pad-coordinates.csv use the same X/Y origin as CPL.</p><main>'''+''.join(cards)+'</main></html>',encoding='utf-8')
    return dict(board_footprints=len(fps),smt=78,hybrid=1,secondary=14,dnp=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-cli',default='kicad-cli')
    parser.add_argument('--out',type=Path,default=ROOT/'build/rev-b-pcba')
    parser.add_argument('--evidence',type=Path,help='Completed simulation directory from this design review')
    parser.add_argument('--firmware',type=Path,help='Fresh 4 MB Rev B merged image')
    args=parser.parse_args()
    args.out=args.out.resolve()
    if args.out.exists():
        raise FileExistsError(f'Refusing to mix stale output: {args.out}; choose a new --out')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env['LC_ALL']='C.UTF-8'
    def run(*cmd):
        subprocess.run([str(args.kicad_cli),*map(str,cmd)],env=env,cwd=ROOT,check=True)
    inputs=[p for p in DESIGN.rglob('*') if p.is_file() and p.suffix not in ('.kicad_prl','.lck')]
    inputs += [ROOT/'tools/export_rev_b_order.py',ROOT/'docs/rev-b-order.md',ROOT/'docs/rev-b-component-review.md',ROOT/'docs/rev-b-bringup.md']
    inputs += [ROOT/'tools'/name for name in ('simulate_rev_b_power.py','screen_rev_b_damping.py','simulate_rev_b.py','rev_b_impedance.py')]
    if args.firmware:
        blob=args.firmware.read_bytes()
        if len(blob)!=4*1024*1024 or any(blob[n]!=0xe9 for n in (0,0x10000)):
            raise ValueError('Expected 4 MB merged Rev B image with bootloader/application headers')
        inputs += [p for p in (ROOT/'firmware/Gowuji').glob('*') if p.is_file()]+[ROOT/'firmware/flash.py',ROOT/'tools/build_firmware.py']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    with tempfile.TemporaryDirectory(prefix='rev-b-export-',dir=args.out.parent) as work:
        out=Path(work)
        for folder in ['gerber','assembly','positions','validation','drawings','source']:(out/folder).mkdir()
        run('sch','erc','--format','json','--exit-code-violations','-o',out/'validation/erc.json',STEM.with_suffix('.kicad_sch'))
        run('pcb','drc','--schematic-parity','--format','json','--exit-code-violations','-o',out/'validation/drc.json',STEM.with_suffix('.kicad_pcb'))
        drc=json.loads((out/'validation/drc.json').read_text());erc=json.loads((out/'validation/erc.json').read_text())
        if any(drc.get(key) for key in ('violations','unconnected_items','schematic_parity')) or any(s['violations'] for s in erc['sheets']):
            raise ValueError('ERC/DRC/parity must all be empty')
        run('sch','export','netlist','--format','kicadxml','-o',out/'validation/netlist.xml',STEM.with_suffix('.kicad_sch'))
        run('pcb','export','gerbers','-l','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts',
            '--subtract-soldermask','-o',str(out/'gerber')+'/',STEM.with_suffix('.kicad_pcb'))
        run('pcb','export','drill','--format','excellon','--excellon-separate-th','--excellon-oval-format','route','--generate-report',
            '--report-path',out/'validation/drill.txt','-o',str(out/'gerber')+'/',STEM.with_suffix('.kicad_pcb'))
        run('pcb','export','pos','--side','both','--format','csv','--units','mm','--exclude-dnp','-o',out/'positions/kicad.csv',STEM.with_suffix('.kicad_pcb'))
        for side in ('F','B'):
            run('pcb','export','svg','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--sketch-pads-on-fab-layers',
                '--crossout-DNP-footprints-on-fab-layers','-l',f'{side}.Fab,{side}.Silkscreen,Edge.Cuts',
                *(['--mirror'] if side=='B' else []),'-o',out/f'drawings/{side}-assembly.svg',STEM.with_suffix('.kicad_pcb'))
        b=k.LoadBoard(str(STEM.with_suffix('.kicad_pcb')))
        counts=assembly(b,out)
        tracks=list(b.GetTracks());vias=[t for t in tracks if isinstance(t,k.PCB_VIA)];lines=[t for t in tracks if not isinstance(t,k.PCB_VIA)]
        geom=dict(tracks=len(lines),vias=len(vias),copper_zones=sum(not z.GetIsRuleArea() for z in b.Zones()),
                  rule_areas=sum(z.GetIsRuleArea() for z in b.Zones()),
                  min_trace_mm=min(k.ToMM(t.GetWidth()) for t in lines),
                  min_via_drill_mm=min(k.ToMM(t.GetDrillValue()) for t in vias),
                  min_via_annulus_mm=min(k.ToMM(t.GetWidth(k.F_Cu)-t.GetDrillValue())/2 for t in vias))
        if geom['min_trace_mm']<.1 or geom['min_via_drill_mm']<.2 or geom['min_via_annulus_mm']<.1:
            raise ValueError('Geometry outside the reviewed manufacturing envelope')
        gerbers=sorted((out/'gerber').iterdir())
        required={'.gtl','.g1','.g2','.gbl','.gtp','.gbp','.gto','.gbo','.gts','.gbs','.gm1','.gbrjob','.drl'}
        if len(gerbers)!=14 or {p.suffix for p in gerbers}!=required:
            raise ValueError('Missing or extra manufacturing layers')
        if {p.name.rsplit('-',1)[-1] for p in gerbers if p.suffix=='.drl'}!={'PTH.drl','NPTH.drl'}:
            raise ValueError('PTH/NPTH must be separate')
        job=json.loads(next(p for p in gerbers if p.suffix=='.gbrjob').read_text())['GeneralSpecs']
        if (job['BoardThickness'],job['LayerNumber'],job['Finish'],job['ImpedanceControlled'])!=(1.6,4,'ENIG',True):
            raise ValueError('Unexpected stackup in Gerber job')
        parsed=LayerStack.open(out/'gerber')
        copper={layer for layer in parsed.graphic_layers if layer[1]=='copper'}
        if copper!={('top','copper'),('inner_1','copper'),('inner_2','copper'),('bottom','copper')}:
            raise ValueError('Independent Gerber parser did not find all four copper layers')
        if any(not layer.objects for layer in parsed.graphic_layers.values()):
            raise ValueError('Unexpected empty fabrication layer')
        bounds=parsed.bounding_box()
        expected=((-0.025,-98.025),(95.025,0.025))  # Includes 0.05 mm outline stroke.
        if any(abs(a-b)>1e-5 for p,q in zip(bounds,expected) for a,b in zip(p,q)):
            raise ValueError(f'Unexpected exported board bounds: {bounds}')
        if (len(parsed.drill_pth.objects),len(parsed.drill_npth.objects))!=(202,45):
            raise ValueError('Independent drill parsing disagrees with reviewed hole count')
        (out/'validation/gerber-parse.json').write_text(json.dumps(dict(
            parser='gerbonara',bounds_mm=bounds,pth=202,npth=45,
            primitive_counts={'.'.join(key):len(layer.objects) for key,layer in parsed.graphic_layers.items()}
        ),indent=2)+'\n')
        for p in inputs:
            dest=out/'source'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        for file in ('rev-b-order.md','rev-b-component-review.md','rev-b-bringup.md'):
            shutil.copy2(ROOT/'docs'/file,out/file)
        if args.evidence:
            for path in ('power-final/power.json','power-final/passive-worst.cir',
                         'power-final/passive-worst-r16-energy.cir','power-final/passive-worst-current.cir',
                         'power-final/usb-indicators-mic-worst.cir','power-final/ble-peak-with-led-worst.cir',
                         'logic/screening.json','sources/murata-bias.json','sources/murata-request-url.txt'):
                dest=out/'validation/evidence'/path;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(args.evidence/path,dest)
            power=json.loads((args.evidence/'power-final/power.json').read_text())
            if power['passive']['cases']!=1728 or sum(x['cases'] for x in power['operating'])!=1024:
                raise ValueError('Unexpected power sweep coverage')
            if power['passive']['worst_bus']['bus_peak_V']>=5.5 or power['passive']['worst_r16_power']['r16_peak_W']>=100 or power['passive']['worst_r17_power']['r17_peak_W']>=10:
                raise ValueError('Engineering power/pulse screen failed')
        if args.firmware:
            (out/'firmware').mkdir()
            shutil.copy2(args.firmware,out/'firmware/GOWUJI-RevB-flash-0x0.bin')
            shutil.copy2(ROOT/'firmware/flash.py',out/'firmware/flash.py')
        (out/'README-FIRST.txt').write_text('GOWUJI Rev B - 3-5 engineering PCBA samples\nRead rev-b-order.md before ordering.\nGERBER zip is only PCB copper/mask/paste/drills, NOT a complete PCBA order.\nFactory must confirm stackup/impedance, QFN via process, sourcing and polarized placement.\nNot a production qualification; no physical prototype has been tested.\n',encoding='utf-8')
        if hashes!={str(p.relative_to(ROOT)):sha(p) for p in inputs}:
            raise ValueError('Source changed during export')
        (out/'manifest.json').write_text(json.dumps(dict(created_utc=datetime.now(timezone.utc).isoformat(),
             kicad=drc['kicad_version'],status='engineering_samples_subject_to_factory_CAM',
             counts=counts,geometry=geom,firmware_included=bool(args.firmware),source_sha256=hashes),indent=2)+'\n')
        shutil.copytree(out,args.out)
    with zipfile.ZipFile(args.out/'GOWUJI-RevB-PCB-Gerber.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted((args.out/'gerber').iterdir()):z.write(p,p.name)
    sums=''.join(f'{sha(p)}  {p.relative_to(args.out).as_posix()}\n' for p in sorted(args.out.rglob('*')) if p.is_file())
    (args.out/'SHA256SUMS.txt').write_text(sums)
    archive=args.out.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(args.out.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(args.out))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('Archive CRC error')
        for line in sums.splitlines():
            digest,name=line.split('  ',1)
            if sha256(z.read(name)).hexdigest()!=digest:raise ValueError(f'Hash mismatch {name}')
    print(json.dumps(dict(package=str(archive),sha256=sha(archive),counts=counts,geometry=geom),indent=2))


if __name__=='__main__':main()
