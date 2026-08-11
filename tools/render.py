#!/usr/bin/env python3
"""Gera um site estatico de pagina unica a partir de data/.

Sem dependencia, sem build step. Quando o repo crescer, troque por Quartz ou
Astro — mas so quando doer.

Uso:  python3 tools/render.py   ->  site/index.html
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent


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

    hipoteses.sort(key=lambda h: -float(h.get("prior") or 0))
    dados = json.dumps({"evidencias": evidencias, "hipoteses": hipoteses},
                       ensure_ascii=False)

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
<div class="sub">Hipóteses ordenadas por probabilidade. Toda afirmação aponta para um átomo verificável.</div>
<div id="app"></div>
<script id="dados" type="application/json">__DADOS__</script>
<script>
const d = JSON.parse(document.getElementById('dados').textContent);
const ev = Object.fromEntries(d.evidencias.map(e => [e.id, e]));
const esc = s => (s||'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
document.getElementById('app').innerHTML = d.hipoteses.map(h => `
 <div class="hip ${h.status}">
  <div class="id">${h.id} · ${h.status} · ${(h.prior*100).toFixed(0)}%</div>
  <div class="barra"><i style="width:${h.prior*100}%"></i></div>
  <div class="enun">${esc(h.enunciado)}</div>
  ${(h.apoia||[]).map(a=>`<div class="elo"><code>${a.ev}</code> ${esc(a.como)}
     <span class="prev">— ${esc(ev[a.ev]?.fonte||'?')}, peso ${a.peso}</span></div>`).join('')}
  ${(h.contradiz||[]).map(a=>`<div class="elo contra"><code>${a.ev}</code> ${esc(a.como)}
     <span class="prev">— ${esc(ev[a.ev]?.fonte||'?')}, peso ${a.peso}</span></div>`).join('')}
  <details><summary>previsões (${(h.prediz||[]).length})</summary>
   ${(h.prediz||[]).map(p=>`<div class="prev">[${p.status}] ${esc(p.texto)}</div>`).join('')}
  </details>
 </div>`).join('');
</script>
</html>"""


if __name__ == "__main__":
    raise SystemExit(main())
