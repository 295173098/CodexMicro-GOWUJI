#!/usr/bin/env python3
"""3D steady-state thermal FEA of the Rev B PCB.

The board is modelled as a 95 x 98 x 1.6 mm anisotropic slab:
  * in-plane effective conductivity 8 W/mK (FR-4 + continuous GND planes)
  * through-plane 0.4 W/mK
Heat sources are the worst-case component dissipations.  Convection is applied
to the top and bottom faces; three effective coefficients cover open-board,
enclosed and conservative-enclosed cases.  Junction temperatures add the
package junction-to-case resistance to the local board temperature.

This is a screening FEA, not a CFD model of the enclosure air flow.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from skfem import (Basis, BilinearForm, ElementHex1, FacetBasis, LinearForm,
                   MeshHex, asm, solve)
from skfem.helpers import grad

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/full-board-sim"

W, H, T = 95.0, 98.0, 1.6  # mm
W_M, H_M, T_M = W * 1e-3, H * 1e-3, T * 1e-3  # m

# Component heat sources: ref, x, y, w, h, power W, R_jc C/W
SOURCES = [
    ("U1", 49.0, 13.0, 7.0, 7.0, 0.50, 2.0),   # ESP32-S3 QFN56
    ("U5", 37.0, 18.0, 6.5, 3.5, 0.825, 15.0), # TLV76133 SOT-223, stress
    ("LED1", 30.79, 22.88, 3.5, 3.5, 0.10, 10.0),
    ("LED2", 60.04, 22.88, 3.5, 3.5, 0.10, 10.0),
    ("LED3", 16.83, 41.94, 3.5, 3.5, 0.10, 10.0),
    ("LED4", 35.89, 41.94, 3.5, 3.5, 0.10, 10.0),
    ("LED5", 54.94, 41.94, 3.5, 3.5, 0.10, 10.0),
    ("LED6", 73.98, 41.94, 3.5, 3.5, 0.10, 10.0),
    ("U3", 24.0, 18.0, 3.0, 3.0, 0.05, 20.0),
    ("U2", 22.0, 9.5, 3.0, 3.0, 0.02, 50.0),
    ("U4", 13.0, 11.0, 4.0, 3.0, 0.02, 50.0),
    ("U6", 32.0, 11.8, 3.0, 3.0, 0.02, 50.0),
    ("R16", 24.25, 11.5, 3.2, 1.6, 0.20, 30.0),
    ("R17", 27.3, 17.3, 1.6, 0.8, 0.10, 50.0),
]

KXY = 8.0   # W/mK
KZ = 0.4    # W/mK
T_AMB = 25.0


def build_mesh(nx=64, ny=66, nz=4):
    x = np.linspace(0.0, W_M, nx + 1)
    y = np.linspace(0.0, H_M, ny + 1)
    z = np.linspace(0.0, T_M, nz + 1)
    return MeshHex.init_tensor(x, y, z)


def thermal_case(mesh, h_conv: float):
    elem = ElementHex1()
    basis = Basis(mesh, elem)

    @BilinearForm
    def diffusion(u, v, w):
        gu, gv = grad(u), grad(v)
        return KXY * (gu[0] * gv[0] + gu[1] * gv[1]) + KZ * gu[2] * gv[2]

    # Volumetric heat sources over the component footprints.
    @LinearForm
    def source(v, w):
        x, y, z = w.x[0], w.x[1], w.x[2]
        q = np.zeros_like(x)
        for ref, cx, cy, cw, ch, power, _ in SOURCES:
            cx_m, cy_m = cx * 1e-3, cy * 1e-3
            cw_m, ch_m = cw * 1e-3, ch * 1e-3
            area = cw_m * ch_m
            density = power / (area * T_M)  # W/m^3 through the board
            mask = ((x >= cx_m - cw_m / 2) & (x <= cx_m + cw_m / 2) &
                    (y >= cy_m - ch_m / 2) & (y <= cy_m + ch_m / 2))
            q = q + np.where(mask, density, 0.0)
        return q * v

    # Top and bottom convection.
    facets = mesh.facets_satisfying(
        lambda p: np.isclose(p[2], 0.0) | np.isclose(p[2], T_M))
    fb = FacetBasis(mesh, elem, facets=facets)

    @BilinearForm
    def robin(u, v, w):
        return h_conv * u * v

    @LinearForm
    def robin_rhs(v, w):
        return h_conv * T_AMB * v

    K = asm(diffusion, basis) + asm(robin, fb)
    f = asm(source, basis) + asm(robin_rhs, fb)
    Tfield = solve(K, f)

    nodes = mesh.p.T
    ndofs = basis.nodal_dofs[0]
    out = {}
    for ref, cx, cy, cw, ch, power, rjc in SOURCES:
        d = np.linalg.norm(nodes - np.array([cx * 1e-3, cy * 1e-3, T_M / 2]), axis=1)
        node = int(np.argmin(d))
        tb = float(Tfield[ndofs[node]])
        out[ref] = {
            "board_C": tb,
            "junction_C": tb + rjc * power,
            "power_W": power,
            "R_jc_C_per_W": rjc,
        }
    total_power = sum(s[5] for s in SOURCES)
    out["_total_power_W"] = total_power
    out["_h_W_m2K"] = h_conv
    out["_max_board_C"] = float(np.max(Tfield))
    return out


def thermal(out: Path = OUT):
    mesh = build_mesh()
    cases = {}
    for label, h in (("open_h10", 10.0), ("enclosed_h5", 5.0),
                     ("conservative_h3", 3.0)):
        cases[label] = thermal_case(mesh, h)
    summary = {
        "model": "3D hex thermal FEA, anisotropic slab, top/bottom convection",
        "assumptions": {
            "k_xy_W_mK": KXY, "k_z_W_mK": KZ,
            "ambient_C": T_AMB, "board_mm": [W, H, T],
            "mesh_elements": int(mesh.nelements),
            "sources": {s[0]: s[5] for s in SOURCES},
            "note": "enclosure air flow and case resistance are lumped into h",
        },
        "cases": cases,
        "criteria_C": {"U5_junction": 125.0, "U1_junction": 105.0,
                       "LED_junction": 85.0, "R16_junction": 155.0},
    }
    (out / "thermal.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    print(json.dumps(thermal(args.out), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
