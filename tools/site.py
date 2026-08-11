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
        _s = score.pontuar(meta, evid)
        meta["posterior"] = _s["posterior"]
        meta["detalhe"] = _s["detalhe"]
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
/* a fonte de fallback e ajustada para ocupar o mesmo espaco da Bangers.
   Sem isto o titulo da capa encolhia de 94px para 47px quando a fonte chegava,
   e a pagina inteira subia junto: CLS medido de 0,179. */
@font-face{font-family:"Bangers-fb";src:local("Impact"),local("Haettenschweiler"),local("Arial Black");
  size-adjust:62.7%;ascent-override:105%;descent-override:24%;line-gap-override:0%}
:root{
  /* Grand Line: mar, tesouro, bandeira, pergaminho */
  --papel:#fff6e2; --papel-2:#ffeecb; --tinta:#151016;
  --vermelho:#e03131; --vermelho-esc:#a51d1d;
  --ouro:#ffb703; --ouro-esc:#e08e00;
  --mar:#166d9c; --mar-esc:#0d5580;
  --verde:#217a53; --roxo:#7048a8;
  --sombra:6px 6px 0 var(--tinta);
  --sombra-sm:3px 3px 0 var(--tinta);
  --display:"Bangers","Bangers-fb",Impact,sans-serif;
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
    radial-gradient(rgba(21,16,22,.085) 1px, transparent 1.1px),
    linear-gradient(180deg,var(--papel-2),var(--papel) 22rem);
  background-size:22px 22px, 100% 100%;
  background-attachment:fixed;
}
body::before{ /* halftone de canto, como sombreado de mangá */
  content:"";position:fixed;right:-8rem;top:-8rem;width:26rem;height:26rem;z-index:0;
  pointer-events:none;opacity:.07;border-radius:50%;
  background:radial-gradient(var(--vermelho) 1.4px,transparent 1.6px);background-size:14px 14px;
  -webkit-mask-image:radial-gradient(circle,#000 40%,transparent 72%);
  mask-image:radial-gradient(circle,#000 40%,transparent 72%);
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
.capa .sub{margin:1.8rem auto 0;max-width:56ch;font-size:1.12rem;font-weight:500;
  background:var(--papel);padding:1rem 1.3rem;border-radius:14px;
  border:2.5px solid var(--tinta);box-shadow:var(--sombra-sm)}
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
.cab h1,.cab h2{font:400 2.5rem/1 var(--display);letter-spacing:.03em;text-transform:uppercase;
  color:var(--tinta);text-shadow:0 0 6px var(--papel),0 0 12px var(--papel)}
.cab h1::after,.cab h2::after{content:"";display:block;height:5px;background:var(--ouro);
  border:2.5px solid var(--tinta);border-radius:3px;margin-top:.2rem}
.cab .n{font:700 .78rem/1 var(--mono);background:var(--tinta);color:var(--papel);
  padding:.34rem .6rem;border-radius:999px}
.intro{margin-bottom:2rem;font-weight:500;background:var(--papel);
  padding:.95rem 1.2rem;border-radius:12px;border:2px solid rgba(21,16,22,.14);
  box-shadow:3px 3px 0 rgba(21,16,22,.07)}

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
  color:var(--vermelho-esc);margin:1.6rem 0 .6rem}
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
.busca input[type=search],.busca select{background:var(--papel);border:3px solid var(--tinta);
  color:var(--tinta);padding:.7rem .9rem;border-radius:12px;box-shadow:var(--sombra-sm);
  font:600 .95rem var(--corpo)}
.busca input[type=search]{flex:1;min-width:15rem}
.busca input[type=search]:focus-visible,.busca select:focus-visible{outline:3px solid var(--tinta);
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
blockquote{background:var(--papel-2);border:3px solid var(--tinta);
  border-radius:12px;padding:1.1rem 1.3rem 1.1rem 3.1rem;margin:1.1rem 0;max-width:64ch;
  font-weight:500;box-shadow:var(--sombra-sm);position:relative}
blockquote::before{content:"\201C";position:absolute;left:.7rem;top:.1rem;
  font:400 3.2rem/1 var(--display);color:var(--ouro)}

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
.tabela{width:100%;border-collapse:separate;border-spacing:0;margin:1rem 0;
  border:3px solid var(--tinta);border-radius:14px;overflow:hidden;background:var(--papel);
  box-shadow:var(--sombra)}
.tabela th{background:var(--tinta);color:var(--papel);font:700 .72rem/1 var(--titulo);
  text-transform:uppercase;letter-spacing:.05em;padding:.7rem .9rem;text-align:left}
.tabela td{padding:.65rem .9rem;border-top:2px solid rgba(21,16,22,.12);font-size:.92rem}
.tabela tr:nth-child(even) td{background:var(--papel-2)}
.tabela .num{text-align:right;font:700 .8rem var(--mono);white-space:nowrap}
.tabela a{font-weight:700}
.botao-grande{display:inline-block;background:var(--ouro);border:3px solid var(--tinta);
  border-radius:12px;padding:.7rem 1.2rem;font:400 1.35rem/1 var(--display);
  letter-spacing:.03em;text-transform:uppercase;text-decoration:none;
  box-shadow:var(--sombra);transition:transform .14s;margin:0 .5rem .5rem 0}
.botao-grande:hover{transform:translate(-2px,-3px)}
.botao-grande.alt{background:var(--mar);color:#fff}
pre.cmd{background:var(--tinta);color:#e7ddc9;border-radius:10px;padding:.7rem .9rem;
  margin:.6rem 0;overflow-x:auto;font:.78rem/1.55 var(--mono);white-space:pre}
.card pre.cmd{font-size:.72rem}
.estado{max-width:62ch;margin:2.4rem auto 0;background:var(--papel);border:3px solid var(--tinta);
  border-radius:16px;box-shadow:var(--sombra);padding:1.2rem 1.4rem;text-align:left}
.estado p{margin:.5rem 0}
.estado b{font:400 1.25rem/1 var(--display);letter-spacing:.03em;text-transform:uppercase;
  color:var(--vermelho);display:block;margin-bottom:.2rem}
.estado .miudo{font-size:.9rem;opacity:.8;border-top:2px dotted rgba(21,16,22,.2);
  padding-top:.6rem;margin-top:.8rem}
.legenda-rot{display:grid;gap:.5rem;margin:-.6rem 0 1.8rem}
.legenda-rot div{display:grid;grid-template-columns:9.5rem 1fr;gap:.7rem;align-items:baseline}
.legenda-rot dd{font-size:.9rem;margin:0}
.selo.morta{background:var(--tinta);color:var(--papel)}
.selo.ferida{background:var(--papel-2);color:var(--vermelho-esc);border-color:var(--vermelho);
  border-style:dashed}
.vered{display:inline-flex;align-items:center;gap:.5rem;margin:.2rem 0 1rem;
  font:600 .92rem var(--titulo);background:var(--papel-2);border:2.5px solid var(--tinta);
  border-radius:999px;padding:.35rem .8rem}
.vered b{font:400 1.05rem/1 var(--display);letter-spacing:.04em;text-transform:uppercase;
  color:var(--vermelho)}
.vered.refutada{background:var(--tinta);color:var(--papel)}
.vered.refutada b{color:var(--ouro)}
.conta{font:700 .74rem/1.5 var(--mono);opacity:.72;margin:.3rem 0 1rem;
  border-bottom:2px dotted rgba(21,16,22,.2);padding-bottom:.6rem}
.achados{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:.9rem;
  margin:0 0 1.4rem}
.achado{background:var(--papel);border:3px solid var(--tinta);border-radius:14px;
  box-shadow:var(--sombra-sm);padding:.85rem 1rem;display:flex;gap:.7rem;align-items:flex-start}
.achado b{font:400 2rem/1 var(--display);color:var(--vermelho);letter-spacing:.02em}
.achado:nth-child(2) b{color:var(--mar)}
.achado:nth-child(3) b{color:var(--roxo)}
.achado:nth-child(4) b{color:var(--verde)}
.achado span{font-size:.86rem;font-weight:500;line-height:1.4}
.tabela-grafo{margin:1.4rem 0;border:3px solid var(--tinta);border-radius:14px;
  background:var(--papel);box-shadow:var(--sombra-sm)}
.tabela-grafo>summary{cursor:pointer;padding:.8rem 1rem;font:400 1.15rem/1 var(--display);
  letter-spacing:.04em;text-transform:uppercase}
.tabela-grafo .tabela{margin:0 1rem 1rem;box-shadow:none}
.tabela-grafo .intro{margin:0 1rem 1rem}
.ico{vertical-align:-.22em;margin-right:.45rem;color:var(--vermelho)}
.linha{list-style:none;margin:1.5rem 0;padding:0;position:relative}
.linha::before{content:"";position:absolute;left:8.4rem;top:.5rem;bottom:.5rem;width:4px;
  background:repeating-linear-gradient(180deg,var(--tinta) 0 8px,transparent 8px 14px)}
.marco{display:grid;grid-template-columns:8.4rem 1fr;gap:1.6rem;margin-bottom:1.1rem;
  position:relative}
.marco::before{content:"";position:absolute;left:7.75rem;top:1.15rem;width:1.35rem;
  height:1.35rem;border-radius:50%;background:var(--ouro);border:3px solid var(--tinta);z-index:1}
.marco.ambigua::before{background:var(--papel-2)}
.marco.disputada::before{background:var(--vermelho)}
.marco-data{text-align:right;font:700 .78rem/1.4 var(--mono);padding-top:1.2rem;opacity:.75}
.marco-corpo{background:var(--papel);border:3px solid var(--tinta);border-radius:14px;
  box-shadow:var(--sombra-sm);padding:.9rem 1.1rem}
.marco-corpo h3{font:400 1.4rem/1.15 var(--display);letter-spacing:.03em;
  text-transform:uppercase;margin-bottom:.4rem;display:flex;align-items:center}
.marco-corpo p{font-size:.94rem;margin:.35rem 0}
.marco-ev{margin-top:.6rem;display:flex;gap:.4rem;flex-wrap:wrap}
.marco-ev a{font:700 .68rem var(--mono);text-decoration:none;background:var(--papel-2);
  border:2px solid var(--tinta);border-radius:999px;padding:.22rem .45rem}
.marco-ev a:hover{background:var(--ouro)}
.legenda-cert{display:flex;gap:1.1rem;flex-wrap:wrap;align-items:center;
  font:700 .72rem var(--titulo);text-transform:uppercase;letter-spacing:.03em;margin:-.6rem 0 1.2rem}
.legenda-cert .pt{width:.9rem;height:.9rem;border-radius:50%;border:2.5px solid var(--tinta);
  display:inline-block;margin-right:.25rem;vertical-align:-.1em}
.legenda-cert .pt.canonica{background:var(--ouro)}
.legenda-cert .pt.ambigua{background:var(--papel-2)}
.legenda-cert .pt.disputada{background:var(--vermelho)}
@media(max-width:620px){
  .linha::before{left:.55rem}
  .marco{grid-template-columns:1fr;gap:.3rem;padding-left:2.2rem}
  .marco::before{left:0;top:.4rem}
  .marco-data{text-align:left;padding-top:0}
}
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
#cv{width:100%;height:100%;display:block;cursor:grab;touch-action:pan-y}
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
.g-ajustes{position:relative}
.g-ajustes[open]>summary{background:var(--tinta);color:var(--ouro)}
.g-ajustes summary{list-style:none}
.g-ajustes summary::-webkit-details-marker{display:none}
.g-ctrl{position:absolute;top:2.4rem;left:0;z-index:5;width:17rem;background:var(--papel);
  border:3px solid var(--tinta);border-radius:14px;box-shadow:var(--sombra);padding:.8rem;
  display:flex;flex-direction:column;gap:.55rem;max-height:60vh;overflow-y:auto}
.g-ctrl label{display:grid;font:700 .66rem/1.3 var(--titulo);text-transform:uppercase;
  letter-spacing:.03em;gap:.2rem}
.g-ctrl output{font:700 .72rem var(--mono);color:var(--mar);justify-self:end;margin-top:-1rem}
.g-ctrl input[type=range]{width:100%;accent-color:var(--vermelho);margin:0}
.g-ctrl select{border:2px solid var(--tinta);border-radius:8px;padding:.25rem;
  font:600 .74rem var(--corpo);background:var(--papel)}
.g-ctrl .g-check{display:flex;flex-direction:row;align-items:center;gap:.4rem;text-transform:none}
.g-ctrl .g-bt{margin-top:.3rem}
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
  .g-tela{height:60vh}#painel{max-height:24rem}
  .g-ajustes{position:static}
  .g-ctrl{position:static;width:100%;max-height:none;margin-top:.5rem}
  .g-barra{position:static;padding:.7rem .7rem 0}
  .g-tela{display:flex;flex-direction:column;height:auto}
  #cv{height:56vh;min-height:20rem}}
@media(prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important}
  html{scroll-behavior:auto}
}
.perma-linha{margin:0 0 .4rem}
.perma{text-decoration:none;font:700 .72rem var(--mono);opacity:.55;
  padding:.35rem .5rem;border-radius:6px;display:inline-block;min-height:1.6rem}
.perma:hover,.perma:focus-visible{opacity:1;background:var(--ouro)}
.ev-cita .cita{padding:.35rem .55rem}
.ev-cita .cita i{opacity:.78}
.ev-cita.orfao{opacity:.72}
.ev-item a.fonte{display:inline-block;padding:.25rem 0}
.g-ctrl input[type=range]{height:1.6rem}
.g-ctrl .g-check{min-height:1.6rem}
.pula{position:absolute;left:-9999px;top:0;z-index:200;background:var(--ouro);
  border:3px solid var(--tinta);border-radius:0 0 10px 0;padding:.6rem 1rem;
  font:700 .85rem var(--titulo);text-decoration:none}
.pula:focus{left:0}
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
       ("/cronologia", "cronologia.html", "Cronologia"),
       ("/evidencias", "evidencias.html", "Evidências"),
       ("/historico", "historico.html", "Histórico"),
       ("/metodo", "metodo.html", "Método"), ("/dados", "dados.html", "Dados & API")]


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
<link rel="stylesheet" href="/estilo.__HCSS__.css">
</head><body>
<a class="pula" href="#conteudo">Pular para o conteúdo</a>
<header class="topo"><div class="env">
  <a class="marca" href="/">Século<span>·</span>Perdido</a>
  <nav class="topo-nav">{itens}</nav>
</div></header>
<a id="conteudo" tabindex="-1"></a>"""


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
        vered = ""
        if h.get("redteam"):
            m = re.search(r"[Vv]eredito:?\s*\**\s*(refutada|ferida|sobrevive)",
                          h["redteam"])
            sup = re.search(r"(\d+)\s+suposi", h["redteam"])
            if m:
                vered = (f'<p class="vered {m.group(1)}"><b>red team</b> '
                         f'{m.group(1)}'
                         + (f' · {sup.group(1)} suposições sem evidência' if sup else "")
                         + "</p>")
        rt = (vered + f'<details class="rt"><summary>relatório completo do red team</summary>'
              f'<div class="rt-corpo">{markdown_leve(h["redteam"], 5)}</div></details>'
              ) if h.get("redteam") else ""
        cortes = [d.strip() for d in (h.get("detalhe") or []) if "[teto" in d]
        tetos = ("· " + "; ".join(c.replace("[teto cap]", "teto de capítulo em")
                                   .replace("[teto arco]", "teto de arco em")
                                   for c in cortes[:2])) if cortes else ""
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
    <span class="hip-meta" aria-hidden="true">{"".join(selos)}</span>
  </summary>
  <div class="corpo">
    <p class="perma-linha"><a class="perma" href="#{h['id']}"
      aria-label="link permanente para a hipótese {h['id']}">§ link para {h['id']}</a></p>
    <p class="conta">a priori {h.get("prior", 0):.2f} → posterior {h["posterior"]:.2f}
      · {len(h.get("apoia") or [])} apoios, {len(h.get("contradiz") or [])} contradições
      {tetos}</p>
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
  <div class="estado">
    <p><b>Onde estamos.</b> A leitura mais provável hoje é que o One Piece seja
    o <strong>legado dirigido de Joy Boy</strong> — palavras, um pedido e as condições de
    uma promessa, endereçados a quem chegasse depois dele.</p>
    <p>Ela lidera em <strong>100% de 2000 sorteios</strong> que sacodem todos os pesos, e
    continua liderando mesmo jogando fora tudo que foi publicado depois do capítulo 1100.
    Ainda assim está <strong>ferida</strong>: o red team achou seis suposições sem evidência.</p>
    <p class="miudo">O que mudou no capítulo 1190: Gaban diz a Imu que conhece
    <em>as palavras</em> de Joy Boy — e que não pretende segui-las.</p>
  </div>
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
  <dl class="legenda-rot">
    <div><dt><span class="selo">a priori 0,20</span></dt>
      <dd>a probabilidade antes de olhar as evidências, escolhida a mão e justificada por escrito</dd></div>
    <div><dt><span class="selo ferida">ferida</span></dt>
      <dd>sobreviveu ao ataque, mas com custo — <strong>nenhuma das 15 saiu intacta</strong></dd></div>
    <div><dt><span class="selo morta">refutada</span></dt>
      <dd>saiu do páreo; o motivo fica escrito no cemitério, lá embaixo</dd></div>
  </dl>
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
                f'<a href="/#{hid}" class="cita {rot}" '
                f'title="este átomo {rot} a hipótese {hid}">'
                f'<i>{rot}</i>{hid}</a>'
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
    <div class="card"><h3>Curador</h3><p>Alguém decide e assina. O cálculo é insumo, não
    veredito — <strong>um número que muda sem justificativa escrita é inválido</strong>, e a
    justificativa fica versionada junto com o dado.</p></div>
  </div>

  <div class="cab" style="margin-top:3rem"><h2>Quem escreve isto</h2></div>
  <p class="intro">Os átomos, as hipóteses e os ataques são redigidos por agentes de LLM a
  partir das fontes permitidas, sob uma regra que vale mais que todas as outras: <strong>o
  que o modelo lembra não é fonte</strong>. Se uma cena não tem átomo, ela não pode ser
  afirmada — nem por quem escreve. É o oposto do uso comum de IA para teoria de fandom, em
  que o modelo despeja o que acha que lembra. O validador existe justamente porque essa
  regra precisa ser executável, e não apenas prometida.</p>

  <div class="cab" style="margin-top:3rem"><h2>O ranking aguenta?</h2></div>
  <p class="intro">Três testes rodam contra o próprio resultado, e os números ficam
  publicados mesmo quando são desconfortáveis.</p>
  <table class="tabela">
    <thead><tr><th>teste</th><th>o que faz</th><th>resultado</th></tr></thead>
    <tbody>
      <tr><td><code>perturbar</code></td><td>sacode todos os pesos e prioris em 2000 sorteios</td>
        <td>a líder vence em <strong>100%</strong></td></tr>
      <tr><td><code>remover</code></td><td>tira um átomo por vez e remede</td>
        <td>nenhum troca o líder</td></tr>
      <tr><td><code>recencia</code></td><td>joga fora tudo acima do capítulo 1100</td>
        <td>a mesma hipótese lidera</td></tr>
    </tbody>
  </table>
  <p class="intro">Nem sempre foi assim: nas rodadas anteriores a líder vencia 97,9%, depois
  82,1%, depois 66,5% — e houve um momento em que ela caía para penúltima ao cortar o arco
  em publicação. O que consertou não foi o modelo, foi extrair 74 átomos de arcos antigos.</p>

  <div class="cab" style="margin-top:3rem"><h2>O furo que ainda está aberto</h2></div>
  <p class="intro">O cálculo trata cada elo como independente, e não é. Um mesmo átomo
  costuma alimentar várias hipóteses — inclusive hipóteses que se declaram concorrentes.
  Medindo quanto do apoio de cada uma vem de evidência compartilhada:</p>
  <table class="tabela">
    <thead><tr><th>hipótese</th><th>apoio emprestado</th><th class="num">base própria</th></tr></thead>
    <tbody>
      <tr><td>H-05 <em>(a líder)</em></td><td>71,4%</td><td class="num">2,08</td></tr>
      <tr><td>H-02</td><td>55,0%</td><td class="num">1,44</td></tr>
      <tr><td>H-03</td><td>40,9%</td><td class="num">2,08</td></tr>
      <tr><td>H-04</td><td>30,9%</td><td class="num">8,72</td></tr>
      <tr><td>H-08</td><td>23,9%</td><td class="num">5,70</td></tr>
      <tr><td>H-14</td><td>0,0%</td><td class="num">4,62</td></tr>
    </tbody>
  </table>
  <p class="intro">Contando <strong>só evidência exclusiva</strong>, a ordem vira
  <code>H-08 &gt; H-04 &gt; H-14 &gt; H-11 &gt; H-09 &gt; H-05</code> — a líder cai para
  sexto. E há <strong>onze átomos que apoiam pares de hipóteses declaradamente
  concorrentes</strong>, ou seja, evidência que não discrimina sendo contada como positiva
  dos dois lados. Isso não invalida o ranking, mas muda o que ele significa: uma hipótese
  com base emprestada sobe junto com as rivais em vez de vencer delas.</p>
  <blockquote>Este furo foi encontrado por um agente analisando o grafo, não pelos testes
  de sensibilidade — que medem os pesos, nunca a estrutura. Está publicado aqui antes de
  estar consertado.</blockquote>

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


def pagina_grafo(meta, hips=None, evid=None) -> str:
    linhas_tg = []
    for h in (hips or []):
        for rot in ("apoia", "contradiz"):
            for e in h.get(rot) or []:
                txt = html.escape(str((evid or {}).get(e["ev"], {}).get("texto", ""))[:150])
                linhas_tg.append(
                    f'<tr><td>{h["id"]}</td><td>{rot}</td>'
                    f'<td><a href="/evidencias#{e["ev"]}">{e["ev"]}</a></td>'
                    f'<td class="num">{e.get("peso", "")}</td><td>{txt}</td></tr>')
    tabela_grafo = ('<table class="tabela"><thead><tr><th>hipótese</th><th>relação</th>'
                    '<th>átomo</th><th class="num">peso</th><th>o que o átomo diz</th></tr>'
                    '</thead><tbody>' + "".join(linhas_tg) + "</tbody></table>")
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
  <div class="achados">
    <div class="achado"><b>71%</b><span>do apoio da hipótese líder vem de átomos que também
      alimentam rivais — ela sobe junto, em vez de vencer</span></div>
    <div class="achado"><b>19</b><span>átomos decidem entre hipóteses: apoiam uma e
      contradizem outra. Os outros 135 só empurram num sentido</span></div>
    <div class="achado"><b>47%</b><span>do arquivo não pertence a hipótese nenhuma, e não
      está espalhado: 40 desses átomos falam de Shandora, Birka e da lua</span></div>
    <div class="achado"><b>11</b><span>átomos apoiam pares de hipóteses que se declaram
      concorrentes — evidência que não discrimina, contada dos dois lados</span></div>
  </div>
  <div class="g-wrap">
    <div class="g-tela">
      <div class="g-barra">
        <label class="sr-only" for="g-busca">Buscar nó e centralizar</label>
        <input id="g-busca" type="search" placeholder="buscar e centralizar…" autocomplete="off">
        {chips}
        <button class="g-bt" id="g-tudo">abrir tudo</button>
        <button class="g-bt" id="g-reset">recomeçar</button>
        <button class="g-bt" id="g-caber">caber na tela</button>
        <button class="g-bt" id="g-pausa" aria-pressed="false">pausar</button>
        <details class="g-ajustes"><summary class="g-bt">ajustes</summary>
          <div class="g-ctrl">
            <label for="c-repulsao">repulsão <output data-eco="c-repulsao" aria-hidden="true"></output>
              <input id="c-repulsao" aria-label="repulsão" type="range" min="400" max="9000" step="100"></label>
            <label for="c-mola">rigidez das arestas <output data-eco="c-mola" aria-hidden="true"></output>
              <input id="c-mola" aria-label="rigidez das arestas" type="range" min="0.0008" max="0.03" step="0.0008"></label>
            <label for="c-dist">distância de repouso <output data-eco="c-dist" aria-hidden="true"></output>
              <input id="c-dist" aria-label="distância de repouso" type="range" min="50" max="360" step="5"></label>
            <label for="c-grav">gravidade ao centro <output data-eco="c-grav" aria-hidden="true"></output>
              <input id="c-grav" aria-label="gravidade ao centro" type="range" min="0" max="0.008" step="0.0002"></label>
            <label for="c-atrito">atrito <output data-eco="c-atrito" aria-hidden="true"></output>
              <input id="c-atrito" aria-label="atrito" type="range" min="0.5" max="0.98" step="0.01"></label>
            <label for="c-tam">tamanho dos nós <output data-eco="c-tam" aria-hidden="true"></output>
              <input id="c-tam" aria-label="tamanho dos nós" type="range" min="0.5" max="2.4" step="0.1"></label>
            <label>rótulo das arestas
              <select id="c-rot-a"><option value="auto">automático</option>
                <option value="sempre">sempre</option><option value="nunca">nunca</option></select></label>
            <label>rótulo dos nós
              <select id="c-rot-n"><option value="auto">automático</option>
                <option value="sempre">sempre</option><option value="nunca">nunca</option></select></label>
            <label class="g-check"><input id="c-seta" type="checkbox"> setas de direção</label>
            <button class="g-bt" id="g-padrao" type="button">voltar ao padrão</button>
          </div>
        </details>
      </div>
      <canvas id="cv" aria-label="Grafo de {meta['n_nos']} nós e {meta['n_rels']} relações. A mesma informação está na tabela abaixo do explorador."></canvas>
      <div class="g-legenda">{leg}</div>
      <div class="g-conta" id="g-conta"></div>
    </div>
    <aside id="painel"></aside>
  </div>
  <details class="tabela-grafo"><summary>ver as ligações como tabela</summary>
    <p class="intro">Equivalente textual do explorador: cada hipótese com os átomos que a
    apoiam e a contradizem, com peso e justificativa. Navegável por teclado e por leitor de
    tela, sem depender do canvas.</p>
    {tabela_grafo}
  </details>
  <p class="intro" style="margin-top:1.4rem">O contorno tracejado marca <strong>átomo
  órfão</strong>: evidência que ainda não pertence a nenhuma hipótese. Acúmulo de órfãos é o
  sintoma de uma alternativa que ninguém formulou — foi assim que três hipóteses deste
  arquivo nasceram.</p>
</div></section></main>
<button id="ao-topo" hidden aria-label="Voltar ao topo">↑</button>""" + RODAPE)


def pagina_dados(meta, tamanhos) -> str:
    def kb(n):
        return f"{tamanhos.get(n, 0)/1024:.0f} KB"
    arquivos = [
        ("tudo.json", "base inteira, com metadados e vocabulário", "json"),
        ("evidencias.json", f"os {meta['n_ev']} átomos, com quem cita cada um", "json"),
        ("hipoteses.json", "hipóteses com elos, previsões e red team", "json"),
        ("meta.json", "só os metadados — comece por aqui, é leve", "json"),
        ("evidencias.csv", "átomos em planilha", "csv"),
        ("elos.csv", "cada ligação hipótese↔átomo, com peso e justificativa", "csv"),
        ("hipoteses.csv", "hipóteses em planilha", "csv"),
        ("evidencias.ndjson", "um átomo por linha, para pipeline", "ndjson"),
        ("seculo-perdido.md", "tudo em markdown — bom para ler ou dar a um LLM", "md"),
        ("grafo.json", "nós e relações tipadas do explorador", "json"),
    ]
    linhas = "".join(
        f'<tr><td><a href="/dados/{n}" download><code>{n}</code></a></td>'
        f'<td>{d}</td><td class="num">{kb(n)}</td></tr>' for n, d, _ in arquivos)
    return (cabeca("Dados & API — Século Perdido",
                   "Baixe a base inteira em JSON, CSV ou Markdown, ou consulte por "
                   "MCP direto do Claude Code.", "dados.html") +
            f"""<main><section style="border-top:0"><div class="env">
  <div class="cab"><h1>Leve a base inteira</h1>
    <span class="n">CC BY-SA 3.0</span></div>
  <p class="intro">Tudo que está no site sai daqui, e sai em formato aberto. Não há
  cadastro, chave nem limite de requisição — é arquivo estático. Se você for reusar,
  a licença pede atribuição e que a obra derivada mantenha a mesma licença.</p>

  <p style="margin:.5rem 0 2rem">
    <a class="botao-grande" href="/dados/seculo-perdido.zip" download>
      baixar tudo · {kb("seculo-perdido.zip")}</a></p>

  <table class="tabela">
    <thead><tr><th>arquivo</th><th>o que é</th><th class="num">tamanho</th></tr></thead>
    <tbody>{linhas}</tbody>
  </table>

  <div class="cab" style="margin-top:3.4rem"><h2>Perguntar pelo Claude Code</h2></div>
  <p class="intro">Em vez de ler 289 átomos, dá para perguntar. O repositório traz um
  servidor <strong>MCP</strong> que expõe a base como ferramentas de consulta — funciona
  no Claude Code, no Claude Desktop e em qualquer cliente que fale MCP.</p>

  <div class="grade">
    <div class="card"><h3>1. Sem clonar nada</h3>
      <p>Baixe só o servidor e rode em modo remoto: ele lê os dados publicados aqui.</p>
      <pre class="cmd">curl -O https://seculo-perdido.vercel.app/mcp/servidor.py</pre>
      <p>Depois acrescente ao <code>~/.claude.json</code>:</p>
      <pre class="cmd">{{
  "mcpServers": {{
    "seculo-perdido": {{
      "command": "python3",
      "args": ["/caminho/servidor.py", "--remoto"]
    }}
  }}
}}</pre>
      <p>Só precisa de Python 3. Nenhuma dependência.</p>
    </div>
    <div class="card"><h3>2. Com o repositório</h3>
      <p>Clonando, o servidor lê <code>data/</code> direto e você ganha as ferramentas
      de linha de comando junto.</p>
      <pre class="cmd">git clone {meta['repo']}
cd seculo-perdido
pip install pyyaml</pre>
      <p>E no <code>~/.claude.json</code>, sem o <code>--remoto</code>:</p>
      <pre class="cmd">"args": ["/caminho/seculo-perdido/mcp/servidor.py"]</pre>
    </div>
  </div>

  <div class="cab" style="margin-top:3rem"><h2>O que dá para perguntar</h2></div>
  <table class="tabela">
    <thead><tr><th>ferramenta</th><th>para quê</th></tr></thead>
    <tbody>
      <tr><td><code>estado_do_arquivo</code></td><td>panorama: ranking, capítulo coberto, órfãos</td></tr>
      <tr><td><code>buscar_evidencia</code></td><td>por texto, tema, capítulo ou confiabilidade</td></tr>
      <tr><td><code>obter_evidencia</code></td><td>um átomo pelo id, com quem o cita</td></tr>
      <tr><td><code>listar_hipoteses</code></td><td>todas, com probabilidade e contagem de elos</td></tr>
      <tr><td><code>obter_hipotese</code></td><td>dossiê completo, incluindo o red team</td></tr>
      <tr><td><code>comparar_hipoteses</code></td><td>base compartilhada e onde a evidência diverge</td></tr>
    </tbody>
  </table>
  <p class="intro" style="margin-top:1.4rem">Perguntas que funcionam bem:
  <em>“o que sustenta a hipótese líder e qual o furo dela?”</em> ·
  <em>“tem evidência de que o One Piece seja um objeto físico?”</em> ·
  <em>“o que H-05 e H-08 têm em comum?”</em> ·
  <em>“quais átomos ninguém está usando?”</em></p>

  <div class="cab" style="margin-top:3rem"><h2>A skill</h2></div>
  <p class="intro">Junto vai uma <strong>skill</strong> que ensina o assistente a usar a
  base direito: citar o id de cada átomo, nunca afirmar de memória, distinguir
  <em>ferida</em> de <em>refutada</em>, e não repetir a porcentagem sem a ressalva de que
  ela assume exaustividade. Ela é configurável — dá para limitar por capítulo, para não
  tomar spoiler, ou restringir a evidência canônica.</p>
  <p style="margin-bottom:2rem">
    <a class="botao-grande" href="/mcp/SKILL.md" download>baixar a skill</a>
    <a class="botao-grande alt" href="/mcp/servidor.py" download>baixar o servidor</a></p>

  <blockquote>Se você usar isto para responder a alguém, cite os ids. O valor do
  arquivo não é a resposta que ele dá, é o fato de a resposta poder ser conferida.</blockquote>
</div></section>
<button id="ao-topo" hidden aria-label="Voltar ao topo">↑</button></main>""" + RODAPE)


ICONES = {
    "poneglyph": '<path d="M6 3h12l2 4v14H4V7z" fill="none" stroke="currentColor" stroke-width="2"/>'
                 '<path d="M8 10h8M8 14h8M8 18h5" stroke="currentColor" stroke-width="2"/>',
    "chama": '<path d="M12 2c3 5-2 6 0 10 1.5 3 5 1 5 5a5 5 0 01-10 0c0-3 2-4 2-7 0-3-2-4 3-8z" '
             'fill="none" stroke="currentColor" stroke-width="2"/>',
    "lua": '<path d="M16 3a9 9 0 100 18 7 7 0 010-18z" fill="none" stroke="currentColor" stroke-width="2"/>',
    "coroa": '<path d="M3 8l4 4 5-8 5 8 4-4v11H3z" fill="none" stroke="currentColor" stroke-width="2"/>',
    "navio": '<path d="M4 16h16l-2 5H6zM12 3v13M12 6l7 3-7 3" fill="none" stroke="currentColor" '
             'stroke-width="2"/>',
    "sol": '<circle cx="12" cy="12" r="5" fill="none" stroke="currentColor" stroke-width="2"/>'
           '<path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" '
           'stroke="currentColor" stroke-width="2"/>',
    "relogio": '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/>'
               '<path d="M12 7v5l3 3" stroke="currentColor" stroke-width="2" fill="none"/>',
}


def icone(nome, tam=22):
    return (f'<svg class="ico" viewBox="0 0 24 24" width="{tam}" height="{tam}" '
            f'aria-hidden="true">{ICONES.get(nome, ICONES["poneglyph"])}</svg>')


def pagina_cronologia(meta, cron, evid) -> str:
    marcos = sorted(cron.get("marcos") or [], key=lambda m: m.get("ordem", 0))
    icos = ["poneglyph", "chama", "lua", "coroa", "navio", "sol", "relogio"]
    itens = []
    for i, m in enumerate(marcos):
        refs = " ".join(f'<a href="/evidencias#{e}">{e}</a>' for e in m.get("ev") or [])
        cert = m.get("certeza", "canonica")
        itens.append(f"""<li class="marco {cert}">
  <div class="marco-data">{html.escape(str(m.get("quando", "")))}</div>
  <div class="marco-corpo">
    <h3>{icone(icos[i % len(icos)])}{html.escape(str(m.get("titulo", "")))}</h3>
    <p>{html.escape(" ".join(str(m.get("texto", "")).split()))}</p>
    <div class="marco-ev">{refs}</div>
  </div></li>""")
    return (cabeca("Cronologia — Século Perdido",
                   "A linha do tempo do mundo de One Piece reconstruída só a partir de "
                   "evidência datada, com a fonte de cada marco.", "cronologia.html") +
            f"""<main><section style="border-top:0"><div class="env">
  <div class="cab"><h1>Cronologia do mundo</h1>
    <span class="n">{len(marcos)} marcos</span></div>
  <p class="intro">{html.escape(" ".join(str(cron.get("descricao", "")).split()))}</p>
  <p class="legenda-cert">
    <span class="pt canonica"></span> a obra afirma
    <span class="pt ambigua"></span> leitura de painel ou estimativa de personagem
    <span class="pt disputada"></span> depende da escolha do tradutor</p>
  <ol class="linha">{"".join(itens)}</ol>
  <p class="intro">A régua não é uniforme de propósito: a obra data com precisão os últimos
  cinquenta anos e é vaga sobre tudo que veio antes do Século Perdido. O intervalo entre os
  três mil anos da instalação de Elbaf e os novecentos do Século Perdido é o buraco mais
  gritante daqui — dois milênios sobre os quais o arquivo tem uma frase.</p>
</div></section>
<button id="ao-topo" hidden aria-label="Voltar ao topo">↑</button></main>""" + RODAPE)


def pagina_historico(meta, rodadas) -> str:
    itens = []
    for r in rodadas:
        corpo = "".join(f"<p>{html.escape(l)}</p>" for l in r["corpo"][:4] if l.strip())
        itens.append(f"""<li class="marco canonica">
  <div class="marco-data">{r['data']}</div>
  <div class="marco-corpo">
    <h3>{icone("relogio")}{html.escape(r['titulo'])}</h3>
    {corpo}
    <div class="marco-ev"><a href="{meta['repo']}/commit/{r['hash']}">{r['hash'][:7]}</a></div>
  </div></li>""")
    return (cabeca("Histórico — Século Perdido",
                   "O rastro do arquivo: cada rodada, o que entrou e o que mudou de posição.",
                   "historico.html") + f"""<main><section style="border-top:0"><div class="env">
  <div class="cab"><h1>O rastro</h1><span class="n">{len(rodadas)} rodadas</span></div>
  <p class="intro">O valor deste projeto não é a resposta que ele dá hoje, é o registro de
  uma hipótese subindo e caindo ao longo dos capítulos. Cada rodada abaixo é um estado
  completo do arquivo, com o que entrou de evidência e o que isso fez com o ranking — em
  ordem inversa, do mais recente para o começo.</p>
  <ol class="linha">{"".join(itens)}</ol>
  <p class="intro">O histórico completo, commit a commit, está em
  <a href="{meta['repo']}/commits/main">{meta['repo'].replace("https://github.com/", "")}</a>.
  Nada é reescrito: quando uma hipótese cai, o motivo fica escrito e ela vai para o
  cemitério em vez de ser apagada.</p>
</div></section>
<button id="ao-topo" hidden aria-label="Voltar ao topo">↑</button></main>""" + RODAPE)


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

    tamanhos = {p.name: p.stat().st_size for p in (SAIDA / "dados").glob("*")} \
        if (SAIDA / "dados").is_dir() else {}
    if (SAIDA / "grafo.json").exists():
        tamanhos["grafo.json"] = (SAIDA / "grafo.json").stat().st_size
    gj = SAIDA / "grafo.json"
    if gj.exists():
        g = json.loads(gj.read_text(encoding="utf-8"))["meta"]
        meta["n_nos"], meta["n_rels"] = g["n_nos"], g["n_rels"]
    repo = git("remote", "get-url", "origin", padrao="")
    repo = re.sub(r"\.git$", "", repo) or "https://github.com/pedropasinn/seculo-perdido"
    meta["repo"] = repo

    cron = {}
    pc = RAIZ / "data" / "cronologia.md"
    if pc.exists():
        cron, _ = ler(pc)

    # o rastro sai do proprio git: os commits de rodada sao a narrativa
    rodadas = []
    bruto = git("log", "--format=%H|%cI|%s|%b", "--reverse", padrao="")
    for bloco in bruto.split("\n\ncommit-sep\n\n") if "commit-sep" in bruto else [bruto]:
        pass
    linhas = git("log", "--format=%H\t%cI\t%s", padrao="").splitlines()
    MES = ["", "jan", "fev", "mar", "abr", "mai", "jun",
           "jul", "ago", "set", "out", "nov", "dez"]
    for ln in linhas:
        partes = ln.split("\t")
        if len(partes) < 3:
            continue
        h, iso, titulo = partes[0], partes[1], partes[2]
        corpo = git("log", "-1", "--format=%b", h, padrao="").split("\n")
        corpo = [c for c in corpo if c.strip() and not c.startswith("Co-Authored")]
        junto, atual = [], ""
        for c in corpo:
            if not c.strip():
                continue
            atual = (atual + " " + c.strip()).strip()
            if c.rstrip().endswith((".", ":", "?")) or len(atual) > 210:
                junto.append(atual)
                atual = ""
        if atual:
            junto.append(atual)
        rodadas.append({"hash": h, "titulo": titulo, "corpo": junto,
                        "data": f"{int(iso[8:10])} {MES[int(iso[5:7])]}"})
    rodadas.reverse()
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
        "grafo.html": pagina_grafo(meta, hips, evid),
        "dados.html": pagina_dados(meta, tamanhos),
        "cronologia.html": pagina_cronologia(meta, cron, evid),
        "historico.html": pagina_historico(meta, rodadas),
    }
    for nome, conteudo in paginas.items():
        (SAIDA / nome).write_text(conteudo.replace(RODAPE, rodape), encoding="utf-8")
    import hashlib
    css_txt, js_txt = CSS.strip() + "\n", JS.strip() + "\n"
    h_css = hashlib.sha256(css_txt.encode()).hexdigest()[:8]
    h_js = hashlib.sha256(js_txt.encode()).hexdigest()[:8]
    h_gj = hashlib.sha256((SAIDA / "grafo.js").read_bytes()).hexdigest()[:8] \
        if (SAIDA / "grafo.js").exists() else "0"
    for velho in SAIDA.glob("estilo.*.css"):
        velho.unlink()
    for velho in SAIDA.glob("app.*.js"):
        velho.unlink()
    for velho in SAIDA.glob("grafo.*.js"):
        if velho.name != "grafo.js":
            velho.unlink()
    (SAIDA / f"estilo.{h_css}.css").write_text(css_txt, encoding="utf-8")
    (SAIDA / f"app.{h_js}.js").write_text(js_txt, encoding="utf-8")
    (SAIDA / f"grafo.{h_gj}.js").write_bytes((SAIDA / "grafo.js").read_bytes())
    (SAIDA / "estilo.css").write_text(css_txt, encoding="utf-8")
    import shutil
    (SAIDA / "mcp").mkdir(exist_ok=True)
    shutil.copy2(RAIZ / "mcp" / "servidor.py", SAIDA / "mcp" / "servidor.py")
    shutil.copy2(RAIZ / "skill" / "seculo-perdido" / "SKILL.md", SAIDA / "mcp" / "SKILL.md")
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
        js = f"/grafo.{h_gj}.js" if nome == "grafo.html" else f"/app.{h_js}.js"
        p.write_text(p.read_text(encoding="utf-8")
                     .replace("__HCSS__", h_css)
                     .replace("</body>", f'<script src="{js}"></script></body>'),
                     encoding="utf-8")
    print(f"{SAIDA}  ({meta['n_ev']} atomos, {meta['n_hip']} hipoteses, cap {meta['cap']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
