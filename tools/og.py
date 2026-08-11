#!/usr/bin/env python3
"""Gera web/og.png (cartao de compartilhamento) e web/favicon.svg.

Sem o og:image, o link colado no WhatsApp ou no Discord aparece como um retangulo
cinza — que e exatamente o oposto do que este projeto quer transmitir.

Uso:  python3 tools/og.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"
CACHE = RAIZ / ".cache" / "fontes"

PAPEL = (255, 246, 226)
PAPEL2 = (255, 238, 203)
TINTA = (21, 16, 22)
VERMELHO = (224, 49, 49)
OURO = (255, 183, 3)
MAR = (26, 127, 181)

FONTES = {
    "bangers": "https://github.com/google/fonts/raw/main/ofl/bangers/Bangers-Regular.ttf",
    "baloo": "https://github.com/google/fonts/raw/main/ofl/baloo2/Baloo2%5Bwght%5D.ttf",
}


def fonte(nome: str, tam: int):
    CACHE.mkdir(parents=True, exist_ok=True)
    alvo = CACHE / f"{nome}.ttf"
    if not alvo.exists():
        subprocess.run(["curl", "-sSL", "-o", str(alvo), FONTES[nome]],
                       capture_output=True, timeout=60)
    try:
        return ImageFont.truetype(str(alvo), tam)
    except Exception:
        for alt in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
            if Path(alt).exists():
                return ImageFont.truetype(alt, tam)
        return ImageFont.load_default()


def contorno(d, xy, txt, f, cor, borda, esp=5, ancora="mm"):
    x, y = xy
    for dx in range(-esp, esp + 1):
        for dy in range(-esp, esp + 1):
            if dx * dx + dy * dy <= esp * esp:
                d.text((x + dx, y + dy), txt, font=f, fill=borda, anchor=ancora)
    d.text((x, y), txt, font=f, fill=cor, anchor=ancora)


def main() -> int:
    L, A = 1200, 630
    img = Image.new("RGB", (L, A), PAPEL)
    d = ImageDraw.Draw(img)

    for y in range(0, A, 16):          # trama de halftone
        for x in range(0, L, 16):
            d.ellipse([x, y, x + 2, y + 2], fill=(228, 216, 194))
    for i in range(220):               # meio-tom vermelho no canto
        import math
        a = (i * 137.5) * math.pi / 180
        r = 14 * math.sqrt(i)
        x, y = L - 120 + math.cos(a) * r, 90 + math.sin(a) * r
        if 0 < x < L and 0 < y < A:
            d.ellipse([x, y, x + 5, y + 5], fill=(247, 205, 205))

    d.rectangle([0, 0, L, 26], fill=VERMELHO)
    d.rectangle([0, A - 16, L, A], fill=TINTA)

    f_tit = fonte("bangers", 132)
    f_sub = fonte("baloo", 34)
    f_num = fonte("bangers", 64)
    f_rot = fonte("baloo", 26)

    contorno(d, (L // 2, 176), "SÉCULO PERDIDO", f_tit, PAPEL, TINTA, 6)
    d.text((L // 2, 176), "SÉCULO PERDIDO", font=f_tit, fill=PAPEL, anchor="mm")
    contorno(d, (L // 2, 262), "o que é o One Piece, por evidência", f_sub, TINTA, PAPEL, 2)

    cx, cy, cw = 76, 330, 262
    dados = [("átomos", 0, OURO), ("hipóteses", 0, MAR),
             ("refutadas", 0, VERMELHO), ("ataques", 0, (47, 158, 110))]
    gj = WEB / "grafo.json"
    n_ev = n_hip = 0
    if gj.exists():
        g = json.loads(gj.read_text(encoding="utf-8"))
        n_ev = sum(1 for n in g["nos"] if n["label"] == "Evidencia")
        n_hip = sum(1 for n in g["nos"] if n["label"] == "Hipotese")
    n_ref = len(list((RAIZ / "data" / "hipoteses").glob("H-*.md")))
    refut = sum(1 for p in (RAIZ / "data" / "hipoteses").glob("H-*.md")
                if not p.name.endswith(".redteam.md")
                and "status: refutada" in p.read_text(encoding="utf-8"))
    n_rt = len(list((RAIZ / "data" / "hipoteses").glob("*.redteam.md")))
    valores = [n_ev, n_hip, refut, n_rt]

    for i, ((rot, _, cor), val) in enumerate(zip(dados, valores)):
        x = cx + i * cw
        d.rounded_rectangle([x + 6, cy + 8, x + cw - 26 + 6, cy + 150 + 8], 20, fill=TINTA)
        d.rounded_rectangle([x, cy, x + cw - 26, cy + 150], 20, fill=PAPEL2,
                            outline=TINTA, width=5)
        d.text((x + (cw - 26) // 2, cy + 62), str(val), font=f_num, fill=cor, anchor="mm")
        d.text((x + (cw - 26) // 2, cy + 116), rot.upper(), font=f_rot, fill=TINTA, anchor="mm")

    d.text((L // 2, A - 52), "hipóteses ranqueadas · evidência verificável · red team adversarial",
           font=f_rot, fill=TINTA, anchor="mm")

    WEB.mkdir(exist_ok=True)
    img.save(WEB / "og.png", optimize=True)

    (WEB / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#e03131"/>'
        '<circle cx="32" cy="32" r="19" fill="#ffb703" stroke="#151016" stroke-width="4.5"/>'
        '<path d="M32 15v34M15 32h34" stroke="#151016" stroke-width="4.5"/>'
        '<circle cx="32" cy="32" r="5.5" fill="#151016"/></svg>', encoding="utf-8")
    print(f"{WEB/'og.png'}  ({img.size[0]}x{img.size[1]}) · favicon.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
