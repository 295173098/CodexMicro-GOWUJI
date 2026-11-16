"""Write the matching merged image to a GOWUJI ESP32-S3 board via USB."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("port", help="COM6, /dev/ttyACM0, /dev/cu.usbmodem…")
    p.add_argument("image", type=Path, help="GOWUJI-*-flash-0x0.bin")
    args = p.parse_args()
    if not args.image.is_file() or args.image.stat().st_size > 4 * 1024 * 1024:
        p.error("expected a merged ESP32-S3 image no larger than 4 MB")
    with args.image.open("rb") as fh:
        if fh.read(1) != b"\xe9":
            p.error("image does not start with an ESP image header")
    print("Writing the merged ESP32-S3 image at 0x0; existing flash data in its range will be replaced.", flush=True)
    subprocess.run(
        [sys.executable, "-m", "esptool", "--chip", "esp32s3", "--port", args.port,
         "--baud", "460800", "write-flash", "0x0", str(args.image)], check=True)


if __name__ == "__main__":
    main()
