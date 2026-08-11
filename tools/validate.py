#!/usr/bin/env python3
"""Portao de fundamentacao.

Deterministico, sem LLM. Roda antes de todo commit. Rejeita:
  - id fora do padrao ou duplicado
  - referencia a EV-/H- inexistente  (a alucinacao mais comum)
  - citacao cujo texto nao bate com o atomo citado
  - hipotese viva sem previsao aberta
  - enum invalido, prior fora de faixa
  - prioris de hipoteses mutuamente exclusivas somando muito acima de 1

Uso:  python3 tools/validate.py [--raiz .] [--limiar 0.35]
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
import unicodedata
from pathlib import Path

import yaml

RE_EV = re.compile(r"^EV-\d{4}-\d{2}$")
RE_H = re.compile(r"^H-\d{2,3}$")
RE_REF = re.compile(r"\b(EV-\d{4}-\d{2}|H-\d{2,3})\b")

CONFIABILIDADE = {"canonico", "sbs", "ambiguo", "traducao_disputada"}
TIPO = {"fala", "narracao", "imagem", "sbs", "databook", "entrevista", "capa"}
STATUS = {"viva", "refutada", "confirmada", "dormente"}
STATUS_PREV = {"aberta", "cumprida", "falhada"}

STOPWORDS = {
    "de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "que", "em", "no",
    "na", "nos", "nas", "um", "uma", "por", "para", "com", "se", "ao", "aos", "the",
}


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\s]", " ", texto)


def tokens(texto: str) -> set[str]:
    return {t for t in normalizar(texto).split() if len(t) > 2 and t not in STOPWORDS}


def similaridade(a: str, b: str) -> float:
    """Contencao assimetrica: quanto do vocabulario do atomo reaparece na
    justificativa (ou vice-versa).

    Jaccard seria errado aqui: a justificativa ACRESCENTA vocabulario
    interpretativo de proposito, e seria punida por isso. O que queremos medir e
    se a justificativa esta realmente falando do atomo citado — ou seja,
    cobertura, nao igualdade.
    """
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return difflib.SequenceMatcher(None, normalizar(a), normalizar(b)).ratio()
    inter = len(ta & tb)
    return max(inter / len(ta), inter / len(tb))


def carregar(caminho: Path) -> tuple[dict, str]:
    bruto = caminho.read_text(encoding="utf-8")
    if not bruto.startswith("---"):
        raise ValueError("arquivo sem frontmatter YAML")
    _, fm, corpo = bruto.split("---", 2)
    dados = yaml.safe_load(fm) or {}
    if not isinstance(dados, dict):
        raise ValueError("frontmatter nao e um mapa YAML")
    return dados, corpo


class Relatorio:
    def __init__(self) -> None:
        self.erros: list[str] = []
        self.avisos: list[str] = []

    def erro(self, onde: str, msg: str) -> None:
        self.erros.append(f"ERRO  {onde}: {msg}")

    def aviso(self, onde: str, msg: str) -> None:
        self.avisos.append(f"AVISO {onde}: {msg}")


def validar(raiz: Path, limiar: float) -> Relatorio:
    rel = Relatorio()
    evidencias: dict[str, dict] = {}
    hipoteses: dict[str, dict] = {}

    # --- carga -------------------------------------------------------------
    for caminho in sorted((raiz / "data" / "evidencias").glob("EV-*.md")):
        try:
            dados, _ = carregar(caminho)
        except Exception as exc:  # noqa: BLE001
            rel.erro(caminho.name, str(exc))
            continue
        ident = dados.get("id", "")
        if not RE_EV.match(str(ident)):
            rel.erro(caminho.name, f"id invalido: {ident!r} (esperado EV-####-##)")
            continue
        if ident != caminho.stem:
            rel.erro(caminho.name, f"id {ident} nao bate com o nome do arquivo")
        if ident in evidencias:
            rel.erro(caminho.name, f"id duplicado: {ident}")
        evidencias[ident] = dados

    for caminho in sorted((raiz / "data" / "hipoteses").glob("H-*.md")):
        if caminho.name.endswith(".redteam.md"):
            continue
        try:
            dados, _ = carregar(caminho)
        except Exception as exc:  # noqa: BLE001
            rel.erro(caminho.name, str(exc))
            continue
        ident = dados.get("id", "")
        if not RE_H.match(str(ident)):
            rel.erro(caminho.name, f"id invalido: {ident!r} (esperado H-##)")
            continue
        if ident in hipoteses:
            rel.erro(caminho.name, f"id duplicado: {ident}")
        hipoteses[ident] = dados

    # --- evidencias --------------------------------------------------------
    for ident, ev in evidencias.items():
        for campo in ("fonte", "tipo", "confiabilidade", "texto", "temas"):
            if not ev.get(campo):
                rel.erro(ident, f"campo obrigatorio ausente: {campo}")
        if ev.get("tipo") not in TIPO and ev.get("tipo"):
            rel.erro(ident, f"tipo invalido: {ev['tipo']}")
        if ev.get("confiabilidade") not in CONFIABILIDADE and ev.get("confiabilidade"):
            rel.erro(ident, f"confiabilidade invalida: {ev['confiabilidade']}")
        if not ev.get("fonte_url"):
            rel.aviso(ident, "sem fonte_url — impossivel reverificar depois")
        if len(str(ev.get("texto", ""))) > 400:
            rel.aviso(ident, "texto longo demais; um atomo = uma afirmacao")

    # --- hipoteses ---------------------------------------------------------
    for ident, hip in hipoteses.items():
        if hip.get("status") not in STATUS:
            rel.erro(ident, f"status invalido: {hip.get('status')}")
        prior = hip.get("prior")
        if not isinstance(prior, (int, float)) or not 0 <= prior <= 1:
            rel.erro(ident, f"prior fora de faixa: {prior!r}")
        elif prior > 0.85:
            rel.aviso(ident, f"prior {prior} acima de 0.85 — calibracao suspeita")

        previsoes = hip.get("prediz") or []
        if not previsoes:
            rel.erro(ident, "sem previsao falseavel — hipotese nao entra no repo")
        for prev in previsoes:
            if prev.get("status") not in STATUS_PREV:
                rel.erro(ident, f"status de previsao invalido: {prev.get('status')}")
        if hip.get("status") == "viva":
            if not any(p.get("status") == "aberta" for p in previsoes):
                rel.erro(ident, "hipotese viva sem nenhuma previsao aberta")
            if not (hip.get("apoia") or []):
                rel.erro(ident, "hipotese viva sem nenhum atomo de apoio")

        # o coracao do portao: toda citacao precisa resolver E bater
        for rotulo in ("apoia", "contradiz"):
            for elo in hip.get(rotulo) or []:
                ref = elo.get("ev", "")
                if ref not in evidencias:
                    rel.erro(ident, f"{rotulo} aponta para atomo inexistente: {ref}")
                    continue
                peso = elo.get("peso")
                if not isinstance(peso, (int, float)) or not 0 <= peso <= 1:
                    rel.erro(ident, f"{rotulo} {ref}: peso invalido {peso!r}")
                conf = evidencias[ref].get("confiabilidade")
                if conf == "traducao_disputada" and isinstance(peso, (int, float)) and peso > 0.4:
                    rel.aviso(ident, f"{ref}: peso {peso} alto para traducao disputada")
                como = str(elo.get("como", ""))
                if len(como) < 15:
                    rel.erro(ident, f"{rotulo} {ref}: campo 'como' vazio ou generico")
                else:
                    sim = similaridade(como, str(evidencias[ref].get("texto", "")))
                    if sim < limiar:
                        rel.erro(
                            ident,
                            f"{rotulo} {ref}: a justificativa nao corresponde ao atomo "
                            f"(similaridade {sim:.2f} < {limiar}) — possivel alucinacao",
                        )

        for conc in hip.get("concorrentes") or []:
            if conc not in hipoteses:
                rel.erro(ident, f"concorrente inexistente: {conc}")

    # --- referencias soltas no corpo de qualquer arquivo -------------------
    for caminho in sorted((raiz / "data").rglob("*.md")):
        texto = caminho.read_text(encoding="utf-8")
        for ref in set(RE_REF.findall(texto)):
            if ref.startswith("EV-") and ref not in evidencias:
                rel.erro(caminho.name, f"referencia orfa no corpo: {ref}")
            if ref.startswith("H-") and ref not in hipoteses:
                rel.erro(caminho.name, f"referencia orfa no corpo: {ref}")

    # --- calibracao global -------------------------------------------------
    vivas = [h for h in hipoteses.values() if h.get("status") in {"viva", "confirmada"}]
    one_piece = [h for h in vivas if h.get("escopo") == "one_piece"]
    soma = sum(float(h.get("prior") or 0) for h in one_piece)
    if soma > 1.25:
        rel.aviso(
            "GLOBAL",
            f"prioris de hipoteses 'one_piece' somam {soma:.2f} — sao mutuamente "
            "exclusivas, deflacione o conjunto",
        )

    orfaos = raiz / "data" / "hipoteses" / "_orfaos.md"
    if orfaos.exists():
        n = len([l for l in orfaos.read_text(encoding="utf-8").splitlines() if l.startswith("- EV-")])
        if n >= 10:
            rel.aviso("GLOBAL", f"{n} atomos orfaos — provavelmente falta formular uma hipotese")

    print(f"  {len(evidencias)} atomos, {len(hipoteses)} hipoteses verificados")
    return rel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--limiar", type=float, default=0.35,
                    help="similaridade minima entre justificativa e atomo citado")
    args = ap.parse_args()

    rel = validar(Path(args.raiz), args.limiar)
    for linha in rel.avisos:
        print(linha)
    for linha in rel.erros:
        print(linha, file=sys.stderr)

    if rel.erros:
        print(f"\nFALHOU: {len(rel.erros)} erro(s), {len(rel.avisos)} aviso(s)", file=sys.stderr)
        return 1
    print(f"\nOK: 0 erros, {len(rel.avisos)} aviso(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
