#!/usr/bin/env python3
"""O ranking e do dado ou dos pesos que o Curador escolheu?

Dois testes, ambos deterministicos (semente fixa) e sem LLM:

  perturbar  — sacode todos os pesos e prioris dentro de uma faixa e mede com
               que frequencia cada hipotese continua liderando. Se a lider so
               lidera com os numeros exatos que alguem digitou, o ranking e
               opiniao com aparencia de calculo.

  remover    — tira um atomo de cada vez e remede. Quantifica o que o Red Team
               aponta a mao como 'ponto unico de falha': se apagar um atomo
               derruba a lider, o repositorio inteiro esta apoiado nele.

Uso:  python3 tools/sensibilidade.py [perturbar|remover] [--n 2000] [--delta 0.15]
"""
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import score  # noqa: E402

ESCOPO = "one_piece"


def carregar() -> tuple[dict, list[dict]]:
    evidencias = score.carregar_evidencias()
    hipoteses = []
    todas_h = []
    for p in sorted((RAIZ / "data" / "hipoteses").glob("H-*.md")):
        if p.name.endswith(".redteam.md"):
            continue
        h = score.ler(p)
        todas_h.append(h)
        if h.get("escopo") == ESCOPO and h.get("status") in {"viva", "confirmada"}:
            hipoteses.append(h)
    score.indexar_compartilhamento(todas_h)
    return evidencias, hipoteses


def ranquear(hipoteses: list[dict], evidencias: dict) -> list[tuple[str, float]]:
    r = [(h["id"], score.pontuar(h, evidencias)["posterior"]) for h in hipoteses]
    return sorted(r, key=lambda t: -t[1])


def perturbar(hipoteses: list[dict], delta: float, prior_delta: float,
              rng: random.Random) -> list[dict]:
    saida = deepcopy(hipoteses)
    for h in saida:
        p = float(h.get("prior") or 0.5) + rng.uniform(-prior_delta, prior_delta)
        h["prior"] = min(max(p, 0.01), 0.99)
        for rotulo in ("apoia", "contradiz"):
            for elo in h.get(rotulo) or []:
                w = float(elo.get("peso") or 0) + rng.uniform(-delta, delta)
                elo["peso"] = min(max(w, 0.0), 1.0)
    return saida


def cmd_perturbar(n: int, delta: float, prior_delta: float) -> None:
    evidencias, hipoteses = carregar()
    base = ranquear(hipoteses, evidencias)
    print(f"ranking atual: {' > '.join(i for i, _ in base)}\n")
    print(f"{n} sorteios, pesos +/-{delta}, prioris +/-{prior_delta}\n")

    rng = random.Random(20260811)
    lider = Counter()
    posicoes: dict[str, list[int]] = defaultdict(list)
    for _ in range(n):
        r = ranquear(perturbar(hipoteses, delta, prior_delta, rng), evidencias)
        lider[r[0][0]] += 1
        for pos, (ident, _) in enumerate(r, 1):
            posicoes[ident].append(pos)

    print("  hipotese   lidera    posicao media")
    for ident, _ in base:
        vezes = lider[ident]
        media = sum(posicoes[ident]) / len(posicoes[ident])
        print(f"  {ident}   {vezes/n*100:5.1f}%    {media:.2f}   "
              f"{'#' * round(vezes / n * 40)}")

    topo = lider.most_common(1)[0]
    print(f"\nveredito: {topo[0]} lidera em {topo[1]/n*100:.1f}% dos sorteios.")
    if topo[1] / n < 0.6:
        print("  ABAIXO DE 60% — o ranking e instavel; nao reporte a ordem como resultado.")
    elif topo[1] / n < 0.85:
        print("  entre 60% e 85% — a lideranca e real mas nao confortavel.")
    else:
        print("  acima de 85% — a lideranca sobrevive a escolha de pesos.")


def cmd_remover() -> None:
    evidencias, hipoteses = carregar()
    base = ranquear(hipoteses, evidencias)
    lider_base = base[0][0]
    print(f"lider com a base completa: {lider_base}\n")

    usados = sorted({e["ev"] for h in hipoteses
                     for r in ("apoia", "contradiz") for e in h.get(r) or []})
    trocas = []
    for ev in usados:
        podadas = deepcopy(hipoteses)
        for h in podadas:
            for r in ("apoia", "contradiz"):
                h[r] = [e for e in h.get(r) or [] if e["ev"] != ev]
        r = ranquear(podadas, evidencias)
        if r[0][0] != lider_base:
            trocas.append((ev, r[0][0], r[0][1] - dict(base)[r[0][0]]))

    if not trocas:
        print("nenhum atomo isolado troca o lider. O resultado nao depende de um so.")
        return
    print(f"{len(trocas)} atomo(s) que, removidos sozinhos, trocam o lider:\n")
    for ev, novo, _ in trocas:
        conf = evidencias.get(ev, {}).get("confiabilidade", "?")
        fonte = evidencias.get(ev, {}).get("fonte", "?")
        print(f"  {ev}  ({fonte}, {conf})  ->  passa a liderar {novo}")
    print("\nEstes sao os pontos unicos de falha do repositorio. Verifique a traducao\n"
          "e a fonte de cada um antes de confiar no ranking.")


def cmd_recencia(corte: int) -> None:
    """A lider vence porque a evidencia manda, ou porque o arco atual e o mais extraido?

    TETO_POR_FONTE freia um capitulo que empurra sozinho, mas nao freia quinze
    capitulos do mesmo arco empurrando juntos. Este teste corta tudo acima de
    `corte` e mostra o que a base anterior, sozinha, sustentava.
    """
    evidencias, hipoteses = carregar()
    base = ranquear(hipoteses, evidencias)
    print(f"com tudo:            {' > '.join(i for i, _ in base)}")

    print(f"\ndependencia do apoio vindo de capitulos > {corte}:")
    for h in hipoteses:
        rec = tot = 0.0
        for e in h.get("apoia") or []:
            atomo = evidencias.get(e["ev"], {})
            c = score.contribuicao(e.get("peso", 0), atomo.get("confiabilidade", ""),
                                   atomo.get("tipo", ""))
            tot += c
            if int(e["ev"].split("-")[1]) > corte:
                rec += c
        f = rec / tot if tot else 0.0
        print(f"  {h['id']}  {f*100:5.1f}%  {'#' * round(f * 30)}")

    podadas = deepcopy(hipoteses)
    for h in podadas:
        for r in ("apoia", "contradiz"):
            h[r] = [e for e in h.get(r) or [] if int(e["ev"].split("-")[1]) <= corte]
    sobrevivem = [h for h in podadas if h.get("apoia")]
    r = ranquear(sobrevivem, evidencias)
    print(f"\nso com cap <= {corte}:  {' > '.join(i for i, _ in r)}")
    if r and base and r[0][0] != base[0][0]:
        print(f"\n  A lideranca de {base[0][0]} e propriedade do arco atual: sem ele,\n"
              f"  quem lidera e {r[0][0]}. Trate o ranking como provisorio ate o arco fechar.")
    else:
        print("\n  A mesma hipotese lidera antes e depois do corte.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["perturbar", "remover", "recencia"],
                    nargs="?", default="perturbar")
    ap.add_argument("--corte", type=int, default=1100,
                    help="capitulo a partir do qual o atomo conta como 'arco atual'")
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--delta", type=float, default=0.15, help="ruido nos pesos dos elos")
    ap.add_argument("--prior-delta", type=float, default=0.05, help="ruido nos prioris")
    a = ap.parse_args()
    if a.modo == "perturbar":
        cmd_perturbar(a.n, a.delta, a.prior_delta)
    elif a.modo == "recencia":
        cmd_recencia(a.corte)
    else:
        cmd_remover()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
