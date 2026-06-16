"""Inspect a multipage TIFF packet for LSCO TDCJ intake."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image


def frame_fingerprint(frame: Image.Image) -> str:
    """Return a short fingerprint for the actual frame pixels."""
    rgb = frame.convert("RGB")
    digest = hashlib.sha256(rgb.tobytes()).hexdigest()
    return digest[:16]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tiff_path", help="Path to multipage TIFF packet")
    args = parser.parse_args()

    tiff_path = Path(args.tiff_path)
    if not tiff_path.exists():
        raise FileNotFoundError(f"TIFF not found: {tiff_path}")

    with Image.open(tiff_path) as image:
        frame_count = getattr(image, "n_frames", 1)

        print(f"Input:  {tiff_path}")
        print(f"Format: {image.format}")
        print(f"Frames: {frame_count}")

        fingerprints: list[str] = []

        for index in range(frame_count):
            image.seek(index)
            frame = image.copy()

            dpi = frame.info.get("dpi")
            compression = frame.info.get("compression")
            fingerprint = frame_fingerprint(frame)
            fingerprints.append(fingerprint)

            print()
            print(f"Frame {index + 1}")
            print(f"  mode:        {frame.mode}")
            print(f"  size:        {frame.size[0]} x {frame.size[1]}")
            print(f"  dpi:         {dpi}")
            print(f"  compression: {compression}")
            print(f"  fingerprint: {fingerprint}")

        if len(fingerprints) != len(set(fingerprints)):
            print()
            print("WARNING: Duplicate frame fingerprints detected.")


if __name__ == "__main__":
    main()