"""Require clean KiCad checks and export fabrication and review files."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,Edge.Cuts"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli",default="kicad-cli")
    p.add_argument("--render",action="store_true",help="Include KiCad views of bare assembly and fitted case")
    args=p.parse_args()
    def cli(*argv):
        subprocess.run([args.kicad_cli,*argv],cwd=ROOT,check=True)
    for folder in ["build/fab","build/review"]:
        (ROOT/folder).mkdir(parents=True,exist_ok=True)
    pcb = "hardware/Gowuji-RevA.kicad_pcb"
    sch = "hardware/Gowuji-RevA.kicad_sch"
    cli("sch","erc","--exit-code-violations","--format","json","-o","build/erc.json",sch)
    cli("pcb","drc","--exit-code-violations","--schematic-parity","--format","json","-o","build/drc.json",pcb)
    cli("pcb","export","gerbers","-o","build/fab/","-l",LAYERS,"--subtract-soldermask",pcb)
    cli("pcb","export","drill","-o","build/fab/","--format","excellon","--excellon-separate-th",pcb)
    cli("sch","export","svg","-o","build/review/","--no-background-color",sch)
    cli("pcb","export","svg","-o","build/review/PCB-top.svg","-l","F.Cu,F.SilkS,Edge.Cuts",
        "--mode-single","--fit-page-to-board","--exclude-drawing-sheet",pcb)
    if args.render:
        opts=("--width","1440","--height","1050","--background","opaque","--quality","high",
              "--rotate","330,0,18","--zoom","0.76")
        cli("pcb","render",*opts,"--output","build/review/GOWUJI-RevA4-3D.png",pcb)
        # Put the optional case on a temporary display-only PCB. The fab source
        # and footprint library retain their normal electrical contents.
        preview=ROOT/"build/review/assembly-preview-a4.kicad_pcb"
        source=(ROOT/pcb).read_text(encoding="utf-8").rstrip()
        source=source.replace("${KIPRJMOD}",(ROOT/"hardware").as_posix())
        case=json.dumps((ROOT/"mechanical/enclosure-preview.step").as_posix(),ensure_ascii=False)
        preview.write_text(source[:-1]+f'''(footprint "Preview:Enclosure" (layer "F.Cu") (at 0 0)
          (attr board_only exclude_from_bom exclude_from_pos_files)
          (model {case} (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0))))
        )\n''',encoding="utf-8")
        cli("pcb","render",*opts,"--output","build/review/GOWUJI-RevA4-assembled.png",str(preview))


if __name__ == "__main__":
    main()
