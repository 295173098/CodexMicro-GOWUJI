"""Rev C power-tree screening: separate VBUS_LED branch and soft start.

Behavioral loads, not vendor device models.  The TPS22918 CT ramp is modelled
as a linear 129 ms 10-90% ramp at 5 V (C9 = 47 nF, SR = 0.55*CT + 30 us/V).
The firmware's first pixel update is at ~144 ms, after the rail ramp.
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


def operating_deck(v, cable, series, esr, bulk, cpu, led, start_ms, led_bulk=45,
                   ramp_ms=129, pixel_ms=144):
    return f"""Rev C startup and load: bounded behavioral model
Vhost host 0 PWL(0 0 1u {v})
Rcable host line {cable}
Lcable line raw 2u
R16 raw main {series}
Rinput main bus 0.04
C10 bus 0 2u
R17 main damp {esr}
C14 damp 0 2.2u
R18 raw vled 1.0
R20 vled c28 2.2
C28 c28 0 4.7u
Vset ref 0 PWL(0 0 0.2m 0 {start_ms}m 3.24225)
Bldo bus core I=min(1.1,min(max(0,(v(bus)-v(core))/1.6),max(0,(v(ref)-v(core))/0.06)))
C15 core 0 {bulk}u
Rplane core chip 0.08
Cchip chip 0 3u
Vcpu cpu 0 PWL(0 0 1m 0 3m .065 42m .065 42.002m {cpu} 42.8m {cpu} 42.802m .09)
Bcpu chip 0 I=v(cpu)*min(1,max(0,v(chip)/3))
Vtarget ledref 0 PWL(0 0 3m 0 {3+ramp_ms}m 5.25)
Bsw vled led I=max(0,(min(v(vled),v(ledref))-v(led))/0.05)
Cled led 0 {led_bulk}u
Rled led last 0.23
Vpix pix 0 PWL(0 0 {pixel_ms}m 0 {pixel_ms+0.1}m .006 200m .006 200.002m {led} 200.252m {led} 200.254m .012)
BLED last 0 I=v(pix)*min(1,max(0,v(last)/3.3))
.tran 2u 160m 0 2u
.end
"""


def run(spice, out, r16=(0.779, 0.861), r17=(1.445, 1.635)):
    rows = []
    for v, cable, series, esr, bulk, cpu, led, start, led_bulk in product(
            (4.75, 5.25), (0.10, 0.55), r16, r17, (10, 28),
            (0.18, 0.25, 0.36, 0.50), (0.222,), (1, 2.5), (45,)):
        circuit = operating_deck(v, cable, series, esr, bulk, cpu, led, start, led_bulk)
        t, raw, bus, vled, ledrail, chip, host = spice.run(
            circuit, "time", "v(raw)", "v(bus)", "v(vled)", "v(last)", "v(chip)", "vhost#branch")
        if t[-1] < 0.159 or not all(np.all(np.isfinite(a)) for a in (raw, bus, vled, ledrail, chip, host)):
            raise RuntimeError(f"invalid transient: {v,cable,series,esr,bulk,cpu,led,start}")
        early = (t >= 0.003) & (t < 0.020)
        settled = t >= 0.150
        rows.append(dict(
            host_V=v, cable_ohm=cable, r16_ohm=series, r17_ohm=esr,
            c15_uF=bulk, cpu_A=cpu, led_A=led, start_ms=start,
            peak_3_to_20ms_mA=float(-host[early].min() * 1e3),
            vbus_raw_min_V=float(raw[settled].min()),
            ldo_in_min_V=float(bus[settled].min()),
            vbus_led_min_V=float(vled[settled].min()),
            led_rail_min_V=float(ledrail[settled].min()),
            u3_in_peak_V=float(vled.max()),
            led_rail_peak_V=float(ledrail.max()),
            chip_min_V=float(chip[settled].min()),
        ))
    worst_early = max(rows, key=lambda r: r["peak_3_to_20ms_mA"])
    worst_led = min(rows, key=lambda r: r["led_rail_min_V"])
    worst_u3 = max(rows, key=lambda r: r["u3_in_peak_V"])
    worst_chip = min(rows, key=lambda r: r["chip_min_V"])
    result = dict(
        cases=len(rows),
        ramp_ms=129,
        pixel_first_ms=144,
        max_peak_3_to_20ms=worst_early,
        min_led_rail=worst_led,
        max_u3_input=worst_u3,
        min_chip=worst_chip,
        criteria=dict(
            pre_enumeration_mA=100.0,
            led_rail_min_V=4.5,
            u3_abs_max_V=6.0,
            led_rail_max_V=5.5,
            chip_min_V=3.0,
        ),
    )
    (out / "operating.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
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
