"""Require clean KiCad checks and export fabrication and review files."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,Edge.Cuts"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-cli",default="kicad-cli")
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


if __name__ == "__main__":
    main()
