#!/usr/bin/env python3
"""USB 2.0 full-speed SI and 2.4 GHz RF transmission-line checks.

USB:
  * 12 Mbit/s PRBS through the board pair (35.8/31.7 mm, 90 ohm differential)
  * 22 ohm series resistors, 3 pF ESD, 1 m cable (45 ohm per line, 5 ns)
  * 15 kOhm host pull-downs, 10 pF host input; eye height and rise time
RF:
  * 8.38 mm, 0.16 mm RF_FEED line from the 2D field solver
  * series 2.2 nH tuning inductor into a 50 ohm load; S11 at 2.4 GHz
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/full-board-sim"
sys.path.insert(0, str(ROOT / "tools"))

from rev_b_impedance import estimate  # noqa: E402
from simulate_preproduction import Spice  # noqa: E402

C_LIGHT = 299792458.0
NGSPICE = Path("/home/carl/tools/kicad10/AppDir/shared/lib/libngspice.so.0")


def pwl_points(bits, period, rise, vlow, vhigh):
    """Return PWL points for a complementary pair (p and n)."""
    p, n = [], []
    prev = bits[0]
    p.append((0.0, vlow + (vhigh - vlow) * prev))
    n.append((0.0, vhigh - (vhigh - vlow) * prev))
    for i in range(1, len(bits)):
        t = i * period
        if bits[i] != bits[i - 1]:
            p.append((t, vlow + (vhigh - vlow) * bits[i - 1]))
            p.append((t + rise, vlow + (vhigh - vlow) * bits[i]))
            n.append((t, vhigh - (vhigh - vlow) * bits[i - 1]))
            n.append((t + rise, vhigh - (vhigh - vlow) * bits[i]))
    end = len(bits) * period
    p.append((end, vlow + (vhigh - vlow) * bits[-1]))
    n.append((end, vhigh - (vhigh - vlow) * bits[-1]))
    return p, n


def fmt_pwl(points):
    return " ".join(f"{t:.6e} {v:.4f}" for t, v in points)


def usb_eye(out: Path = OUT):
    random.seed(20261118)
    bits = [random.getrandbits(1) for _ in range(40)]
    period = 1 / 12e6
    rise = 4e-9
    p, n = pwl_points(bits, period, rise, 0.0, 3.3)

    # Odd-mode line: 90 ohm differential -> 45 ohm per line to ground.
    deck = f"""GOWUJI Rev B USB full-speed eye
Vp p 0 PWL({fmt_pwl(p)})
Vn n 0 PWL({fmt_pwl(n)})
Rp p pin 52
Rn n nin 52
T1 pin 0 pout 0 Z0=45 TD=0.21n
T2 nin 0 nout 0 Z0=45 TD=0.21n
Cp pout 0 3p
Cn nout 0 3p
T3 pout 0 phost 0 Z0=45 TD=5n
T4 nout 0 nhost 0 Z0=45 TD=5n
Ch phost 0 10p
Cn2 nhost 0 10p
Rh phost 0 15k
Rn2 nhost 0 15k
.tran 0.1n 3.5u 0 0.1n
.end
"""
    sp = Spice(NGSPICE)
    t, vp, vn = sp.run(deck, "time", "v(phost)", "v(nhost)")
    d = vp - vn

    # Sample at 0.75 UI after each bit, skipping the first 6 bits.
    samples = []
    for i in range(6, len(bits)):
        ts = i * period + 0.75 * period
        j = int(np.argmin(np.abs(t - ts)))
        samples.append((bits[i], float(d[j])))
    high = [v for b, v in samples if b == 1]
    low = [v for b, v in samples if b == 0]
    eye_height = min(high) - max(low) if high and low else float("nan")

    # 10-90 % rise time at the host, measured single-ended on D+.
    def edge_time(wave, level0, level1, t0):
        lo = level0 + 0.1 * (level1 - level0)
        hi = level0 + 0.9 * (level1 - level0)
        idx = np.where((t >= t0) & (t <= t0 + 30e-9))[0]
        seg_t, seg = t[idx], wave[idx]
        i_lo = np.argmax(seg >= lo)
        i_hi = np.argmax(seg >= hi)
        return float(seg_t[i_hi] - seg_t[i_lo]) if i_hi > i_lo else float("nan")

    rise_time = float("nan")
    for i in range(6, len(bits) - 1):
        if bits[i] == 0 and bits[i + 1] == 1:
            # The 0->1 transition starts at the beginning of bit i+1.
            rise_time = edge_time(vp, 0.0, 3.3, (i + 1) * period)
            break

    # Eye mask opening over the central 50 % of the UI.
    phases = np.linspace(0.25, 0.75, 21)
    eye_open = []
    for ph in phases:
        vals = []
        for i in range(6, len(bits)):
            ts = i * period + ph * period
            j = int(np.argmin(np.abs(t - ts)))
            vals.append(float(d[j]))
        eye_open.append((float(np.min(vals)), float(np.max(vals))))
    min_eye = min(hi - lo for lo, hi in eye_open)

    result = {
        "bits": len(bits),
        "bit_rate_Mbps": 12.0,
        "eye_height_V": eye_height,
        "eye_open_50pct_UI_V": min_eye,
        "rise_time_10_90_ns": rise_time,
        "max_V": float(np.max(d)),
        "min_V": float(np.min(d)),
        "pass_criteria": {"eye_height_V": 1.0, "rise_time_ns": [4.0, 20.0]},
        "pass": bool(eye_height >= 1.0 and 4.0 <= rise_time <= 20.0),
    }
    (out / "usb_eye.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return result


def rf_line(out: Path = OUT):
    # 2D field solver for the 0.16 mm RF trace over 0.0994 mm prepreg.
    z0, eps_eff = estimate(0.16)
    f = 2.4e9
    length = 8.381e-3
    beta = 2 * math.pi * f * math.sqrt(eps_eff) / C_LIGHT
    # Series 2.2 nH tuning inductor into a 50 ohm ESP32 RF port.
    zl = 50.0 + 1j * 2 * math.pi * f * 2.2e-9
    # Lossless line input impedance.
    z_in = z0 * (zl + 1j * z0 * math.tan(beta * length)) / (
        z0 + 1j * zl * math.tan(beta * length))
    s11 = abs((z_in - 50.0) / (z_in + 50.0))
    s11_db = 20 * math.log10(max(s11, 1e-12))
    # Line-only S11 with a 50 ohm load.
    z_line = z0 * (50.0 + 1j * z0 * math.tan(beta * length)) / (
        z0 + 1j * 50.0 * math.tan(beta * length))
    s11_line = abs((z_line - 50.0) / (z_line + 50.0))
    s11_line_db = 20 * math.log10(max(s11_line, 1e-12))
    result = {
        "Z0_ohm": z0,
        "eps_eff": eps_eff,
        "length_mm": length * 1e3,
        "beta_l_deg": math.degrees(beta * length),
        "S11_line_50ohm_dB": s11_line_db,
        "S11_with_2n2H_dB": s11_db,
        "pass_criteria": {"S11_dB": -10.0},
        "pass_line": bool(s11_line_db <= -10.0),
        "pass_matching": bool(s11_db <= -10.0),
        "note": "antenna VSWR is not modelled; 50 ohm load assumed",
    }
    (out / "rf_line.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["usb", "rf", "all"])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.stage in ("usb", "all"):
        print(json.dumps(usb_eye(args.out), ensure_ascii=False, indent=1))
    if args.stage in ("rf", "all"):
        print(json.dumps(rf_line(args.out), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
