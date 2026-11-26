"""Entry program for make.fun news-image-20261125.

Copies the pre-rendered entry.png to the output directory required by the
harness. Standard library only: no network, no fonts, no external programs.

The image was composed in the build session (see render.py) and shipped in
this repository as entry.png. This program only copies it, so the two
harness runs are byte-identical by construction.
"""

import os
import shutil
import sys


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/tmp"
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "entry.png")
    shutil.copyfile(src, dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
