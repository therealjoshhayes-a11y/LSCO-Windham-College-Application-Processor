"""Extract frames from a multipage TIFF packet."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tiff_path", help="Path to multipage TIFF packet")
    parser.add_argument(
        "--output-dir",
        default="data/working/tiff_frames",
        help="Folder where extracted frame PNGs will be written",
    )
    args = parser.parse_args()

    tiff_path = Path(args.tiff_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not tiff_path.exists():
        raise FileNotFoundError(f"TIFF not found: {tiff_path}")

    with Image.open(tiff_path) as image:
        frame_count = getattr(image, "n_frames", 1)

        print(f"Input:  {tiff_path}")
        print(f"Frames: {frame_count}")
        print(f"Output: {output_dir}")

        for index in range(frame_count):
            image.seek(index)

            # Critical: copy the active frame before moving the TIFF cursor.
            frame = image.copy().convert("RGB")

            output_path = output_dir / f"{tiff_path.stem}_frame_{index + 1:02d}.png"
            frame.save(output_path)

            print(f"  Frame {index + 1} -> {output_path}")


if __name__ == "__main__":
    main()