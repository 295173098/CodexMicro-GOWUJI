"""Prepare Huaqiu quotation inputs from the hash-checked Rev B engineering pack.

This does not upload files or place an order. Huaqiu must review the stackup.
"""
from collections import OrderedDict
import csv
from hashlib import sha256
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'build/rev-b-pcba'
OUT = ROOT / 'build/huaqiu-rfq'


def read(name):
    with (SOURCE/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write(name, rows):
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    if OUT.exists():
        raise FileExistsError(f'Refusing to overwrite {OUT}')
    for line in (SOURCE/'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        if sha256((SOURCE/name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Source package changed: {name}')
    smt = read('assembly/BOM.csv')
    secondary = read('assembly/secondary-assembly.csv')
    placements = read('assembly/CPL.csv')
    groups = OrderedDict()
    for row in smt + secondary:
        process = 'Secondary/DIP' if row in secondary else 'SMT/USB hybrid'
        key = (row['MPN'], row['Manufacturer'], row['Footprint'], process)
        if key not in groups:
            groups[key] = dict(MPN=row['MPN'], Manufacturer=row['Manufacturer'],
                Footprint=row['Footprint'], Designator=[], Quantity=0,
                Specification=row['Specification'], Process=process)
        groups[key]['Designator'].append(row['Designator'])
        groups[key]['Quantity'] += 1
    for row in groups.values():
        row['Designator'] = ','.join(row['Designator'])
    fields = list(placements[0])
    placements += [{key: row[key] for key in fields} for row in secondary]
    all_refs = {r for row in groups.values() for r in row['Designator'].split(',')}
    if (len(smt), len(secondary), len(groups), len(all_refs)) != (79, 14, 35, 93):
        raise ValueError('Unexpected assembly scope')
    if all_refs != {row['Designator'] for row in placements}:
        raise ValueError('BOM/CPL mismatch')
    OUT.mkdir(parents=True)
    write('BOM-HuaQiu.csv', list(groups.values()))
    write('CPL-HuaQiu.csv', placements)
    shutil.copy2(SOURCE/'GOWUJI-RevB-PCB-Gerber.zip', OUT/'PCB-Gerber.zip')
    for folder in ('drawings', 'assembly'):
        shutil.copytree(SOURCE/folder, OUT/'reference'/folder)
    shutil.copy2(ROOT/'docs/rev-b-huaqiu.md', OUT/'READ-FIRST-HuaQiu.md')
    manifest = dict(status='quotation_only_pending_Huaqiu_stackup_and_CAM',
        pcb_quantity=5, pcba_quantity=5, total_component_refs=93, bom_rows=35,
        smt_and_usb_hybrid_refs=79, secondary_refs=14,
        original_design_stackup='JLC04161H-3313; reference only, not a Huaqiu approval',
        source_package_sha256=sha256((ROOT/'build/rev-b-pcba.zip').read_bytes()).hexdigest())
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    sums=''.join(f'{sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT).as_posix()}\n'
                 for p in sorted(OUT.rglob('*')) if p.is_file())
    (OUT/'SHA256SUMS.txt').write_text(sums)
    archive=OUT.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(OUT))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for line in sums.splitlines():
            digest,name=line.split('  ',1)
            assert sha256(z.read(name)).hexdigest()==digest
    print(archive)
    print(sha256(archive.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
