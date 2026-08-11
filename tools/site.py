#!/usr/bin/env python3
"""Gera o site publico em web/ a partir de data/.

Estatico puro, sem build step e sem framework — o mesmo principio do resto do
repositorio. Vercel serve a pasta direto.

Uso:  python3 tools/site.py
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "web"
sys.path.insert(0, str(RAIZ / "tools"))
import score  # noqa: E402

ROTULO_ESCOPO = {
    "one_piece": "o que é o One Piece",
    "seculo_vazio": "Século Vazio",
    "imu": "Imu",
    "joy_boy": "Joy Boy",
    "poneglyph": "Poneglyphs",
    "outro": "outro",
}

ROTULO_CONF = {
    "canonico": "canônico",
    "sbs": "SBS",
    "ambiguo": "ambíguo",
    "traducao_disputada": "tradução disputada",
}


def ler(p: Path) -> tuple[dict, str]:
    bruto = p.read_text(encoding="utf-8")
    _, fm, corpo = bruto.split("---", 2)
    return (yaml.safe_load(fm) or {}), corpo.strip()


def markdown_leve(txt: str) -> str:
    """Subconjunto suficiente para os corpos que escrevemos."""
    out = []
    for bloco in re.split(r"\n{2,}", txt.strip()):
        b = html.escape(bloco.strip())
        b = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", b, flags=re.S)
        b = re.sub(r"`(.+?)`", r"<code>\1</code>", b)
        if b.startswith("## "):
            out.append(f"<h4>{b[3:]}</h4>")
        elif b.startswith("- ") or b.startswith("1. "):
            itens = "".join(f"<li>{re.sub(r'^([-*]|\d+\.)\s*', '', l)}</li>"
                            for l in b.splitlines() if l.strip())
            out.append(f"<ul>{itens}</ul>")
        else:
            out.append(f"<p>{b.replace(chr(10), ' ')}</p>")
    return "".join(out)


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
  --abismo:#081420; --abismo-2:#0c1c2b; --fundo-carta:#0a1826;
  --pergaminho:#ece3d2; --pergaminho-fraco:#a99f8d; --linha:#1d3346;
  --latao:#d0a338; --latao-fraco:#8a6d24;
  --oxido:#b4443a; --verdete:#4a8f7b;
  --serif:"Newsreader",Georgia,serif;
  --display:"Fraunces","Newsreader",Georgia,serif;
  --mono:"IBM Plex Mono",ui-monospace,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  background:var(--abismo); color:var(--pergaminho);
  font:400 17px/1.65 var(--serif); -webkit-font-smoothing:antialiased;
  background-image:
    radial-gradient(ellipse 80% 50% at 50% -10%, rgba(208,163,56,.10), transparent 70%),
    repeating-linear-gradient(0deg, transparent 0 79px, rgba(29,51,70,.35) 79px 80px),
    repeating-linear-gradient(90deg, transparent 0 79px, rgba(29,51,70,.22) 79px 80px);
  background-attachment:fixed;
}
body::after{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:99;opacity:.035;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E");
}
.env{max-width:64rem;margin:0 auto;padding:0 1.6rem}
a{color:inherit}

/* ---------- topo ---------- */
header.topo{border-bottom:1px solid var(--linha);position:sticky;top:0;z-index:50;
  background:rgba(8,20,32,.86);backdrop-filter:blur(12px)}
.topo .env{display:flex;align-items:baseline;gap:1.6rem;padding-top:.9rem;padding-bottom:.9rem}
.marca{font:600 1.05rem/1 var(--display);letter-spacing:.01em;text-decoration:none;
  font-variation-settings:"SOFT" 30,"WONK" 1}
.marca span{color:var(--latao)}
nav.topo-nav{margin-left:auto;display:flex;gap:1.4rem;font:500 .82rem/1 var(--mono);
  letter-spacing:.04em;text-transform:uppercase}
nav.topo-nav a{color:var(--pergaminho-fraco);text-decoration:none;padding-bottom:.2rem;
  border-bottom:1px solid transparent;transition:.18s}
nav.topo-nav a:hover,nav.topo-nav a[aria-current]{color:var(--latao);border-color:var(--latao)}

/* ---------- capa ---------- */
.capa{padding:5.5rem 0 3.5rem;position:relative;overflow:hidden}
.capa::before{content:"";position:absolute;left:50%;top:-14rem;width:44rem;height:44rem;
  transform:translateX(-50%);border-radius:50%;pointer-events:none;
  background:radial-gradient(circle,rgba(208,163,56,.09),transparent 62%)}
.rotulo{font:500 .74rem/1 var(--mono);letter-spacing:.22em;text-transform:uppercase;
  color:var(--latao-fraco);margin-bottom:1.4rem}
.capa h1{font:600 clamp(2.6rem,7vw,4.6rem)/1.02 var(--display);letter-spacing:-.022em;
  font-variation-settings:"SOFT" 40,"WONK" 1;max-width:16ch;text-wrap:balance}
.capa h1 em{font-style:italic;color:var(--latao);font-variation-settings:"SOFT" 80,"WONK" 1}
.capa .sub{margin-top:1.6rem;max-width:52ch;font-size:1.12rem;color:#cdc3b0}
.painel{display:flex;flex-wrap:wrap;gap:2.6rem;margin-top:3rem;padding-top:1.8rem;
  border-top:1px solid var(--linha)}
.painel div{min-width:6rem}
.painel b{display:block;font:600 1.9rem/1 var(--display);color:var(--latao);
  font-variation-settings:"SOFT" 20}
.painel small{font:400 .76rem/1.4 var(--mono);letter-spacing:.08em;text-transform:uppercase;
  color:var(--pergaminho-fraco)}

/* ---------- seções ---------- */
section{padding:4rem 0;border-top:1px solid var(--linha)}
.cab{display:flex;align-items:baseline;gap:1rem;margin-bottom:.7rem}
.cab h2{font:600 1.9rem/1.1 var(--display);letter-spacing:-.015em;font-variation-settings:"SOFT" 30}
.cab .n{font:500 .8rem/1 var(--mono);color:var(--latao-fraco)}
.intro{max-width:60ch;color:#bdb3a2;margin-bottom:2.4rem}

/* ---------- hipóteses ---------- */
.hip{border-top:1px solid var(--linha);padding:1.7rem 0;position:relative}
.hip:last-child{border-bottom:1px solid var(--linha)}
.hip-cab{display:grid;grid-template-columns:3.4rem 1fr auto;gap:1.2rem;align-items:start;
  cursor:pointer;background:none;border:0;color:inherit;text-align:left;width:100%;font:inherit}
.hip-id{font:500 .78rem/1.6 var(--mono);color:var(--latao-fraco);letter-spacing:.04em}
.hip-enun{font:500 1.16rem/1.45 var(--serif);text-wrap:pretty}
.hip-pct{font:600 1.5rem/1 var(--display);color:var(--latao);font-variation-settings:"SOFT" 20;
  white-space:nowrap}
.sonda{grid-column:2/4;margin-top:.85rem;height:3px;background:var(--linha);position:relative;
  border-radius:2px;overflow:hidden}
.sonda i{position:absolute;inset:0 auto 0 0;background:linear-gradient(90deg,var(--latao-fraco),var(--latao));
  border-radius:2px;transform-origin:left;animation:sonda 1.1s cubic-bezier(.2,.8,.2,1) both}
@keyframes sonda{from{transform:scaleX(0)}}
.hip-meta{grid-column:2/4;margin-top:.7rem;display:flex;gap:1rem;flex-wrap:wrap;
  font:400 .78rem/1 var(--mono);color:var(--pergaminho-fraco);letter-spacing:.03em}
.selo{border:1px solid var(--linha);padding:.24rem .5rem;border-radius:2px}
.selo.ferida{color:var(--oxido);border-color:rgba(180,68,58,.4)}
.hip[data-status="refutada"]{opacity:.62}
.hip[data-status="refutada"] .hip-pct{color:var(--oxido);font-size:1rem}
.corpo{display:none;padding:1.6rem 0 .4rem;grid-column:1/4}
.hip.aberta .corpo{display:block;animation:desdobra .3s ease both}
@keyframes desdobra{from{opacity:0;transform:translateY(-6px)}}
.corpo h4{font:600 .78rem/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;
  color:var(--latao-fraco);margin:1.6rem 0 .7rem}
.corpo p{margin:.7rem 0;color:#c8bfae;max-width:66ch}
.corpo ul{margin:.6rem 0 .6rem 1.1rem;color:#c8bfae}
.corpo li{margin:.3rem 0}
code{font:.86em var(--mono);color:var(--latao);background:rgba(208,163,56,.08);
  padding:.1em .35em;border-radius:2px}

.elo{display:grid;grid-template-columns:auto 1fr;gap:.9rem;padding:.62rem 0;
  border-bottom:1px dotted rgba(29,51,70,.8);align-items:start}
.elo:last-child{border-bottom:0}
.elo .ev{font:500 .78rem/1.5 var(--mono);color:var(--verdete);text-decoration:none;
  border-bottom:1px solid transparent}
.elo .ev:hover{border-color:currentColor}
.elo.contra .ev{color:var(--oxido)}
.elo .como{font-size:.94rem;color:#bdb3a2}
.elo .peso{font:400 .72rem var(--mono);color:var(--pergaminho-fraco);white-space:nowrap}
.prev{display:flex;gap:.7rem;padding:.5rem 0;font-size:.95rem;color:#bdb3a2}
.prev b{font:500 .7rem/1.6 var(--mono);letter-spacing:.08em;text-transform:uppercase;
  color:var(--latao-fraco);white-space:nowrap}
details.rt{margin-top:1.4rem;border:1px solid var(--linha);border-radius:3px}
details.rt summary{cursor:pointer;padding:.7rem .9rem;font:500 .76rem/1 var(--mono);
  letter-spacing:.1em;text-transform:uppercase;color:var(--oxido)}
details.rt pre{padding:0 .9rem 1rem;white-space:pre-wrap;font:.82rem/1.6 var(--mono);
  color:#a99f8d;max-height:32rem;overflow:auto}

/* ---------- evidências ---------- */
.busca{display:flex;gap:.8rem;flex-wrap:wrap;margin-bottom:1.6rem}
.busca input{flex:1;min-width:14rem;background:var(--abismo-2);border:1px solid var(--linha);
  color:var(--pergaminho);padding:.72rem .9rem;font:400 .95rem var(--serif);border-radius:3px}
.busca input:focus{outline:0;border-color:var(--latao-fraco)}
.busca select{background:var(--abismo-2);border:1px solid var(--linha);color:var(--pergaminho);
  padding:.72rem .8rem;font:.85rem var(--mono);border-radius:3px}
.ev-item{border-top:1px solid var(--linha);padding:1rem 0;display:grid;
  grid-template-columns:7.2rem 1fr;gap:1.1rem;align-items:start}
.ev-item:last-child{border-bottom:1px solid var(--linha)}
.ev-id{font:500 .76rem/1.6 var(--mono);color:var(--latao-fraco)}
.ev-cap{display:block;font:400 .7rem/1.6 var(--mono);color:var(--pergaminho-fraco)}
.ev-txt{font-size:.99rem;text-wrap:pretty}
.ev-tags{margin-top:.5rem;display:flex;gap:.5rem;flex-wrap:wrap;
  font:400 .68rem/1 var(--mono);letter-spacing:.05em;color:var(--pergaminho-fraco)}
.tag{border:1px solid var(--linha);padding:.24rem .46rem;border-radius:2px}
.tag.canonico{color:var(--verdete);border-color:rgba(74,143,123,.35)}
.tag.traducao_disputada{color:var(--oxido);border-color:rgba(180,68,58,.35)}
.tag.ambiguo{color:var(--latao-fraco);border-color:rgba(138,109,36,.4)}
.ev-item a.fonte{font:.7rem var(--mono);color:var(--pergaminho-fraco);text-decoration:none;
  border-bottom:1px dotted currentColor}
.vazio{padding:2rem 0;color:var(--pergaminho-fraco);font-style:italic}

/* ---------- método ---------- */
.grade{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:1.6rem;margin-top:2rem}
.card{border:1px solid var(--linha);border-radius:3px;padding:1.3rem;background:rgba(12,28,43,.45)}
.card h3{font:600 1.02rem/1.3 var(--display);margin-bottom:.5rem;color:var(--latao)}
.card p{font-size:.93rem;color:#bdb3a2}
blockquote{border-left:2px solid var(--latao-fraco);padding-left:1.1rem;margin:1.6rem 0;
  font-style:italic;color:#cdc3b0;max-width:60ch}

footer{border-top:1px solid var(--linha);padding:3rem 0 4rem;font-size:.86rem;
  color:var(--pergaminho-fraco)}
footer p{max-width:62ch;margin:.6rem 0}
footer a{color:var(--latao-fraco)}
@media(max-width:640px){
  .hip-cab{grid-template-columns:1fr auto}
  .hip-id{display:none}
  .sonda,.hip-meta,.corpo{grid-column:1/3}
  .ev-item{grid-template-columns:1fr}
}
"""

JS = """
document.querySelectorAll('.hip-cab').forEach(b=>{
  b.addEventListener('click',()=>b.closest('.hip').classList.toggle('aberta'));
});
const cx=document.getElementById('busca'), fc=document.getElementById('filtro-conf'),
      ft=document.getElementById('filtro-tema'), lista=document.getElementById('lista-ev');
function filtra(){
  if(!lista) return;
  const q=(cx.value||'').toLowerCase().trim(), c=fc.value, t=ft.value;
  let n=0;
  lista.querySelectorAll('.ev-item').forEach(el=>{
    const ok = (!q || el.dataset.busca.includes(q))
            && (!c || el.dataset.conf===c)
            && (!t || el.dataset.temas.includes(t));
    el.style.display = ok?'':'none'; if(ok) n++;
  });
  document.getElementById('conta').textContent = n;
  document.getElementById('vazio').style.display = n?'none':'block';
}
[cx,fc,ft].forEach(el=>el&&el.addEventListener('input',filtra));
"""


def cabeca(titulo: str, desc: str, ativo: str) -> str:
    nav = [("index.html", "Hipóteses"), ("evidencias.html", "Evidências"),
           ("metodo.html", "Método")]
    itens = "".join(
        f'<a href="{u}"{" aria-current=page" if u == ativo else ""}>{t}</a>' for u, t in nav)
    return f"""<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{html.escape(titulo)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT,WONK@0,9..144,400..700,0..100,0..1;1,9..144,400..700,0..100,0..1&family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..500&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="estilo.css">
</head><body>
<header class="topo"><div class="env">
  <a class="marca" href="index.html">Século<span>·</span>Vazio</a>
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
<p>Código e dados: <a href="__REPO__" rel="noopener">__REPO_CURTO__</a> · gerado em __COMMIT__</p>
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
        selos.append(f'<span class="selo">prior {h.get("prior", 0):.2f}</span>')
        pct = (f'{h["fatia"]*100:.0f}<small style="font-size:.55em">%</small>'
               if h["fatia"] else '†')
        apo = "".join(
            f'<div class="elo"><a class="ev" href="evidencias.html#{e["ev"]}">{e["ev"]}</a>'
            f'<div><div class="como">{html.escape(e.get("como", ""))}</div>'
            f'<div class="peso">peso {e.get("peso", 0)} · '
            f'{html.escape(str(evid.get(e["ev"], {}).get("fonte", "?")))}</div></div></div>'
            for e in h.get("apoia") or [])
        con = "".join(
            f'<div class="elo contra"><a class="ev" href="evidencias.html#{e["ev"]}">{e["ev"]}</a>'
            f'<div><div class="como">{html.escape(e.get("como", ""))}</div>'
            f'<div class="peso">peso {e.get("peso", 0)} · '
            f'{html.escape(str(evid.get(e["ev"], {}).get("fonte", "?")))}</div></div></div>'
            for e in h.get("contradiz") or [])
        prev = "".join(
            f'<div class="prev"><b>{p.get("status", "")}</b>'
            f'<span>{html.escape(p.get("texto", ""))}</span></div>'
            for p in h.get("prediz") or [])
        rt = (f'<details class="rt"><summary>relatório do red team</summary>'
              f'<pre>{html.escape(h["redteam"])}</pre></details>') if h.get("redteam") else ""
        return f"""<article class="hip" data-status="{st}">
<button class="hip-cab" aria-expanded="false">
  <span class="hip-id">{h["id"]}</span>
  <span class="hip-enun">{html.escape(h.get("enunciado", ""))}</span>
  <span class="hip-pct">{pct}</span>
  <span class="sonda"><i style="width:{max(h['fatia']*100, 1):.1f}%;animation-delay:{i*.06:.2f}s"></i></span>
  <span class="hip-meta">{"".join(selos)}</span>
</button>
<div class="corpo">
  {markdown_leve(h.get("corpo", ""))}
  <h4>Evidência a favor · {len(h.get("apoia") or [])}</h4>{apo or "<p>—</p>"}
  <h4>Evidência contra · {len(h.get("contradiz") or [])}</h4>{con or "<p>—</p>"}
  <h4>Previsões falseáveis</h4>{prev or "<p>—</p>"}
  {rt}
</div></article>"""

    return (cabeca("Século Vazio — o que é o One Piece, por evidência",
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
    <div><b>{meta['n_ev']}</b><small>átomos de evidência</small></div>
    <div><b>{meta['n_hip']}</b><small>hipóteses</small></div>
    <div><b>{meta['n_mortas']}</b><small>refutadas</small></div>
    <div><b>{meta['n_rt']}</b><small>ataques de red team</small></div>
  </div>
</div>

<section><div class="env">
  <div class="cab"><h2>As alternativas</h2><span class="n">escopo: o que é o tesouro</span></div>
  <p class="intro">A porcentagem é a repartição da probabilidade entre hipóteses mutuamente
  exclusivas — e ela assume que a resposta certa está entre as listadas, que é justamente o
  que não se pode garantir. Clique para abrir o dossiê de cada uma.</p>
  {"".join(bloco(h, i) for i, h in enumerate(vivas))}
</div></section>

<section><div class="env">
  <div class="cab"><h2>Fora do tesouro</h2><span class="n">hipóteses auxiliares</span></div>
  <p class="intro">Estas não disputam a pergunta central: podem ser verdadeiras junto com
  qualquer uma das de cima.</p>
  {"".join(bloco(h) for h in outras)}
</div></section>

<section><div class="env">
  <div class="cab"><h2>Cemitério</h2><span class="n">{len(mortas)} refutadas</span></div>
  <p class="intro">A parte mais valiosa do arquivo. Cada uma traz escrito o que a matou —
  é isso que impede o projeto de reinventar a mesma teoria ruim daqui a seis meses.</p>
  {"".join(bloco(h) for h in mortas)}
</div></section>
</main>""" + RODAPE)


def pagina_evidencias(evid, meta) -> str:
    temas = sorted({t for e in evid.values() for t in (e.get("temas") or [])})
    itens = []
    for ident, e in sorted(evid.items()):
        conf = e.get("confiabilidade", "")
        tags = f'<span class="tag {conf}">{ROTULO_CONF.get(conf, conf)}</span>' \
               f'<span class="tag">{html.escape(str(e.get("tipo", "")))}</span>' + \
               "".join(f'<span class="tag">{html.escape(t)}</span>'
                       for t in (e.get("temas") or [])[:4])
        url = e.get("fonte_url", "")
        fonte = (f'<a class="fonte" href="{html.escape(url)}" rel="noopener nofollow">verificar fonte</a>'
                 if url else "")
        busca = (ident + " " + str(e.get("texto", "")) + " " +
                 " ".join(e.get("temas") or []) + " " +
                 " ".join(e.get("atores") or [])).lower()
        itens.append(f"""<article class="ev-item" id="{ident}" data-conf="{conf}"
 data-temas="{html.escape("|".join(e.get("temas") or []))}" data-busca="{html.escape(busca)}">
  <div><span class="ev-id">{ident}</span><span class="ev-cap">{html.escape(str(e.get("fonte", "")))}</span></div>
  <div><div class="ev-txt">{html.escape(str(e.get("texto", "")))}</div>
  <div class="ev-tags">{tags} {fonte}</div></div>
</article>""")

    ops_t = "".join(f'<option value="{html.escape(t)}">{html.escape(t)}</option>' for t in temas)
    return (cabeca("Evidências — Século Vazio",
                   "Todos os átomos de evidência do arquivo, com fonte e confiabilidade.",
                   "evidencias.html") + f"""<main><section style="border-top:0"><div class="env">
  <div class="cab"><h2>Átomos de evidência</h2><span class="n"><span id="conta">{len(evid)}</span> de {len(evid)}</span></div>
  <p class="intro">Um átomo é uma afirmação verificável, com fonte e nível de confiabilidade.
  Ele não interpreta — interpretar é papel das hipóteses. Quando a afirmação depende da escolha
  do tradutor, ela é marcada como <em>tradução disputada</em> e seu peso é limitado.</p>
  <div class="busca">
    <input id="busca" type="search" placeholder="buscar por texto, personagem, tema ou id…" autocomplete="off">
    <select id="filtro-conf">
      <option value="">toda confiabilidade</option>
      <option value="canonico">canônico</option><option value="ambiguo">ambíguo</option>
      <option value="traducao_disputada">tradução disputada</option><option value="sbs">SBS</option>
    </select>
    <select id="filtro-tema"><option value="">todos os temas</option>{ops_t}</select>
  </div>
  <div id="lista-ev">{"".join(itens)}</div>
  <p class="vazio" id="vazio" style="display:none">Nenhum átomo corresponde a esse filtro.</p>
</div></section></main>""" + RODAPE)


def pagina_metodo(meta) -> str:
    return (cabeca("Método — Século Vazio",
                   "Como o arquivo funciona: átomos, hipóteses, red team e o portão que "
                   "recusa afirmação sem fonte.", "metodo.html") + f"""<main>
<section style="border-top:0"><div class="env">
  <div class="cab"><h2>Como isto funciona</h2></div>
  <p class="intro">O problema clássico da teoria de fandom é que ela é elástica: se molda a
  qualquer capítulo novo e nunca pode estar errada. Este arquivo foi construído para tornar
  isso impossível.</p>

  <div class="grade">
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

  <h4 style="margin-top:3rem"></h4>
  <div class="cab"><h2>O que não sabemos</h2></div>
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
</div></section></main>""" + RODAPE)


def main() -> int:
    evid, hips = carregar()
    SAIDA.mkdir(exist_ok=True)
    caps = [int(i.split("-")[1]) for i in evid if i.split("-")[1].isdigit()]
    meta = {
        "n_ev": len(evid), "n_hip": len(hips),
        "n_mortas": sum(1 for h in hips if h["status"] == "refutada"),
        "n_rt": len(list((RAIZ / "data" / "hipoteses").glob("*.redteam.md"))),
        "cap": max(caps) if caps else 0,
    }
    repo = git("remote", "get-url", "origin", padrao="")
    repo = re.sub(r"\.git$", "", repo) or "https://github.com/pedropasinn/seculo-vazio"
    rodape = (RODAPE.replace("__REPO__", repo)
              .replace("__REPO_CURTO__", repo.replace("https://github.com/", ""))
              .replace("__COMMIT__", git("rev-parse", "--short", "HEAD", padrao="local")))
    global RODAPE_ATUAL
    paginas = {
        "index.html": pagina_hipoteses(evid, hips, meta),
        "evidencias.html": pagina_evidencias(evid, meta),
        "metodo.html": pagina_metodo(meta),
    }
    for nome, conteudo in paginas.items():
        (SAIDA / nome).write_text(conteudo.replace(RODAPE, rodape), encoding="utf-8")
    (SAIDA / "estilo.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    (SAIDA / "app.js").write_text(JS.strip() + "\n", encoding="utf-8")
    for nome in paginas:
        p = SAIDA / nome
        p.write_text(p.read_text(encoding="utf-8").replace(
            "</body>", '<script src="app.js"></script></body>'), encoding="utf-8")
    print(f"{SAIDA}  ({meta['n_ev']} atomos, {meta['n_hip']} hipoteses, cap {meta['cap']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
