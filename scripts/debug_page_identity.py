from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from lsco_tdcj_intake.packets.page_identity import classify_page_image, require_page  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--expect-page", type=int, choices=(1, 2), default=None)
    args = parser.parse_args()

    if args.expect_page:
        result = require_page(args.image, args.expect_page)
    else:
        result = classify_page_image(args.image)

    print(json.dumps(result.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())