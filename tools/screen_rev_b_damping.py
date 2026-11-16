"""Screen passive Rev B VBUS damping candidates; does not change the PCB."""

import argparse
from itertools import product
import json
from pathlib import Path

import numpy as np

from simulate_preproduction import Spice


def deck(v, r, l, c10, c14, rise, series, esr10, esr14):
    return f"""Rev B passive VBUS damping screen
Vhost host 0 PWL(0 0 {rise}u {v})
Rcable host line {r}
Lcable line connector {l}u
Rseries connector bus {series}
R10 bus c10 {esr10}
R14 bus c14 {esr14}
C10 c10 0 {c10}u
C14 c14 0 {c14}u
.tran 0.05u 100u 0 0.05u
.end
"""


def screen(spice, candidate):
    name, resistors = candidate
    rows = []
    worst_deck = None
    worst_voltage = -1
    corners = product((4.75, 5.25), (.10, .22, .55), (.5, 1.5, 2.0),
                      (.45, 1.05), (2.0, 5.2), (.1, 1, 20), *resistors)
    for values in corners:
        circuit = deck(*values)
        t, raw, bus, i = spice.run(circuit, "time", "v(connector)", "v(bus)",
                                    "vhost#branch")
        if t[-1] < 99e-6 or not all(np.all(np.isfinite(a)) for a in (raw, bus, i)):
            raise RuntimeError(f"Incomplete transient: {name} {values}")
        voltage = float(bus.max())
        rows.append(dict(parameters=values, bus_peak_V=voltage,
                         connector_peak_V=float(raw.max()),
                         source_peak_A=float((-i).max()),
                         positive_charge_uC=float(np.trapezoid(np.maximum(-i, 0), t)*1e6)))
        if voltage > worst_voltage:
            worst_voltage, worst_deck = voltage, circuit
    return dict(cases=len(rows), over_5v5=sum(row["bus_peak_V"] > 5.5 for row in rows),
                over_6v=sum(row["bus_peak_V"] > 6 for row in rows),
                worst_bus=max(rows, key=lambda row: row["bus_peak_V"]),
                worst_connector=max(rows, key=lambda row: row["connector_peak_V"]),
                peak_source_A=max(row["source_peak_A"] for row in rows),
                max_charge_uC=max(row["positive_charge_uC"] for row in rows),
                added_drop_at_400mA_V=max(resistors[0]) * .4, corners=rows), worst_deck


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ngspice", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    spice = Spice(args.ngspice)
    candidates = {
        # First tuple: common series R. Other tuples include capacitor ESR.
        "existing": ((.001,), (.02, .06), (.02, .06)),
        "cap-branch-only": ((.001,), (2.58, 2.90), (2.11, 2.37)),
        "series-and-cap-branches": ((.4465, .4935), (2.58, 2.90), (2.11, 2.37)),
    }
    report = {}
    for candidate in candidates.items():
        name = candidate[0]
        report[name], worst = screen(spice, candidate)
        (args.out / f"{name}-worst.cir").write_text(worst, encoding="ascii")
    data = dict(parameter_order=["host_V", "cable_ohm", "cable_uH", "C10_uF",
                                 "C14_uF", "host_rise_us", "common_series_ohm",
                                 "C10_series_ohm", "C14_series_ohm"], candidates=report)
    (args.out / "screen.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({n: {k: v for k, v in row.items() if k != "corners"}
                      for n, row in report.items()}, indent=2))


if __name__ == "__main__":
    main()
