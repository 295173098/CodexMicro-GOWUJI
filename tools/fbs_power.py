#!/usr/bin/env python3
"""Board-level DC IR-drop and PDN impedance for the Rev B power tree.

IR-drop model:
  * copper tracks, vias and pads of VBUS_RAW/VBUS/LED_5V/V3V3/RF_3V3
  * series components R16 (0.82 ohm), R17 (1.5 ohm, capacitor branch, no DC),
    L2 ferrite bead DCR and U3 load-switch Ron
  * source at USB-C VBUS; LDO output treated as the 3.3 V source
  * loads distributed from the ngspice operating scenarios

PDN model:
  * 3.3 V rail: LDO closed-loop source impedance, bulk/decoupling capacitors,
    trace spreading inductance and plane capacitance
  * 5 V LED rail: load switch, 47 uF bulk, 100 nF local capacitors.  R18 and
    C28 are upstream of U3 and do not load the LED_5V output PDN directly.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/full-board-sim"

RHO_CU = 1.72e-8
T_OUTER = 35e-6
T_INNER = 15.2e-6
COPPER = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")
LAYER_T = {"F.Cu": T_OUTER, "B.Cu": T_OUTER, "In1.Cu": T_INNER, "In2.Cu": T_INNER}
BOARD_T = 1.6e-3
BARREL_T = 25e-6


def layer_thickness(layer: str) -> float:
    return LAYER_T.get(layer, T_OUTER)


def via_resistance(drill_mm: float) -> float:
    r = drill_mm * 1e-3 / 2
    area = 2 * math.pi * r * BARREL_T
    return RHO_CU * BOARD_T / area if area > 0 else 1e-3


def node_key(x: float, y: float, layer: str, net: str):
    # Keep nets separate: two nets must never merge just because their copper
    # happens to pass through the same coordinate.
    return (round(x, 3), round(y, 3), layer, str(net))


def pad_layers(pad: dict):
    layers = pad.get("layers") or []
    if "*.Cu" in layers:
        return list(COPPER)
    return [l for l in layers if l in COPPER]


def add_node(nodes, key):
    if key not in nodes:
        nodes[key] = len(nodes)
    return nodes[key]


def build_graph(board: dict, net_ids: set[str], extra_edges=None):
    """Build a resistive graph for the given nets plus optional component edges."""
    nodes = {}
    edges = []  # (node_a, node_b, R_ohm, label)
    net_ids = {str(n) for n in net_ids}

    # Tracks
    for s in board["segments"]:
        if s["net"] not in net_ids or s["layer"] not in COPPER:
            continue
        a = node_key(s["x1"], s["y1"], s["layer"], s["net"])
        b = node_key(s["x2"], s["y2"], s["layer"], s["net"])
        ia, ib = add_node(nodes, a), add_node(nodes, b)
        length = math.hypot(s["x2"] - s["x1"], s["y2"] - s["y1"])
        area = s["w"] * layer_thickness(s["layer"])
        r = RHO_CU * (length * 1e-3) / area if area > 0 else 1e-3
        edges.append((ia, ib, r, f"track {s['layer']} {s['w']}mm"))

    # Vias
    for v in board["vias"]:
        if v["net"] not in net_ids:
            continue
        layers = [l for l in v["layers"] if l in COPPER] or list(COPPER)
        if len(layers) == 2 and set(layers) == {"F.Cu", "B.Cu"}:
            layers = list(COPPER)
        idx = []
        for l in layers:
            idx.append(add_node(nodes, node_key(v["x"], v["y"], l, v["net"])))
        rv = via_resistance(v["drill"])
        for a, b in zip(idx, idx[1:]):
            edges.append((a, b, rv, f"via {v['drill']}mm"))

    # Pads: add node(s) and connect to nearest track/via node on the same layer.
    pad_nodes = {}
    for p in board["pads"]:
        if p["net"] not in net_ids:
            continue
        for l in pad_layers(p):
            key = node_key(p["x"], p["y"], l, p["net"])
            idx = add_node(nodes, key)
            pad_nodes.setdefault((p["ref"], p["num"]), []).append(idx)
            # Nearest existing node of the same net on this layer within a
            # pad-sized radius.
            best = None
            best_d = 1e9
            for (x, y, lay, net), j in nodes.items():
                if lay != l or net != p["net"] or j == idx:
                    continue
                d = math.hypot(x - p["x"], y - p["y"])
                if d < best_d:
                    best_d, best = d, j
            if best is not None and best_d <= max(p["w"], p["h"], 0.5) + 0.25:
                edges.append((idx, best, 2e-4, f"pad {p['ref']}.{p['num']}"))

    # Optional series component edges: (ref1,pin1,ref2,pin2,R)
    if extra_edges:
        for r1, n1, r2, n2, r, label in extra_edges:
            a = pad_nodes.get((r1, n1))
            b = pad_nodes.get((r2, n2))
            if not a or not b:
                raise RuntimeError(f"missing pad for {label}: {r1}.{n1} / {r2}.{n2}")
            edges.append((a[0], b[0], r, label))

    return nodes, edges, pad_nodes


def solve_ir(nodes, edges, pad_nodes, source_pad, loads, source_voltage=0.0):
    """Solve G V = I with the source node fixed; loads are currents drawn.

    Only the connected component containing the source is solved; pads outside
    it are reported as unconnected rather than making the matrix singular.
    """
    from scipy.sparse.csgraph import connected_components

    n = len(nodes)
    rows, cols, vals = [], [], []
    for a, b, r, _ in edges:
        g = 1.0 / max(r, 1e-9)
        rows += [a, b, a, b]
        cols += [a, b, b, a]
        vals += [g, g, -g, -g]
    G = coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsr()

    src_list = pad_nodes[source_pad]
    src = src_list[0]
    ncomp, labels = connected_components(G, directed=False)
    mask = labels == labels[src]
    keep = np.flatnonzero(mask)
    remap = {int(old): i for i, old in enumerate(keep)}

    I = np.zeros(len(keep))
    unconnected = []
    for pad, current in loads.items():
        for idx in pad_nodes[pad]:
            if mask[idx]:
                I[remap[int(idx)]] -= current
            else:
                unconnected.append(f"{pad[0]}.{pad[1]}")

    Gsub = G[keep][:, keep].tocsc()
    src_sub = remap[int(src)]
    free = np.ones(len(keep), dtype=bool)
    free[src_sub] = False
    Gff = Gsub[free][:, free]
    if source_voltage == 0.0:
        rhs = I[free]
    else:
        rhs = I[free] - np.asarray(Gsub[free][:, src_sub].todense()).ravel() * source_voltage
    Vf = spsolve(Gff, rhs)
    V = np.full(n, np.nan)
    V[keep] = 0.0
    V[keep[free]] = Vf
    V[src] = source_voltage
    return V, src, unconnected


def path_resistance(nodes, edges, src, dst):
    g = nx.Graph()
    for a, b, r, label in edges:
        if g.has_edge(a, b):
            if r < g[a][b]["r"]:
                g[a][b].update(r=r, label=label)
        else:
            g.add_edge(a, b, r=r, label=label)
    try:
        return nx.shortest_path_length(g, src, dst, weight="r")
    except nx.NetworkXNoPath:
        return float("inf")


def ir_drop(out: Path = OUT, r16: float = 0.82, r18: float = 1.0):
    board = json.loads((out / "board.json").read_text())
    # Net names from the extracted board.
    nets = board["nets"]
    ids = {name.lstrip("/"): name for name in nets.values()}
    rev_c = "VBUS_LED" in ids
    n_vbus_raw = ids["VBUS_RAW"]
    n_vbus = ids["VBUS"]
    n_vbus_led = ids.get("VBUS_LED")
    n_led = ids["LED_5V"]
    n_v3 = ids["V3V3"]
    n_rf = ids["RF_3V3"]

    # Power tree graph: USB-C -> R16 -> VBUS (LDO); Rev C adds USB-C -> R18 ->
    # VBUS_LED -> U3 -> LED_5V.  V3V3/RF_3V3 are fed by U5, joined at L2.
    all_ids = {n_vbus_raw, n_vbus, n_led, n_v3, n_rf}
    extra = [
        ("R16", "1", "R16", "2", r16, f"R16 {r16}R"),
        ("U3", "1", "U3", "6", 0.050, "U3 TPS22918 Ron"),
        ("L2", "1", "L2", "2", 0.35, "L2 BLM18PG221 DCR"),
        ("U2", "5", "U3", "6", 0.010, "U2 VCC stub"),
    ]
    if rev_c:
        all_ids.add(n_vbus_led)
        extra.insert(1, ("R18", "1", "R18", "2", r18, f"R18 {r18}R"))
    nodes, edges, pad_nodes = build_graph(board, all_ids, extra)

    # Load allocation (A). Worst case follows the 582 mA unrestricted BLE
    # stress: core 450 mA, RF 130 mA, LEDs 60 mA, translator 5 mA, mic 2 mA.
    # The 5 V VBUS current is computed from the 3.3 V loads through the LDO.
    loads_v3 = {
        ("U1", "20"): 0.225,
        ("U1", "46"): 0.225,
        ("U4", "1"): 0.002,
    }
    loads_rf = {
        ("U1", "2"): 0.0325,
        ("U1", "3"): 0.0325,
        ("U1", "55"): 0.0325,
        ("U1", "56"): 0.0325,
    }
    led_current = 0.060 / 6
    loads_led = {(f"LED{i}", "1"): led_current for i in range(1, 7)}
    loads_led[("U2", "5")] = 0.005
    v3_total = sum(loads_v3.values()) + sum(loads_rf.values())
    # LDO input current = 3.3 V load / (5 V * 0.9).
    vbus_ldo = v3_total * 3.3 / (5.0 * 0.90)
    loads_vbus = {
        ("U5", "3"): vbus_ldo,
        ("U6", "5"): 0.001,
    }
    led_rail_total = sum(loads_led.values())

    # Two separate 3.3 V/5 V source trees: solve VBUS/RAW/LED with source at
    # J2.A4, and V3V3/RF with source at U5.2.  The graph is shared, but the
    # source differs; solve once with the USB source and once with the LDO.
    results = {}
    V_usb, src_usb, un_usb = solve_ir(nodes, edges, pad_nodes, ("J2", "A4"),
                                     {**loads_vbus, **loads_led})
    probes = [("J2.A4 VBUS_RAW", ("J2", "A4")),
              ("U5.3 LDO in", ("U5", "3")),
              ("U3.1 LED switch in", ("U3", "1")),
              ("U3.6 LED rail", ("U3", "6"))]
    if rev_c:
        probes.insert(1, ("R18.1 VBUS_RAW", ("R18", "1")))
    for label, pad in probes:
        idx = pad_nodes[pad][0]
        results[label] = {"V": float(V_usb[idx]),
                          "drop_mV": float(-V_usb[idx] * 1000)}
    for i in range(1, 7):
        idx = pad_nodes[(f"LED{i}", "1")][0]
        results[f"LED{i}.1"] = {"V": float(V_usb[idx]),
                                "drop_mV": float(-V_usb[idx] * 1000)}
    idx = pad_nodes[("U2", "5")][0]
    results["U2.5 level VCC"] = {"V": float(V_usb[idx]),
                                 "drop_mV": float(-V_usb[idx] * 1000)}

    V_3v3, src_3v3, un_3v3 = solve_ir(nodes, edges, pad_nodes, ("U5", "2"),
                                     {**loads_v3, **loads_rf})
    for label, pad in (("U5.2 LDO out", ("U5", "2")),
                       ("U1.20 core 3V3", ("U1", "20")),
                       ("U1.46 core 3V3", ("U1", "46")),
                       ("U1.2 RF 3V3", ("U1", "2")),
                       ("U1.3 RF 3V3", ("U1", "3")),
                       ("U1.55 RF 3V3", ("U1", "55")),
                       ("U1.56 RF 3V3", ("U1", "56")),
                       ("U4.1 mic VDD", ("U4", "1"))):
        idx = pad_nodes[pad][0]
        results[label] = {"V": float(V_3v3[idx]),
                          "drop_mV": float(-V_3v3[idx] * 1000)}

    # Path resistance from the LDO to the worst core pin and RF pin.
    core_idx = pad_nodes[("U1", "20")][0]
    rf_idx = pad_nodes[("U1", "2")][0]
    results["path_R_LDO_to_U1_20_mohm"] = path_resistance(
        nodes, edges, src_3v3, core_idx) * 1000
    results["path_R_LDO_to_U1_2_mohm"] = path_resistance(
        nodes, edges, src_3v3, rf_idx) * 1000
    results["path_R_USB_to_U5_mohm"] = path_resistance(
        nodes, edges, src_usb, pad_nodes[("U5", "3")][0]) * 1000

    # GND plane upper bound: total return current through the plane stack.
    # The plane is continuous on In1/In2 and stitched by vias; a conservative
    # spreading estimate is 1 mOhm per square over a 95 mm path.
    results["GND_plane_estimate_mV"] = (vbus_ldo + led_rail_total + 0.001) * 1.0 * (95 / 95)

    # Actual rail voltages at the USB host limits.  USB 2.0 allows 4.75-5.25 V
    # at the host; the board sees the drop through the connector, R16 and R18.
    drops = {
        "U5_in": -results["U5.3 LDO in"]["V"],
        "U3_in": -results["U3.1 LED switch in"]["V"],
        "LED": -results["LED1.1"]["V"],
    }
    source_cases = {}
    for label, vbus in (("4.75V host", 4.75), ("5.00V host", 5.00),
                        ("5.25V host", 5.25)):
        source_cases[label] = {
            "VBUS_at_U5_V": vbus - drops["U5_in"],
            "VBUS_LED_at_U3_V": vbus - drops["U3_in"],
            "LED_rail_V": vbus - drops["LED"],
            "LDO_input_ok": (vbus - drops["U5_in"]) >= 3.8,
            "LED_ok": (vbus - drops["LED"]) >= 4.5,
        }

    summary = {
        "loads": {
            "V3V3_total_mA": v3_total * 1000,
            "RF_total_mA": sum(loads_rf.values()) * 1000,
            "LED_total_mA": 60.0,
            "LED_rail_total_mA": led_rail_total * 1000,
            "VBUS_ldo_mA": vbus_ldo * 1000,
            "VBUS_RAW_total_mA": (vbus_ldo + led_rail_total + 0.001) * 1000,
        },
        "results": results,
        "source_cases": source_cases,
        "criteria": {
            "V3V3_U1_min_V": 3.0,
            "LDO_input_min_V": 3.8,
            "LED_min_V": 4.5,
        },
        "graph": {"nodes": len(nodes), "edges": len(edges)},
        "R16_ohm": r16,
        "R18_ohm": r18,
        "unconnected_loads": sorted(set(un_usb + un_3v3)),
    }
    (out / "ir_drop.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


# ---------------------------------------------------------------- PDN
def pdn(out: Path = OUT):
    """Lumped PDN impedance for the 3.3 V and 5 V rails.

    The model is a ladder of series R/L and shunt R/C elements from the
    regulator/load-switch to the load.  Capacitor values use the effective
    DC-bias values documented in docs/rev-b-component-review.md.
    """
    # 3.3 V rail: LDO -> trace -> U1.  Effective capacitance at 3.3 V:
    # C15 22 uF -> 10 uF, C25/C27 1 uF -> 0.6 uF each, C16/C26 100 nF,
    # C11/C12 100 nF/1 uF at the microphone, C13 1 uF near EN.
    f = np.logspace(2, 8, 1200)
    w = 2 * np.pi * f

    def shunt_cap(c, esr=5e-3, esl=0.5e-9):
        z = esr + 1j * w * esl + 1 / (1j * w * c)
        return 1 / z

    def series_rl(r, l):
        return r + 1j * w * l

    # LDO closed-loop output impedance: 50 mOhm up to ~50 kHz, rising above.
    # Model as a 50 mOhm resistor in parallel with a 1 uH inductor.
    z_ldo = 1 / (1 / 0.05 + 1 / (1j * w * 1e-6))
    # Trace from U5 to U1: 138 mm of 0.35 mm copper, ~0.35 nH/mm.
    z_trace = series_rl(0.012, 138e-3 * 0.35e-9)
    # Bulk + local caps at the load.
    y_load = (shunt_cap(10e-6, 8e-3, 1.0e-9) + shunt_cap(0.6e-6, 5e-3, 0.6e-9)
              + shunt_cap(0.6e-6, 5e-3, 0.6e-9) + shunt_cap(100e-9, 4e-3, 0.5e-9)
              + shunt_cap(100e-9, 4e-3, 0.5e-9) + shunt_cap(100e-9, 4e-3, 0.5e-9)
              + shunt_cap(1e-6, 5e-3, 0.7e-9) + shunt_cap(1e-6, 5e-3, 0.7e-9))
    # Plane capacitance of the 3.3 V traces over In1 GND (small).
    y_load += 1j * w * 18e-12
    z3 = 1 / (1 / (z_ldo + z_trace) + y_load)

    # 5 V LED rail: U3 Ron 50 mOhm, C8 47 uF (effective 30 uF at 5 V),
    # six 100 nF local caps.
    z_sw = 0.05 + 1j * w * 0.2e-9
    z_led_trace = series_rl(0.02, 164e-3 * 0.35e-9)
    y_led = (shunt_cap(30e-6, 8e-3, 1.0e-9) + 6 * shunt_cap(100e-9, 4e-3, 0.5e-9))
    z5 = 1 / (1 / (z_sw + z_led_trace) + y_led)

    def band_stats(z):
        bands = [(1e3, 1e5), (1e5, 1e6), (1e6, 1e7), (1e7, 1e8)]
        out = {}
        for lo, hi in bands:
            m = (f >= lo) & (f < hi)
            out[f"{lo:.0e}-{hi:.0e}"] = {
                "max_ohm": float(np.max(np.abs(z[m]))),
                "fmax_Hz": float(f[m][np.argmax(np.abs(z[m]))]),
            }
        return out

    # Target impedance for a 500 mA step with 50 mV droop: 0.1 ohm.
    summary = {
        "model": "lumped RLC ladder; not a full-wave cavity model",
        "target_ohm": 0.1,
        "v3v3": band_stats(z3),
        "led5v": band_stats(z5),
        "min_z_v3v3_ohm": float(np.min(np.abs(z3))),
        "min_z_led_ohm": float(np.min(np.abs(z5))),
        "assumptions": {
            "C15_eff_uF": 10.0, "C25_C27_eff_uF": 0.6,
            "C8_eff_uF": 30.0, "LDO_Rout_mOhm": 50.0,
            "trace_L_nH_per_mm": 0.35,
            "R18_ohm": 1.0, "C28_eff_uF": 4.7,
            "note": "R18/C28 are upstream of U3; LED_5V PDN is measured at U3 output",
        },
    }
    (out / "pdn.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["ir", "pdn", "all"])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--r16", type=float, default=0.82)
    ap.add_argument("--r18", type=float, default=1.0)
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.stage in ("ir", "all"):
        if args.sweep:
            sweep = {}
            for r in (0.82, 0.47, 0.33, 0.25):
                s = ir_drop(args.out, r)
                sweep[f"{r:.2f}"] = {
                    "source_cases": s["source_cases"],
                    "VBUS_total_mA": s["loads"]["VBUS_total_mA"],
                }
            (args.out / "ir_drop_sweep.json").write_text(
                json.dumps(sweep, ensure_ascii=False, indent=1))
            print(json.dumps(sweep, ensure_ascii=False, indent=1))
        else:
            print(json.dumps(ir_drop(args.out, args.r16, args.r18), ensure_ascii=False, indent=1))
    if args.stage in ("pdn", "all"):
        print(json.dumps(pdn(args.out), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
