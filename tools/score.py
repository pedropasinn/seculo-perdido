#!/usr/bin/env python3
"""Score bruto de uma hipotese, em log-odds.

Isto NAO decide nada. E insumo para o Curador, que ajusta com julgamento e
escreve a justificativa. Um numero sem justificativa escrita e invalido.

Modelo: cada elo e tratado como um fator de Bayes fraco e independente.
A independencia e falsa (atomos do mesmo capitulo se correlacionam), por isso o
teto de deflacao por fonte existe: sem ele, dez atomos do mesmo capitulo
"provariam" qualquer coisa.

Uso:  python3 tools/score.py [H-XX ...]
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent

# quanto cada nivel de confiabilidade vale
PESO_CONF = {
    "canonico": 1.0,
    "sbs": 0.8,
    "ambiguo": 0.6,
    "traducao_disputada": 0.4,
}

# forca maxima que um unico capitulo pode contribuir, em log-odds.
# freio contra o vies de "arco recente prova tudo".
TETO_POR_FONTE = 1.2


def ler(caminho: Path) -> dict:
    bruto = caminho.read_text(encoding="utf-8")
    _, fm, _ = bruto.split("---", 2)
    return yaml.safe_load(fm) or {}


def carregar_evidencias() -> dict[str, dict]:
    return {
        (d := ler(p))["id"]: d
        for p in (RAIZ / "data" / "evidencias").glob("EV-*.md")
    }


def contribuicao(peso: float, conf: str) -> float:
    """Converte um peso 0-1 em log-odds, escalado pela confiabilidade."""
    efetivo = float(peso) * PESO_CONF.get(conf, 0.5)
    # peso 1.0 canonico -> ~1.6 log-odds (fator ~5x). Deliberadamente modesto.
    return efetivo * 1.6


def pontuar(hip: dict, evidencias: dict[str, dict]) -> dict:
    prior = float(hip.get("prior") or 0.5)
    prior = min(max(prior, 0.01), 0.99)
    logodds = math.log(prior / (1 - prior))

    por_fonte: dict[str, float] = defaultdict(float)
    detalhe: list[str] = []

    for rotulo, sinal in (("apoia", 1), ("contradiz", -1)):
        for elo in hip.get(rotulo) or []:
            ev = evidencias.get(elo.get("ev", ""))
            if not ev:
                continue
            delta = sinal * contribuicao(elo.get("peso", 0), ev.get("confiabilidade", ""))
            por_fonte[str(ev.get("fonte", "?"))] += delta
            detalhe.append(f"    {elo['ev']:<14} {rotulo:<10} {delta:+.2f}")

    # aplica o teto por fonte
    total = 0.0
    for fonte, soma in por_fonte.items():
        limitado = max(-TETO_POR_FONTE, min(TETO_POR_FONTE, soma))
        if abs(limitado) < abs(soma):
            detalhe.append(f"    [teto] {fonte}: {soma:+.2f} -> {limitado:+.2f}")
        total += limitado

    logodds += total
    posterior = 1 / (1 + math.exp(-logodds))

    # previsoes falhadas sao veneno: cada uma corta o posterior pela metade
    falhadas = sum(1 for p in hip.get("prediz") or [] if p.get("status") == "falhada")
    if falhadas:
        posterior *= 0.5 ** falhadas
        detalhe.append(f"    [previsoes falhadas: {falhadas}] penalidade aplicada")

    return {"prior": prior, "posterior": posterior, "detalhe": detalhe,
            "n_apoia": len(hip.get("apoia") or []),
            "n_contra": len(hip.get("contradiz") or [])}


def main() -> int:
    evidencias = carregar_evidencias()
    alvos = sys.argv[1:]
    arquivos = sorted((RAIZ / "data" / "hipoteses").glob("H-*.md"))
    arquivos = [p for p in arquivos if not p.name.endswith(".redteam.md")]
    if alvos:
        arquivos = [p for p in arquivos if p.stem in alvos]
    if not arquivos:
        print("nenhuma hipotese encontrada")
        return 1

    for caminho in arquivos:
        hip = ler(caminho)
        r = pontuar(hip, evidencias)
        print(f"\n{hip['id']}  [{hip.get('status')}]  {hip.get('enunciado', '')[:70]}")
        print(f"  prior {r['prior']:.2f} -> posterior {r['posterior']:.2f}   "
              f"({r['n_apoia']} apoios, {r['n_contra']} contradicoes)")
        for linha in r["detalhe"]:
            print(linha)
    print("\nLembrete: isto e insumo. O Curador decide e escreve o porque.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
