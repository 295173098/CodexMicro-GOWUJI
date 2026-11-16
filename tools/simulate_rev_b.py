"""Check the Rev B schematic netlist; optionally reproduce the old USB input screen."""
import argparse
from itertools import product
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from simulate_preproduction import Spice, matrix_topology, read_nets


def check_nets(path):
    nets = read_nets(path)
    groups = {
        "VBUS": {
            "R16": (2,), "U3": (1,), "U5": (3,), "U6": (5,), "C10": (1,), "C14": (1,),
        },
        "VBUS_RAW": {"J2": ("A4", "A9", "B4", "B9"), "R16": (1,)},
        "VBUS_DAMP": {"C14": (2,), "R17": (1,)},
        "GND": {
            "J2": ("A1", "A12", "B1", "B12", "S1"), "U1": (57,), "U3": (2,),
            "U4": (2, 5), "U5": (1,), "U6": (2,), "R12": (2,), "R13": (2,),
            "C10": (2,), "R17": (2,), "C15": (2,),
        },
        "USB_P": {"J2": ("A6", "B6"), "U6": (3, 4), "R11": (1,)},
        "USB_N": {"J2": ("A7", "B7"), "U6": (1, 6), "R10": (1,)},
        "USB_P_MCU": {"R11": (2,), "U1": (26,)},
        "USB_N_MCU": {"R10": (2,), "U1": (25,)},
        "CC1": {"J2": ("A5",), "R12": (1,)},
        "CC2": {"J2": ("B5",), "R13": (1,)},
        "V3V3": {"U3": (3,), "U4": (1,), "U5": (2,), "C15": (1,)},
        "PDM_CLK": {"R8": (1,), "U4": (3,)},
        "PDM_DATA": {"R9": (2,), "U4": (4,)},
        "PDM_CLK_MCU": {"R8": (2,), "U1": (8,)},
        "PDM_DATA_MCU": {"R9": (1,), "U1": (49,)},
    }
    for name, refs in groups.items():
        for ref, pins in refs.items():
            for pin in pins:
                actual = nets.get((ref, str(pin)))
                if actual != name:
                    raise ValueError(f"{ref}.{pin}: expected {name}, found {actual}")
        if name in ("VBUS_RAW", "VBUS_DAMP"):
            expected = {(ref, str(pin)) for ref, pins in refs.items() for pin in pins}
            if {pad for pad, net in nets.items() if net == name} != expected:
                raise ValueError(f"Unexpected connection on {name}")
    values = {el.get("ref"): el.findtext("value") for el in ET.parse(path).findall("./components/comp")}
    for ref, expected in {"C10": "2.2u", "C14": "4.7u", "R12": "5.1k", "R13": "5.1k",
                          "R16": "0.82R", "R17": "1.5R"}.items():
        if values[ref].split()[0] != expected:
            raise ValueError(f"{ref}: expected {expected}, found {values[ref]}")
    return {"checked_schematic_nets": list(groups), "matrix": matrix_topology(nets)}


def sweep_input(spice, out):
    # C10+C14 total 5.7 uF nominal; lower effective capacitance allows DC-bias derating.
    # Source impedance and rise times are assumptions, not USB host specifications.
    corners = product((4.75, 5.25), (.22, .55), (.5, 1.5), (2.8, 5.7), (.02, .06), (1, 20))
    results = []
    worst_deck = None
    worst_peak = -1
    for v, r, l, cap, esr, tr in corners:
        deck = f"""GOWUJI Rev B passive VBUS input at hot plug (pre-layout)
Vhost host 0 PWL(0 0 {tr}u {v})
Rcable host line {r}
Lcable line bus {l}u
Rcap bus cap {esr}
Cinput cap 0 {cap}u
.tran 0.025u 100u 0 0.025u
.end
"""
        t, bus, current = spice.run(deck, "time", "v(bus)", "vhost#branch")
        if t[-1] < 99e-6 or not np.all(np.isfinite(bus)):
            raise RuntimeError("Incomplete ngspice transient")
        peak = float(bus.max())
        results.append(dict(source_V=v, series_ohm=r, series_uH=l, effective_uF=cap,
                            capacitor_esr_ohm=esr, source_rise_us=tr, peak_vbus_V=peak,
                            peak_source_A=float((-current).max()),
                            positive_charge_uC=float(np.trapezoid(np.maximum(-current, 0), t)*1e6)))
        if peak > worst_peak:
            worst_peak, worst_deck = peak, deck
    (out / "usb-passive-worst.cir").write_text(worst_deck, encoding="ascii")
    return {"cases": len(results), "over_6V_screen": sum(x["peak_vbus_V"] > 6 for x in results),
            "worst_vbus": max(results, key=lambda x: x["peak_vbus_V"]), "corners": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--netlist", required=True, type=Path)
    parser.add_argument("--legacy-ngspice", type=Path, help="Repeat the passive screen for the original pre-damping input only")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = check_nets(args.netlist)
    if args.legacy_ngspice:
        report["legacy_usb_passive_input"] = sweep_input(Spice(args.legacy_ngspice), args.out)
    (args.out / "screening.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if "legacy_usb_passive_input" in report:
        report["legacy_usb_passive_input"].pop("corners")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
