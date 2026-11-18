"""Generate the Rev C schematic from the Rev B electrical design.

Rev C changes (soft-start variant):
  * separate VBUS_LED branch: VBUS_RAW -> R18 1.0 ohm -> U3 VIN
  * damped LED input: C28 4.7 uF + R20 2.2 ohm to GND
  * C14 4.7 uF -> 2.2 uF to keep the hot-plug charge within the 50 uC
    engineering reference while the R17 branch still damps VBUS
  * C9 4.7 nF -> 47 nF: TPS22918 CT slew control slows the LED rail to about
    129 ms (10-90% at 5 V), keeping the pre-enumeration LED bulk inrush low.
    U3 ON stays tied to V3V3; the firmware's existing ~144 ms touch-calibration
    delay keeps the first pixel update after the rail ramp.
  * L1 2.2 nH -> 1.8 nH

The PCB is edited separately by tools/rev_c_board_text.py; this script only
writes the schematic, project and BOM inputs.  It reuses the Rev B UUID
namespace so the existing PCB footprint paths remain valid.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import design as a  # noqa: E402
import hardware as gen  # noqa: E402
import integrated as b  # noqa: E402


def rev_c_parts():
    parts = []
    for p in b.parts():
        nets = dict(p.nets)
        if p.ref == "U3":
            nets["1"] = "VBUS_LED"
        val = p.val
        if p.ref == "C9":
            val = "47n C0G"
        elif p.ref == "C14":
            val = "2.2u 16V"
        elif p.ref == "L1":
            val = "1.8nH RF tune"
        parts.append(a.Part(p.ref, val, p.kind, p.xy, nets))
    parts += [
        a.Part("R18", "1.0R", "R1206", (5.0, 18.0),
               a.pn("VBUS_RAW", "VBUS_LED")),
        a.Part("C28", "4.7u 16V", "C1206", (5.0, 21.5),
               a.pn("VBUS_LED", "LED_SNUB")),
        a.Part("R20", "2.2R", "R1206", (8.0, 21.5),
               a.pn("LED_SNUB", "GND")),
    ]
    return parts


def make(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    gen.PCB = out
    gen.LIB = out / "Gowuji.pretty"
    gen.parts = rev_c_parts()
    gen.FP["Probe"] = (1.4, 1.4, 0, 0, [gen.sm(1, 0, 0, 1.4, 1.4)])

    original = gen.pins

    def pins(kind):
        if kind not in b.LABELS:
            return original(kind)
        labels = list(b.LABELS[kind].items())
        cut = (len(labels) + 1) // 2
        width = 10.16 if kind == "S3" else 5.08
        groups = [labels[:cut], labels[cut:]]
        return [(n, name, side * (width + 2.54),
                 ((len(g) - 1) / 2 - i) * 2.54,
                 0 if side == -1 else 180, "passive")
                for side, g in zip((-1, 1), groups)
                for i, (n, name) in enumerate(g)], width, cut * 1.27 + 1.27

    gen.pins = pins
    gen.NETS = {n: i for i, n in enumerate(sorted(
        {n for p in gen.parts for n in gen.board_nets(p).values()}), 1)}

    loc = dict(b.NEW_LOC)
    loc.update({"R18": (172.72, 233.68), "C28": (172.72, 247.65),
                "R20": (172.72, 260.35)})
    sch_fp = {kind: ("Gowuji:" + kind if kind in ("USB_C", "LDO", "S3")
                     else name) for kind, name in b.STOCK.items()}
    gen.put(out / "Gowuji-RevC.kicad_sch",
            gen.schematic("C", "Gowuji-RevC", loc, sch_fp))

    project = json.loads(
        (ROOT / "hardware/rev-b/Gowuji-RevB.kicad_pro").read_text())
    project["meta"]["filename"] = "Gowuji-RevC.kicad_pro"
    gen.put(out / "Gowuji-RevC.kicad_pro", json.dumps(project, indent=2) + "\n")
    print(out / "Gowuji-RevC.kicad_sch")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "hardware/rev-c")
    make(p.parse_args().out.resolve())


if __name__ == "__main__":
    main()
