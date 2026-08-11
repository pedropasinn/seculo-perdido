#!/usr/bin/env python3
"""Baixa wikitext da One Piece Wiki e limpa para leitura, preservando [ch. NNN].

O ponto: o wikitext traz {{Qref|chap=395|...}} colado na propria frase. E isso que
permite ao Extrator atribuir capitulo a cada atomo sem depender de memoria — sem
esta ferramenta, o passo `make extract` vira adivinhacao.

So pega paginas da One Piece Wiki (CC BY-SA), que e fonte permitida. Nao busque
scan nem scanlation com isto.

Uso:  python3 tools/coletar.py "Void Century" "Chapter 1191"
      -> .cache/wiki/Void_Century.txt
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = "https://onepiece.fandom.com/api.php"
SAIDA = Path(__file__).resolve().parent.parent / ".cache" / "wiki"
SAIDA.mkdir(parents=True, exist_ok=True)


def baixar(titulo: str) -> str | None:
    url = (f"{BASE}?action=parse&page={titulo.replace(' ', '%20')}"
           "&prop=wikitext&format=json&formatversion=2&redirects=1")
    r = subprocess.run(["curl", "-sS", "-m", "40", url], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    if "error" in d:
        return None
    return d["parse"]["wikitext"]


def refs_do_template(corpo: str) -> str:
    caps = re.findall(r"\bchap\d?\s*=\s*(\d+)", corpo)
    if not caps:
        return ""
    return "[ch. " + ", ".join(dict.fromkeys(caps)) + "]"


def tirar_templates(texto: str) -> str:
    """Remove {{...}} balanceado; Qref/qref vira [ch. NNN]."""
    saida, i, n = [], 0, len(texto)
    while i < n:
        if texto.startswith("{{", i):
            prof, j = 1, i + 2
            while j < n and prof:
                if texto.startswith("{{", j):
                    prof += 1
                    j += 2
                elif texto.startswith("}}", j):
                    prof -= 1
                    j += 2
                else:
                    j += 1
            corpo = texto[i + 2:j - 2]
            nome = corpo.split("|")[0].strip().lower()
            if nome.startswith("qref"):
                saida.append(refs_do_template(corpo))
            elif nome == "nihongo":
                partes = corpo.split("|")
                saida.append(partes[1] if len(partes) > 1 else "")
            i = j
        else:
            saida.append(texto[i])
            i += 1
    return "".join(saida)


def limpar(w: str) -> str:
    w = re.sub(r"<ref[^>]*/>", "", w)
    w = re.sub(r"<ref[^>]*>.*?</ref>", "", w, flags=re.S)
    w = re.sub(r"<!--.*?-->", "", w, flags=re.S)
    w = re.sub(r"\{\|.*?\|\}", "", w, flags=re.S)          # tabelas
    w = tirar_templates(w)
    w = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]|]*)\]\]", r"\1", w)  # links
    w = re.sub(r"\[\[File:.*?\]\]", "", w, flags=re.S)
    w = re.sub(r"'{2,}", "", w)
    w = re.sub(r"<[^>]+>", "", w)
    linhas = []
    for l in w.splitlines():
        l = l.strip()
        if not l or l.startswith(("|", "!", "{", "}")):
            continue
        linhas.append(l)
    return "\n".join(linhas)


PAGINAS = sys.argv[1:]
for titulo in PAGINAS:
    w = baixar(titulo)
    if w is None:
        print(f"FALHOU  {titulo}")
        continue
    texto = limpar(w)
    destino = SAIDA / (re.sub(r"[^A-Za-z0-9]+", "_", titulo).strip("_") + ".txt")
    destino.write_text(texto, encoding="utf-8")
    print(f"ok      {titulo:<34} {len(texto):>6} chars -> {destino.name}")
    time.sleep(0.4)
