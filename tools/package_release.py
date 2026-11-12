"""Create local release assets from a clean Git commit plus verified build outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version",default="v0.1.0-alpha.4")
    parser.add_argument("--include-simulation",action="store_true")
    args=parser.parse_args()
    if not args.version or not all(c.isalnum() or c in ".-" for c in args.version):
        parser.error("invalid version")
    status=subprocess.check_output(["git","status","--porcelain"],cwd=ROOT)
    if status:
        parser.error("commit reviewed source before packaging")
    v=args.version
    build=ROOT/"build"
    out=ROOT/"release"/v
    out.mkdir(parents=True,exist_ok=True)
    flash=build/"firmware"/"Gowuji.ino.merged.bin"
    app=build/"firmware"/"Gowuji.ino.bin"
    gerber=(sorted((build/"fab").glob("*.g*"))+
            sorted((build/"fab").glob("*-PTH.drl"))+
            sorted((build/"fab").glob("*-NPTH.drl")))
    if flash.stat().st_size != 4*1024*1024 or not app.is_file() or len(gerber)!=11:
        parser.error("compile firmware and export both drill files plus all Gerber layers first")
    reports=[build/"erc.json",build/"drc.json"]
    reviews=[build/"review"/f for f in ("Gowuji-RevA.svg","PCB-top.svg")]
    for report in reports:
        payload=json.loads(report.read_text(encoding="utf-8-sig"))
        if payload.get("violations") or payload.get("unconnected_items") or payload.get("schematic_parity"):
            parser.error(f"review reported design violations in {report.name}")
    base=f"GOWUJI-{v}"
    merged=out/f"{base}-flash-0x0.bin"
    source=out/f"{base}-source.zip"
    fab=out/f"{base}-gerber.zip"
    review=out/f"{base}-review.zip"
    shutil.copyfile(flash,merged)
    subprocess.run(["git","archive","--format=zip",f"--prefix={base}/","-o",str(source),"HEAD"],cwd=ROOT,check=True)
    with zipfile.ZipFile(fab,"w",zipfile.ZIP_DEFLATED) as z:
        for path in gerber:
            z.write(path,path.name)
    with zipfile.ZipFile(review,"w",zipfile.ZIP_DEFLATED) as z:
        for path in reports+reviews+[ROOT/"hardware"/"BOM.csv"]:
            z.write(path,path.name)
        if args.include_simulation:
            for name in ("GOWUJI-RevA4-3D.png","GOWUJI-RevA4-assembled.png"):
                z.write(build/"review"/name,name)
            for filename in ("results.json","pcb-metrics.json","power-A1.cir","power-A4.cir",
                             "matrix-A4-corner.cir","usb-attach.png"):
                z.write(build/"simulation"/filename,f"simulation/{filename}")
    (out/"SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in [merged,source,fab,review]),
        encoding="ascii")
    print(out)


if __name__ == "__main__":
    main()
