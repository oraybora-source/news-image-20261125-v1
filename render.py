# render.py — V1 news-image-20261125
# Merender entry.png 1024x1024 + manifest-verifikasi-V1.json dari koordinat
# yang sama dengan yang digambar (manifest dihasilkan kode ini, bukan diketik).
# Jalur aset: file ini HANYA dipakai saat build di sesi ini; penilai tidak
# menjalankannya. main.py (stdlib-only) hanya menyalin entry.png.
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stories import STORIES, PANEL, UTC_STRIP, DATECHECK, REGION_LABELS, REGION_COLORS

W, H = 1024, 1024
PACK = "/home/hatch/workspace/makefun-prompt-v12"
DARATAN = os.path.join(PACK, "reference", "daratan.json")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
ENTRY_PNG = os.path.join(OUT_DIR, "entry.png")
MANIFEST_JSON = "/home/hatch/workspace/makefun/news-image-20261125-notes/manifest-verifikasi-V1.json"

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
def _font(name, size):
    path = FONT_DIR + name
    if not os.path.exists(path):
        # DejaVuSerif-Italic.ttf tidak ada di sistem: pakai serif biasa.
        path = FONT_DIR + "DejaVuSerif.ttf"
    return ImageFont.truetype(path, size)


F = {
    "sans": lambda s: ImageFont.truetype(FONT_DIR + "DejaVuSans.ttf", s),
    "sans_b": lambda s: ImageFont.truetype(FONT_DIR + "DejaVuSans-Bold.ttf", s),
    "serif_b": lambda s: ImageFont.truetype(FONT_DIR + "DejaVuSerif-Bold.ttf", s),
    "serif_i": lambda s: _font("DejaVuSerif-Italic.ttf", s),
    "mono": lambda s: ImageFont.truetype(FONT_DIR + "DejaVuSansMono.ttf", s),
}

PAPER = (251, 248, 241)      # #FBF8F1
INK = (26, 26, 26)           # #1A1A1A
INK_SOFT = (74, 74, 74)
RED = (156, 27, 27)          # #9C1B1B
NAVY = (29, 53, 87)          # #1D3557
NAVY_LIGHT = (217, 226, 236)
RULE = (26, 26, 26)
CARD_BG = (255, 255, 255)
CARD_LINE = (210, 205, 195)
MAP_DOT = (168, 160, 148)
GREEN = (30, 107, 52)        # badge CONFIRMED
AMBER = (138, 109, 0)        # badge REPORTED

STATUS_COLOR = {"CONFIRMED": GREEN, "REPORTED": AMBER}


def lum(rgb):
    def f(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# --- daratan: titik-dalam-poligon (logika sama dengan verifikasi-visual.py) ---
def di_dalam_poligon(lon, lat, poligon):
    di_dalam = False
    n = len(poligon)
    j = n - 1
    for i in range(n):
        xi, yi = poligon[i]
        xj, yj = poligon[j]
        if (yi > lat) != (yj > lat):
            xinters = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < xinters:
                di_dalam = not di_dalam
        j = i
    return di_dalam


with open(DARATAN, encoding="utf-8") as fh:
    DARATAN_DATA = json.load(fh)["benua"]
POLIGON = [(b["nama"], b["poligon"]) for b in DARATAN_DATA]


def di_darat(lon, lat):
    return any(di_dalam_poligon(lon, lat, poli) for _, poli in POLIGON)


def nudge_ke_darat(lon, lat):
    """Pin kota pesisir yang jatuh di luar poligon kasar digeser minimal
    (maks 0.5 derajat) ke daratan terdekat. Mengembalikan (lon, lat, digeser)."""
    if di_darat(lon, lat):
        return lon, lat, 0.0
    for step in (0.1, 0.2, 0.3, 0.4, 0.5):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nl, nt = round(lon + dx * step, 2), round(lat + dy * step, 2)
            if di_darat(nl, nt):
                return nl, nt, step
    return lon, lat, 0.0


# --- pengukuran teks ---
def measure(text, font):
    return font.getlength(text)


def wrap(text, font, max_w, max_lines=None):
    """Bungkus teks di batas kata ke lebar max_w. Kembalikan daftar baris."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if measure(trial, font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        # pendekkan baris terakhir di batas kata + elipsis
        while lines and measure(lines[-1] + "…", font) > max_w:
            parts = lines[-1].split()
            if len(parts) <= 1:
                lines[-1] = ""
                break
            lines[-1] = " ".join(parts[:-1])
        if lines:
            lines[-1] = (lines[-1].rstrip(".,;:!?—–") + "…").strip()
    return lines


def shorten(text, font, max_w):
    """Pendekkan di batas kata + '…' sampai muat. Elipsis selalu sesudah
    kata utuh yang berakhir huruf/angka (bukan tanda baca)."""
    if measure(text, font) <= max_w:
        return text
    words = text.split()
    while len(words) > 1:
        words = words[:-1]
        cand = " ".join(words).rstrip(".,;:!?—–") + "…"
        if measure(cand, font) <= max_w:
            return cand
    return "…"


# --- peta: proyeksi linier (sama dengan yang dihitung ulang verifikasi) ---
MAP_BOX = [16, 684, 330, 213]  # kotak titik-titik peta (di bawah judul peta)
LON_MIN, LON_MAX, LAT_MIN, LAT_MAX = -180.0, 180.0, -60.0, 85.0


def proyeksi(lon, lat):
    x0, y0, w, h = MAP_BOX
    x = x0 + (lon - LON_MIN) / (LON_MAX - LON_MIN) * w
    y = y0 + (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * h
    return x, y


def penempatan_pin():
    """Tempatkan pin untuk 50 cerita: satu pin per klaster geografis.
    (1) Pra-klaster: cerita yang proyeksinya <= 14 px dari perwakilan
    klaster bergabung (kota yang sama / metro yang sama) — jadi cerita
    satu kota tidak pernah terpecah ke dua pin.
    (2) Tiap klaster ditempatkan menurut prioritas (kartu 1-12 dulu):
    di proyeksinya bila >= 28 px dari pin lain, bila tidak digeser
    (radius sampai 40 px, 16 arah, garis pemimpin bila > 4 px).
    (3) Bila tidak ada tempat, klaster bergabung ke pin terdekat
    (klaster yang berdekatan secara geografis)."""
    MIN_JARAK = 28.0
    AMBANG_PRA = 14.0
    # (1) pra-klaster
    pra = []
    for s in STORIES:
        lon, lat, nudged = nudge_ke_darat(s["lon"], s["lat"])
        s["lon_pakai"], s["lat_pakai"], s["nudge"] = lon, lat, nudged
        px, py = proyeksi(lon, lat)
        s["px"], s["py"] = px, py
        gabung = None
        for kl in pra:
            rep = kl["rep"]
            if math.hypot(px - rep["px"], py - rep["py"]) <= AMBANG_PRA:
                gabung = kl
                break
        if gabung is None:
            pra.append({"rep": s, "anggota": [s]})
        else:
            gabung["anggota"].append(s)
    # (2) tempatkan klaster — TANPA leader: geser maks 4 px (tidak butuh
    # garis penunjuk); bila tetap bertabrakan, gabung ke pin terdekat
    # (pendekatan ni24: semua pin digeser <= 3,6 px, tanpa leader).
    placed = []
    for kl in pra:
        rep = kl["rep"]
        px, py = rep["px"], rep["py"]

        def bebas(cx, cy):
            if not (MAP_BOX[0] + 8 <= cx <= MAP_BOX[0] + MAP_BOX[2] - 8
                    and MAP_BOX[1] + 8 <= cy <= MAP_BOX[1] + MAP_BOX[3] - 8):
                return False
            return all(math.hypot(cx - p["cx"], cy - p["cy"]) >= MIN_JARAK
                       for p in placed)

        if bebas(px, py):
            placed.append({"cerita": [m["n"] for m in kl["anggota"]],
                           "rep": rep, "cx": px, "cy": py, "shift": 0.0})
            continue
        done = False
        for r in (4,):
            for ang in range(0, 360, 22):
                cx = px + r * math.cos(math.radians(ang))
                cy = py + r * math.sin(math.radians(ang))
                if bebas(cx, cy):
                    placed.append({"cerita": [m["n"] for m in kl["anggota"]],
                                   "rep": rep, "cx": cx, "cy": cy,
                                   "shift": math.hypot(cx - px, cy - py)})
                    done = True
                    break
            if done:
                break
        if done:
            continue
        # (3) gabung ke pin terdekat
        nearest = min(placed,
                      key=lambda p: math.hypot(px - p["cx"], py - p["cy"]))
        nearest["cerita"].extend(m["n"] for m in kl["anggota"])
        nearest["cerita"].sort()
    return placed


def cek_pin(placed):
    """Simulasi cek jarak_pin + kelompok_pin seperti verifikasi-visual.py."""
    masalah = []
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a, b = placed[i], placed[j]
            d = math.hypot(a["cx"] - b["cx"], a["cy"] - b["cy"])
            if d < 26:
                masalah.append(f"pin {a['cerita'][0]}-{b['cerita'][0]} jarak {d:.1f}")
    for p in placed:
        dalam = [q for q in placed
                 if p["cx"] <= q["cx"] < p["cx"] + 100
                 and p["cy"] <= q["cy"] < p["cy"] + 100]
        if len(dalam) > 8:
            tanpa = [q["cerita"][0] for q in dalam
                     if len(q["cerita"]) == 1 and q["shift"] <= 4]
            if tanpa:
                masalah.append(f"kotak 100x100 di pin {p['cerita'][0]}: "
                               f"{len(dalam)} pin, tanpa kelompok/leader: {tanpa}")
    return masalah

# --- ilustrasi: adegan datar geometris, tanpa manusia, tanpa wajah ---
# Setiap fungsi menggambar dalam kotak (bx, by, bw, bh) dan mengembalikan
# daftar elemen adegan {"id":..., "bbox":[x,y,w,h]}; tiap bbox >= 2 px
# di dalam kotak ilustrasi (G32).


def _rel(box, fx0, fy0, fx1, fy1):
    bx, by, bw, bh = box
    return [bx + fx0 * bw, by + fy0 * bh, bx + fx1 * bw, by + fy1 * bh]


def _bbox_of(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [int(min(xs)), int(min(ys)), int(max(xs) - min(xs)),
            int(max(ys) - min(ys))]


def _poly(d, box, pts, fill, outline=None):
    d.polygon(pts, fill=fill, outline=outline)
    return _bbox_of(pts)


def _rect(d, box, fx0, fy0, fx1, fy1, fill, outline=None):
    x0, y0, x1, y1 = _rel(box, fx0, fy0, fx1, fy1)
    d.rectangle([x0, y0, x1, y1], fill=fill, outline=outline)
    return [int(x0), int(y0), int(x1 - x0), int(y1 - y0)]


def _ellipse(d, box, fx0, fy0, fx1, fy1, fill):
    x0, y0, x1, y1 = _rel(box, fx0, fy0, fx1, fy1)
    d.ellipse([x0, y0, x1, y1], fill=fill)
    return [int(x0), int(y0), int(x1 - x0), int(y1 - y0)]


def scene_tariffs(d, box):
    els = []
    bx, by, bw, bh = box
    _rect(d, box, 0.0, 0.0, 1.0, 0.62, (198, 214, 226))          # langit
    _rect(d, box, 0.0, 0.62, 1.0, 1.0, (44, 90, 122))           # laut
    # derek pelabuhan
    x0, y0, x1, y1 = _rel(box, 0.05, 0.08, 0.30, 0.62)
    d.line([(x0 + 8, y1), (x0 + 8, y0)], fill=(60, 60, 60), width=3)
    d.line([(x0, y0 + 10), (x1, y0 + 10)], fill=(60, 60, 60), width=3)
    els.append({"id": "crane", "bbox": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)]})
    # kapal kontainer
    hull = [(bx + 0.30 * bw, by + 0.72 * bh), (bx + 0.62 * bw, by + 0.72 * bh),
            (bx + 0.58 * bw, by + 0.88 * bh), (bx + 0.34 * bw, by + 0.88 * bh)]
    els.append({"id": "ship", "bbox": _poly(d, box, hull, (26, 40, 60))})
    els.append({"id": "containers",
                "bbox": _rect(d, box, 0.33, 0.50, 0.47, 0.72, (178, 52, 44))})
    _rect(d, box, 0.47, 0.56, 0.59, 0.72, (44, 90, 122))
    # bbox adegan "containers" mencakup kedua tumpukan kontainer
    els[-1] = {"id": "containers",
               "bbox": [int(bx + 0.33 * bw), int(by + 0.50 * bh),
                        int(0.26 * bw), int(0.22 * bh)]}
    # diagram batang tarif (naik)
    bars = []
    for i, hfrac in enumerate((0.18, 0.30, 0.44)):
        b = _rect(d, box, 0.68 + i * 0.09, 0.90 - hfrac, 0.75 + i * 0.09, 0.90,
                  (178, 52, 44))
        bars.append(b)
    els.append({"id": "tariff-bars",
                "bbox": [bars[0][0], bars[0][1],
                         bars[-1][0] + bars[-1][2] - bars[0][0],
                         bars[-1][1] + bars[-1][3] - bars[0][1]]})
    return els


def scene_hormuz(d, box):
    els = []
    bx, by, bw, bh = box
    _rect(d, box, 0.0, 0.0, 1.0, 1.0, (44, 110, 140))           # laut
    coast_l = [(bx + 0.02 * bw, by + 0.03 * bh), (bx + 0.16 * bw, by + 0.03 * bh),
               (bx + 0.10 * bw, by + 0.97 * bh), (bx + 0.02 * bw, by + 0.97 * bh)]
    els.append({"id": "coast-west", "bbox": _poly(d, box, coast_l, (198, 178, 138))})
    coast_r = [(bx + 0.98 * bw, by + 0.03 * bh), (bx + 0.84 * bw, by + 0.03 * bh),
               (bx + 0.90 * bw, by + 0.97 * bh), (bx + 0.98 * bw, by + 0.97 * bh)]
    els.append({"id": "coast-east", "bbox": _poly(d, box, coast_r, (198, 178, 138))})
    # tanker
    hull = [(bx + 0.30 * bw, by + 0.55 * bh), (bx + 0.62 * bw, by + 0.55 * bh),
            (bx + 0.58 * bw, by + 0.68 * bh), (bx + 0.34 * bw, by + 0.68 * bh)]
    els.append({"id": "tanker", "bbox": _poly(d, box, hull, (26, 26, 26))})
    _rect(d, box, 0.52, 0.44, 0.58, 0.55, (240, 240, 240))
    # asap
    els.append({"id": "smoke", "bbox": _ellipse(d, box, 0.50, 0.18, 0.62, 0.44,
                                                 (120, 120, 120))})
    # ranjau (titik hitam di air)
    mines = []
    for fx, fy in ((0.24, 0.80), (0.70, 0.82), (0.78, 0.62)):
        mines.append(_ellipse(d, box, fx - 0.015, fy - 0.02, fx + 0.015,
                              fy + 0.02, (10, 10, 10)))
    els.append({"id": "mines",
                "bbox": [min(m[0] for m in mines), min(m[1] for m in mines),
                         max(m[0] + m[2] for m in mines) - min(m[0] for m in mines),
                         max(m[1] + m[3] for m in mines) - min(m[1] for m in mines)]})
    return els


def scene_shenzhou(d, box):
    els = []
    bx, by, bw, bh = box
    _rect(d, box, 0.0, 0.0, 1.0, 1.0, (16, 24, 48))             # langit malam
    stars = []
    for fx, fy in ((0.08, 0.12), (0.20, 0.08), (0.90, 0.15), (0.78, 0.08),
                   (0.60, 0.12), (0.12, 0.30)):
        stars.append(_ellipse(d, box, fx - 0.008, fy - 0.012, fx + 0.008,
                              fy + 0.012, (255, 255, 255)))
    els.append({"id": "stars",
                "bbox": [min(s[0] for s in stars), min(s[1] for s in stars),
                         max(s[0] + s[2] for s in stars) - min(s[0] for s in stars),
                         max(s[1] + s[3] for s in stars) - min(s[1] for s in stars)]})
    # stasiun (busur kanan atas) — bbox mencakup badan + panel surya
    els.append({"id": "station",
                "bbox": _rect(d, box, 0.62, 0.14, 0.95, 0.22, (120, 130, 150))})
    _rect(d, box, 0.66, 0.22, 0.91, 0.26, (44, 90, 160))
    els[-1] = {"id": "station",
               "bbox": [int(bx + 0.62 * bw), int(by + 0.14 * bh),
                        int(0.33 * bw), int(0.12 * bh)]}
    # menara peluncuran
    els.append({"id": "tower",
                "bbox": _rect(d, box, 0.18, 0.30, 0.26, 0.92, (90, 95, 105))})
    # roket — bbox mencakup badan + ujung merah
    els.append({"id": "rocket",
                "bbox": _rect(d, box, 0.30, 0.22, 0.38, 0.72, (240, 240, 240))})
    tip = [(bx + 0.30 * bw, by + 0.22 * bh), (bx + 0.38 * bw, by + 0.22 * bh),
           (bx + 0.34 * bw, by + 0.12 * bh)]
    _poly(d, box, tip, (178, 52, 44))
    els[-1] = {"id": "rocket",
               "bbox": [int(bx + 0.30 * bw), int(by + 0.12 * bh),
                        int(0.08 * bw), int(0.60 * bh)]}
    # api
    flame = [(bx + 0.30 * bw, by + 0.72 * bh), (bx + 0.38 * bw, by + 0.72 * bh),
             (bx + 0.34 * bw, by + 0.92 * bh)]
    els.append({"id": "flame", "bbox": _poly(d, box, flame, (230, 120, 30))})
    return els


def scene_hodeidah(d, box):
    els = []
    _rect(d, box, 0.0, 0.55, 1.0, 1.0, (44, 110, 140))
    _rect(d, box, 0.0, 0.0, 1.0, 0.55, (226, 222, 214))
    cranes = []
    for fx in (0.12, 0.38):
        x0, y0, x1, y1 = _rel(box, fx, 0.10, fx + 0.16, 0.60)
        d.line([(x0 + 4, y1), (x0 + 4, y0)], fill=(60, 60, 60), width=2)
        d.line([(x0, y0 + 6), (x1, y0 + 6)], fill=(60, 60, 60), width=2)
        cranes.append([int(x0), int(y0), int(x1 - x0), int(y1 - y0)])
    els.append({"id": "cranes",
                "bbox": [cranes[0][0], cranes[0][1],
                         cranes[-1][0] + cranes[-1][2] - cranes[0][0],
                         cranes[-1][1] + cranes[-1][3] - cranes[0][1]]})
    els.append({"id": "containers",
                "bbox": _rect(d, box, 0.58, 0.38, 0.80, 0.60, (178, 52, 44))})
    els.append({"id": "smoke",
                "bbox": _ellipse(d, box, 0.84, 0.08, 0.95, 0.55, (120, 120, 120))})
    return els


def scene_chips(d, box):
    els = []
    _rect(d, box, 0.0, 0.0, 1.0, 1.0, (245, 243, 238))
    pts = [(0.06, 0.30), (0.22, 0.42), (0.38, 0.36), (0.55, 0.62),
           (0.72, 0.72), (0.90, 0.88)]
    bx, by, bw, bh = box
    xy = [(bx + fx * bw, by + fy * bh) for fx, fy in pts]
    d.line(xy, fill=(178, 52, 44), width=3)
    els.append({"id": "chart", "bbox": _bbox_of(xy)})
    chips = []
    for fx in (0.12, 0.46, 0.78):
        chips.append(_rect(d, box, fx, 0.62, fx + 0.14, 0.92, (26, 40, 60)))
    els.append({"id": "chips",
                "bbox": [chips[0][0], chips[0][1],
                         chips[-1][0] + chips[-1][2] - chips[0][0],
                         chips[-1][1] + chips[-1][3] - chips[0][1]]})
    return els


def scene_treaty(d, box):
    els = []
    bx, by, bw, bh = box
    _rect(d, box, 0.0, 0.0, 1.0, 1.0, (245, 243, 238))
    els.append({"id": "document",
                "bbox": _rect(d, box, 0.30, 0.10, 0.62, 0.90, (255, 255, 255),
                              outline=(90, 90, 90))})
    for i, fy in enumerate((0.24, 0.38, 0.52)):
        x0, y0, x1, y1 = _rel(box, 0.35, fy, 0.57, fy + 0.03)
        d.line([(x0, y0), (x1, y0)], fill=(120, 120, 120), width=2)
    els.append({"id": "seal",
                "bbox": _ellipse(d, box, 0.52, 0.62, 0.62, 0.86, (178, 52, 44))})
    els.append({"id": "flags",
                "bbox": _rect(d, box, 0.70, 0.18, 0.92, 0.34, (0, 90, 60))})
    _rect(d, box, 0.70, 0.34, 0.92, 0.50, (0, 60, 140))
    _rect(d, box, 0.70, 0.50, 0.92, 0.66, (255, 200, 40))
    els[-1] = {"id": "flags",
               "bbox": [int(bx + 0.70 * bw), int(by + 0.18 * bh),
                        int(0.22 * bw), int(0.48 * bh)]}
    return els


def scene_savasleyka(d, box):
    els = []
    _rect(d, box, 0.0, 0.0, 1.0, 1.0, (198, 214, 200))
    bx, by, bw, bh = box
    els.append({"id": "runway",
                "bbox": _rect(d, box, 0.04, 0.40, 0.96, 0.52, (90, 95, 105))})
    els.append({"id": "hangar",
                "bbox": _rect(d, box, 0.06, 0.08, 0.30, 0.34, (140, 145, 155))})
    # pesawat tampak atas (siluet datar)
    pts = [(0.55, 0.62), (0.62, 0.58), (0.66, 0.68), (0.62, 0.86),
           (0.58, 0.86), (0.56, 0.70), (0.52, 0.68), (0.50, 0.62)]
    xy = [(bx + fx * bw, by + fy * bh) for fx, fy in pts]
    els.append({"id": "aircraft", "bbox": _poly(d, box, xy, (26, 40, 60))})
    els.append({"id": "smoke",
                "bbox": _ellipse(d, box, 0.76, 0.10, 0.88, 0.38, (120, 120, 120))})
    return els


def scene_samara(d, box):
    els = []
    _rect(d, box, 0.0, 0.0, 1.0, 1.0, (226, 222, 214))
    towers = []
    for fx, fh in ((0.10, 0.55), (0.30, 0.70), (0.52, 0.60)):
        towers.append(_rect(d, box, fx, 0.92 - fh, fx + 0.12, 0.92,
                            (90, 95, 105)))
    els.append({"id": "towers",
                "bbox": [towers[0][0], towers[0][1],
                         towers[-1][0] + towers[-1][2] - towers[0][0],
                         towers[-1][1] + towers[-1][3] - towers[0][1]]})
    flame = [(0.72, 0.92), (0.78, 0.92), (0.75, 0.60)]
    bx, by, bw, bh = box
    els.append({"id": "flame",
                "bbox": _poly(d, box, [(bx + fx * bw, by + fy * bh) for fx, fy in flame],
                              (230, 120, 30))})
    els.append({"id": "smoke",
                "bbox": _ellipse(d, box, 0.80, 0.08, 0.94, 0.50, (120, 120, 120))})
    return els


def scene_gaza(d, box):
    els = []
    _rect(d, box, 0.0, 0.0, 1.0, 1.0, (226, 222, 214))
    blocks = []
    for fx, fh in ((0.06, 0.45), (0.24, 0.65), (0.44, 0.55), (0.64, 0.70)):
        blocks.append(_rect(d, box, fx, 0.92 - fh, fx + 0.14, 0.92,
                            (120, 125, 135)))
    els.append({"id": "blocks",
                "bbox": [blocks[0][0], blocks[0][1],
                         blocks[-1][0] + blocks[-1][2] - blocks[0][0],
                         blocks[-1][1] + blocks[-1][3] - blocks[0][1]]})
    els.append({"id": "smoke",
                "bbox": _ellipse(d, box, 0.82, 0.08, 0.95, 0.62, (120, 120, 120))})
    return els


def scene_cartagena(d, box):
    els = []
    _rect(d, box, 0.0, 0.0, 1.0, 1.0, (245, 243, 238))
    els.append({"id": "building",
                "bbox": _rect(d, box, 0.08, 0.16, 0.58, 0.92, (44, 90, 122))})
    _rect(d, box, 0.14, 0.28, 0.24, 0.44, (255, 255, 255))
    _rect(d, box, 0.30, 0.28, 0.40, 0.44, (255, 255, 255))
    _rect(d, box, 0.44, 0.28, 0.52, 0.44, (255, 255, 255))
    _rect(d, box, 0.26, 0.60, 0.40, 0.92, (255, 255, 255))
    bx, by, bw, bh = box
    shield = [(0.78, 0.14), (0.92, 0.14), (0.92, 0.55), (0.85, 0.82),
              (0.78, 0.55)]
    els.append({"id": "shield",
                "bbox": _poly(d, box, [(bx + fx * bw, by + fy * bh) for fx, fy in shield],
                              (29, 53, 87))})
    return els


def scene_ramaphosa(d, box):
    els = []
    _rect(d, box, 0.0, 0.0, 1.0, 1.0, (245, 243, 238))
    bx, by, bw, bh = box
    ped = [(0.08, 0.30), (0.42, 0.30), (0.25, 0.10)]
    _poly(d, box, [(bx + fx * bw, by + fy * bh) for fx, fy in ped],
          (90, 95, 105))
    cols = []
    for fx in (0.10, 0.21, 0.32):
        cols.append(_rect(d, box, fx, 0.32, fx + 0.05, 0.92, (140, 145, 155)))
    els.append({"id": "columns",
                "bbox": [cols[0][0], int(by + 0.10 * bh),
                         cols[-1][0] + cols[-1][2] - cols[0][0],
                         int(by + 0.92 * bh) - int(by + 0.10 * bh)]})
    els.append({"id": "gavel",
                "bbox": _rect(d, box, 0.62, 0.30, 0.92, 0.48, (120, 82, 40))})
    _rect(d, box, 0.70, 0.48, 0.78, 0.90, (120, 82, 40))
    els[-1] = {"id": "gavel",
               "bbox": [int(bx + 0.62 * bw), int(by + 0.30 * bh),
                        int(0.30 * bw), int(0.60 * bh)]}
    return els


def scene_ucl(d, box):
    els = []
    _rect(d, box, 0.0, 0.0, 1.0, 1.0, (245, 243, 238))
    bx, by, bw, bh = box
    els.append({"id": "stadium",
                "bbox": _ellipse(d, box, 0.04, 0.10, 0.96, 0.92, (0, 110, 60))})
    _ellipse(d, box, 0.10, 0.22, 0.90, 0.86, (255, 255, 255))
    els.append({"id": "ball",
                "bbox": _ellipse(d, box, 0.42, 0.34, 0.58, 0.66, (26, 26, 26))})
    _ellipse(d, box, 0.46, 0.42, 0.54, 0.58, (255, 255, 255))
    return els


SCENES = {1: scene_tariffs, 2: scene_hormuz, 3: scene_shenzhou,
          4: scene_hodeidah, 5: scene_chips, 6: scene_treaty,
          7: scene_savasleyka, 8: scene_samara, 9: scene_gaza,
          10: scene_cartagena, 11: scene_ramaphosa, 12: scene_ucl}

# --- render utama ---
ELEMEN = []
PIN = []
LEADERS = []


def add_el(eid, jenis, bbox, **kw):
    e = {"id": eid, "jenis": jenis, "bbox": [int(v) for v in bbox]}
    e.update(kw)
    ELEMEN.append(e)
    return e


def draw_badge(d, x, y, w, h, text, status):
    d.rounded_rectangle([x, y, x + w, y + h], radius=4,
                        fill=STATUS_COLOR[status])
    f = F["sans_b"](10)
    tw = f.getlength(text)
    d.text((x + (w - tw) / 2, y + 2), text, font=f, fill=(255, 255, 255))


def card_text_lines(s, is_lead):
    """Kembalikan (meta, title_lines, dek) yang sudah diukur muat."""
    meta = f"{s['n']} · {s['place'].upper()} · {s['field']} — {s['source']}"
    if is_lead:
        title_lines = wrap(s["title"], F["sans_b"](17), 306, max_lines=2)
        dek = shorten(s["dek"], F["sans"](11), 306)
        return meta, title_lines, dek
    title_lines = wrap(s["title"], F["sans_b"](13), 310, max_lines=2)
    dek = shorten(s["dek"], F["sans"](11), 310) if len(title_lines) == 1 else ""
    return meta, title_lines, dek


def render():
    # kontras teks (lantai 4.5:1) — gagal keras bila ada warna yang tidak lolos
    for nama, c in list(REGION_COLORS.items()):
        rgb = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
        assert contrast(rgb, PAPER) >= 4.5, f"kontras region {nama} {contrast(rgb, PAPER):.2f}"
    assert contrast((255, 255, 255), NAVY) >= 4.5
    assert contrast((255, 255, 255), GREEN) >= 4.5
    assert contrast((255, 255, 255), AMBER) >= 4.5

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # ---------- masthead (disusun dari kotak tinta tiap baris) ----------
    d.line([(16, 12), (1008, 12)], fill=RULE, width=2)
    f_press = F["sans"](10)
    press = "PRESS TIME 24:00 UTC"
    d.text((1008 - f_press.getlength(press), 15), press, font=f_press, fill=INK_SOFT)
    sub = "Tariffs return, the Gulf burns, and a Pakistani reaches Tiangong."
    count = ("50 STORIES · 10 REGIONS · 15 FIELDS · "
             "EVERY ONE DATED WEDNESDAY 25 NOVEMBER 2026")
    # B-ORI-1: masthead lama "THE WORLD, IN ONE DAY" mereproduksi masthead
    # yang dilarang (referensi/contoh-news-image/README.md:115-118) dan
    # dipakai rank 1 ni21/ni22/ni25. Pengganti "WEDNESDAY, COUNTED"
    # (kandidat K11 konsep.md) — nol kata bersama dengan masthead larangan.
    # Lebar masthead diukur SEBELUM digambar: harus muat di baris yang sama
    # dengan PRESS TIME (kanan) tanpa tumpang tindih dan tanpa terpotong.
    assert (F["sans_b"](12).getlength("WEDNESDAY, COUNTED")
            + f_press.getlength(press) + 32) <= 992, "masthead tidak muat"
    baris_masthead = [
        ("WEDNESDAY, COUNTED", F["sans_b"](12), INK),
        ("Wednesday 25 November 2026", F["serif_b"](52), INK),
        (sub, F["serif_i"](16), RED),
        (count, F["sans_b"](12), INK),
    ]
    y = 15
    for teks_line, fnt, warna in baris_masthead:
        bb = d.textbbox((0, 0), teks_line, font=fnt)
        d.text((16, y - bb[1]), teks_line, font=fnt, fill=warna)
        y += (bb[3] - bb[1]) + 4
    add_el("masthead", "masthead", [16, 12, 992, 102],
           teks=("WEDNESDAY, COUNTED / Wednesday 25 November 2026 / " + sub +
                 " / " + count + " / " + press),
           ukuran_font=52,
           lebar_terukur=max(F["serif_b"](52).getlength("Wednesday 25 November 2026"),
                             F["sans_b"](12).getlength(count),
                             F["serif_i"](16).getlength(sub)))

    # ---------- panel angka ----------
    d.rectangle([16, 126, 1008, 174], fill=NAVY)
    panel_teks = []
    panel_lebar = 0.0
    for i, (angka, tanya) in enumerate(PANEL):
        cx0 = 16 + i * 166
        if i > 0:
            d.line([(cx0 - 2, 134), (cx0 - 2, 166)], fill=NAVY_LIGHT, width=1)
        f_num = F["sans_b"](24)
        f_q = F["sans"](10)
        d.text((cx0 + (162 - f_num.getlength(angka)) / 2, 130), angka,
               font=f_num, fill=(255, 255, 255))
        d.text((cx0 + (162 - f_q.getlength(tanya)) / 2, 158), tanya,
               font=f_q, fill=NAVY_LIGHT)
        panel_teks.append(f"{angka} — {tanya}")
        panel_lebar = max(panel_lebar, f_num.getlength(angka),
                          f_q.getlength(tanya))
    add_el("pita-angka", "strip", [16, 126, 992, 48],
           teks=" / ".join(panel_teks), ukuran_font=24,
           lebar_terukur=panel_lebar)

    # ---------- bar wilayah ----------
    counts = {}
    for s in STORIES:
        counts[s["region"]] = counts.get(s["region"], 0) + 1
    urutan = sorted(counts, key=lambda r: -counts[r])
    x = 16
    bar_parts = []
    f_bar = F["sans"](10)
    bar_lebar = 0.0
    for ri, r in enumerate(urutan):
        rgb = tuple(int(REGION_COLORS[r][i:i + 2], 16) for i in (1, 3, 5))
        d.rectangle([x, 189, x + 8, 197], fill=rgb)
        x += 11
        label = f"{REGION_LABELS[r]} {counts[r]}"
        d.text((x, 186), label, font=f_bar, fill=INK)
        x += f_bar.getlength(label)
        bar_lebar += 11 + f_bar.getlength(label)
        bar_parts.append(label)
        if ri < len(urutan) - 1:
            d.text((x, 186), " · ", font=f_bar, fill=INK_SOFT)
            x += f_bar.getlength(" · ")
            bar_lebar += f_bar.getlength(" · ")
    add_el("bar-wilayah", "strip", [16, 186, 992, 14],
           teks=" · ".join(bar_parts), ukuran_font=10,
           lebar_terukur=bar_lebar)

    # ---------- strip UTC ----------
    x = 16
    utc_parts = []
    f_tb = F["sans_b"](10)
    f_t = F["sans"](10)
    utc_lebar = 0.0
    for i, (jam, label) in enumerate(UTC_STRIP):
        if i > 0:
            d.text((x, 212), "· ", font=f_t, fill=INK_SOFT)
            x += f_t.getlength("· ")
            utc_lebar += f_t.getlength("· ")
        d.text((x, 212), jam + " ", font=f_tb, fill=INK)
        x += f_tb.getlength(jam + " ")
        d.text((x, 212), label, font=f_t, fill=INK)
        x += f_t.getlength(label)
        utc_lebar += f_tb.getlength(jam + " ") + f_t.getlength(label)
        utc_parts.append(f"{jam} {label}")
    utc_teks = " · ".join(utc_parts)
    add_el("strip-utc", "strip", [16, 212, 992, 20],
           teks=utc_teks, ukuran_font=10, lebar_terukur=utc_lebar)

    # ---------- kartu (3 lead + 3 menengah image-first = 6 kartu;
    # cerita 7-50 daftar) ----------
    # Kartu menengah image-first (pelajaran ni26: ilustrasi strip 41 px
    # "seperti perangko", tidak menonjol): ilustrasi 310x110 (55% tinggi
    # kartu), teks di bawahnya. Hanya 3 kartu menengah muat.
    for idx, s in enumerate(STORIES[:6]):
        is_lead = idx < 3
        col = idx % 3
        if is_lead:
            cx, cy, ch = 16 + col * 335, 244, 202
            ill = [cx + 8, cy + 8, 306, 92]
            teks_box = [cx + 8, cy + 106, 306, 90]
            badge_box = [cx + 242, cy + 11, 72, 15]
        else:
            cx, cy, ch = 16 + col * 335, 458, 200
            ill = [cx + 6, cy + 6, 310, 110]
            teks_box = [cx + 6, cy + 122, 310, 72]
            badge_box = [cx + 242, cy + 9, 72, 15]
        d.rectangle([cx, cy, cx + 322, cy + ch], fill=CARD_BG,
                    outline=CARD_LINE, width=1)
        adegan = SCENES[s["n"]](d, ill)
        draw_badge(d, *badge_box, s["status"], s["status"])
        meta, title_lines, dek = card_text_lines(s, is_lead)
        tx, ty = teks_box[0], teks_box[1]
        if is_lead:
            d.text((tx, ty), meta, font=F["sans"](13), fill=INK_SOFT)
            yy = ty + 21
            for ln in title_lines:
                d.text((tx, yy), ln, font=F["sans_b"](17), fill=INK)
                yy += 22
            if dek:
                d.text((tx, yy + 4), dek, font=F["sans"](11), fill=INK_SOFT)
            teks = meta + " / " + " ".join(title_lines) + (" / " + dek if dek else "")
            lebar = max(F["sans"](13).getlength(meta),
                        max(F["sans_b"](17).getlength(ln) for ln in title_lines),
                        F["sans"](11).getlength(dek) if dek else 0)
            ukuran = 17
        else:
            d.text((tx, ty), meta, font=F["sans"](11), fill=INK_SOFT)
            yy = ty + 17
            for ln in title_lines:
                d.text((tx, yy), ln, font=F["sans_b"](13), fill=INK)
                yy += 17
            if dek:
                d.text((tx, yy + 3), dek, font=F["sans"](11), fill=INK_SOFT)
            teks = meta + " / " + " ".join(title_lines) + (" / " + dek if dek else "")
            lebar = max(F["sans"](11).getlength(meta),
                        max(F["sans_b"](13).getlength(ln) for ln in title_lines),
                        F["sans"](11).getlength(dek) if dek else 0)
            ukuran = 13
        kid = f"kartu-{s['n']}"
        add_el(kid, "kartu", [cx, cy, 322, ch],
               jenis_kartu="lead" if is_lead else "grid",
               ilustrasi_bbox=ill, elemen_adegan=adegan)
        add_el(f"teks-{s['n']}", "teks", teks_box, induk=kid,
               teks=teks, ukuran_font=ukuran, lebar_terukur=lebar)
        add_el(f"badge-{s['n']}", "badge", badge_box, induk=kid, kartu=kid)

    # ---------- peta ----------
    placed = penempatan_pin()
    masalah = cek_pin(placed)
    if masalah:
        print("PERINGATAN pin:", masalah)
    peta_box = [16, 670, 330, 227]
    d.text((16, 671), "WHERE IT HAPPENED", font=F["sans_b"](10), fill=INK)
    # titik-titik daratan
    for gy in range(MAP_BOX[1] + 3, MAP_BOX[1] + MAP_BOX[3], 6):
        for gx in range(MAP_BOX[0] + 3, MAP_BOX[0] + MAP_BOX[2], 6):
            lon = LON_MIN + (gx - MAP_BOX[0]) / MAP_BOX[2] * (LON_MAX - LON_MIN)
            lat = LAT_MAX - (gy - MAP_BOX[1]) / MAP_BOX[3] * (LAT_MAX - LAT_MIN)
            if di_darat(lon, lat):
                d.rectangle([gx, gy, gx + 1, gy + 1], fill=MAP_DOT)
    by_n = {s["n"]: s for s in STORIES}
    for p in placed:
        rep = p["rep"]
        rgb = tuple(int(REGION_COLORS[rep["region"]][i:i + 2], 16)
                    for i in (1, 3, 5))
        # garis pemimpin anggota klaster
        for n_member in p["cerita"][1:]:
            m = by_n[n_member]
            mx, my = proyeksi(m["lon_pakai"], m["lat_pakai"])
            d.line([(p["cx"], p["cy"]), (mx, my)], fill=(120, 120, 120), width=1)
            mrgb = tuple(int(REGION_COLORS[m["region"]][i:i + 2], 16)
                         for i in (1, 3, 5))
            d.ellipse([mx - 2, my - 2, mx + 2, my + 2], fill=mrgb)
        # garis pemimpin bila pin digeser > 4 px
        if p["shift"] > 4:
            px, py = proyeksi(rep["lon_pakai"], rep["lat_pakai"])
            d.line([(p["cx"], p["cy"]), (px, py)], fill=(120, 120, 120), width=1)
            d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=rgb)
            lx0 = max(int(min(p["cx"], px) - 2), peta_box[0])
            ly0 = max(int(min(p["cy"], py) - 2), peta_box[1])
            lx1 = min(int(max(p["cx"], px) + 2), peta_box[0] + peta_box[2])
            ly1 = min(int(max(p["cy"], py) + 2), peta_box[1] + peta_box[3])
            add_el(f"leader-pin-{rep['n']}", "label",
                   [lx0, ly0, lx1 - lx0, ly1 - ly0], induk="peta")
        # pin
        d.ellipse([p["cx"] - 7, p["cy"] - 7, p["cx"] + 7, p["cy"] + 7],
                  fill=rgb, outline=(255, 255, 255), width=1)
        f_pin = F["sans_b"](8 if rep["n"] >= 10 else 9)
        num = str(rep["n"])
        d.text((p["cx"] - f_pin.getlength(num) / 2, p["cy"] - 5), num,
               font=f_pin, fill=(255, 255, 255))
        bx0 = int(round(p["cx"] - 7))
        by0 = int(round(p["cy"] - 7))
        ccx, ccy = bx0 + 7, by0 + 7
        px, py = proyeksi(rep["lon_pakai"], rep["lat_pakai"])
        digeser = round(math.hypot(ccx - px, ccy - py), 2)
        pin = {"id": f"pin-{rep['n']}", "bbox": [bx0, by0, 14, 14],
               "diameter": 14, "lon": rep["lon_pakai"], "lat": rep["lat_pakai"],
               "titik_proyeksi_px": [round(px, 2), round(py, 2)],
               "digeser_px": digeser, "cerita": p["cerita"]}
        if len(p["cerita"]) > 1:
            pin["kelompok"] = f"klaster-{rep['n']}"
        PIN.append(pin)
    add_el("peta", "peta", peta_box, teks="WHERE IT HAPPENED",
           ukuran_font=10,
           lebar_terukur=F["sans_b"](10).getlength("WHERE IT HAPPENED"))

    # ---------- legenda daftar ----------
    d.ellipse([358, 674, 366, 682], fill=GREEN)
    d.ellipse([438, 674, 446, 682], fill=AMBER)
    leg = "CONFIRMED REPORTED — dot = status · number colour = region"
    d.text((370, 670), "CONFIRMED", font=F["sans"](10), fill=INK)
    d.text((450, 670), "REPORTED — dot = status · number colour = region",
           font=F["sans"](10), fill=INK)
    add_el("legenda-daftar", "label", [358, 670, 650, 16],
           teks=leg, ukuran_font=10,
           lebar_terukur=F["sans"](10).getlength(leg))

    # ---------- daftar (3 kolom, urutan sekuensial seperti ni24) ----------
    # Lebar kolom 208 px, celah antar kolom 12 px (ambang verifikasi).
    daftar = STORIES[6:]
    kolom = [daftar[0:15], daftar[15:30], daftar[30:44]]
    for ci, items in enumerate(kolom):
        colx = 358 + ci * 220
        rows = []
        lebar_max = 0.0
        for ri, s in enumerate(items):
            ry = 698 + ri * 15
            rgb = tuple(int(REGION_COLORS[s["region"]][i:i + 2], 16)
                        for i in (1, 3, 5))
            d.ellipse([colx + 1, ry + 4, colx + 7, ry + 10],
                      fill=STATUS_COLOR[s["status"]])
            f_num = F["sans_b"](13)
            f_t = F["sans"](13)
            num = f"{s['n']}."
            nw = f_num.getlength(num)
            judul = shorten(s["short"], f_t, 208 - 10 - nw - 2)
            d.text((colx + 10, ry), num, font=f_num, fill=rgb)
            d.text((colx + 10 + nw + 2, ry), judul, font=f_t, fill=INK)
            rows.append(f"{num} {judul}")
            lebar_max = max(lebar_max, nw + 2 + f_t.getlength(judul))
        add_el(f"daftar-{['kiri', 'tengah', 'kanan'][ci]}", "daftar",
               [colx, 698, 208, 15 * len(items)],
               teks=" / ".join(rows), ukuran_font=13, lebar_terukur=lebar_max)

    # ---------- caption peta ----------
    groups = [p for p in placed if len(p["cerita"]) > 1]
    listing = "  -  ".join(
        f"{p['cerita'][0]}: {', '.join(str(n) for n in p['cerita'][1:])}"
        for p in groups)
    header = "Pins show each story's number; shared pins also cover:"
    lines = [header]
    for ukuran in (10, 9, 8):
        f_cap = F["sans"](ukuran)
        rest = wrap(listing, f_cap, 326)
        if len(rest) <= 3:
            break
    lines += rest
    cap_h = 2 + 11 * len(lines) + 2
    cap_top = 957 - cap_h
    for i, ln in enumerate(lines):
        d.text((16, cap_top + 1 + i * 11), ln, font=f_cap, fill=INK_SOFT)
    add_el("caption-peta", "caption", [16, cap_top, 330, cap_h],
           teks=" / ".join(lines), ukuran_font=10,
           lebar_terukur=max(f_cap.getlength(ln) for ln in lines))

    # ---------- DATE CHECK ----------
    dc_head = "DATE CHECK — What we left out, and why it is not 25 November:"
    dc_body = " · ".join(f"{label} {tgl}" for label, tgl in DATECHECK)
    d.text((16, 970), dc_head, font=F["sans_b"](11), fill=INK)
    d.text((16, 984), dc_body, font=F["sans"](11), fill=INK_SOFT)
    add_el("kotak-datecheck", "datecheck", [16, 969, 992, 28],
           teks=dc_head + " / " + dc_body, ukuran_font=11,
           lebar_terukur=max(F["sans_b"](11).getlength(dc_head),
                             F["sans"](11).getlength(dc_body)))

    # ---------- footer ----------
    foot = ("Sources: Reuters · AP · BBC · Al Jazeera · Le Monde · USA Today · "
            "Kyiv Independent · DFAT · WHO · IANS · "
            "every story dated 25 November 2026.")
    d.text((16, 1010), foot, font=F["sans"](8), fill=INK_SOFT)
    add_el("footer", "teks", [16, 1009, 992, 10],
           teks=foot, ukuran_font=8,
           lebar_terukur=F["sans"](8).getlength(foot))

    # ---------- simpan ----------
    img.save(ENTRY_PNG, optimize=True)
    manifest = {
        "gambar": {"file": "entry.png", "lebar": W, "tinggi": H},
        "jenis_artefak": "news-image",
        "elemen": ELEMEN,
        "pin": PIN,
        "peta": {"proyeksi": "linier", "map_box": MAP_BOX,
                 "lon_min": LON_MIN, "lon_max": LON_MAX,
                 "lat_min": LAT_MIN, "lat_max": LAT_MAX},
        "irisan_diizinkan": [],
        "area": {"atas": [0, 0, 1024, 341], "tengah": [0, 341, 1024, 341],
                 "bawah": [0, 682, 1024, 342], "peta": peta_box,
                 "daftar": [358, 698, 650, 225]},
    }
    with open(MANIFEST_JSON, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
    print(f"entry.png: {os.path.getsize(ENTRY_PNG)} byte")
    print(f"elemen: {len(ELEMEN)}, pin: {len(PIN)} "
          f"(klaster: {sum(1 for p in PIN if 'kelompok' in p)})")
    print(f"cerita terpin: {sum(len(p['cerita']) for p in PIN)}")
    print(f"caption: {len(lines)} baris, top {cap_top}, h {cap_h}")
    for p in PIN:
        if len(p["cerita"]) > 1:
            print(f"  klaster {p['id']}: {p['cerita']} digeser {p['digeser_px']}")
    for s in STORIES:
        if s.get("nudge"):
            print(f"  nudge darat cerita {s['n']} ({s['place']}): "
                  f"({s['lon']},{s['lat']}) -> ({s['lon_pakai']},{s['lat_pakai']})")


if __name__ == "__main__":
    # MAP_BOX disesuaikan dengan kotak peta final [16,670,330,227]:
    # judul 670..684, titik-titik 684..897.
    MAP_BOX = [16, 684, 330, 213]
    render()
