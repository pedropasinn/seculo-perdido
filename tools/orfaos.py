#!/usr/bin/env python3
"""Regenera data/hipoteses/_orfaos.md — atomos sem nenhum elo.

Cuidado que ja custou caro: orfao e o atomo sem ELO no frontmatter de alguma
hipotese. Menção dentro de um relatorio de red team NAO conta — o red team cita
atomos o tempo todo para argumentar, e contar isso como vinculo escondia orfaos
de verdade. Dois vinculadores tropecaram nisso na mesma rodada.

Uso:  python3 tools/orfaos.py
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
HIP = RAIZ / "data" / "hipoteses"
EV = RAIZ / "data" / "evidencias"


def main() -> int:
    vinculados: set[str] = set()
    for p in sorted(HIP.glob("H-*.md")):
        if p.name.endswith(".redteam.md"):
            continue                      # <- a correcao
        fm = yaml.safe_load(p.read_text(encoding="utf-8").split("---")[1]) or {}
        for rotulo in ("apoia", "contradiz"):
            for elo in fm.get(rotulo) or []:
                vinculados.add(elo.get("ev", ""))

    atomos = {}
    for p in sorted(EV.glob("EV-*.md")):
        d = yaml.safe_load(p.read_text(encoding="utf-8").split("---")[1]) or {}
        atomos[d["id"]] = d

    orf = [atomos[i] for i in sorted(atomos) if i not in vinculados]
    temas = Counter(t for d in orf for t in (d.get("temas") or []))
    grandes = [f"{t} ({n})" for t, n in temas.most_common(8) if n >= 3]

    L = ["# Átomos órfãos\n\n",
         "Átomos que não têm elo em nenhuma hipótese. Acúmulo aqui é sintoma de\n",
         "hipótese faltando — foi assim que H-11, H-14, H-16 e H-17 nasceram.\n\n",
         f"**{len(orf)} de {len(atomos)} átomos.** ",
         ("Concentrados em: " + ", ".join(grandes) + ".\n\n") if grandes else "\n\n",
         "Menção num relatório de red team não conta como vínculo: o atacante cita\n",
         "átomos para argumentar, e contar isso escondia órfãos de verdade.\n\n"]
    for d in orf:
        L.append(f"- {d['id']} — {str(d.get('texto',''))[:112]}\n")
    (HIP / "_orfaos.md").write_text("".join(L), encoding="utf-8")

    print(f"{len(orf)} orfaos de {len(atomos)} atomos")
    for t, n in temas.most_common(10):
        if n >= 3:
            print(f"    {n:>3}  {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
