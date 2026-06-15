"""Inspect a multipage TIFF packet for LSCO TDCJ intake."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageSequence


def main() -> None:
    """Print frame count and frame details for one TIFF file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("tiff_path", help="Path to multipage TIFF packet")
    args = parser.parse_args()

    tiff_path = Path(args.tiff_path)
    if not tiff_path.exists():
        raise FileNotFoundError(f"TIFF not found: {tiff_path}")

    with Image.open(tiff_path) as image:
        frames = list(ImageSequence.Iterator(image))

        print(f"Input:  {tiff_path}")
        print(f"Format: {image.format}")
        print(f"Frames: {len(frames)}")

        for index, frame in enumerate(frames, start=1):
            dpi = frame.info.get("dpi")
            compression = frame.info.get("compression")
            print()
            print(f"Frame {index}")
            print(f"  mode:        {frame.mode}")
            print(f"  size:        {frame.size[0]} x {frame.size[1]}")
            print(f"  dpi:         {dpi}")
            print(f"  compression: {compression}")


if __name__ == "__main__":
    main()