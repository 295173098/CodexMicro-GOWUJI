"""Compile the pinned Arduino firmware with the module's native USB configuration."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FQBN = "esp32:esp32:waveshare_esp32_s3_zero:USBMode=default,CDCOnBoot=cdc"
INDEX = "https://espressif.github.io/arduino-esp32/package_esp32_index.json"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arduino-cli",default="arduino-cli")
    p.add_argument("--install",action="store_true",help="Install pinned core and NeoPixel library before building")
    args = p.parse_args()
    def cli(*cmd):
        subprocess.run([args.arduino_cli,*cmd],cwd=ROOT,check=True)
    if args.install:
        cli("core","update-index","--additional-urls",INDEX)
        cli("core","install","esp32:esp32@3.3.7","--additional-urls",INDEX)
        cli("lib","install","Adafruit NeoPixel@1.15.2")
    cli("compile","--fqbn",FQBN,"--build-path","build/arduino","--output-dir","build/firmware","firmware/Gowuji")


if __name__ == "__main__":
    main()
