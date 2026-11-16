"""Estimate Rev B transmission-line impedance from a 2D electrostatic cross-section.

Solves Laplace's equation with and without dielectrics. Includes trapezoidal
copper, solder mask and grounded same-layer pours. This is a board-design
screen, not a fabricator field-solver result or coupon measurement.
"""
import argparse
from math import sqrt

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

C_LIGHT = 299792458
EPSILON0 = 8.8541878128e-12


def estimate(width, spacing=None, gap=.20, *, h=.0994, dk=4.1, copper=.035,
             etch=.0178, step=.003, mask=3.8, mask_on_copper=.0152,
             mask_on_base=.0305):
    """Widths and clearances are in mm. Spacing selects a differential pair."""
    if min(width, gap, h, dk, copper, step) <= 0 or not 0 <= etch < width:
        raise ValueError("Invalid geometry for the cross-section")
    if spacing is not None and spacing <= 0:
        raise ValueError("Differential spacing must be positive")
    if min(mask, mask_on_copper, mask_on_base) <= 0:
        raise ValueError("Invalid solder mask parameters")
    pair = spacing is not None
    center = (width + spacing) / 2 if pair else 0
    # Mirror symmetry: RF is even; the differential odd mode is antisymmetric.
    max_x = center + width/2 + gap + 8*h
    xs = np.arange(0, max_x+step, step)
    ys = np.arange(0, h+copper+8*h+step, step)
    x, y = np.meshgrid(xs, ys)
    eta = np.clip((y-h)/copper, 0, 1)
    trace = (abs(x-center) <= (width-etch*eta)/2) & (y >= h) & (y <= h+copper)
    side = (x >= center+width/2+gap+etch*eta/2) & (y >= h) & (y <= h+copper)
    if pair and spacing > 2*gap:
        side |= (x <= (spacing-2*gap-etch*eta)/2) & (y >= h) & (y <= h+copper)
    mask_top = np.where(trace | side, h+copper+mask_on_copper, h+mask_on_base)
    # Keep a coating above the foil where a vertical grid column meets copper.
    over_foil = (abs(x-center) <= (width-etch)/2) | (x >= center+width/2+gap+etch/2)
    if pair and spacing > 2*gap:
        over_foil |= x <= (spacing-2*gap-etch)/2
    mask_top = np.where(over_foil, h+copper+mask_on_copper, mask_top)
    eps = np.where(y < h, dk, np.where(y <= mask_top, mask, 1.0))
    ny, nx = x.shape
    known = trace | side
    known[0,:] = known[-1,:] = known[:,-1] = True
    if pair:
        known[:,0] = True
    fixed = trace.astype(float).ravel()
    is_known = known.ravel()
    vertices = np.arange(nx*ny).reshape(ny,nx)
    i = np.concatenate((vertices[:,:-1].ravel(), vertices[:-1,:].ravel()))
    j = np.concatenate((vertices[:,1:].ravel(), vertices[1:,:].ravel()))
    weights = np.ones(len(i))
    # The symmetry boundary has half-width vertical faces in the even solve.
    if not pair:
        weights[(i % nx == 0) & (j % nx == 0)] = .5
    unknown = np.flatnonzero(~is_known)
    eps = eps.ravel()

    def capacitance(material):
        conductance = weights * 2/(1/material[i]+1/material[j])
        matrix = coo_matrix((np.tile(conductance,4)*np.repeat([1,1,-1,-1],len(i)),
                             (np.r_[i,j,i,j],np.r_[i,j,j,i])), shape=(len(fixed),len(fixed))).tocsr()
        voltage = fixed.copy()
        voltage[unknown] = spsolve(matrix[unknown,:][:,unknown], -(matrix @ fixed)[unknown])
        energy = np.sum(conductance * (voltage[i]-voltage[j])**2)
        return EPSILON0 * energy * (1 if pair else 2)

    c0 = capacitance(np.ones_like(eps))
    c = capacitance(eps)
    return (2 if pair else 1)/(C_LIGHT * sqrt(c0*c)), c/c0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=float, required=True)
    parser.add_argument("--spacing", type=float)
    parser.add_argument("--gap", type=float, default=.20, help="same-layer copper to ground clearance")
    parser.add_argument("--h", type=float, default=.0994)
    parser.add_argument("--dk", type=float, default=4.1)
    parser.add_argument("--copper", type=float, default=.035)
    parser.add_argument("--step", type=float, default=.003)
    args = parser.parse_args()
    z, dk = estimate(args.width, args.spacing, args.gap, h=args.h, dk=args.dk,
                     copper=args.copper, step=args.step)
    print(f"{z:.2f} ohm, effective relative permittivity {dk:.3f}")


if __name__ == "__main__":
    main()
