#!/usr/bin/env python3
"""Full-board simulation toolkit for the Rev B PCB.

Stages:
  extract  - parse the KiCad board into JSON geometry and net data
  irdrop   - DC IR-drop on rasterized copper for VBUS/V3V3/GND
  pdn      - AC PDN impedance and plane-pair cavity model
  thermal  - 3D thermal FEA of the board + enclosure
  usb      - USB 2.0 full-speed SI (transmission line + eye)
  rf       - 2.4 GHz RF trace transmission-line check
  report   - compile all results into a Markdown report

The models are deliberately explicit about assumptions; they are engineering
screening models, not a substitute for fabrication TDR or first-article tests.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware/rev-b/Gowuji-RevB.kicad_pcb"
OUT = ROOT / "build/full-board-sim"

# Copper resistivity (Ohm*m) at 20 C.
RHO_CU = 1.72e-8
# Finished copper thickness from the JLC04161H-3313 stackup.
T_OUTER = 35e-6
T_INNER = 15.2e-6


# ---------------------------------------------------------------- S-expression
def parse_sexp(text: str):
    """Parse a KiCad S-expression into nested Python lists."""
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', text)
    stack = [[]]
    for tok in tokens:
        if tok == "(":
            node = []
            stack[-1].append(node)
            stack.append(node)
        elif tok == ")":
            if len(stack) == 1:
                raise ValueError("unbalanced ')'")
            stack.pop()
        elif tok.startswith('"') and tok.endswith('"'):
            stack[-1].append(tok[1:-1].replace('\\"', '"'))
        else:
            stack[-1].append(tok)
    if len(stack) != 1:
        raise ValueError("unbalanced '('")
    return stack[0]


def child(node, name):
    for item in node:
        if isinstance(item, list) and item and item[0] == name:
            return item
    return None


def children(node, name):
    return [item for item in node if isinstance(item, list) and item and item[0] == name]


def atom(node, name, index=1, default=None):
    item = child(node, name)
    if item is None or len(item) <= index:
        return default
    return item[index]


def fnum(node, name, index=1, default=0.0):
    v = atom(node, name, index, None)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- board parse
def parse_board(path: Path = BOARD) -> dict:
    text = path.read_text(encoding="utf-8")
    root = parse_sexp(text)
    if not root or root[0][0] != "kicad_pcb":
        raise ValueError("not a kicad_pcb file")
    kicad = root[0]

    nets = {}
    for n in children(kicad, "net"):
        if len(n) >= 3:
            nets[str(n[1])] = str(n[2])

    stackup = []
    st = child(kicad, "stackup")
    if st:
        for layer in children(st, "layer"):
            name = atom(layer, "layer", 1, "")
            typ = atom(layer, "type", 1, "")
            thickness = fnum(layer, "thickness", 1, 0.0)
            material = atom(layer, "material", 1, "")
            er = fnum(layer, "epsilon_r", 1, 0.0)
            loss = fnum(layer, "loss_tangent", 1, 0.0)
            stackup.append({
                "name": name, "type": typ, "thickness_mm": thickness,
                "material": material, "er": er, "loss_tangent": loss,
            })

    footprints = []
    pads = []
    for fp in children(kicad, "footprint"):
        ref = ""
        value = ""
        for prop in children(fp, "property"):
            if len(prop) >= 3 and prop[1] == "Reference":
                ref = prop[2]
            elif len(prop) >= 3 and prop[1] == "Value":
                value = prop[2]
        fp_at = child(fp, "at")
        fx = float(fp_at[1]) if fp_at else 0.0
        fy = float(fp_at[2]) if fp_at else 0.0
        frot = float(fp_at[3]) if fp_at and len(fp_at) > 3 else 0.0
        layer = atom(fp, "layer", 1, "")
        fp_name = fp[1] if len(fp) > 1 else ""
        fp_pads = []
        for pad in children(fp, "pad"):
            pnum = pad[1] if len(pad) > 1 else ""
            ptype = pad[2] if len(pad) > 2 else ""
            pshape = pad[3] if len(pad) > 3 else ""
            pat = child(pad, "at")
            px = float(pat[1]) if pat else 0.0
            py = float(pat[2]) if pat else 0.0
            prot = float(pat[3]) if pat and len(pat) > 3 else 0.0
            size = child(pad, "size")
            sx = float(size[1]) if size else 0.0
            sy = float(size[2]) if size else 0.0
            drill = child(pad, "drill")
            dvals = []
            if drill:
                for v in drill[1:]:
                    try:
                        dvals.append(float(v))
                    except (TypeError, ValueError):
                        pass
            dx = dvals[0] if dvals else 0.0
            dy = dvals[1] if len(dvals) > 1 else dx
            net = child(pad, "net")
            nid = str(net[1]) if net else "0"
            nname = str(net[2]) if net and len(net) > 2 else nets.get(nid, "")
            layers = child(pad, "layers")
            player = [x for x in layers[1:] if isinstance(x, str)] if layers else []
            # Absolute pad position: footprint placement + pad offset (rotated).
            th = math.radians(frot)
            ax = fx + px * math.cos(th) - py * math.sin(th)
            ay = fy + px * math.sin(th) + py * math.cos(th)
            p = {
                "ref": ref, "value": value, "fp": fp_name, "layer": layer,
                "num": pnum, "type": ptype, "shape": pshape,
                "x": ax, "y": ay, "rot": prot + frot,
                "w": sx, "h": sy, "drill": max(dx, dy),
                "net": nid, "net_name": nname, "layers": player,
            }
            fp_pads.append(p)
            pads.append(p)
        footprints.append({
            "ref": ref, "value": value, "fp": fp_name, "layer": layer,
            "x": fx, "y": fy, "rot": frot, "pads": fp_pads,
        })

    segments = []
    for seg in children(kicad, "segment"):
        s = child(seg, "start")
        e = child(seg, "end")
        net = child(seg, "net")
        segments.append({
            "x1": float(s[1]), "y1": float(s[2]),
            "x2": float(e[1]), "y2": float(e[2]),
            "w": fnum(seg, "width", 1, 0.0),
            "layer": atom(seg, "layer", 1, ""),
            "net": str(net[1]) if net else "0",
        })

    vias = []
    for via in children(kicad, "via"):
        at = child(via, "at")
        net = child(via, "net")
        layers = child(via, "layers")
        vias.append({
            "x": float(at[1]), "y": float(at[2]),
            "size": fnum(via, "size", 1, 0.0),
            "drill": fnum(via, "drill", 1, 0.0),
            "net": str(net[1]) if net else "0",
            "layers": [x for x in layers[1:] if isinstance(x, str)] if layers else [],
        })

    zones = []
    for zone in children(kicad, "zone"):
        net = child(zone, "net")
        nname = atom(zone, "net_name", 1, "")
        zlayers = []
        lyr = child(zone, "layer")
        if lyr:
            zlayers.append(lyr[1])
        layers_node = child(zone, "layers")
        if layers_node:
            zlayers.extend(x for x in layers_node[1:] if isinstance(x, str))
        polys = []
        for fp in children(zone, "filled_polygon"):
            pts = child(fp, "pts")
            if not pts:
                continue
            poly = []
            for xy in children(pts, "xy"):
                poly.append((float(xy[1]), float(xy[2])))
            if poly:
                polys.append({"layer": atom(fp, "layer", 1, zlayers[0] if zlayers else ""),
                              "points": poly})
        zones.append({
            "net": str(net[1]) if net else "0",
            "net_name": nname,
            "layers": zlayers,
            "polygons": polys,
        })

    return {
        "path": str(path),
        "nets": nets,
        "stackup": stackup,
        "footprints": footprints,
        "pads": pads,
        "segments": segments,
        "vias": vias,
        "zones": zones,
    }


# ---------------------------------------------------------------- summary
def summarize(board: dict) -> dict:
    net_names = board["nets"]
    seg_by_net = defaultdict(lambda: {"count": 0, "length_mm": 0.0, "widths": Counter()})
    for s in board["segments"]:
        d = math.hypot(s["x2"] - s["x1"], s["y2"] - s["y1"])
        rec = seg_by_net[s["net"]]
        rec["count"] += 1
        rec["length_mm"] += d
        rec["widths"][s["w"]] += 1
    via_by_net = Counter(v["net"] for v in board["vias"])
    pads_by_net = Counter(p["net"] for p in board["pads"])

    interesting = {}
    for nid, name in net_names.items():
        if not name:
            continue
        key = name.lstrip("/")
        if re.search(r"(VBUS|V3V3|GND|USB|RF|LED|VLED|3V3)", key, re.I):
            rec = seg_by_net.get(nid, {"count": 0, "length_mm": 0.0, "widths": Counter()})
            interesting[key] = {
                "net_id": nid,
                "segments": rec["count"],
                "length_mm": round(rec["length_mm"], 3),
                "widths_mm": {str(k): v for k, v in sorted(rec["widths"].items())},
                "vias": via_by_net.get(nid, 0),
                "pads": pads_by_net.get(nid, 0),
            }

    refs = {}
    for fp in board["footprints"]:
        if fp["ref"]:
            refs[fp["ref"]] = {
                "value": fp["value"], "fp": fp["fp"],
                "x": fp["x"], "y": fp["y"], "layer": fp["layer"],
            }

    return {
        "nets": len(net_names),
        "footprints": len(board["footprints"]),
        "pads": len(board["pads"]),
        "segments": len(board["segments"]),
        "vias": len(board["vias"]),
        "zones": len(board["zones"]),
        "interesting_nets": interesting,
        "refs": refs,
        "stackup": board["stackup"],
    }


def extract(out: Path = OUT) -> dict:
    board = parse_board()
    summary = summarize(board)
    out.mkdir(parents=True, exist_ok=True)
    (out / "board.json").write_text(json.dumps(board, ensure_ascii=False, indent=1))
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["extract"])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    if args.stage == "extract":
        s = extract(args.out)
        print(json.dumps(s, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
