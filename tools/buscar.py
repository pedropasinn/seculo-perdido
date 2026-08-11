#!/usr/bin/env python3
"""Busca lexical simples sobre atomos e hipoteses.

Deliberadamente sem embeddings no esqueleto: comece assim, meca o quanto voce
sente falta, e so entao ligue um vector store (sqlite-vec ou LanceDB). Muito
projeto morre montando infra de busca semantica antes de ter 50 documentos.

Uso:  python3 tools/buscar.py "reino antigo afundou"
      python3 tools/buscar.py --tema "Século Vazio"
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent


def normalizar(t: str) -> set[str]:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return {w for w in re.sub(r"[^a-z0-9\s]", " ", t).split() if len(w) > 2}


def docs():
    for pasta in ("evidencias", "hipoteses"):
        for p in (RAIZ / "data" / pasta).glob("*.md"):
            if p.name.startswith("_") or p.name.endswith(".redteam.md"):
                continue
            bruto = p.read_text(encoding="utf-8")
            if not bruto.startswith("---"):
                continue
            _, fm, corpo = bruto.split("---", 2)
            yield p, (yaml.safe_load(fm) or {}), corpo


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("termo", nargs="?", default="")
    ap.add_argument("--tema")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()

    alvo = normalizar(a.termo)
    achados = []
    for caminho, meta, corpo in docs():
        if a.tema and a.tema not in (meta.get("temas") or []):
            continue
        campo = " ".join([
            str(meta.get("texto", "")), str(meta.get("enunciado", "")),
            " ".join(meta.get("temas") or []), " ".join(meta.get("atores") or []), corpo,
        ])
        toks = normalizar(campo)
        score = len(alvo & toks) / len(alvo) if alvo else 1.0
        if score > 0:
            achados.append((score, meta.get("id", caminho.stem),
                            str(meta.get("texto") or meta.get("enunciado") or "")[:90]))

    for score, ident, resumo in sorted(achados, reverse=True)[: a.top]:
        print(f"{score:.2f}  {ident:<14} {resumo}")
    if not achados:
        print("nada encontrado — se voce esperava um atomo aqui, ele nao existe. Crie-o.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
