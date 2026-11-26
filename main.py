#!/usr/bin/env python3
"""Program entry: menyalin entry.png yang sudah jadi ke folder keluaran.

Memakai pustaka standar saja, tanpa jaringan dan tanpa font.
"""
import os
import shutil
import sys

PNG_SIGNATURE = bytes([137, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def fail(message):
    print("GALAT: " + message, file=sys.stderr)
    sys.exit(1)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    name = "entry.png"
    src = os.path.join(here, name)
    if not os.path.exists(src):
        fail(
            "berkas %s tidak ditemukan di %s (folder main.py: %s). "
            "Jalankan program build di folder itu (python3 compose.py) "
            "atau salin entry.png ke folder itu, "
            "lalu jalankan ulang main.py." % (name, src, here)
        )
    with open(src, "rb") as f:
        head = f.read(8)
    if head != PNG_SIGNATURE:
        fail(
            "berkas %s bukan PNG yang utuh (8 byte pertama tidak cocok). "
            "Tanda tangan PNG yang diharapkan: %s. "
            "Render ulang entry.png dari program build di folder yang sama "
            "sampai file-nya PNG utuh, lalu jalankan ulang main.py."
            % (src, PNG_SIGNATURE.hex())
        )
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as e:
        fail("tidak bisa membuat folder keluaran %s: %s" % (out_dir, e))
    dst = os.path.join(out_dir, name)
    try:
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o644)
    except OSError as e:
        fail("tidak bisa menyalin %s ke %s: %s" % (src, dst, e))
    if os.path.getsize(dst) != os.path.getsize(src):
        fail(
            "ukuran salinan %s (%d byte) tidak sama dengan sumber %s (%d byte)."
            % (dst, os.path.getsize(dst), src, os.path.getsize(src))
        )
    print("Berhasil menyalin %s ke %s" % (src, dst))


if __name__ == "__main__":
    main()
