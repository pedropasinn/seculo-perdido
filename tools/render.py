#!/usr/bin/env python3
"""Gera um site estatico de pagina unica a partir de data/.

Sem dependencia, sem build step. Quando o repo crescer, troque por Quartz ou
Astro — mas so quando doer.

Uso:  python3 tools/render.py   ->  site/index.html
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import score  # noqa: E402  — reusa o mesmo modelo de log-odds da linha de comando


def ler(p: Path) -> tuple[dict, str]:
    bruto = p.read_text(encoding="utf-8")
    _, fm, corpo = bruto.split("---", 2)
    return (yaml.safe_load(fm) or {}), corpo.strip()


def main() -> int:
    evidencias = []
    for p in sorted((RAIZ / "data" / "evidencias").glob("EV-*.md")):
        meta, corpo = ler(p)
        meta["corpo"] = corpo
        evidencias.append(meta)

    hipoteses = []
    for p in sorted((RAIZ / "data" / "hipoteses").glob("H-*.md")):
        if p.name.endswith(".redteam.md"):
            continue
        meta, corpo = ler(p)
        meta["corpo"] = corpo
        rt = p.with_suffix("").with_suffix(".redteam.md")
        meta["redteam"] = rt.read_text(encoding="utf-8") if rt.exists() else ""
        hipoteses.append(meta)

    # o site mostra o posterior, nao o prior: o prior tem que continuar sendo a
    # crenca ANTES dos atomos, senao a proxima rodada conta os mesmos elos duas vezes
    indice_ev = {e["id"]: e for e in evidencias}
    for h in hipoteses:
        h["posterior"] = score.pontuar(h, indice_ev)["posterior"]
    vivas = {h["id"] for h in hipoteses if h.get("escopo") == "one_piece"
             and h.get("status") in {"viva", "confirmada"}}
    soma = sum(h["posterior"] for h in hipoteses if h["id"] in vivas) or 1.0
    for h in hipoteses:
        h["fatia"] = h["posterior"] / soma if h["id"] in vivas else 0.0

    hipoteses.sort(key=lambda h: -float(h.get("posterior") or 0))
    # default=str: o YAML converte 2026-08-11 sem aspas em datetime.date, e um
    # campo de data mal citado num arquivo nao deve derrubar o site inteiro
    dados = json.dumps({"evidencias": evidencias, "hipoteses": hipoteses},
                       ensure_ascii=False, default=str)

    saida = RAIZ / "site" / "index.html"
    saida.parent.mkdir(exist_ok=True)
    saida.write_text(PAGINA.replace("__DADOS__", html.escape(dados, quote=False)
                                    .replace("</", "<\\/")), encoding="utf-8")
    print(f"{saida}  ({len(evidencias)} atomos, {len(hipoteses)} hipoteses)")
    return 0


PAGINA = """<!doctype html>
<html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wiki de Evidências — One Piece</title>
<style>
 :root{--tinta:#1b1a17;--papel:#f4f1ea;--fraco:#7a736a;--linha:#ddd6c9;--vermelho:#9c2b2b}
 *{box-sizing:border-box}
 body{margin:0;background:var(--papel);color:var(--tinta);
      font:16px/1.6 ui-serif,Georgia,serif;padding:2rem 1.2rem;max-width:52rem;margin:auto}
 h1{font-size:1.5rem;margin:0 0 .2rem}
 .sub{color:var(--fraco);font-size:.9rem;margin-bottom:2rem}
 .hip{border-left:3px solid var(--linha);padding:.2rem 0 .2rem 1rem;margin:1.6rem 0}
 .hip.refutada{opacity:.55;border-color:var(--vermelho)}
 .id{font:600 .75rem ui-monospace,monospace;color:var(--fraco);letter-spacing:.04em}
 .enun{font-weight:600;margin:.25rem 0 .5rem}
 .barra{height:5px;background:var(--linha);border-radius:3px;overflow:hidden;margin:.5rem 0}
 .barra i{display:block;height:100%;background:var(--tinta)}
 .elo{font-size:.85rem;margin:.35rem 0;padding-left:.8rem;border-left:2px solid var(--linha)}
 .elo.contra{border-color:var(--vermelho)}
 .prev{font-size:.85rem;color:var(--fraco)}
 details{margin-top:.5rem}summary{cursor:pointer;font-size:.85rem;color:var(--fraco)}
 code{font:.8rem ui-monospace,monospace;background:#e9e4d9;padding:.05rem .3rem;border-radius:3px}
</style>
<h1>Wiki de Evidências — One Piece</h1>
<div class="sub">Hipóteses ordenadas pelo posterior. A porcentagem grande é a fatia repartida
entre as alternativas de escopo <code>one_piece</code>, que são mutuamente exclusivas —
ela assume que a resposta certa está entre as listadas. Toda afirmação aponta para um
átomo verificável.</div>
<div id="app"></div>
<script id="dados" type="application/json">__DADOS__</script>
<script>
const d = JSON.parse(document.getElementById('dados').textContent);
const ev = Object.fromEntries(d.evidencias.map(e => [e.id, e]));
const esc = s => (s||'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
document.getElementById('app').innerHTML = d.hipoteses.map(h => `
 <div class="hip ${h.status}">
  <div class="id">${h.id} · ${h.status} · fatia ${(h.fatia*100).toFixed(1)}%
   <span class="prev">(prior ${(h.prior*100).toFixed(0)}% → posterior ${(h.posterior*100).toFixed(0)}%)</span></div>
  <div class="barra"><i style="width:${h.fatia*100}%"></i></div>
  <div class="enun">${esc(h.enunciado)}</div>
  ${(h.apoia||[]).map(a=>`<div class="elo"><code>${a.ev}</code> ${esc(a.como)}
     <span class="prev">— ${esc(ev[a.ev]?.fonte||'?')}, peso ${a.peso}</span></div>`).join('')}
  ${(h.contradiz||[]).map(a=>`<div class="elo contra"><code>${a.ev}</code> ${esc(a.como)}
     <span class="prev">— ${esc(ev[a.ev]?.fonte||'?')}, peso ${a.peso}</span></div>`).join('')}
  <details><summary>previsões (${(h.prediz||[]).length})</summary>
   ${(h.prediz||[]).map(p=>`<div class="prev">[${p.status}] ${esc(p.texto)}</div>`).join('')}
  </details>
  ${h.redteam ? `<details><summary>red team</summary><pre>${esc(h.redteam)}</pre></details>` : ''}
 </div>`).join('');
</script>
</html>"""


if __name__ == "__main__":
    raise SystemExit(main())
