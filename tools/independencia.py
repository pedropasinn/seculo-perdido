#!/usr/bin/env python3
"""Quanto do apoio de cada hipotese e emprestado?

score.py trata cada elo como um fator de Bayes independente. A independencia e
falsa de dois jeitos, e so um deles ja estava tratado:

  correlacao de FONTE   atomos do mesmo capitulo ou do mesmo arco se
                        correlacionam — freada por TETO_POR_FONTE e TETO_POR_ARCO
  correlacao de ATOMO   o MESMO atomo alimenta varias hipoteses concorrentes.
                        Isso nao era medido, e e maior.

Este script mede a segunda. Uma hipotese cujo apoio vem quase todo de atomos
compartilhados com rivais nao tem terreno proprio: ela sobe junto com as outras
em vez de vencer delas.

Uso:  python3 tools/independencia.py
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import score  # noqa: E402
import yaml   # noqa: E402


def carregar():
    evid = score.carregar_evidencias()
    hips = []
    for p in sorted((RAIZ / "data" / "hipoteses").glob("H-*.md")):
        if p.name.endswith(".redteam.md"):
            continue
        hips.append(score.ler(p))
    return evid, hips


def main() -> int:
    evid, hips = carregar()
    vivas = [h for h in hips if h.get("status") in {"viva", "confirmada"}]
    ids_vivas = {h["id"] for h in vivas}

    # quantas hipoteses vivas cada atomo toca
    toca = defaultdict(set)
    for h in vivas:
        for rot in ("apoia", "contradiz"):
            for e in h.get(rot) or []:
                toca[e["ev"]].add(h["id"])

    print("emprestado = fracao do apoio que vem de atomo que tambem toca outra hipotese viva\n")
    print(f"  {'hip':<6} {'apoio':>7} {'exclusivo':>10} {'emprestado':>11}   base propria")
    linhas = []
    for h in sorted(vivas, key=lambda x: x["id"]):
        total = excl = 0.0
        for e in h.get("apoia") or []:
            c = score.contribuicao(e.get("peso", 0),
                                   evid.get(e["ev"], {}).get("confiabilidade", ""))
            total += c
            if len(toca[e["ev"]] & ids_vivas) <= 1:
                excl += c
        frac = 1 - (excl / total) if total else 0.0
        linhas.append((h["id"], total, excl, frac))
        barra = "#" * round(frac * 26)
        print(f"  {h['id']:<6} {total:7.2f} {excl:10.2f} {frac*100:10.1f}%   {barra}")

    print("\n--- ordenacao por saldo, contando so evidencia exclusiva ---")
    saldo = []
    for h in vivas:
        s = 0.0
        for rot, sinal in (("apoia", 1), ("contradiz", -1)):
            for e in h.get(rot) or []:
                if len(toca[e["ev"]] & ids_vivas) <= 1:
                    s += sinal * score.contribuicao(
                        e.get("peso", 0), evid.get(e["ev"], {}).get("confiabilidade", ""))
        saldo.append((h["id"], s))
    for i, (hid, s) in enumerate(sorted(saldo, key=lambda x: -x[1]), 1):
        print(f"  {i:>2}. {hid}  {s:+.2f}")

    print("\n--- atomos que apoiam DUAS hipoteses que se declaram concorrentes ---")
    conc = {h["id"]: set(h.get("concorrentes") or []) for h in hips}
    achados = []
    for ev_id, hs in toca.items():
        apoiam = [h["id"] for h in vivas
                  if any(e["ev"] == ev_id for e in h.get("apoia") or [])]
        for i, a in enumerate(apoiam):
            for b in apoiam[i + 1:]:
                if b in conc.get(a, set()):
                    achados.append((ev_id, a, b))
    for ev_id, a, b in sorted(achados):
        txt = str(evid.get(ev_id, {}).get("texto", ""))[:64]
        print(f"  {ev_id}  apoia {a} e {b} (concorrentes) — {txt}…")
    print(f"  total: {len(achados)} pares. Evidencia que nao discrimina, contada"
          f" como positiva dos dois lados.")

    print("\n--- atomos que DECIDEM (apoiam uma viva e contradizem outra) ---")
    dec = []
    for ev_id in toca:
        ap = [(h["id"], e.get("peso", 0)) for h in vivas
              for e in h.get("apoia") or [] if e["ev"] == ev_id]
        ct = [(h["id"], e.get("peso", 0)) for h in vivas
              for e in h.get("contradiz") or [] if e["ev"] == ev_id]
        for a, pa in ap:
            for c, pc in ct:
                dec.append((pa + pc, ev_id, a, c))
    for forca, ev_id, a, c in sorted(dec, reverse=True)[:12]:
        print(f"  {forca:.2f}  {ev_id}  apoia {a}, contradiz {c}")
    print(f"  {len({d[1] for d in dec})} atomos decidem, em {len(dec)} pares — "
          f"de {len(toca)} vinculados")

    print("\n--- rivalidades declaradas que nenhum atomo testou ---")
    n = 0
    for h in vivas:
        for c in h.get("concorrentes") or []:
            if c <= h["id"] or c not in ids_vivas:
                continue
            base_a = {e["ev"] for r in ("apoia", "contradiz") for e in h.get(r) or []}
            outro = next((x for x in vivas if x["id"] == c), None)
            if not outro:
                continue
            base_b = {e["ev"] for r in ("apoia", "contradiz") for e in outro.get(r) or []}
            if not (base_a & base_b):
                print(f"  {h['id']} ~ {c}: concorrem no papel, base totalmente disjunta")
                n += 1
    print(f"  {n} pares sem nenhuma evidencia em comum — pauta de trabalho\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
