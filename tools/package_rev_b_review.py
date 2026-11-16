"""Bundle a fresh, local Rev B sample review with checksums and source inputs."""
from hashlib import sha256
from pathlib import Path
import argparse
import csv
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package(review, shell, image, output):
    def read_csv(file):
        with file.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    parts = read_csv(review / "positions/process.csv")
    smt = read_csv(review / "positions/smt-review.csv")
    by_ref = {p["Ref"]: p for p in parts}
    if len(by_ref) != len(parts) or {p["Ref"] for p in smt} != {p["Ref"] for p in parts if p["Process"] == "SMT"}:
        raise ValueError("Placement files disagree")
    if by_ref["J2"]["Process"] != "hybrid" or {"C19", "C20"} & by_ref.keys():
        raise ValueError("Incorrect USB connector assembly class or RF DNP placement")
    if {p["Ref"] for p in smt if p["Side"] == "bottom"} != {"R16", "R17", "U5"}:
        raise ValueError("Unexpected bottom assembly")
    firmware = image.read_bytes()
    if len(firmware) != 4*1024*1024 or any(firmware[i] != 0xe9 for i in (0, 0x10000)):
        raise ValueError("Expected a 4 MB Rev B merged ESP32-S3 image with bootloader and application")
    gerbers = sorted(p for p in (review / "gerber").iterdir() if p.is_file())
    suffixes = {p.suffix for p in gerbers}
    required = set(".gtl .g1 .g2 .gbl .gtp .gbp .gto .gbo .gts .gbs .gm1 .gbrjob .drl".split())
    if suffixes != required or len(gerbers) != 14 or {x.stem.rsplit("-", 1)[-1] for x in gerbers if x.suffix == ".drl"} != {"PTH", "NPTH"}:
        raise ValueError("Expected exactly eleven plot layers, Gerber job, PTH and NPTH")
    job = json.loads(next(p for p in gerbers if p.suffix == ".gbrjob").read_text(encoding="utf-8"))["GeneralSpecs"]
    if (job["BoardThickness"], job["LayerNumber"], job["Finish"], job["ImpedanceControlled"]) != (1.6, 4, "ENIG", True):
        raise ValueError("Gerber job does not carry the Rev B stack selection")

    entries = {}

    def add(path, name):
        if name in entries:
            raise ValueError(f"Duplicate entry: {name}")
        blob = path.read_bytes()
        if not blob:
            raise ValueError(f"Empty file: {path}")
        entries[name] = blob

    for p in gerbers:
        add(p, f"fabrication/gerber/{p.name}")
    for f in ("BOM.csv", "drill.txt", "erc.rpt", "drc.rpt", "fabrication-notes.md", "README.txt",
              "positions/review.csv", "positions/process.csv", "positions/smt-review.csv"):
        add(review / f, f"fabrication/{f}")
    for f in ("base", "face", "rear-disk", "encoder-knob", "key-accept", "key-agent", "key-decline",
              "key-find", "key-interrupt", "key-new-chat", "key-ptt"):
        for suffix in (".stl", ".step"):
            add(shell / (f+suffix), f"printing/{f}{suffix}")
    add(shell / "enclosure.step", "printing/enclosure.step")
    for f in ("joystick-cap.stl", "light-pipes.stl", "mx-fit-coupon.stl"):
        add(ROOT / "mechanical" / f, f"printing/{f}")
    board = ROOT / "hardware/rev-b"
    for p in sorted(board.rglob("*")):
        if p.is_file() and p.suffix not in (".kicad_prl", ".lck") and p.name != "BOM.csv":
            add(p, p.relative_to(ROOT).as_posix())
    for p in sorted((ROOT / "hardware/models").glob("*.step")):
        add(p, p.relative_to(ROOT).as_posix())
    for base in ("firmware/Gowuji", "companion"):
        for p in sorted((ROOT / base).rglob("*")):
            if p.is_file() and p.suffix in (".h", ".ino", ".py", ".json", ".md", ".txt"):
                add(p, p.relative_to(ROOT).as_posix())
    for f in ("firmware/flash.py", "docs/rev-b.md", "docs/rev-b-validation.md", "docs/rev-b-bringup.md",
              "mechanical/appearance.py", "mechanical/generate.py", "tools/build_firmware.py",
              "tools/integrated_layout.py"):
        add(ROOT / f, f)
    entries["firmware/GOWUJI-RevB-flash-0x0.bin"] = firmware
    entries["README.txt"] = (
        "GOWUJI Rev B — engineering sample review, not an order or production release.\n"
        "Read fabrication/fabrication-notes.md and docs/rev-b-bringup.md before proceeding.\n"
        "The packing list includes the merged Rev B USB image and the continuous-face enclosure.\n"
    ).encode("utf-8")
    entries["SHA256SUMS.txt"] = "".join(f"{sha256(data).hexdigest()}  {name}\n"
                                       for name, data in sorted(entries.items())).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() or any(archive.read(name) != data for name, data in entries.items()):
            raise ValueError("Archive verification failed")
    print(f"{output}: {len(entries)} verified files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=ROOT / "build/rev-b-fab-review")
    parser.add_argument("--shell", type=Path, default=ROOT / "build/rev-b-shell")
    parser.add_argument("--firmware", type=Path, default=ROOT / "build/firmware-rev-b/Gowuji.ino.merged.bin")
    parser.add_argument("--output", type=Path, default=ROOT / "build/rev-b-prototype/GOWUJI-RevB-sample-review.zip")
    args = parser.parse_args()
    package(args.review, args.shell, args.firmware, args.output)
