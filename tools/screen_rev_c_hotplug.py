"""Rev C hot-plug screen: VBUS_RAW -> R16/R18 -> VBUS/VBUS_LED.

Behavioral passive model.  U3 is off during the first 100 us, so C8 on the
LED_5V rail is isolated; the host sees C28 plus the existing VBUS capacitors.
"""
from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path

import numpy as np
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate_preproduction import Spice  # noqa: E402


def deck(v, cable, cable_uh, rise_us, r16, r18, r20, c10, c14, c28, esr10, esr14):
    return f"""Rev C passive hot-plug screen
Vhost host 0 PWL(0 0 {rise_us}u {v})
Rcable host connector {cable}
Lcable connector raw {cable_uh}u
R16 raw bus {r16}
R18 raw vled {r18}
R17 bus damp 1.5
R10 bus c10 {esr10}
R14 damp c14 {esr14}
C10 c10 0 {c10}u
C14 c14 0 {c14}u
R20 vled c28 {r20}
C28 c28 0 {c28}u
.tran 0.05u 100u 0 0.05u
.end
"""


def run(spice, out):
    rows = []
    for v, cable, luh, rise, r16, r18, r20, c10, c14, c28, esr10, esr14 in product(
            (4.75, 5.25), (0.08, 0.10, 0.22, 0.55), (0.5, 1.5, 2.0, 2.8),
            (0.1, 1, 20), (0.779, 0.861), (0.95, 1.05), (2.09, 2.31),
            (2.0, 2.2), (2.2,), (4.7,), (0.02, 0.06), (0.02, 0.06)):
        circuit = deck(v, cable, luh, rise, r16, r18, r20, c10, c14, c28, esr10, esr14)
        t, raw, bus, vled, c28n, host = spice.run(
            circuit, "time", "v(connector)", "v(bus)", "v(vled)", "v(c28)", "vhost#branch")
        if t[-1] < 99e-6 or not all(np.all(np.isfinite(a)) for a in (raw, bus, vled, c28n, host)):
            raise RuntimeError(f"invalid transient: {v,cable,luh,rise,r16,r18,r20,c10,c14,c28}")
        i_r18 = (raw - vled) / r18
        p_r18 = i_r18 ** 2 * r18
        i_r20 = (vled - c28n) / r20
        p_r20 = i_r20 ** 2 * r20
        rows.append(dict(
            host_V=v, cable_ohm=cable, cable_uH=luh, rise_us=rise,
            r16_ohm=r16, r18_ohm=r18, r20_ohm=r20,
            c10_uF=c10, c14_uF=c14, c28_uF=c28,
            raw_peak_V=float(raw.max()), bus_peak_V=float(bus.max()),
            vled_peak_V=float(vled.max()),
            host_peak_A=float((-host).max()),
            charge_uC=float(np.trapezoid(np.maximum(-host, 0), t) * 1e6),
            r18_peak_W=float(p_r18.max()),
            r18_energy_uJ=float(np.trapezoid(p_r18, t) * 1e6),
            r20_peak_W=float(p_r20.max()),
            r20_energy_uJ=float(np.trapezoid(p_r20, t) * 1e6),
        ))
    result = dict(
        cases=len(rows),
        max_raw=float(max(r["raw_peak_V"] for r in rows)),
        max_bus=float(max(r["bus_peak_V"] for r in rows)),
        max_vled=float(max(r["vled_peak_V"] for r in rows)),
        max_charge_uC=float(max(r["charge_uC"] for r in rows)),
        max_host_A=float(max(r["host_peak_A"] for r in rows)),
        max_r18_W=float(max(r["r18_peak_W"] for r in rows)),
        max_r18_uJ=float(max(r["r18_energy_uJ"] for r in rows)),
        max_r20_W=float(max(r["r20_peak_W"] for r in rows)),
        max_r20_uJ=float(max(r["r20_energy_uJ"] for r in rows)),
        worst_vled=max(rows, key=lambda r: r["vled_peak_V"]),
        worst_charge=max(rows, key=lambda r: r["charge_uC"]),
        worst_r18=max(rows, key=lambda r: r["r18_energy_uJ"]),
        worst_r20=max(rows, key=lambda r: r["r20_energy_uJ"]),
        criteria=dict(vled_abs_max_V=6.0, charge_reference_uC=50.0,
                      r18_energy_reference_uJ=70.92,
                      r20_energy_reference_uJ=54.19),
    )
    (out / "hotplug.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ngspice", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    sp = Spice(args.ngspice)
    print(json.dumps(run(sp, args.out), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
