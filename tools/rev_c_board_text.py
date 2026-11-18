"""Apply the Rev C electrical and routing changes as S-expression text edits.

This is deliberately text-based: the KiCad Python bindings in this build become
unstable when nets, tracks and footprints are edited in one process.  The input
is the Rev B-derived Gowuji-RevC.kicad_pcb; the output is the same file.

Rev C (soft-start variant):
  * VBUS_LED branch: VBUS_RAW -> R18 1.0 ohm -> U3 VIN.
  * Damped LED input: C28 4.7 uF -> R20 2.2 ohm -> GND.
  * C14 4.7 uF -> 2.2 uF to keep the hot-plug charge within the 50 uC
    engineering reference; R17 1.5 ohm still damps VBUS.
  * U3 ON stays tied to V3V3.  C9 is changed from 4.7 nF to 47 nF so the
    TPS22918 CT ramp is about 129 ms (10-90% at 5 V), below the firmware's
    ~144 ms touch-calibration delay before the first pixel update.
  * L1 value 2.2 nH -> 1.8 nH (footprint and RF routing unchanged).
  * GND thermal vias around U5 and LED1.
"""
from __future__ import annotations

import argparse
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hardware as gen  # noqa: E402

BOARD = ROOT / "hardware/rev-c/Gowuji-RevC.kicad_pcb"
BLOCKS = ROOT / "build/rev-c/fp-blocks"


def blocks(text: str, tag: str):
    out = []
    for m in re.finditer(rf"\n\t\({tag}\b", text):
        start = m.start() + 1
        depth = 0
        i = start
        while i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    out.append((start, i + 1, text[start:i + 1]))
                    break
            i += 1
    return out


def find_fp(text: str, ref: str):
    marker = f'(property "Reference" "{ref}"'
    for start, end, block in blocks(text, "footprint"):
        if marker in block:
            return start, end, block
    raise ValueError(f"footprint {ref} not found")


def find_pad(fp: str, num: str):
    for m in re.finditer(rf'\n\t\t\(pad "{num}"', fp):
        start = m.start() + 1
        depth = 0
        i = start
        while i < len(fp):
            if fp[i] == "(":
                depth += 1
            elif fp[i] == ")":
                depth -= 1
                if depth == 0:
                    return fp[start:i + 1]
            i += 1
    raise ValueError(f"pad {num} not found")


def set_pad_net(fp: str, num: str, code: int, name: str):
    old = find_pad(fp, num)
    new = re.sub(r'\n\t\t\t\(net \d+ "[^"]+"\)', "", old)
    new = new.replace("\n\t\t\t(uuid ",
                      f'\n\t\t\t(net {code} "{name}")\n\t\t\t(uuid ', 1)
    return fp.replace(old, new, 1)


def regen_uuids(block: str):
    return re.sub(r'\(uuid "[^"]+"\)',
                  lambda _: f'(uuid "{uuid.uuid4()}")', block)


def fmt(v: float):
    return ("%.6f" % v).rstrip("0").rstrip(".")


def segment(a, b, width, layer, code):
    return (f"\t(segment\n"
            f"\t\t(start {fmt(a[0])} {fmt(a[1])})\n"
            f"\t\t(end {fmt(b[0])} {fmt(b[1])})\n"
            f"\t\t(width {fmt(width)})\n"
            f'\t\t(layer "{layer}")\n'
            f"\t\t(net {code})\n"
            f'\t\t(uuid "{uuid.uuid4()}")\n'
            f"\t)\n")


def via(at, code, diameter=0.6, drill=0.3):
    return (f"\t(via\n"
            f"\t\t(at {fmt(at[0])} {fmt(at[1])})\n"
            f"\t\t(size {fmt(diameter)})\n"
            f"\t\t(drill {fmt(drill)})\n"
            f'\t\t(layers "F.Cu" "B.Cu")\n'
            f"\t\t(net {code})\n"
            f'\t\t(uuid "{uuid.uuid4()}")\n'
            f"\t)\n")


def near(a, b, tol=0.02):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def delete_segments(text: str, specs):
    removed = 0
    for s, e, block in reversed(blocks(text, "segment")):
        sm = re.search(r'\(start\s+([-\d.]+)\s+([-\d.]+)\)', block)
        em = re.search(r'\(end\s+([-\d.]+)\s+([-\d.]+)\)', block)
        lm = re.search(r'\(layer "([^"]+)"\)', block)
        nm = re.search(r'\(net (\d+)\)', block)
        if not (sm and em and lm and nm):
            continue
        a = (float(sm.group(1)), float(sm.group(2)))
        b = (float(em.group(1)), float(em.group(2)))
        for net, layer, p, q in specs:
            if (lm.group(1) == layer and int(nm.group(1)) == net and
                    ((near(a, p) and near(b, q)) or
                     (near(a, q) and near(b, p)))):
                text = text[:s] + text[e:]
                removed += 1
                break
    return text, removed


def delete_vias(text: str, specs):
    removed = 0
    for s, e, block in reversed(blocks(text, "via")):
        am = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)\)', block)
        nm = re.search(r'\(net (\d+)\)', block)
        if not (am and nm):
            continue
        at = (float(am.group(1)), float(am.group(2)))
        for net, p in specs:
            if int(nm.group(1)) == net and near(at, p):
                text = text[:s] + text[e:]
                removed += 1
                break
    return text, removed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--board", type=Path, default=BOARD)
    args = p.parse_args()
    text = args.board.read_text()
    if '(property "Reference" "R18"' in text:
        raise ValueError("Board already has Rev C parts; use a fresh Rev B copy")

    # Net table: existing max is 98.
    text = text.replace('\t(net 98 "/VBUS_DAMP")\n',
                        '\t(net 98 "/VBUS_DAMP")\n'
                        '\t(net 99 "/VBUS_LED")\n'
                        '\t(net 100 "/LED_SNUB")\n', 1)
    text = text.replace('(rev "B")', '(rev "C")', 1)

    # U3 pin 1 -> VBUS_LED.  Pin 3 stays on V3V3 (ON tied high).
    u3_s, u3_e, u3 = find_fp(text, "U3")
    p1 = find_pad(u3, "1")
    p1 = re.sub(r'\(net \d+ "/VBUS"\)', '(net 99 "/VBUS_LED")', p1, 1)
    u3 = u3.replace(find_pad(u3, "1"), p1, 1)
    text = text[:u3_s] + u3 + text[u3_e:]

    # C9, C14 and L1 values only; footprints and RF routing stay unchanged.
    c9_s, c9_e, c9 = find_fp(text, "C9")
    c9 = c9.replace('"4.7n C0G"', '"47n C0G"', 1)
    text = text[:c9_s] + c9 + text[c9_e:]
    c14_s, c14_e, c14 = find_fp(text, "C14")
    c14 = c14.replace('"4.7u 16V"', '"2.2u 16V"', 1)
    text = text[:c14_s] + c14 + text[c14_e:]
    l1_s, l1_e, l1 = find_fp(text, "L1")
    l1 = l1.replace('"2.2nH RF tune"', '"1.8nH RF tune"', 1)
    text = text[:l1_s] + l1 + text[l1_e:]

    # Remove the old U3 VBUS stub and its now-dangling In2 branch.  The via at
    # (22.58, 19.94) would otherwise sit almost on the new VBUS_LED pad.
    specs = [(60, "F.Cu", (23.05, 19.18), (22.58, 19.94)),
             (60, "In2.Cu", (26.37, 16.15), (22.58, 19.94)),
             (60, "In2.Cu", (27.35, 16.15), (26.37, 16.15))]
    # Move the ENC_A through-via north out of the VBUS_LED channel.  Its old
    # B.Cu jog is replaced by one short segment to the existing diagonal.
    specs += [(10, "B.Cu", (22.2, 19.15), (22.2, 19.35)),
              (10, "B.Cu", (22.2, 19.35), (22.05, 19.5)),
              (10, "B.Cu", (22.05, 19.5), (22.05, 19.55)),
              (10, "B.Cu", (22.05, 19.55), (22.0, 19.6)),
              (10, "B.Cu", (22.0, 19.6), (22.0, 19.65)),
              (10, "B.Cu", (22.0, 19.65), (21.95, 19.7)),
              (10, "B.Cu", (21.95, 19.7), (21.95, 19.75)),
              (10, "In2.Cu", (22.45, 19.15), (22.2, 19.15))]
    text, removed = delete_segments(text, specs)
    if removed != 11:
        raise ValueError(f"expected 11 stub segments, removed {removed}")
    text, removed = delete_vias(text, [(60, (22.58, 19.94)),
                                       (10, (22.2, 19.15))])
    if removed != 2:
        raise ValueError(f"expected 2 stub vias, removed {removed}")

    r18 = (BLOCKS / "R18.txt").read_text()
    r18 = set_pad_net(r18, "1", 97, "/VBUS_RAW")
    r18 = set_pad_net(r18, "2", 99, "/VBUS_LED")

    c28 = (BLOCKS / "C28.txt").read_text()
    c28 = set_pad_net(c28, "1", 99, "/VBUS_LED")
    c28 = set_pad_net(c28, "2", 100, "/LED_SNUB")

    r20 = (BLOCKS / "R20.txt").read_text()
    r20 = set_pad_net(r20, "1", 100, "/LED_SNUB")
    r20 = set_pad_net(r20, "2", 12, "/GND")

    new = []
    # VBUS_RAW: R16.1 up to y=10.0 (above the GND via at 14.95, 11.0), west
    # on B.Cu, down the left edge, then to R18.1.
    new.append(segment((22.788, 11.5), (22.788, 10.0), 0.32, "B.Cu", 97))
    new.append(segment((22.788, 10.0), (2.0, 10.0), 0.32, "B.Cu", 97))
    new.append(segment((2.0, 10.0), (2.0, 18.0), 0.32, "B.Cu", 97))
    new.append(via((2.0, 18.0), 97))
    new.append(segment((2.0, 18.0), (3.5375, 18.0), 0.32, "F.Cu", 97))

    # VBUS_LED: R18.2 and C28.1 join on the y=19.0 channel, then run east to
    # U3.1 between C9 (bottom 18.475) and D14 (top 19.85).
    new.append(segment((6.4625, 18.0), (6.4625, 19.0), 0.32, "F.Cu", 99))
    new.append(segment((5.0, 20.1), (5.0, 19.0), 0.32, "F.Cu", 99))
    new.append(segment((5.0, 19.0), (6.4625, 19.0), 0.32, "F.Cu", 99))
    new.append(segment((6.4625, 19.0), (23.05, 19.0), 0.32, "F.Cu", 99))
    new.append(segment((23.05, 19.0), (23.05, 19.18), 0.32, "F.Cu", 99))

    # Damped LED input: C28.2 -> R20.1, R20.2 -> GND.
    new.append(segment((5.0, 22.9), (6.8375, 22.9), 0.32, "F.Cu", 100))
    new.append(segment((6.8375, 22.9), (6.8375, 21.5), 0.32, "F.Cu", 100))
    new.append(segment((9.7625, 21.5), (9.7625, 23.1), 0.32, "F.Cu", 12))
    new.append(via((9.7625, 23.1), 12))

    # ENC_A: moved through-via north of the VBUS_LED channel and clear of the
    # In2 V3V3 diagonal.
    new.append(via((22.2, 19.7), 10))
    new.append(segment((22.2, 19.7), (21.95, 19.75), 0.2, "B.Cu", 10))
    new.append(segment((22.45, 19.15), (22.2, 19.7), 0.2, "In2.Cu", 10))

    # GND thermal vias around U5 and LED1 (target effective k_xy >= 20 W/mK).
    for at in [(37.3, 15.5), (38.1, 15.5), (38.9, 15.5),
               (28.5, 22.0), (28.5, 25.0), (31.0, 27.0),
               (32.5, 25.5), (33.5, 26.0), (35.5, 26.0), (36.5, 26.0)]:
        new.append(via(at, 12))

    pos = text.rfind("\n)")
    text = text[:pos] + "\n" + "".join(new) + r18 + "\n" + c28 + "\n" + r20 + "\n" + text[pos:]
    args.board.write_text(text)
    print(args.board)


if __name__ == "__main__":
    main()
