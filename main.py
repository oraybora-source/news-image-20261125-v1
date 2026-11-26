#!/usr/bin/env python3
"""Program penyalin entry V2 news-image-20261125 — versi 2.

Menyalin entry.png (gambar final, sudah dirakit di sesi build) ke folder
keluaran penilai. Pustaka standar saja (os + shutil + sys): tanpa biner sistem,
font sistem, pustaka pihak ketiga, jaringan, subprocess, atau pemeriksaan
hash sendiri.
"""
import os
import shutil
import sys

ENTRY = "entry.png"


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, ENTRY)
    if not os.path.isfile(src):
        print(
            f"error: entry final tidak ditemukan: {src} "
            "(entry.png harus berada di samping main.py)",
            file=sys.stderr,
        )
        raise SystemExit(1)
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, ENTRY)
    shutil.copyfile(src, dst)
    os.chmod(dst, 0o644)
    print(f"disalin: {dst}")


if __name__ == "__main__":
    main()
