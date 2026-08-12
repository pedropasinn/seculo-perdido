#!/usr/bin/env python3
"""Score bruto de uma hipotese, em log-odds.

Isto NAO decide nada. E insumo para o Curador, que ajusta com julgamento e
escreve a justificativa. Um numero sem justificativa escrita e invalido.

Modelo: cada elo e tratado como um fator de Bayes fraco e independente.
A independencia e falsa (atomos do mesmo capitulo se correlacionam), por isso o
teto de deflacao por fonte existe: sem ele, dez atomos do mesmo capitulo
"provariam" qualquer coisa.

Uso:  python3 tools/score.py [H-XX ...] [--tetos]

`--tetos` esconde as linhas de elo e mostra so os tetos. Existe por causa de um
vazamento real: o Red Team de H-17 foi instruido a rodar `score.py H-17` para ler
as linhas de teto, e a saida despejou os 23 ids de apoio e os 7 de contradicao do
alvo. O agente declarou a contaminacao em vez de esconde-la, e a ferramenta e que
estava errada. Ao encomendar um ataque, use `--tetos`.
"""
from __future__ import annotations

import math
import re
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

# ...e um deflator paralelo, por TIPO. `confiabilidade` responde "a fonte de fato
# diz isto"; `tipo` responde "que camada da obra e essa". Uma historia de capa
# realmente afirma o que afirma — mas afirma numa camada que a linha principal
# nao ratifica. Sem isto, um mural lido por Enel numa pagina de titulo valia, log-odds
# por log-odds, o mesmo que o discurso de Clover.
#
# Medido em 11/08/2026: os sete atomos `tipo: capa` do corpus, todos da mesma
# historia de capa, somavam +3.7 log-odds sozinhos — o bastante para levar um prior
# neutro de 0.50 a 0.977. O posterior de H-16 era a capa, e mais nada.
PESO_TIPO = {
    "capa": 0.4,
}

# forca maxima que um unico capitulo pode contribuir, em log-odds.
# freio contra o vies de "arco recente prova tudo".
TETO_POR_FONTE = 1.2

# ...so que o teto por capitulo nao freia quinze capitulos do MESMO arco
# empurrando juntos, que foi o que o teste de recencia mostrou: a lider tirava
# 69% do apoio de um arco so. Este segundo teto age sobre o arco inteiro.
#
# Mas um teto FIXO por arco pune quem extrai bem: dez capitulos distintos de
# Ohara somavam +4.56 e eram cortados para +1.80, o mesmo que quatro capitulos
# dariam. Isso premia base rala. O teto entao escala com a raiz do numero de
# capitulos distintos que contribuem — que e a forma classica de tamanho
# efetivo de amostra sob correlacao: mais capitulos carregam mais informacao
# independente, com retorno decrescente.
#
#   1 capitulo  -> 1.2   (o teto por capitulo ja domina, nada muda)
#   4 capitulos -> 2.4
#  10 capitulos -> 3.8
#  16 capitulos -> 4.8
TETO_ARCO_BASE = 1.2

# faixas aproximadas. Nao precisam ser exatas: o objetivo e agrupar capitulos que
# foram publicados juntos e que por isso se correlacionam, nao catalogar a obra.
ARCOS = [
    (1, 100, "East Blue"),
    (101, 216, "Arabasta"),
    (217, 302, "Skypiea"),
    (303, 374, "Water 7"),
    (375, 441, "Enies Lobby / Ohara"),
    (442, 489, "Thriller Bark"),
    (490, 513, "Sabaody"),
    (514, 580, "Marineford"),
    (581, 602, "pos-guerra"),
    (603, 653, "Ilha dos Homens-Peixe"),
    (654, 699, "Punk Hazard"),
    (700, 801, "Dressrosa"),
    (802, 824, "Zou"),
    (825, 902, "Whole Cake"),
    (903, 908, "Reverie"),
    (909, 1057, "Wano"),
    (1058, 1125, "Egghead"),
    (1126, 9999, "Elbaf"),
]


def arco(fonte: str) -> str:
    """'cap 1138' -> 'Elbaf'. O que nao tiver numero vira arco proprio.

    Le o PRIMEIRO numero, nao a concatenacao dos digitos. A versao antiga juntava
    tudo: "historia de capa caps 470-472" virava 470472, que nao cai em faixa
    nenhuma e ganhava um balde de arco so dele, com teto proprio — e o atomo que
    escapava era justamente o mais carregado de H-16. Bug de parser com efeito de
    tese.
    """
    # so casa numero precedido de "cap": senao "SBS volume 4" viraria capitulo 4
    # e cairia em East Blue. Nao ha SBS no corpus hoje, mas o vocabulario ja
    # preve databook e entrevista, e o erro seria silencioso.
    m = re.search(r"caps?\s*(\d+)", str(fonte), re.IGNORECASE)
    if not m:
        return str(fonte)
    n = int(m.group(1))
    for lo, hi, nome in ARCOS:
        if lo <= n <= hi:
            return nome
    return str(fonte)


def ler(caminho: Path) -> dict:
    bruto = caminho.read_text(encoding="utf-8")
    _, fm, _ = bruto.split("---", 2)
    return yaml.safe_load(fm) or {}


def carregar_evidencias() -> dict[str, dict]:
    return {
        (d := ler(p))["id"]: d
        for p in (RAIZ / "data" / "evidencias").glob("EV-*.md")
    }


def contribuicao(peso: float, conf: str, tipo: str = "") -> float:
    """Converte um peso 0-1 em log-odds, escalado pela confiabilidade e pelo tipo."""
    efetivo = float(peso) * PESO_CONF.get(conf, 0.5) * PESO_TIPO.get(tipo, 1.0)
    # peso 1.0 canonico -> ~1.6 log-odds (fator ~5x). Deliberadamente modesto.
    return efetivo * 1.6


# --- correcao de independencia -------------------------------------------
# score trata cada elo como fator de Bayes independente. Um atomo que apoia k
# hipoteses concorrentes do mesmo escopo NAO distingue entre elas: em Bayes, uma
# evidencia igualmente compativel com k alternativas nao altera a razao entre
# elas. Contar cheio para cada uma infla todas juntas.
#
# O fator divide a contribuicao pelo numero de hipoteses do mesmo escopo que
# recebem a MESMA relacao daquele atomo. Um atomo que apoia uma e contradiz
# outra continua valendo integral nas duas — esse discrimina, e e justamente o
# tipo de evidencia que decide.
_COMPART: dict[tuple[str, str, str], int] = {}


def indexar_compartilhamento(hipoteses: list[dict]) -> None:
    _COMPART.clear()
    contagem: dict[tuple[str, str, str], int] = {}
    for h in hipoteses:
        if h.get("status") not in {"viva", "confirmada"}:
            continue
        esc = str(h.get("escopo") or "outro")
        for rotulo in ("apoia", "contradiz"):
            for elo in h.get(rotulo) or []:
                k = (elo.get("ev", ""), rotulo, esc)
                contagem[k] = contagem.get(k, 0) + 1
    _COMPART.update(contagem)


def fator_discriminacao(ev: str, rotulo: str, escopo: str) -> float:
    k = _COMPART.get((ev, rotulo, str(escopo or "outro")), 1)
    return 1.0 / max(k, 1)


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
            fd = fator_discriminacao(elo.get("ev", ""), rotulo, hip.get("escopo", ""))
            delta = sinal * contribuicao(elo.get("peso", 0), ev.get("confiabilidade", ""),
                                         ev.get("tipo", "")) * fd
            por_fonte[str(ev.get("fonte", "?"))] += delta
            marca = f"  (÷{round(1/fd)} compartilhado)" if fd < 1 else ""
            detalhe.append(f"    {elo['ev']:<14} {rotulo:<10} {delta:+.2f}{marca}")

    # teto por capitulo, depois teto por arco sobre o que sobrou
    por_arco: dict[str, float] = defaultdict(float)
    caps_do_arco: dict[str, set[str]] = defaultdict(set)
    for fonte, soma in por_fonte.items():
        limitado = max(-TETO_POR_FONTE, min(TETO_POR_FONTE, soma))
        if abs(limitado) < abs(soma):
            detalhe.append(f"    [teto cap] {fonte}: {soma:+.2f} -> {limitado:+.2f}")
        por_arco[arco(fonte)] += limitado
        caps_do_arco[arco(fonte)].add(str(fonte))

    total = 0.0
    for nome, soma in por_arco.items():
        teto = TETO_ARCO_BASE * math.sqrt(len(caps_do_arco[nome]))
        limitado = max(-teto, min(teto, soma))
        if abs(limitado) < abs(soma):
            detalhe.append(f"    [teto arco] {nome} ({len(caps_do_arco[nome])} caps, "
                           f"teto {teto:.2f}): {soma:+.2f} -> {limitado:+.2f}")
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


def normalizar_por_escopo(linhas: list[tuple[dict, dict]]) -> dict[str, list[tuple[str, float]]]:
    """Reparte a massa de probabilidade entre hipoteses do mesmo escopo.

    O score por hipotese e independente, entao os posteriores somam bem mais que
    1 quando as hipoteses sao mutuamente exclusivas. Normalizar e o minimo para
    poder ler os numeros como alternativas. Vale enfatizar o que a normalizacao
    assume e nao verifica: que o conjunto e exaustivo. Se a resposta certa nao
    estiver escrita em nenhum H-*.md, ela redistribui a massa entre erradas.
    """
    # so `one_piece` foi construido como conjunto mutuamente exclusivo, com o
    # campo `concorrentes` preenchido. Os escopos auxiliares agrupam hipoteses
    # que podem ser verdadeiras ao mesmo tempo — repartir probabilidade entre
    # elas seria inventar uma disputa que nao existe.
    por_escopo: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for hip, r in linhas:
        if hip.get("status") not in {"viva", "confirmada"}:
            continue  # refutada nao disputa a massa; ela ja saiu do pareo
        if str(hip.get("escopo")) != "one_piece":
            continue
        por_escopo["one_piece"].append((hip["id"], r["posterior"]))
    return {e: v for e, v in por_escopo.items() if len(v) > 1}


def main() -> int:
    evidencias = carregar_evidencias()
    todas = [ler(p) for p in sorted((RAIZ / "data" / "hipoteses").glob("H-*.md"))
             if not p.name.endswith(".redteam.md")]
    indexar_compartilhamento(todas)
    argv = sys.argv[1:]
    so_tetos = "--tetos" in argv
    alvos = [a for a in argv if not a.startswith("--")]
    arquivos = sorted((RAIZ / "data" / "hipoteses").glob("H-*.md"))
    arquivos = [p for p in arquivos if not p.name.endswith(".redteam.md")]
    if alvos:
        arquivos = [p for p in arquivos if p.stem in alvos]
    if not arquivos:
        print("nenhuma hipotese encontrada")
        return 1

    linhas = []
    for caminho in arquivos:
        hip = ler(caminho)
        r = pontuar(hip, evidencias)
        linhas.append((hip, r))
        print(f"\n{hip['id']}  [{hip.get('status')}]  {hip.get('enunciado', '')[:70]}")
        print(f"  prior {r['prior']:.2f} -> posterior {r['posterior']:.2f}   "
              f"({r['n_apoia']} apoios, {r['n_contra']} contradicoes)")
        for linha in r["detalhe"]:
            if so_tetos and not linha.lstrip().startswith("["):
                continue
            print(linha)

    for escopo, itens in normalizar_por_escopo(linhas).items():
        soma = sum(p for _, p in itens) or 1.0
        print(f"\n--- repartido dentro do escopo '{escopo}' (soma bruta {soma:.2f}) ---")
        for ident, post in sorted(itens, key=lambda t: -t[1]):
            fatia = post / soma
            print(f"  {ident}  {fatia*100:5.1f}%  {'#' * round(fatia * 40)}")
        print("  (assume que a resposta certa esta entre as hipoteses listadas)")

    print("\nLembrete: isto e insumo. O Curador decide e escreve o porque.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
