"""Rev B power margin screen; behavioral loads, not vendor device models."""

import argparse
from itertools import product
import json
from pathlib import Path

import numpy as np

from screen_rev_b_damping import deck
from simulate_preproduction import Spice


def operating_deck(v, cable, series, esr, bulk, switch_ms, cpu, led, start_ms, led_bulk=45):
    # The LDO uses the published worst pass resistance (1.6 V dropout at 1 A).
    # Graceful current turn-on avoids a constant current sink at zero voltage.
    # The capacitor ranges are assumed effective values, after DC bias.
    return f"""Rev B startup and load: bounded behavioral model
Vhost host 0 PWL(0 0 1u {v})
Rcable host line {cable}
Lcable line connector 2u
R16 connector main {series}
Rinput main bus 0.04
C10 bus 0 2u
R17 main damp {esr}
C14 damp 0 4u
Vset ref 0 PWL(0 0 0.2m 0 {start_ms}m 3.24225)
Bldo bus core I=min(1.1,min(max(0,(v(bus)-v(core))/1.6),max(0,(v(ref)-v(core))/0.06)))
C15 core 0 {bulk}u
Rplane core chip 0.08
Cchip chip 0 3u
Vcpu cpu 0 PWL(0 0 1m 0 3m .065 42m .065 42.002m {cpu} 42.8m {cpu} 42.802m .09)
Bcpu chip 0 I=v(cpu)*min(1,max(0,v(chip)/3))
Vtarget ledref 0 PWL(0 0 3m 0 {3+switch_ms}m 5.25)
Bsw main led I=max(0,(min(v(main),v(ledref))-v(led))/0.1)
Cled led 0 {led_bulk}u
Rled led last 0.23
Vpix pix 0 PWL(0 0 20m 0 20.1m .006 42m .006 42.002m {led} 42.252m {led} 42.254m .012)
BLED last 0 I=v(pix)*min(1,max(0,v(last)/3.3))
.tran 1u 46m 0 1u
.end
"""


def run_operating(spice, out, r16=(.779,.861), r17=(1.445,1.635)):
    results = []
    ramps = (1, 2.5)
    loads = {
        "usb-indicators-mic": (.18, .222),
        "ble-peak-with-led": (.25, .222),
        "unrestricted-ble-stress": (.36, .222),
        "regulator-only-500mA": (.50, .006),
    }
    for name, (cpu, led) in loads.items():
        rows = []
        for v, cable, series, esr, bulk, switch, start, led_bulk in product(
            (4.75, 5.25), (.10, .55), r16, r17, (10, 28), (7, 19), ramps, (12, 62)
        ):
            # C8 loses substantial capacitance at 5 V. Include the conservative
            # 12 uF floor from the selected part, not just its 47 uF nameplate.
            params = (v, cable, series, esr, bulk, switch, cpu, led, start, led_bulk)
            circuit = operating_deck(*params)
            t, bus, chip, endled, core, host = spice.run(
                circuit, "time", "v(bus)", "v(chip)", "v(last)", "v(core)", "vhost#branch")
            if t[-1] < .04599 or not all(np.all(np.isfinite(a)) for a in (bus, chip, endled, core, host)):
                raise RuntimeError(f"Invalid transient {name}: {params}")
            settled = t >= .040
            initial = (t >= .003) & (t < .020)
            drop = np.maximum(0, bus[settled]-core[settled])
            pass_current = np.minimum(drop/1.6, np.clip((3.24225-core[settled])/.06,0,1.1))
            rows.append((dict(params=params, chip_min_V=float(chip[settled].min()),
                         led_min_V=float(endled[settled].min()), bus_min_V=float(bus[settled].min()),
                         peak_configured_mA=float(-host[settled].min()*1e3),
                         peak_3_to_20ms_mA=float(-host[initial].min()*1e3),
                         ldo_peak_W=float(np.max(drop * pass_current))), circuit))
        worst = min(rows, key=lambda row: row[0]["chip_min_V"])
        (out / f"{name}-worst.cir").write_text(worst[1], encoding="ascii")
        results.append(dict(name=name, cases=len(rows), worst_chip=worst[0],
                       worst_led=min(rows, key=lambda row: row[0]["led_min_V"])[0],
                       max_configured=max(rows, key=lambda row: row[0]["peak_configured_mA"])[0],
                       max_early=max(rows, key=lambda row: row[0]["peak_3_to_20ms_mA"])[0],
                       corners=[row[0] for row in rows]))
    return results


def run_passive(spice, out, r16=(.779,.861), r17=(1.445,1.635)):
    rows = []
    for params in product((4.75, 5.25), (.08, .22, .55), (.5, 1.5, 2.0),
                          (1., 2.8), (2., 6.0), (.1, 1., 20.),
                          r16, (.02, .06), r17):
        circuit = deck(*params)
        t, raw, bus, damp, current = spice.run(circuit, "time", "v(connector)", "v(bus)", "v(c14)", "vhost#branch")
        if t[-1] < 99e-6 or not all(np.all(np.isfinite(a)) for a in (raw, bus, current)):
            raise RuntimeError(f"Invalid passive transient: {params}")
        p16 = current**2 * params[6]
        p17 = (bus-damp)**2 / params[8]
        rows.append((dict(params=params, raw_peak_V=float(raw.max()), bus_peak_V=float(bus.max()),
                          peak_A=float(-current.min()),
                          charge_uC=float(np.trapezoid(np.maximum(-current, 0), t) * 1e6),
                          r16_peak_W=float(p16.max()), r16_pulse_uJ=float(np.trapezoid(p16,t)*1e6),
                          r17_peak_W=float(p17.max()), r17_pulse_uJ=float(np.trapezoid(p17,t)*1e6)), circuit))
    worst = max(rows, key=lambda row: row[0]["bus_peak_V"])
    (out / "passive-worst.cir").write_text(worst[1], encoding="ascii")
    pulse = max(rows, key=lambda row: row[0]["r16_pulse_uJ"])
    surge = max(rows, key=lambda row: row[0]["peak_A"])
    (out / "passive-worst-r16-energy.cir").write_text(pulse[1], encoding="ascii")
    (out / "passive-worst-current.cir").write_text(surge[1], encoding="ascii")
    return dict(cases=len(rows), worst_bus=worst[0],
                worst_raw=max(rows,key=lambda row:row[0]["raw_peak_V"])[0],
                worst_charge=max(rows,key=lambda row:row[0]["charge_uC"])[0],
                worst_current=surge[0], worst_r16_pulse=pulse[0],
                worst_r16_power=max(rows,key=lambda row:row[0]["r16_peak_W"])[0],
                worst_r17_pulse=max(rows,key=lambda row:row[0]["r17_pulse_uJ"])[0],
                worst_r17_power=max(rows,key=lambda row:row[0]["r17_peak_W"])[0],
                corners=[row[0] for row in rows])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ngspice", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--r16-corners", nargs=2, type=float, default=(.779,.861), metavar=("MIN", "MAX"))
    parser.add_argument("--r17-esr-corners", nargs=2, type=float, default=(1.445,1.635), metavar=("MIN", "MAX"))
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--operating-only", action="store_true")
    modes.add_argument("--passive-only", action="store_true")
    args = parser.parse_args()
    if any(not 0 < lo <= hi for lo, hi in (args.r16_corners, args.r17_esr_corners)):
        parser.error("positive, ordered resistance corners required")
    args.out.mkdir(parents=True, exist_ok=True)
    sp = Spice(args.ngspice)
    passive = None if args.operating_only else run_passive(sp, args.out, args.r16_corners, args.r17_esr_corners)
    stages = [] if args.passive_only else run_operating(sp, args.out, args.r16_corners, args.r17_esr_corners)
    result = dict(passive=passive, operating=stages)
    (args.out / "power.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    brief = lambda d: {k:v for k,v in d.items() if k != "corners"}
    print(json.dumps(dict(passive=brief(passive) if passive else None,
                          operating=[brief(d) for d in stages]), indent=2))


if __name__ == "__main__":
    main()
