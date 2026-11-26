#!/usr/bin/env python3
"""Salin entry.png yang sudah jadi ke folder keluaran.

Memakai pustaka standar saja, tanpa jaringan dan tanpa font.
"""
import hashlib
import os
import shutil
import sys

ENTRY_NAME = "entry.png"
PNG_SIGNATURE = bytes([137, 80, 78, 71, 13, 10, 26, 10])


def fail(msg):
    print("GALAT: " + msg, file=sys.stderr)
    return 1


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, ENTRY_NAME)
    if not os.path.exists(src):
        return fail(
            "berkas %s tidak ditemukan di %s (folder main.py: %s). "
            "Perbaikan: salin atau render ulang entry.png ke folder itu, "
            "lalu jalankan ulang main.py." % (ENTRY_NAME, src, here)
        )
    with open(src, "rb") as f:
        head = f.read(8)
    if head != PNG_SIGNATURE:
        return fail(
            "berkas %s bukan PNG utuh: 8 byte pertamanya bukan tanda tangan PNG "
            "yang diharapkan (hex: %s). Perbaikan: render ulang entry.png dari "
            "program build di folder yang sama sampai file-nya PNG utuh, lalu "
            "jalankan ulang main.py." % (src, PNG_SIGNATURE.hex())
        )
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        return fail("tidak bisa membuat folder keluaran %s: %s" % (out_dir, exc))
    dst = os.path.join(out_dir, ENTRY_NAME)
    try:
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o644)
    except OSError as exc:
        return fail("tidak bisa menyalin %s ke %s: %s" % (src, dst, exc))
    if os.path.getsize(dst) != os.path.getsize(src):
        return fail(
            "ukuran salinan %s (%d byte) tidak sama dengan sumber %s (%d byte)."
            % (dst, os.path.getsize(dst), src, os.path.getsize(src))
        )
    if sha256_of(dst) != sha256_of(src):
        return fail(
            "isi salinan %s tidak sama dengan sumber %s (hash SHA-256 beda), "
            "padahal ukurannya sama. Perbaikan: hapus salinan itu lalu "
            "jalankan ulang main.py." % (dst, src)
        )
    print("Berhasil menyalin entry.png ke %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
