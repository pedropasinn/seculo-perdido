#!/usr/bin/env python3
"""Monta o grafo de propriedades a partir de data/ e emite web/grafo.json.

O modelo e o de um banco de grafos: nos com label e propriedades, relacoes
tipadas e com propriedades proprias. E isso que faz a ligacao ter significado —
uma aresta nao e so "estao ligados", e APOIA com peso 0.45 e uma justificativa.

  (:Evidencia)-[:APOIA    {peso, como}]->(:Hipotese)
  (:Evidencia)-[:CONTRADIZ {peso, como}]->(:Hipotese)
  (:Hipotese) -[:CONCORRE_COM]->(:Hipotese)
  (:Evidencia)-[:TEM_TEMA]->(:Tema)
  (:Evidencia)-[:MENCIONA]->(:Ator)

Uso:  python3 tools/grafo.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import score  # noqa: E402

# temas e atores com menos ocorrencias que isto viram ruido no grafo
MIN_TEMA = 3
MIN_ATOR = 3


def ler(p: Path) -> tuple[dict, str]:
    bruto = p.read_text(encoding="utf-8")
    _, fm, corpo = bruto.split("---", 2)
    return (yaml.safe_load(fm) or {}), corpo.strip()


def main() -> int:
    evid, hips = {}, []
    for p in sorted((RAIZ / "data" / "evidencias").glob("EV-*.md")):
        meta, _ = ler(p)
        evid[meta["id"]] = meta
    for p in sorted((RAIZ / "data" / "hipoteses").glob("H-*.md")):
        if p.name.endswith(".redteam.md"):
            continue
        meta, corpo = ler(p)
        meta["corpo"] = corpo
        meta["posterior"] = score.pontuar(meta, evid)["posterior"]
        hips.append(meta)

    vivas = [h for h in hips if h.get("escopo") == "one_piece"
             and h.get("status") in {"viva", "confirmada"}]
    soma = sum(h["posterior"] for h in vivas) or 1.0
    ids_vivas = {h["id"] for h in vivas}

    cont_tema = Counter(t for e in evid.values() for t in (e.get("temas") or []))
    cont_ator = Counter(a for e in evid.values() for a in (e.get("atores") or []))

    nos, rels = [], []

    for h in hips:
        fatia = h["posterior"] / soma if h["id"] in ids_vivas else 0.0
        nos.append({
            "id": h["id"], "label": "Hipotese", "nome": h["id"],
            "props": {
                "enunciado": h.get("enunciado", ""),
                "status": h.get("status", ""),
                "escopo": h.get("escopo", ""),
                "prior": h.get("prior", 0),
                "posterior": round(h["posterior"], 3),
                "fatia": round(fatia, 3),
            },
            "peso": 1.0 + fatia * 4,
        })
        for c in h.get("concorrentes") or []:
            if c > h["id"]:  # uma aresta por par
                rels.append({"de": h["id"], "para": c, "tipo": "CONCORRE_COM", "props": {}})

    usados = set()
    for h in hips:
        for rotulo, tipo in (("apoia", "APOIA"), ("contradiz", "CONTRADIZ")):
            for e in h.get(rotulo) or []:
                if e["ev"] not in evid:
                    continue
                usados.add(e["ev"])
                rels.append({"de": e["ev"], "para": h["id"], "tipo": tipo,
                             "props": {"peso": e.get("peso", 0), "como": e.get("como", "")}})

    for ident, e in evid.items():
        cap = ident.split("-")[1]
        nos.append({
            "id": ident, "label": "Evidencia", "nome": ident,
            "props": {
                "texto": e.get("texto", ""),
                "fonte": e.get("fonte", ""),
                "tipo": e.get("tipo", ""),
                "confiabilidade": e.get("confiabilidade", ""),
                "fonte_url": e.get("fonte_url", ""),
                "capitulo": int(cap) if cap.isdigit() else 0,
                "orfao": ident not in usados,
            },
            "peso": 1.0,
        })
        for t in e.get("temas") or []:
            if cont_tema[t] >= MIN_TEMA:
                rels.append({"de": ident, "para": f"tema:{t}", "tipo": "TEM_TEMA", "props": {}})
        for a in e.get("atores") or []:
            if cont_ator[a] >= MIN_ATOR:
                rels.append({"de": ident, "para": f"ator:{a}", "tipo": "MENCIONA", "props": {}})

    for t, n in cont_tema.items():
        if n >= MIN_TEMA:
            nos.append({"id": f"tema:{t}", "label": "Tema", "nome": t,
                        "props": {"átomos": n}, "peso": 0.8 + min(n, 30) / 30})
    for a, n in cont_ator.items():
        if n >= MIN_ATOR:
            nos.append({"id": f"ator:{a}", "label": "Ator", "nome": a,
                        "props": {"átomos": n}, "peso": 0.8 + min(n, 30) / 30})

    grau = Counter()
    for r in rels:
        grau[r["de"]] += 1
        grau[r["para"]] += 1
    for n in nos:
        n["grau"] = grau.get(n["id"], 0)

    dados = {
        "nos": nos, "rels": rels,
        "meta": {
            "labels": ["Hipotese", "Evidencia", "Tema", "Ator"],
            "tipos": ["APOIA", "CONTRADIZ", "CONCORRE_COM", "TEM_TEMA", "MENCIONA"],
            "n_nos": len(nos), "n_rels": len(rels),
            "sementes": sorted(ids_vivas),
        },
    }
    destino = RAIZ / "web" / "grafo.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")),
                       encoding="utf-8")
    print(f"{destino}  ({len(nos)} nos, {len(rels)} relacoes)")
    for lab in dados["meta"]["labels"]:
        print(f"    {lab:<10} {sum(1 for n in nos if n['label'] == lab):>4}")
    for tp in dados["meta"]["tipos"]:
        print(f"    :{tp:<14} {sum(1 for r in rels if r['tipo'] == tp):>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
