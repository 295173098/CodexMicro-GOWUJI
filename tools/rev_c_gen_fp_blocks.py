"""Generate Rev C footprint blocks from KiCad libraries.

Each footprint is added to a throw-away copy of the Rev C board, saved, and its
S-expression block is extracted.  The final board is edited as text; this avoids
the KiCad Python proxy instability seen when mixing net edits and footprint
loading in one process.
"""
from __future__ import annotations

import re
import subprocess
import sys
import uuid
from pathlib import Path

import pcbnew as k

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hardware as gen  # noqa: E402

SRC = ROOT / "hardware/rev-c/Gowuji-RevC.kicad_pcb"
OUT = ROOT / "build/rev-c/fp-blocks"
STOCK = Path("/home/carl/tools/kicad10/AppDir/usr/share/kicad/footprints")


def extract_block(text: str, ref: str) -> str:
    marker = f'(property "Reference" "{ref}"'
    for m in re.finditer(r'\n\t\(footprint ', text):
        start = m.start() + 1
        depth = 0
        i = start
        while i < len(text):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    block = text[start:i + 1]
                    if marker in block:
                        return block
                    break
            i += 1
    raise ValueError(f"Footprint block {ref} not found")


def regen_uuids(block: str) -> str:
    def repl(m):
        return f'(uuid "{uuid.uuid4()}")'
    return re.sub(r'\(uuid "[^"]+"\)', repl, block)


def gen_one(ref, lib, name, fpid, x, y, angle, layer, value, path_ref=None):
    tmp = OUT / f"{ref}.kicad_pcb"
    board = k.LoadBoard(str(SRC))
    fp = k.FootprintLoad(str(lib), name)
    if fp is None:
        raise ValueError(f"{lib}/{name}")
    fp.SetFPID(k.LIB_ID(*fpid))
    fp.SetPosition(k.VECTOR2I(k.FromMM(x), k.FromMM(y)))
    fp.SetOrientationDegrees(angle)
    if layer == k.B_Cu:
        fp.Flip(fp.GetPosition(), False)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPath(k.KIID_PATH(
        f"/{gen.uid('schematic')}/{gen.uid(path_ref or ref)}"))
    board.Add(fp)
    k.SaveBoard(str(tmp), board)
    block = regen_uuids(extract_block(tmp.read_text(), ref))
    (OUT / f"{ref}.txt").write_text(block + "\n")
    tmp.unlink()
    print(OUT / f"{ref}.txt")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("R18", STOCK / "Resistor_SMD.pretty", "R_1206_3216Metric",
         ("Resistor_SMD", "R_1206_3216Metric"), 5.0, 18.0, 0, k.F_Cu, "1.0R"),
        ("C28", ROOT / "hardware/rev-c/Gowuji.pretty", "C1206",
         ("Gowuji", "C1206"), 5.0, 21.5, 270, k.F_Cu, "4.7u 16V"),
        ("R20", STOCK / "Resistor_SMD.pretty", "R_1206_3216Metric",
         ("Resistor_SMD", "R_1206_3216Metric"), 8.3, 21.5, 0, k.F_Cu, "2.2R"),
    ]
    for job in jobs:
        gen_one(*job)


if __name__ == "__main__":
    main()
