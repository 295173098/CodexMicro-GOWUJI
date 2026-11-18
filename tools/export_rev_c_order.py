#!/usr/bin/env python3
"""Export and validate the Rev C factory BOM/CPL.

The review package previously carried a costing BOM and a raw KiCad position
file.  A factory needs one row per fitted designator: SMT plus the J2 USB-C
hybrid.  This script derives those rows from the board, the assembly-parts
list and a fresh KiCad position export, and rejects inconsistent data before
anything is packaged.

Outputs (under --out, default build/rev-c-fab-review):
  assembly/BOM.csv          SMT + HYBRID, one row per designator
  assembly/CPL.csv          SMT + HYBRID, one row per designator
  assembly/SECONDARY.csv    hand-solder / secondary assembly
  assembly/NOT_FITTED.csv   DNP, bare pads, manual and mechanical parts
  assembly/validation.txt   coverage and consistency checks
  positions/kicad.csv       fresh KiCad position export

The CPL keeps KiCad's Y-up convention (negative Y for positions below the
origin), matching the Rev B package that Huaqiu parsed successfully.  Flip Y
only if a factory explicitly asks for a top-left-origin, Y-down file.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware/rev-c/Gowuji-RevC.kicad_pcb"
PARTS = ROOT / "hardware/rev-c/assembly-parts.csv"
DEFAULT_OUT = ROOT / "build/rev-c-fab-review"

FITTED = {"SMT", "HYBRID"}
REF_RE = re.compile(r"^[A-Za-z]+\d+$")
RANGE_RE = re.compile(r"^([A-Za-z]+)(\d+)-([A-Za-z]+)(\d+)$")


def expand_refs(value: str) -> list[str]:
    """Expand ``R3-R7`` and comma-separated groups into individual refs."""
    out: list[str] = []
    for token in re.split(r"[,\s]+", value.strip()):
        if not token:
            continue
        m = RANGE_RE.fullmatch(token)
        if m:
            if m.group(1) != m.group(3):
                raise ValueError(f"mixed-prefix range: {token}")
            first, last = int(m.group(2)), int(m.group(4))
            if last < first:
                raise ValueError(f"descending range: {token}")
            out.extend(f"{m.group(1)}{i}" for i in range(first, last + 1))
        elif REF_RE.fullmatch(token):
            out.append(token)
        else:
            raise ValueError(f"unrecognised designator: {token}")
    return out


def natural_key(ref: str):
    m = re.fullmatch(r"([A-Za-z]+)(\d+)", ref)
    if not m:
        return (ref, 0)
    return (m.group(1), int(m.group(2)))


def board_refs(board: Path) -> set[str]:
    text = board.read_text()
    refs = re.findall(r'\(property "Reference" "([^"]+)"', text)
    duplicates = {r for r in refs if refs.count(r) > 1}
    if duplicates:
        raise ValueError(f"duplicate references in board: {sorted(duplicates)}")
    return set(refs)


def find_kicad_cli(explicit: str | None) -> str:
    candidates = [
        explicit,
        os.environ.get("KICAD_CLI"),
        shutil.which("kicad-cli"),
        "/home/carl/tools/kicad10/AppDir/bin/kicad-cli",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise FileNotFoundError("kicad-cli not found; pass --kicad-cli")


def export_pos(kicad_cli: str, board: Path, pos_path: Path) -> None:
    pos_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            kicad_cli,
            "pcb",
            "export",
            "pos",
            "--format",
            "csv",
            "--units",
            "mm",
            "--side",
            "both",
            "--output",
            str(pos_path),
            str(board),
        ],
        check=True,
    )


def read_pos(pos_path: Path) -> dict[str, dict[str, str]]:
    rows = list(csv.DictReader(pos_path.open(encoding="utf-8-sig")))
    by_ref: dict[str, dict[str, str]] = {}
    for row in rows:
        ref = row["Ref"].strip()
        if ref in by_ref:
            raise ValueError(f"duplicate reference in position file: {ref}")
        by_ref[ref] = row
    return by_ref


def read_parts(parts_path: Path):
    rows = list(csv.DictReader(parts_path.open(encoding="utf-8-sig")))
    required = {"Refs", "Manufacturer", "MPN", "Process", "Specification"}
    missing = required - set(rows[0]) if rows else required
    if missing:
        raise ValueError(f"assembly-parts.csv missing columns: {sorted(missing)}")

    by_ref: dict[str, dict[str, str]] = {}
    for row in rows:
        refs = expand_refs(row["Refs"])
        for ref in refs:
            if ref in by_ref:
                old = by_ref[ref]
                raise ValueError(
                    f"duplicate designator {ref}: "
                    f"{old['MPN'] or old['Process']} vs {row['MPN'] or row['Process']}"
                )
            by_ref[ref] = row
    return by_ref


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fmt_mm(value: float) -> str:
    return f"{value:.6f}mm"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, default=BOARD)
    parser.add_argument("--parts", type=Path, default=PARTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pos", type=Path, default=None,
                        help="existing KiCad position CSV; otherwise export a fresh one")
    parser.add_argument("--kicad-cli", default=None)
    args = parser.parse_args()

    out: Path = args.out
    assembly_dir = out / "assembly"
    assembly_dir.mkdir(parents=True, exist_ok=True)

    refs = board_refs(args.board)
    parts = read_parts(args.parts)
    if set(parts) != refs:
        missing = sorted(refs - set(parts), key=natural_key)
        extra = sorted(set(parts) - refs, key=natural_key)
        raise ValueError(f"assembly-parts coverage mismatch; missing={missing} extra={extra}")

    if args.pos:
        pos_path = args.pos
    else:
        pos_path = out / "positions/kicad.csv"
        export_pos(find_kicad_cli(args.kicad_cli), args.board, pos_path)
    pos = read_pos(pos_path)

    fitted = sorted(
        (ref for ref, row in parts.items() if row["Process"] in FITTED),
        key=natural_key,
    )
    secondary = sorted(
        (ref for ref, row in parts.items() if row["Process"] == "SECONDARY"),
        key=natural_key,
    )
    not_fitted = sorted(
        (ref for ref, row in parts.items() if row["Process"] not in FITTED | {"SECONDARY"}),
        key=natural_key,
    )

    missing_pos = [ref for ref in fitted if ref not in pos]
    if missing_pos:
        raise ValueError(f"fitted refs missing from position file: {missing_pos}")

    bom_rows: list[dict[str, str]] = []
    cpl_rows: list[dict[str, str]] = []
    for ref in fitted:
        row = parts[ref]
        p = pos[ref]
        if not row["MPN"]:
            raise ValueError(f"fitted ref {ref} has no MPN")
        side = p["Side"].strip().lower()
        if side not in {"top", "bottom"}:
            raise ValueError(f"{ref}: unexpected side {p['Side']!r}")
        x = float(p["PosX"])
        y = float(p["PosY"])
        rot = float(p["Rot"])
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(rot)):
            raise ValueError(f"{ref}: non-finite position/rotation")
        if not (-1.0 <= x <= 96.0 and -99.0 <= y <= 1.0):
            raise ValueError(f"{ref}: position outside board envelope ({x}, {y})")
        rot = rot % 360.0
        bom_rows.append({
            "Comment": row["MPN"],
            "Designator": ref,
            "Footprint": p["Package"].strip(),
            "Manufacturer": row["Manufacturer"],
            "MPN": row["MPN"],
            "Quantity": "1",
            "Specification": row["Specification"],
        })
        cpl_rows.append({
            "Designator": ref,
            "Mid X": fmt_mm(x),
            "Mid Y": fmt_mm(y),
            "Rotation": f"{rot:.6f}",
            "Layer": "Top" if side == "top" else "Bottom",
        })

    if len(bom_rows) != len(fitted) or len(cpl_rows) != len(fitted):
        raise ValueError("BOM/CPL row count mismatch")
    if len({r["Designator"] for r in bom_rows}) != len(bom_rows):
        raise ValueError("duplicate designator in BOM")
    if len({r["Designator"] for r in cpl_rows}) != len(cpl_rows):
        raise ValueError("duplicate designator in CPL")
    if any(r["Designator"] == "C28" and "4.7uF" not in r["Specification"] for r in bom_rows):
        raise ValueError("C28 must be the 4.7 uF VBUS_LED damping capacitor")

    secondary_rows = [
        {
            "Designator": ref,
            "Manufacturer": parts[ref]["Manufacturer"],
            "MPN": parts[ref]["MPN"],
            "Process": parts[ref]["Process"],
            "Specification": parts[ref]["Specification"],
        }
        for ref in secondary
    ]
    not_fitted_rows = [
        {
            "Designator": ref,
            "Process": parts[ref]["Process"],
            "Specification": parts[ref]["Specification"],
        }
        for ref in not_fitted
    ]

    write_csv(assembly_dir / "BOM.csv",
              ["Comment", "Designator", "Footprint", "Manufacturer", "MPN",
               "Quantity", "Specification"], bom_rows)
    write_csv(assembly_dir / "CPL.csv",
              ["Designator", "Mid X", "Mid Y", "Rotation", "Layer"], cpl_rows)
    write_csv(assembly_dir / "SECONDARY.csv",
              ["Designator", "Manufacturer", "MPN", "Process", "Specification"],
              secondary_rows)
    write_csv(assembly_dir / "NOT_FITTED.csv",
              ["Designator", "Process", "Specification"], not_fitted_rows)

    process_counts: dict[str, int] = {}
    for row in parts.values():
        process_counts[row["Process"]] = process_counts.get(row["Process"], 0) + 1

    report = [
        "Rev C assembly validation",
        f"board refs: {len(refs)}",
        f"assembly-parts unique refs: {len(parts)}",
        f"process counts: {dict(sorted(process_counts.items()))}",
        f"fitted (SMT+HYBRID): {len(fitted)}",
        f"secondary: {len(secondary)}",
        f"not fitted: {len(not_fitted)}",
        f"BOM rows: {len(bom_rows)}",
        f"CPL rows: {len(cpl_rows)}",
        f"position file: {pos_path}",
        "duplicate designators: none",
        "C28: 4.7 uF VBUS_LED damping capacitor",
        "coverage: every board reference appears exactly once",
        "CPL convention: KiCad Y-up, negative Y; flip Y only if requested",
        "status: PASS",
    ]
    (assembly_dir / "validation.txt").write_text("\n".join(report) + "\n")

    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
