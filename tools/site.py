#!/usr/bin/env python3
"""Gera o site publico em web/ a partir de data/.

Estatico puro, sem build step e sem framework — o mesmo principio do resto do
repositorio. Vercel serve a pasta direto.

Uso:  python3 tools/site.py
"""
from __future__ import annotations

import html
import json
import unicodedata
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "web"
sys.path.insert(0, str(RAIZ / "tools"))
import score  # noqa: E402

ROTULO_ESCOPO = {
    "one_piece": "o que é o One Piece",
    "seculo_vazio": "Século Perdido",
    "imu": "Imu",
    "joy_boy": "Joy Boy",
    "poneglyph": "Poneglyphs",
    "outro": "outro",
}

ROTULO_TIPO = {
    "narracao": "narração", "fala": "fala", "imagem": "imagem", "capa": "capa",
    "sbs": "SBS", "databook": "databook", "entrevista": "entrevista",
}

ROTULO_CONF = {
    "canonico": "canônico",
    "sbs": "SBS",
    "ambiguo": "ambíguo",
    "traducao_disputada": "tradução disputada",
}


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def ler(p: Path) -> tuple[dict, str]:
    bruto = p.read_text(encoding="utf-8")
    _, fm, corpo = bruto.split("---", 2)
    return (yaml.safe_load(fm) or {}), corpo.strip()


ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+")


def markdown_leve(txt: str, nivel: int = 4) -> str:
    """Subconjunto suficiente para os corpos e para os relatorios de red team.

    A versao anterior transformava CADA linha de um bloco de lista em <li>, o que
    picava bullets longos em varios itens soltos. Agora a linha so abre item novo
    se comecar com marcador; o resto e continuacao.
    """
    out = []
    for bloco in re.split(r"\n{2,}", txt.strip()):
        b = bloco.strip()
        if not b:
            continue
        cab = re.match(r"^(#{1,4})\s+(.*)", b)
        if cab and "\n" not in b:
            n = min(nivel + len(cab.group(1)) - 2, 6)
            out.append(f"<h{n}>{fmt(cab.group(2))}</h{n}>")
            continue
        if ITEM.match(b):
            itens, atual = [], ""
            for l in b.splitlines():
                if ITEM.match(l):
                    if atual:
                        itens.append(atual)
                    atual = ITEM.sub("", l).strip()
                elif l.strip():
                    atual += " " + l.strip()
            if atual:
                itens.append(atual)
            out.append("<ul>" + "".join(f"<li>{fmt(i)}</li>" for i in itens) + "</ul>")
            continue
        if b.startswith("> "):
            texto = " ".join(l.lstrip("> ").strip() for l in b.splitlines())
            out.append(f"<blockquote>{fmt(texto)}</blockquote>")
            continue
        if set(b) <= set("-=|") and len(b) > 3:
            continue
        out.append(f"<p>{fmt(' '.join(l.strip() for l in b.splitlines()))}</p>")
    return "".join(out)


def fmt(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"\b(EV-\d{4}-\d{2})\b", r'<a class="ref" href="/evidencias#\1">\1</a>', s)
    s = re.sub(r"(?<![-\w])(H-\d{2})(?![-\w])", r'<a class="ref" href="/#\1">\1</a>', s)
    return s


def carregar():
    evid = {}
    for p in sorted((RAIZ / "data" / "evidencias").glob("EV-*.md")):
        meta, corpo = ler(p)
        meta["corpo"] = corpo
        evid[meta["id"]] = meta

    hips = []
    for p in sorted((RAIZ / "data" / "hipoteses").glob("H-*.md")):
        if p.name.endswith(".redteam.md"):
            continue
        meta, corpo = ler(p)
        meta["corpo"] = corpo
        rt = p.with_suffix("").with_suffix(".redteam.md")
        meta["redteam"] = rt.read_text(encoding="utf-8") if rt.exists() else ""
        meta["posterior"] = score.pontuar(meta, evid)["posterior"]
        hips.append(meta)

    vivas = [h for h in hips if h.get("escopo") == "one_piece"
             and h.get("status") in {"viva", "confirmada"}]
    soma = sum(h["posterior"] for h in vivas) or 1.0
    for h in hips:
        h["fatia"] = h["posterior"] / soma if h in vivas else 0.0
    hips.sort(key=lambda h: (h.get("status") != "viva", -h["fatia"], -h["posterior"]))
    return evid, hips


def git(*args, padrao=""):
    try:
        return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True,
                              text=True, timeout=10).stdout.strip() or padrao
    except Exception:
        return padrao


CSS = """
:root{
  /* Grand Line: mar, tesouro, bandeira, pergaminho */
  --papel:#fff6e2; --papel-2:#ffeecb; --tinta:#151016;
  --vermelho:#e03131; --vermelho-esc:#a51d1d;
  --ouro:#ffb703; --ouro-esc:#e08e00;
  --mar:#166d9c; --mar-esc:#0d5580;
  --verde:#217a53; --roxo:#7048a8;
  --sombra:6px 6px 0 var(--tinta);
  --sombra-sm:3px 3px 0 var(--tinta);
  --display:"Bangers",Impact,sans-serif;
  --titulo:"Baloo 2",system-ui,sans-serif;
  --corpo:"Nunito",system-ui,sans-serif;
  --mono:"Space Mono",ui-monospace,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth;scroll-padding-top:5.5rem}
body{
  background:var(--papel); color:var(--tinta);
  font:400 17px/1.62 var(--corpo); -webkit-font-smoothing:antialiased;
  background-image:
    radial-gradient(var(--tinta) 0.9px, transparent 0.9px),
    linear-gradient(180deg,var(--papel-2),var(--papel) 22rem);
  background-size:14px 14px, 100% 100%;
  background-attachment:fixed;
}
body::before{ /* halftone de canto, como sombreado de mangá */
  content:"";position:fixed;right:-6rem;top:-6rem;width:28rem;height:28rem;z-index:0;
  pointer-events:none;opacity:.14;border-radius:50%;
  background:radial-gradient(var(--vermelho) 1.6px,transparent 1.7px);background-size:11px 11px;
}
.env{max-width:85rem;margin:0 auto;padding:0 1.4rem;position:relative;z-index:1}
a{color:inherit}

/* ---------- topo ---------- */
header.topo{background:var(--vermelho);border-bottom:4px solid var(--tinta);
  position:sticky;top:0;z-index:60;box-shadow:0 4px 0 rgba(21,16,22,.18)}
.topo .env{display:flex;align-items:center;gap:1.4rem;padding:.7rem 1.4rem}
.marca{font:400 1.9rem/1 var(--display);letter-spacing:.045em;color:var(--papel);
  text-decoration:none;text-shadow:2.5px 2.5px 0 var(--tinta);transform:rotate(-1.6deg);
  display:inline-block;transition:transform .18s}
.marca:hover{transform:rotate(-1.6deg) scale(1.05)}
.marca span{color:var(--ouro)}
nav.topo-nav{margin-left:auto;display:flex;gap:.5rem;flex-wrap:wrap}
nav.topo-nav a{font:600 .84rem/1 var(--titulo);letter-spacing:.03em;text-transform:uppercase;
  color:var(--tinta);background:var(--papel);text-decoration:none;padding:.5rem .8rem;
  border:2.5px solid var(--tinta);border-radius:999px;box-shadow:var(--sombra-sm);
  transition:transform .14s, background .14s}
nav.topo-nav a:hover{transform:translate(-1px,-2px);background:var(--ouro)}
nav.topo-nav a[aria-current]{background:var(--ouro);transform:rotate(-2deg)}

/* ---------- capa ---------- */
.capa{padding:4.5rem 0 3rem;text-align:center}
.rotulo{display:inline-block;font:600 .8rem/1 var(--titulo);letter-spacing:.1em;
  text-transform:uppercase;background:var(--mar);color:#fff;padding:.5rem .9rem;
  border:2.5px solid var(--tinta);border-radius:999px;box-shadow:var(--sombra-sm);
  transform:rotate(-1.5deg);margin-bottom:1.6rem}
.capa h1{font:400 clamp(3.2rem,10vw,6.5rem)/.92 var(--display);letter-spacing:.02em;
  text-transform:uppercase;color:var(--papel);
  text-shadow:4px 4px 0 var(--tinta),8px 8px 0 var(--ouro);
  -webkit-text-stroke:3px var(--tinta);animation:entra .55s cubic-bezier(.2,1.4,.4,1) both}
.capa h1 em{font-style:normal;color:var(--ouro);-webkit-text-stroke:3px var(--tinta);
  display:inline-block;animation:balanca 3.6s ease-in-out infinite}
@keyframes entra{from{opacity:0;transform:scale(.86) rotate(-3deg)}}
@keyframes balanca{0%,100%{transform:rotate(-2.5deg)}50%{transform:rotate(2.5deg)}}
.capa .sub{margin:1.8rem auto 0;max-width:54ch;font-size:1.12rem;font-weight:500}
.painel{display:flex;flex-wrap:wrap;justify-content:center;gap:1rem;margin-top:2.6rem}
.painel div{background:var(--papel);border:3px solid var(--tinta);border-radius:14px;
  box-shadow:var(--sombra);padding:.9rem 1.3rem;min-width:8.5rem;
  animation:pula .5s cubic-bezier(.2,1.5,.4,1) both}
.painel div:nth-child(2){transform:rotate(1.4deg);animation-delay:.07s}
.painel div:nth-child(3){transform:rotate(-1.2deg);animation-delay:.14s}
.painel div:nth-child(4){animation-delay:.21s}
@keyframes pula{from{opacity:0;transform:translateY(14px) scale(.9)}}
.painel b{display:block;font:400 2.3rem/1 var(--display);letter-spacing:.03em;color:var(--vermelho)}
.painel div:nth-child(2) b{color:var(--mar)}
.painel div:nth-child(3) b{color:var(--roxo)}
.painel div:nth-child(4) b{color:var(--verde)}
.painel small{font:700 .72rem/1.3 var(--titulo);letter-spacing:.07em;text-transform:uppercase;opacity:.72}

/* ---------- seções ---------- */
section{padding:3.4rem 0}
.cab{display:flex;align-items:center;gap:.9rem;flex-wrap:wrap;margin-bottom:.6rem}
.cab h2{font:400 2.5rem/1 var(--display);letter-spacing:.03em;text-transform:uppercase;
  color:var(--tinta)}
.cab h2::after{content:"";display:block;height:5px;background:var(--ouro);
  border:2.5px solid var(--tinta);border-radius:3px;margin-top:.2rem}
.cab .n{font:700 .78rem/1 var(--mono);background:var(--tinta);color:var(--papel);
  padding:.34rem .6rem;border-radius:999px}
.intro{max-width:62ch;margin-bottom:2rem;font-weight:500}

/* ---------- hipóteses ---------- */
.hip{background:var(--papel);border:3px solid var(--tinta);border-radius:16px;
  box-shadow:var(--sombra);margin-bottom:1.5rem;overflow:hidden;transition:transform .16s}
.hip:hover{transform:translate(-2px,-3px)}
.hip:nth-of-type(even){transform:rotate(.35deg)}
.hip:nth-of-type(even):hover{transform:rotate(.35deg) translate(-2px,-3px)}
.hip details{border:0}
.hip summary::-webkit-details-marker{display:none}
.hip summary::marker{content:""}
.hip-cab{display:grid;grid-template-columns:auto 1fr auto;gap:1rem;align-items:center;
  cursor:pointer;list-style:none;padding:1.2rem 1.3rem}
.hip-id{font:700 .78rem/1 var(--mono);background:var(--mar);color:#fff;padding:.35rem .55rem;
  border:2px solid var(--tinta);border-radius:8px}
.hip-enun{font:600 1.14rem/1.4 var(--titulo);text-wrap:pretty;margin:0;max-width:74ch}
.hip-pct{font:400 2.1rem/1 var(--display);color:var(--vermelho);letter-spacing:.02em;white-space:nowrap}
.sonda{grid-column:1/4;height:16px;background:var(--papel-2);border:2.5px solid var(--tinta);
  border-radius:999px;overflow:hidden;margin-top:.2rem}
.sonda i{display:block;height:100%;border-right:2.5px solid var(--tinta);
  background:repeating-linear-gradient(45deg,var(--ouro) 0 9px,var(--ouro-esc) 9px 18px);
  animation:sonda 1s cubic-bezier(.2,1.2,.3,1) both}
@keyframes sonda{from{width:0!important}}
.hip[data-rank="0"] .sonda i{background:repeating-linear-gradient(45deg,var(--ouro) 0 9px,var(--ouro-esc) 9px 18px)}
.hip[data-rank="1"] .sonda i{background:repeating-linear-gradient(45deg,var(--mar) 0 9px,var(--mar-esc) 9px 18px)}
.hip[data-rank="2"] .sonda i{background:repeating-linear-gradient(45deg,var(--verde) 0 9px,#217a53 9px 18px)}
.hip .sonda i{background:repeating-linear-gradient(45deg,var(--roxo) 0 9px,#523381 9px 18px)}
.hip-meta{grid-column:1/4;display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.2rem}
.selo{font:700 .7rem/1 var(--titulo);letter-spacing:.04em;text-transform:uppercase;
  background:var(--papel-2);border:2px solid var(--tinta);padding:.32rem .55rem;border-radius:999px}
.selo.ferida{background:var(--vermelho);color:#fff}
.hip[data-status="refutada"]{background:repeating-linear-gradient(45deg,#efe6d2 0 12px,#e9dfc9 12px 24px)}
.hip[data-status="refutada"] .hip-pct{color:var(--tinta);font-size:1.6rem;opacity:.5}
.hip[data-status="refutada"] .hip-enun{text-decoration:line-through;text-decoration-thickness:2px;
  text-decoration-color:var(--vermelho)}
.corpo{padding:0 1.3rem 1.4rem;animation:desdobra .26s ease both}
@keyframes desdobra{from{opacity:0;transform:translateY(-8px)}}
.corpo h4{font:400 1.25rem/1 var(--display);letter-spacing:.03em;text-transform:uppercase;
  color:var(--vermelho);margin:1.6rem 0 .6rem}
.corpo p{margin:.65rem 0;max-width:68ch}
.corpo ul{margin:.5rem 0 .5rem 1.2rem}
.corpo li{margin:.3rem 0}
code{font:.85em var(--mono);background:var(--tinta);color:var(--ouro);
  padding:.12em .4em;border-radius:5px}
.elo{display:grid;grid-template-columns:auto 1fr;gap:.8rem;padding:.6rem .8rem;margin:.45rem 0;
  background:var(--papel-2);border:2px solid var(--tinta);border-radius:10px;align-items:start}
.elo.contra{background:#ffe3e0}
.elo .ev{font:700 .74rem/1.5 var(--mono);color:#fff;background:var(--verde);text-decoration:none;
  padding:.25rem .45rem;border:2px solid var(--tinta);border-radius:7px;white-space:nowrap}
.elo.contra .ev{background:var(--vermelho)}
.elo .ev:hover{background:var(--tinta)}
.elo .como{font-size:.95rem;max-width:78ch}
.elo .peso{font:700 .7rem var(--mono);opacity:.6;margin-top:.2rem}
.prev{display:flex;gap:.7rem;align-items:baseline;max-width:86ch;padding:.5rem .8rem;margin:.4rem 0;
  background:#e7f3fb;border:2px solid var(--tinta);border-radius:10px}
.prev b{font:700 .68rem/1.5 var(--titulo);letter-spacing:.06em;text-transform:uppercase;
  background:var(--mar);color:#fff;padding:.2rem .45rem;border-radius:999px;white-space:nowrap}
details.rt{margin-top:1.3rem;border:2.5px solid var(--tinta);border-radius:12px;
  background:var(--tinta);overflow:hidden}
details.rt summary{cursor:pointer;padding:.7rem .9rem;font:400 1.15rem/1 var(--display);
  letter-spacing:.05em;text-transform:uppercase;color:var(--ouro);list-style:none}
details.rt summary::-webkit-details-marker{display:none}
details.rt summary::before{content:"⚔ "}
.rt-corpo{padding:0 1rem 1rem;max-width:96ch;color:#e7ddc9;max-height:34rem;overflow:auto;font-size:.9rem}
.rt-corpo h5,.rt-corpo h6{font:400 1.05rem/1.2 var(--display);letter-spacing:.04em;
  color:var(--ouro);margin:1rem 0 .4rem;text-transform:uppercase}
.rt-corpo p{margin:.5rem 0;max-width:66ch}
.rt-corpo ul{margin:.4rem 0 .4rem 1.1rem}
.rt-corpo li{margin:.25rem 0}
.rt-corpo code{background:#2a2230;color:var(--ouro)}
.rt-corpo strong{color:#fff}
.rt-corpo .ref{color:var(--ouro)}

/* ---------- evidências ---------- */
.busca{display:flex;gap:.7rem;flex-wrap:wrap;margin-bottom:1.6rem}
.busca input,.busca select{background:var(--papel);border:3px solid var(--tinta);
  color:var(--tinta);padding:.7rem .9rem;border-radius:12px;box-shadow:var(--sombra-sm);
  font:600 .95rem var(--corpo)}
.busca input{flex:1;min-width:15rem}
.busca input:focus-visible,.busca select:focus-visible{outline:3px solid var(--tinta);
  outline-offset:2px;background:var(--papel-2)}
.ev-item{content-visibility:auto;contain-intrinsic-size:auto 132px;background:var(--papel);border:2.5px solid var(--tinta);border-radius:12px;
  box-shadow:var(--sombra-sm);padding:.9rem 1.1rem;margin-bottom:.8rem;
  display:grid;grid-template-columns:7.5rem 1fr;gap:1rem;align-items:start;
  transition:transform .14s}
.ev-item:hover{transform:translate(-2px,-2px)}
.ev-item:target{background:var(--ouro);animation:pisca .9s ease 2}
@keyframes pisca{50%{background:var(--papel-2)}}
.ev-id{font:700 .74rem/1.4 var(--mono);color:#fff;background:#166d9c;text-decoration:none;padding:.25rem .45rem;
  border:2px solid var(--tinta);border-radius:7px;display:inline-block}
.ev-cap{display:block;margin-top:.35rem;font:700 .7rem/1.4 var(--titulo);opacity:.65}
.ev-txt{font-size:.99rem;font-weight:500;text-wrap:pretty;max-width:82ch}
.ev-tags{margin-top:.55rem;display:flex;gap:.4rem;flex-wrap:wrap;align-items:center}
.tag{font:700 .66rem/1 var(--titulo);letter-spacing:.03em;text-transform:uppercase;
  border:2px solid var(--tinta);padding:.26rem .45rem;border-radius:999px;background:var(--papel-2)}
.tag.canonico{background:#1f7d55;color:#fff}
.tag.traducao_disputada{background:var(--vermelho);color:#fff}
.tag.ambiguo{background:var(--ouro)}
.tag.sbs{background:var(--roxo);color:#fff}
.ev-item a.fonte{font:700 .68rem var(--titulo);text-transform:uppercase;letter-spacing:.04em;
  text-decoration:none;border-bottom:2px dotted currentColor;opacity:.7}
.ev-item a.fonte:hover{opacity:1;color:var(--mar)}
.vazio{padding:2rem;text-align:center;font-weight:700;background:var(--papel-2);
  border:3px dashed var(--tinta);border-radius:14px}

/* ---------- método ---------- */
.grade{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:1.2rem;margin-top:1.8rem}
.card{border:3px solid var(--tinta);border-radius:16px;padding:1.3rem;background:var(--papel);
  box-shadow:var(--sombra)}
.card:nth-child(1){background:#fff0d6}.card:nth-child(2){background:#e7f3fb}
.card:nth-child(3){background:#ffe3e0}.card:nth-child(4){background:#e4f6ec}
.card h3{font:400 1.5rem/1 var(--display);letter-spacing:.03em;text-transform:uppercase;
  margin-bottom:.5rem;color:var(--vermelho)}
.card:nth-child(2) h3{color:var(--mar)}.card:nth-child(3) h3{color:var(--vermelho-esc)}
.card:nth-child(4) h3{color:var(--verde)}
.card p{font-size:.94rem;font-weight:500}
blockquote{background:var(--papel);border:3px solid var(--tinta);border-left-width:10px;
  border-radius:12px;padding:1rem 1.2rem;margin:1.1rem 0;max-width:64ch;font-weight:500;
  box-shadow:var(--sombra-sm)}

footer{background:var(--tinta);color:#e7ddc9;border-top:4px solid var(--tinta);
  padding:2.6rem 0 3.5rem;font-size:.88rem;margin-top:3rem}
footer p{max-width:64ch;margin:.7rem 0}
footer a{color:var(--ouro)}
footer code{background:var(--papel);color:var(--tinta)}
@media(max-width:560px){
  header.topo{position:static}
  nav.topo-nav{flex-wrap:nowrap;overflow-x:auto;max-width:100%;padding-bottom:.2rem;
    scrollbar-width:none}
  nav.topo-nav::-webkit-scrollbar{display:none}
  nav.topo-nav a{padding:.45rem .6rem;white-space:nowrap}
  .topo .env{gap:.7rem;padding:.6rem 1rem}
  .marca{font-size:1.5rem}
}
@media(max-width:640px){
  .hip-cab{grid-template-columns:1fr auto;padding:1rem}
  .hip-id{display:none}
  .ev-item{grid-template-columns:1fr}
  .capa h1{-webkit-text-stroke:2px var(--tinta)}
}

/* barra so corre quando entra em vista */
.sonda i{display:block;height:100%;width:0;border-right:2.5px solid var(--tinta);
  background:repeating-linear-gradient(45deg,var(--ouro) 0 9px,var(--ouro-esc) 9px 18px)}
.sonda[data-visivel] i{width:var(--pct);transition:width .95s cubic-bezier(.2,1.2,.3,1)}
/* impacto de mangá ao abrir o dossiê */
.hip-cab{position:relative;overflow:hidden}
.hip-cab.bateu::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:conic-gradient(from 0deg,var(--ouro) 0 3deg,transparent 3deg 30deg);
  animation:bate .38s ease-out both}
@keyframes bate{from{opacity:.55;transform:scale(.2)}to{opacity:0;transform:scale(1.5)}}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
  clip:rect(0 0 0 0);white-space:nowrap;border:0}
.ev-cita{margin-top:.5rem;display:flex;gap:.35rem;flex-wrap:wrap;align-items:center;
  font:700 .66rem/1 var(--titulo);text-transform:uppercase;letter-spacing:.03em;opacity:.85}
.ev-cita .cita{text-decoration:none;border:2px solid var(--tinta);border-radius:999px;
  padding:.22rem .45rem;background:#e4f6ec}
.ev-cita .cita.contradiz{background:#ffe3e0}
.ev-cita .cita i{font-style:normal;opacity:.6;margin-left:.25rem;font-size:.9em}
.ev-cita .cita:hover{background:var(--ouro)}
.ev-cita.orfao{opacity:.55;font-style:italic;text-transform:none;letter-spacing:0}
.perma{margin-left:auto;text-decoration:none;font:700 .9rem var(--mono);opacity:.35;
  padding:.1rem .35rem;border-radius:5px}
.perma:hover{opacity:1;background:var(--ouro)}
.hip-meta{align-items:center}
.ref{color:var(--mar);text-decoration:none;border-bottom:1.5px dotted currentColor;
  font:700 .92em var(--mono)}
.ref:hover{background:var(--ouro);color:var(--tinta)}
mark{background:var(--ouro);color:var(--tinta);padding:0 .12em;border-radius:3px}
.ev-item.selecionado{outline:4px solid var(--mar);outline-offset:2px}
.ev-item[hidden]{display:none}
:focus-visible{outline:3px solid var(--mar);outline-offset:3px;border-radius:4px}
#ao-topo{position:fixed;right:1.1rem;bottom:1.1rem;z-index:70;width:3rem;height:3rem;
  border-radius:50%;border:3px solid var(--tinta);background:var(--ouro);cursor:pointer;
  font:400 1.5rem/1 var(--display);box-shadow:var(--sombra);transition:transform .14s}
#ao-topo:hover{transform:translateY(-3px)}
#ao-topo[hidden]{display:none}
/* pipeline numerado: a ordem dos papéis é o conteúdo */
.grade.passos{counter-reset:passo}
.grade.passos .card{counter-increment:passo;position:relative;padding-top:2.1rem}
.grade.passos .card::before{content:counter(passo);position:absolute;top:-.9rem;left:1.1rem;
  width:2.1rem;height:2.1rem;border-radius:50%;background:var(--tinta);color:var(--ouro);
  display:grid;place-items:center;font:400 1.2rem/1 var(--display);border:3px solid var(--tinta)}
.grade.passos .card::after{content:"→";position:absolute;right:-1.15rem;top:50%;
  transform:translateY(-50%);font:700 1.3rem var(--titulo);color:var(--tinta);opacity:.45}
.grade.passos .card:last-child::after{content:""}
@media(max-width:52rem){.grade.passos .card::after{content:"↓";right:50%;top:auto;bottom:-1.4rem;
  transform:translateX(50%)}}

/* ---------- grafo ---------- */
.g-wrap{display:grid;grid-template-columns:1fr 24rem;gap:1rem;height:min(74vh,780px)}
.g-tela{position:relative;background:var(--papel);border:3px solid var(--tinta);
  border-radius:16px;box-shadow:var(--sombra);overflow:hidden}
#cv{width:100%;height:100%;display:block;cursor:grab;touch-action:none}
.g-barra{position:absolute;left:.7rem;top:.7rem;right:.7rem;display:flex;gap:.45rem;
  flex-wrap:wrap;align-items:center;pointer-events:none;z-index:2}
.g-barra>*{pointer-events:auto}
.g-barra input[type=search]{background:var(--papel);border:2.5px solid var(--tinta);
  border-radius:999px;padding:.4rem .8rem;font:600 .82rem var(--corpo);width:12rem;
  box-shadow:var(--sombra-sm)}
.g-chip{display:inline-flex;align-items:center;gap:.32rem;background:var(--papel);
  border:2.5px solid var(--tinta);border-radius:999px;padding:.32rem .6rem;cursor:pointer;
  font:700 .68rem/1 var(--titulo);text-transform:uppercase;letter-spacing:.03em;
  box-shadow:var(--sombra-sm);user-select:none}
.g-chip input{accent-color:var(--tinta);margin:0}
.g-chip i{width:.62rem;height:.62rem;border-radius:50%;border:1.5px solid var(--tinta);display:inline-block}
.g-bt{background:var(--ouro);border:2.5px solid var(--tinta);border-radius:999px;
  padding:.34rem .7rem;font:700 .68rem/1 var(--titulo);text-transform:uppercase;
  letter-spacing:.03em;cursor:pointer;box-shadow:var(--sombra-sm)}
.g-bt:hover{background:var(--papel)}
.g-conta{position:absolute;right:.8rem;bottom:.7rem;font:700 .7rem var(--mono);
  background:var(--tinta);color:var(--papel);padding:.3rem .6rem;border-radius:999px;z-index:2}
.g-legenda{position:absolute;left:.8rem;bottom:.7rem;display:flex;gap:.5rem;flex-wrap:wrap;z-index:2}
.g-leg{display:flex;align-items:center;gap:.3rem;background:rgba(255,246,226,.92);
  border:2px solid var(--tinta);border-radius:999px;padding:.2rem .5rem;
  font:700 .64rem/1 var(--titulo);text-transform:uppercase}
.g-leg i{width:.6rem;height:.6rem;border-radius:50%;border:1.5px solid var(--tinta)}
#painel{background:var(--papel);border:3px solid var(--tinta);border-radius:16px;
  box-shadow:var(--sombra);padding:1rem;overflow-y:auto}
#painel h4{font:400 1.6rem/1 var(--display);letter-spacing:.03em;margin:.5rem 0 .7rem}
#painel h5{font:700 .7rem/1 var(--mono);margin:.9rem 0 .4rem;letter-spacing:.04em}
.g-lab{display:inline-block;font:700 .66rem/1 var(--titulo);text-transform:uppercase;
  letter-spacing:.05em;border:2px solid var(--tinta);border-radius:999px;padding:.24rem .5rem}
.g-prop{display:grid;grid-template-columns:6.2rem 1fr;gap:.5rem;padding:.32rem 0;
  border-bottom:1px dotted rgba(21,16,22,.18);font-size:.82rem}
.g-prop b{font:700 .66rem/1.5 var(--mono);text-transform:uppercase;opacity:.6}
.g-dica{font-size:.85rem;opacity:.7;font-style:italic}
#g-expandir{width:100%;margin:.8rem 0;background:var(--mar);color:#fff;border:2.5px solid var(--tinta);
  border-radius:10px;padding:.5rem;font:700 .74rem var(--titulo);text-transform:uppercase;
  cursor:pointer;box-shadow:var(--sombra-sm)}
#g-expandir:hover{background:var(--tinta)}
.g-lig{padding:.4rem .5rem;margin:.25rem 0;background:var(--papel-2);border:2px solid var(--tinta);
  border-radius:8px;cursor:pointer;font-size:.78rem}
.g-lig:hover{background:var(--ouro)}
.g-lig i{display:block;font:700 .64rem var(--mono);opacity:.6;font-style:normal}
.g-como{display:block;margin-top:.2rem;opacity:.75;font-size:.74rem;line-height:1.4}
.g-lig-mais{font:700 .7rem var(--mono);opacity:.6;padding:.2rem .5rem}
.g-ir{display:inline-block;margin:.5rem 0;font:700 .72rem var(--titulo);color:var(--mar)}
@media(max-width:820px){.g-wrap{grid-template-columns:1fr;height:auto}
  .g-tela{height:60vh}#painel{max-height:24rem}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

JS = r"""
/* ---- acordeao ------------------------------------------------------- */
/* <details>/<summary> nativo: abre sem JS, o browser cuida do estado e do
   foco. O JS aqui e so o impacto de manga e a abertura por link direto. */
document.querySelectorAll('.hip details').forEach(d => {
  d.addEventListener('toggle', () => {
    if (!d.open) return;
    const s = d.querySelector('summary');
    s.classList.add('bateu');
    s.addEventListener('animationend', () => s.classList.remove('bateu'), {once:true});
  });
});
function abrePeloHash(){
  if (!location.hash) return;
  const alvo = document.querySelector(location.hash);
  const det = alvo && alvo.querySelector(':scope > details');
  if (det) { det.open = true; alvo.scrollIntoView({block:'start'}); }
}
addEventListener('hashchange', abrePeloHash);
document.fonts ? document.fonts.ready.then(abrePeloHash) : abrePeloHash();

/* ---- barras so animam quando entram em vista ------------------------ */
/* antes disso elas corriam no load: quando o leitor chegava na oitava
   hipotese a animacao tinha acabado havia meio minuto. */
const io = new IntersectionObserver(es => {
  es.forEach(e => { if (e.isIntersecting) { e.target.dataset.visivel = '1'; io.unobserve(e.target); } });
}, {threshold:.4});
document.querySelectorAll('.sonda').forEach(el => io.observe(el));

/* ---- contadores da capa -------------------------------------------- */
const suave = t => 1 - Math.pow(1 - t, 3);
const ioNum = new IntersectionObserver(es => {
  es.forEach(e => {
    if (!e.isIntersecting) return;
    ioNum.unobserve(e.target);
    const alvo = +e.target.dataset.alvo, t0 = performance.now();
    (function passo(t){
      const k = Math.min((t - t0) / 850, 1);
      e.target.textContent = Math.round(alvo * suave(k));
      if (k < 1) requestAnimationFrame(passo);
    })(t0);
  });
}, {threshold:.6});
document.querySelectorAll('[data-alvo]').forEach(el => ioNum.observe(el));

/* ---- indice de evidencias ------------------------------------------ */
const cx = document.getElementById('busca'), fc = document.getElementById('filtro-conf'),
      ft = document.getElementById('filtro-tema'), lista = document.getElementById('lista-ev'),
      orf = document.getElementById('so-orfaos');
let visiveis = [], cursor = -1;

function esc(s){ return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
function semAcento(s){ return s.normalize('NFD').replace(/[\u0300-\u036f]/g, ''); }

function filtra(){
  if (!lista) return;
  const bruto = (cx.value || '').trim();
  const termos = semAcento(bruto.toLowerCase()).split(/\s+/).filter(Boolean);
  const c = fc.value, tema = ft.value, soOrf = orf && orf.checked;
  visiveis = []; cursor = -1;
  lista.querySelectorAll('.ev-item').forEach(el => {
    const hay = el.dataset.busca;
    const ok = termos.every(w => hay.includes(w))
            && (!c || el.dataset.conf === c)
            && (!tema || el.dataset.temas.includes('|' + tema + '|'))
            && (!soOrf || el.dataset.orfao === '1');
    el.hidden = !ok;
    el.classList.remove('selecionado');
    if (ok) visiveis.push(el);
    const alvo = el.querySelector('.ev-txt');
    if (!alvo) return;
    const puro = alvo.dataset.puro || (alvo.dataset.puro = alvo.textContent);
    if (ok && bruto.length > 1) {
      const re = new RegExp('(' + esc(bruto) + ')', 'gi');
      alvo.innerHTML = semAcento(puro).match(re)
        ? puro.replace(new RegExp('(' + esc(bruto) + ')', 'gi'), '<mark>$1</mark>') : puro;
    } else if (alvo.innerHTML !== puro) { alvo.textContent = puro; }
  });
  document.getElementById('conta').textContent = visiveis.length;
  document.getElementById('vazio').hidden = visiveis.length > 0;
  const p = new URLSearchParams();
  if (bruto) p.set('q', bruto);
  if (c) p.set('conf', c);
  if (tema) p.set('tema', tema);
  if (soOrf) p.set('orfaos', '1');
  history.replaceState(null, '', p.toString() ? '?' + p : location.pathname);
}

let tempo;
function agenda(){ clearTimeout(tempo); tempo = setTimeout(filtra, 110); }
[cx, fc, ft, orf].forEach(el => el && el.addEventListener('input', agenda));

/* estado vem da URL, e a lista e filtrada no load — bfcache devolvia campo
   preenchido com a lista inteira e o contador mentindo */
if (lista) {
  const u = new URLSearchParams(location.search);
  if (u.get('q')) cx.value = u.get('q');
  if (u.get('conf')) fc.value = u.get('conf');
  if (u.get('tema')) ft.value = u.get('tema');
  if (u.get('orfaos')) orf.checked = true;
  filtra();
  /* deep link com filtro ativo caia num item escondido: limpa e vai */
  if (location.hash && document.querySelector(location.hash)?.hidden) {
    cx.value = ''; fc.value = ''; ft.value = ''; if (orf) orf.checked = false;
    filtra(); document.querySelector(location.hash).scrollIntoView();
  }
}

/* setas percorrem os resultados sem tirar a mao do teclado */
if (cx) cx.addEventListener('keydown', ev => {
  if (!['ArrowDown','ArrowUp','Enter'].includes(ev.key) || !visiveis.length) return;
  ev.preventDefault();
  if (ev.key === 'Enter' && cursor >= 0) { location.hash = visiveis[cursor].id; return; }
  visiveis.forEach(el => el.classList.remove('selecionado'));
  cursor = ev.key === 'ArrowDown'
    ? Math.min(cursor + 1, visiveis.length - 1) : Math.max(cursor - 1, 0);
  const alvo = visiveis[cursor];
  alvo.classList.add('selecionado');
  alvo.scrollIntoView({block:'nearest', behavior:'smooth'});
});

/* ---- voltar ao topo ------------------------------------------------- */
const topo = document.getElementById('ao-topo');
if (topo) {
  addEventListener('scroll', () => { topo.hidden = scrollY < 700; }, {passive:true});
  topo.onclick = () => scrollTo({top:0, behavior:'smooth'});
}
"""


SITE = "https://seculo-perdido.vercel.app"
NAV = [("/", "index.html", "Hipóteses"), ("/grafo", "grafo.html", "Grafo"),
       ("/evidencias", "evidencias.html", "Evidências"), ("/metodo", "metodo.html", "Método")]


def cabeca(titulo: str, desc: str, ativo: str) -> str:
    url = SITE + next((u for u, a, _ in NAV if a == ativo), "/")
    marca_atual = ' aria-current="page"'
    itens = "".join(
        f'<a href="{u}"{marca_atual if a == ativo else ""}>{r}</a>'
        for u, a, r in NAV)
    return f"""<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{html.escape(titulo)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="Século Perdido">
<meta property="og:locale" content="pt_BR">
<meta property="og:image" content="{SITE}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Século Perdido — arquivo de evidências sobre o que é o One Piece">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(titulo)}">
<meta name="twitter:description" content="{html.escape(desc)}">
<meta name="twitter:image" content="{SITE}/og.png">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/og.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bangers&family=Baloo+2:wght@500;600;700&family=Nunito:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="estilo.css">
</head><body>
<header class="topo"><div class="env">
  <a class="marca" href="/">Século<span>·</span>Perdido</a>
  <nav class="topo-nav">{itens}</nav>
</div></header>"""


RODAPE = """<footer><div class="env">
<p><strong>Fontes.</strong> Os átomos de evidência são paráfrases nossas de material da
<a href="https://onepiece.fandom.com" rel="noopener">One Piece Wiki</a>, disponível sob
<a href="https://creativecommons.org/licenses/by-sa/3.0/" rel="noopener">CC BY-SA 3.0</a>;
alguns citam análises de tradução do
<a href="https://thelibraryofohara.com" rel="noopener">The Library of Ohara</a>, com atribuição
no campo <code>fonte_url</code> de cada átomo. Os dados deste site são publicados sob a mesma
licença CC BY-SA 3.0. Nenhum scan ou scanlation é usado.</p>
<p><strong>Spoilers</strong> até o capítulo 1190. <em>One Piece</em> é obra de Eiichiro Oda,
publicada pela Shueisha — este é um projeto de fã, sem vínculo com os detentores dos direitos.</p>
<p><strong>Licenças.</strong> O código é MIT; os dados de <code>data/</code> são CC BY-SA 3.0,
pela cláusula share-alike da fonte.</p>
<p><a href="__REPO__">__REPO_CURTO__</a> ·
<a href="__REPO__/commits/main">histórico de mudanças</a> ·
atualizado em <time datetime="__DATA_ISO__">__DATA__</time></p>
</div></footer></body></html>"""


def pagina_hipoteses(evid, hips, meta) -> str:
    vivas = [h for h in hips if h.get("escopo") == "one_piece" and h["status"] == "viva"]
    outras = [h for h in hips if h.get("escopo") != "one_piece" and h["status"] != "refutada"]
    mortas = [h for h in hips if h["status"] == "refutada"]

    def bloco(h, i=0):
        st = h.get("status", "viva")
        ferida = "ferida" in (h.get("redteam") or "").lower()
        selos = [f'<span class="selo">{ROTULO_ESCOPO.get(h.get("escopo"), "—")}</span>']
        if ferida and st == "viva":
            selos.append('<span class="selo ferida">ferida pelo red team</span>')
        if st == "refutada":
            selos.append('<span class="selo ferida">refutada</span>')
        selos.append(f'<span class="selo" title="probabilidade atribuída antes de olhar '
                     f'as evidências">a priori {h.get("prior", 0):.2f}</span>'.replace(
                         f'{h.get("prior", 0):.2f}', f'{h.get("prior", 0):.2f}'.replace(".", ",")))
        pct = (f'{h["fatia"]*100:.0f}<small style="font-size:.55em">%</small>'
               if h["fatia"] else ('†' if st == "refutada" else '—'))
        apo = "".join(
            f'<div class="elo"><a class="ev" href="/evidencias#{e["ev"]}">{e["ev"]}</a>'
            f'<div><div class="como">{html.escape(e.get("como", ""))}</div>'
            f'<div class="peso">peso {e.get("peso", 0)} · '
            f'{html.escape(str(evid.get(e["ev"], {}).get("fonte", "?")))}</div></div></div>'
            for e in h.get("apoia") or [])
        con = "".join(
            f'<div class="elo contra"><a class="ev" href="/evidencias#{e["ev"]}">{e["ev"]}</a>'
            f'<div><div class="como">{html.escape(e.get("como", ""))}</div>'
            f'<div class="peso">peso {e.get("peso", 0)} · '
            f'{html.escape(str(evid.get(e["ev"], {}).get("fonte", "?")))}</div></div></div>'
            for e in h.get("contradiz") or [])
        prev = "".join(
            f'<div class="prev"><b>{p.get("status", "")}</b>'
            f'<span>{html.escape(p.get("texto", ""))}</span></div>'
            for p in h.get("prediz") or [])
        rt = (f'<details class="rt"><summary>relatório do red team</summary>'
              f'<div class="rt-corpo">{markdown_leve(h["redteam"], 5)}</div></details>'
              ) if h.get("redteam") else ""
        legenda = (f'{h["fatia"]*100:.0f}% da probabilidade repartida'
                   if h["fatia"] else "fora do escopo do tesouro")
        estado = ", ferida pelo red team" if (ferida and st == "viva") else ""
        return f"""<article class="hip" id="{h['id']}" data-rank="{i}" data-status="{st}">
<details>
  <summary class="hip-cab">
    <span class="hip-id" aria-hidden="true">{h["id"]}</span>
    <h3 class="hip-enun">{html.escape(h.get("enunciado", ""))}
      <span class="sr-only"> — {h["id"]}, {legenda}, hipótese {st}{estado}</span></h3>
    <span class="hip-pct" aria-hidden="true">{pct}</span>
    <span class="sonda" style="--pct:{max(h['fatia']*100, 1):.1f}%" aria-hidden="true"><i></i></span>
    <span class="hip-meta" aria-hidden="true">{"".join(selos)}
      <a class="perma" href="#{h['id']}" title="link para esta hipótese">§</a></span>
  </summary>
  <div class="corpo">
    {markdown_leve(h.get("corpo", ""))}
    <h4>Evidências a favor · {len(h.get("apoia") or [])}</h4>{apo or "<p>—</p>"}
    <h4>Evidências contra · {len(h.get("contradiz") or [])}</h4>{con or "<p>—</p>"}
    <h4>Previsões falseáveis</h4>{prev or "<p>—</p>"}
    {rt}
  </div>
</details></article>"""

    return (cabeca("Século Perdido — o que é o One Piece, por evidência",
                   "Hipóteses ranqueadas sobre o mistério central de One Piece, cada uma "
                   "ligada a evidência verificável e atacada por um red team.", "index.html") +
            f"""<main>
<div class="capa env">
  <div class="rotulo">arquivo de evidências · atualizado no capítulo {meta['cap']}</div>
  <h1>O que é o <em>One&nbsp;Piece</em>?</h1>
  <p class="sub">Não é um blog de teorias. Toda afirmação aqui aponta para um átomo de
  evidência verificável, toda hipótese arrisca previsões que podem dar errado, e um
  validador determinístico recusa qualquer coisa que não tenha fonte.</p>
  <div class="painel">
    <div><b data-alvo="{meta['n_ev']}">{meta['n_ev']}</b><small>átomos de evidência</small></div>
    <div><b data-alvo="{meta['n_hip']}">{meta['n_hip']}</b><small>hipóteses</small></div>
    <div><b data-alvo="{meta['n_mortas']}">{meta['n_mortas']}</b><small>refutadas</small></div>
    <div><b data-alvo="{meta['n_rt']}">{meta['n_rt']}</b><small>ataques de red team</small></div>
  </div>
</div>

<section><div class="env">
  <div class="cab"><h2>As alternativas</h2><span class="n">{len(vivas)} hipóteses · o que é o tesouro</span></div>
  <p class="intro">A porcentagem é a repartição da probabilidade entre hipóteses mutuamente
  exclusivas — e ela assume que a resposta certa está entre as listadas, que é justamente o
  que não se pode garantir. Abra o dossiê de cada uma para ver os elos, as previsões e o ataque que sofreu.</p>
  {"".join(bloco(h, i) for i, h in enumerate(vivas))}
</div></section>

<section><div class="env">
  <div class="cab"><h2>Fora do tesouro</h2><span class="n">{len(outras)} auxiliares</span></div>
  <p class="intro">Estas não disputam a pergunta central: podem ser verdadeiras ao mesmo
  tempo que qualquer uma das anteriores.</p>
  {"".join(bloco(h) for h in outras)}
</div></section>

<section><div class="env">
  <div class="cab"><h2>Cemitério</h2><span class="n">{len(mortas)} refutadas</span></div>
  <p class="intro">A parte mais valiosa do arquivo. Cada uma traz escrito o que a matou —
  é isso que impede o projeto de reinventar a mesma teoria ruim daqui a seis meses.</p>
  {"".join(bloco(h) for h in mortas)}
</div></section>
</main>
<button id="ao-topo" hidden aria-label="Voltar ao topo">↑</button>""" + RODAPE)


def pagina_evidencias(evid, hips, meta) -> str:
    # backlink: quem cita cada átomo. Os dados já existiam, faltava inverter o dicionário.
    citado = {}
    for h in hips:
        for rotulo in ("apoia", "contradiz"):
            for e in h.get(rotulo) or []:
                citado.setdefault(e["ev"], []).append((h["id"], rotulo, h.get("status")))

    cont_tema = Counter(x for e in evid.values() for x in (e.get("temas") or []))
    cont_conf = Counter(e.get("confiabilidade", "") for e in evid.values())
    temas = sorted(cont_tema, key=lambda x: sem_acento(x).casefold())

    itens = []
    for ident, e in sorted(evid.items()):
        conf = e.get("confiabilidade", "")
        tipo = e.get("tipo", "")
        tags = (f'<span class="tag {conf}">{ROTULO_CONF.get(conf, conf)}</span>'
                f'<span class="tag">{html.escape(ROTULO_TIPO.get(tipo, tipo))}</span>' +
                "".join(f'<span class="tag">{html.escape(x)}</span>'
                        for x in (e.get("temas") or [])[:4]))
        url = e.get("fonte_url", "")
        fonte = (f'<a class="fonte" href="{html.escape(url)}" rel="noopener nofollow" '
                 f'aria-label="verificar fonte de {ident}">verificar fonte</a>' if url else "")
        refs = citado.get(ident, [])
        if refs:
            cita = '<div class="ev-cita">citado por ' + " ".join(
                f'<a href="/#{hid}" class="cita {rot}" title="{hid} {rot} este átomo">'
                f'{hid}<i>{"apoia" if rot == "apoia" else "contradiz"}</i></a>'
                for hid, rot, _ in refs) + "</div>"
        else:
            cita = '<div class="ev-cita orfao">órfão — nenhuma hipótese cita este átomo</div>'
        busca = sem_acento(" ".join([
            ident, str(e.get("texto", "")), str(e.get("fonte", "")),
            " ".join(e.get("temas") or []), " ".join(e.get("atores") or []),
            " ".join(h for h, _, _ in refs)]).lower())
        itens.append(f"""<article class="ev-item" id="{ident}" data-conf="{conf}"
 data-temas="|{html.escape("|".join(e.get("temas") or []))}|"
 data-orfao="{'1' if not refs else '0'}"
 data-busca="{html.escape(busca)}" aria-labelledby="t-{ident}">
  <div><a class="ev-id" id="t-{ident}" href="#{ident}">{ident}</a>
  <span class="ev-cap">{html.escape(str(e.get("fonte", "")))}</span></div>
  <div><div class="ev-txt">{html.escape(str(e.get("texto", "")))}</div>
  <div class="ev-tags">{tags} {fonte}</div>{cita}</div>
</article>""")

    ops_c = "".join(
        f'<option value="{c}">{ROTULO_CONF.get(c, c)} ({n})</option>'
        for c, n in sorted(cont_conf.items(), key=lambda x: -x[1]) if c)
    ops_t = "".join(f'<option value="{html.escape(x)}">{html.escape(x)} ({cont_tema[x]})</option>'
                    for x in temas)
    n_orf = sum(1 for i in evid if i not in citado)
    return (cabeca("Evidências — Século Perdido",
                   "Todos os átomos de evidência do arquivo, com fonte, confiabilidade e "
                   "as hipóteses que os citam.",
                   "evidencias.html") + f"""<main><section style="border-top:0"><div class="env">
  <div class="cab"><h1>Átomos de evidência</h1>
    <span class="n"><span id="conta" aria-live="polite">{len(evid)}</span> de {len(evid)}</span></div>
  <p class="intro">Um átomo é uma afirmação verificável, com fonte e nível de confiabilidade.
  Ele não interpreta — interpretar é papel das hipóteses. Quando a afirmação depende da escolha
  do tradutor, ela é marcada como <em>tradução disputada</em> e seu peso fica limitado.
  Cada átomo mostra quais hipóteses o citam, e em que direção.</p>
  <form class="busca" role="search" onsubmit="return false">
    <label class="sr-only" for="busca">Buscar átomo por texto, personagem, tema ou ID</label>
    <input id="busca" type="search" placeholder="buscar por texto, personagem, tema ou ID…"
           autocomplete="off">
    <label class="sr-only" for="filtro-conf">Filtrar por confiabilidade</label>
    <select id="filtro-conf"><option value="">qualquer confiabilidade</option>{ops_c}</select>
    <label class="sr-only" for="filtro-tema">Filtrar por tema</label>
    <select id="filtro-tema"><option value="">todos os temas</option>{ops_t}</select>
    <label class="g-chip"><input type="checkbox" id="so-orfaos">só órfãos ({n_orf})</label>
  </form>
  <div id="lista-ev">{"".join(itens)}</div>
  <p class="vazio" id="vazio" hidden>Nenhum átomo corresponde a esta busca.</p>
</div></section>
<button id="ao-topo" hidden aria-label="Voltar ao topo">↑</button></main>""" + RODAPE)


def pagina_metodo(meta) -> str:
    return (cabeca("Método — Século Perdido",
                   "Como o arquivo funciona: átomos, hipóteses, red team e o portão que "
                   "recusa afirmação sem fonte.", "metodo.html") + f"""<main>
<section style="border-top:0"><div class="env">
  <div class="cab"><h1>Como isto funciona</h1></div>
  <p class="intro">O problema clássico da teoria de fandom é que ela é elástica: se molda a
  qualquer capítulo novo e nunca pode estar errada. Este arquivo foi construído para tornar
  isso impossível.</p>

  <div class="grade passos">
    <div class="card"><h3>Átomo</h3><p>Uma afirmação verificável sobre a obra, com fonte,
    capítulo e confiabilidade declarada. Não interpreta. Se não existe átomo, a afirmação
    não pode ser feita — nem por quem escreve.</p></div>
    <div class="card"><h3>Hipótese</h3><p>Uma proposição sobre o mistério, ligada aos átomos
    que a apoiam <em>e aos que a contradizem</em>, com previsões que podem dar errado.
    Sem previsão falseável, não entra.</p></div>
    <div class="card"><h3>Red team</h3><p>Cada hipótese é atacada por um leitor hostil que
    <strong>não vê os argumentos a favor</strong> — só o enunciado, as previsões e a base de
    evidência. O relatório de ataque fica publicado junto.</p></div>
    <div class="card"><h3>Portão</h3><p>Um validador sem IA recusa o commit se uma citação
    apontar para átomo inexistente ou se a justificativa não corresponder ao texto citado.
    É o que impede alucinação de virar conteúdo.</p></div>
  </div>

  <div class="cab" style="margin-top:3.4rem"><h2>O que não sabemos</h2></div>
  <p class="intro">Três limites que o próprio arquivo mede e publica, em vez de esconder.</p>
  <blockquote>A porcentagem assume que a resposta certa está entre as hipóteses listadas.
  Essa é a premissa mais frágil de todas, e nenhum teste estatístico a alcança — só
  formular alternativas novas.</blockquote>
  <blockquote>Boa parte da evidência vem do arco em publicação, e leitura recente pesa mais
  do que deveria. O cálculo limita quanto um mesmo arco pode empurrar, e o resultado é
  medido a cada rodada.</blockquote>
  <blockquote>Tradução é a superfície de ataque mais barata: várias correções aqui vieram de
  descobrir que a paráfrase em inglês tinha uma palavra que o japonês não tem.</blockquote>

  <div class="cab" style="margin-top:3rem"><h2>Acompanhar</h2></div>
  <p class="intro">O arquivo é atualizado a cada capítulo novo. O histórico do repositório é
  parte do projeto: o valor não é a teoria final, é o rastro de uma hipótese subindo e caindo
  ao longo dos capítulos. Estado atual: capítulo {meta['cap']}, {meta['n_ev']} átomos.</p>
</div></section></main>
<button id="ao-topo" hidden aria-label="Voltar ao topo">↑</button>""" + RODAPE)


def pagina_grafo(meta) -> str:
    chips = "".join(
        f'<label class="g-chip"><input type="checkbox" data-tipo="{t}"{" checked" if c else ""}>'
        f'<i style="background:{cor}"></i>{t}</label>'
        for t, cor, c in [("APOIA", "#2f9e6e", True), ("CONTRADIZ", "#e03131", True),
                          ("CONCORRE_COM", "#9a9086", True), ("TEM_TEMA", "#1a7fb5", False),
                          ("MENCIONA", "#7048a8", False)])
    leg = "".join(f'<span class="g-leg"><i style="background:{c}"></i>{n}</span>'
                  for n, c in [("hipótese", "#ffb703"), ("canônico", "#2f9e6e"),
                               ("ambíguo", "#e8a13a"), ("trad. disputada", "#e03131"),
                               ("tema", "#1a7fb5"), ("ator", "#7048a8")])
    return (cabeca("Grafo — Século Perdido",
                   "Explorador do grafo de evidências: nós com propriedades e relações "
                   "tipadas entre hipóteses, átomos, temas e personagens.", "grafo.html") +
            f"""<main><section style="border-top:0;padding-top:2rem"><div class="env">
  <div class="cab"><h1>O grafo</h1><span class="n">{meta['n_nos']} nós · {meta['n_rels']} relações</span></div>
  <p class="intro">Cada ligação tem um tipo e propriedades próprias — não é só "estão
  conectados". Uma aresta <code>:APOIA</code> carrega o peso e a justificativa que ligam
  aquele átomo àquela hipótese. Comece pelas hipóteses e vá abrindo: clique para ver as
  propriedades, duplo clique para expandir as ligações, arraste para reorganizar, role para
  aproximar.</p>
  <div class="g-wrap">
    <div class="g-tela">
      <div class="g-barra">
        <input id="g-busca" type="search" placeholder="buscar e centralizar…" autocomplete="off">
        {chips}
        <button class="g-bt" id="g-tudo">abrir tudo</button>
        <button class="g-bt" id="g-reset">recomeçar</button>
      </div>
      <canvas id="cv"></canvas>
      <div class="g-legenda">{leg}</div>
      <div class="g-conta" id="g-conta"></div>
    </div>
    <aside id="painel"></aside>
  </div>
  <p class="intro" style="margin-top:1.4rem">O contorno tracejado marca <strong>átomo
  órfão</strong>: evidência que ainda não pertence a nenhuma hipótese. Acúmulo de órfãos é o
  sintoma de uma alternativa que ninguém formulou — foi assim que três hipóteses deste
  arquivo nasceram.</p>
</div></section></main>
<button id="ao-topo" hidden aria-label="Voltar ao topo">↑</button>""" + RODAPE)


def main() -> int:
    evid, hips = carregar()
    SAIDA.mkdir(exist_ok=True)
    caps = [int(i.split("-")[1]) for i in evid if i.split("-")[1].isdigit()]
    meta = {
        "n_ev": len(evid), "n_hip": len(hips),
        "n_mortas": sum(1 for h in hips if h["status"] == "refutada"),
        "n_rt": len(list((RAIZ / "data" / "hipoteses").glob("*.redteam.md"))),
        "cap": max(caps) if caps else 0,
        "n_nos": 0, "n_rels": 0,
    }
    gj = SAIDA / "grafo.json"
    if gj.exists():
        g = json.loads(gj.read_text(encoding="utf-8"))["meta"]
        meta["n_nos"], meta["n_rels"] = g["n_nos"], g["n_rels"]
    repo = git("remote", "get-url", "origin", padrao="")
    repo = re.sub(r"\.git$", "", repo) or "https://github.com/pedropasinn/seculo-perdido"
    iso = git("log", "-1", "--format=%cI", padrao="")[:19] or "2026-08-11T00:00:00"
    dia, mes, ano = iso[8:10], iso[5:7], iso[0:4]
    MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
             "agosto", "setembro", "outubro", "novembro", "dezembro"]
    legivel = f"{int(dia)} de {MESES[int(mes)]} de {ano}"
    rodape = (RODAPE.replace("__REPO__", repo)
              .replace("__REPO_CURTO__", repo.replace("https://github.com/", ""))
              .replace("__DATA_ISO__", iso).replace("__DATA__", legivel))
    global RODAPE_ATUAL
    paginas = {
        "index.html": pagina_hipoteses(evid, hips, meta),
        "evidencias.html": pagina_evidencias(evid, hips, meta),
        "metodo.html": pagina_metodo(meta),
        "grafo.html": pagina_grafo(meta),
    }
    for nome, conteudo in paginas.items():
        (SAIDA / nome).write_text(conteudo.replace(RODAPE, rodape), encoding="utf-8")
    (SAIDA / "estilo.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    (SAIDA / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    urls = "".join(
        f"<url><loc>{SITE}{u}</loc><lastmod>{iso[:10]}</lastmod></url>" for u, _, _ in NAV)
    (SAIDA / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + "</urlset>",
        encoding="utf-8")
    (SAIDA / "app.js").write_text(JS.strip() + "\n", encoding="utf-8")
    for nome in paginas:
        p = SAIDA / nome
        js = "grafo.js" if nome == "grafo.html" else "app.js"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "</body>", f'<script src="{js}"></script></body>'), encoding="utf-8")
    print(f"{SAIDA}  ({meta['n_ev']} atomos, {meta['n_hip']} hipoteses, cap {meta['cap']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
