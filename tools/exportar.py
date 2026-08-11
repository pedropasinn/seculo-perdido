#!/usr/bin/env python3
"""Publica a base inteira em formatos abertos, em web/dados/.

O repositorio ja e aberto, mas clonar um repo nao e forma razoavel de consultar
uma base. Aqui ela sai em formatos que qualquer um consome: JSON para codigo,
CSV para planilha, NDJSON para pipeline, Markdown para ler, e um zip com tudo.

Sao os mesmos dados de data/, sem interpretacao acrescentada — a licenca
CC BY-SA acompanha dentro do pacote.

Uso:  python3 tools/exportar.py
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
DEST = RAIZ / "web" / "dados"
sys.path.insert(0, str(RAIZ / "tools"))
import score  # noqa: E402


def ler(p: Path) -> tuple[dict, str]:
    bruto = p.read_text(encoding="utf-8")
    _, fm, corpo = bruto.split("---", 2)
    return (yaml.safe_load(fm) or {}), corpo.strip()


def git(*a, padrao=""):
    try:
        return subprocess.run(["git", *a], cwd=RAIZ, capture_output=True,
                              text=True, timeout=10).stdout.strip() or padrao
    except Exception:
        return padrao


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)

    evid, hips = {}, []
    for p in sorted((RAIZ / "data" / "evidencias").glob("EV-*.md")):
        meta, corpo = ler(p)
        meta["contexto"] = corpo
        evid[meta["id"]] = meta
    for p in sorted((RAIZ / "data" / "hipoteses").glob("H-*.md")):
        if p.name.endswith(".redteam.md"):
            continue
        meta, corpo = ler(p)
        meta["corpo"] = corpo
        rt = p.with_suffix("").with_suffix(".redteam.md")
        meta["redteam"] = rt.read_text(encoding="utf-8") if rt.exists() else ""
        hips.append(meta)

    score.indexar_compartilhamento(hips)      # antes de pontuar
    for h in hips:
        h["posterior"] = round(score.pontuar(h, evid)["posterior"], 4)
    vivas = [h for h in hips if h.get("escopo") == "one_piece"
             and h.get("status") in {"viva", "confirmada"}]
    soma = sum(h["posterior"] for h in vivas) or 1.0
    ids_vivas = {h["id"] for h in vivas}
    for h in hips:
        h["fatia"] = round(h["posterior"] / soma, 4) if h["id"] in ids_vivas else 0.0

    citado: dict[str, list] = {}
    for h in hips:
        for rot in ("apoia", "contradiz"):
            for e in h.get(rot) or []:
                citado.setdefault(e["ev"], []).append(
                    {"hipotese": h["id"], "relacao": rot, "peso": e.get("peso"),
                     "justificativa": e.get("como")})
    for i, e in evid.items():
        e["citado_por"] = citado.get(i, [])

    caps = [int(i.split("-")[1]) for i in evid if i.split("-")[1].isdigit()]
    meta = {
        "projeto": "Século Perdido",
        "descricao": "Arquivo de evidências sobre o mistério central de One Piece.",
        "site": "https://seculo-perdido.vercel.app",
        "repositorio": "https://github.com/pedropasinn/seculo-perdido",
        "licenca_dados": "CC BY-SA 3.0",
        "licenca_codigo": "MIT",
        "atribuicao": "Paráfrases de material da One Piece Wiki (CC BY-SA 3.0). "
                      "One Piece é obra de Eiichiro Oda / Shueisha.",
        "gerado_em": git("log", "-1", "--format=%cI", padrao=""),
        "commit": git("rev-parse", "HEAD", padrao=""),
        "capitulo_mais_recente": max(caps) if caps else 0,
        "n_evidencias": len(evid),
        "n_hipoteses": len(hips),
        "vocabulario": {
            "confiabilidade": ["canonico", "sbs", "ambiguo", "traducao_disputada"],
            "tipo": ["fala", "narracao", "imagem", "sbs", "databook", "entrevista", "capa"],
            "status": ["viva", "refutada", "confirmada", "dormente"],
            "escopo": ["one_piece", "seculo_vazio", "imu", "joy_boy", "poneglyph", "outro"],
            "relacao": ["apoia", "contradiz"],
        },
        "como_ler": {
            "fatia": "repartição da probabilidade entre hipóteses de escopo one_piece; "
                     "assume que a resposta certa está entre as listadas",
            "peso": "0 a 1, força atribuída ao elo pelo curador",
            "posterior": "prior atualizado pelos elos, com teto por capítulo e por arco",
            "traducao_disputada": "a afirmação depende da escolha do tradutor; peso limitado a 0.4",
        },
    }

    lista_ev = [evid[k] for k in sorted(evid)]
    (DEST / "evidencias.json").write_text(
        json.dumps(lista_ev, ensure_ascii=False, indent=1), encoding="utf-8")
    (DEST / "hipoteses.json").write_text(
        json.dumps(hips, ensure_ascii=False, indent=1), encoding="utf-8")
    (DEST / "tudo.json").write_text(json.dumps(
        {"meta": meta, "evidencias": lista_ev, "hipoteses": hips},
        ensure_ascii=False, indent=1), encoding="utf-8")
    (DEST / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                    encoding="utf-8")

    with (DEST / "evidencias.ndjson").open("w", encoding="utf-8") as f:
        for e in lista_ev:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def csv_txt(linhas, cabec):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cabec, extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)
        return buf.getvalue()

    ev_csv = csv_txt([{**e,
                       "temas": "|".join(e.get("temas") or []),
                       "atores": "|".join(e.get("atores") or []),
                       "citado_por": "|".join(c["hipotese"] for c in e["citado_por"]),
                       "capitulo": e["id"].split("-")[1]}
                      for e in lista_ev],
                     ["id", "capitulo", "fonte", "tipo", "confiabilidade", "texto",
                      "atores", "temas", "citado_por", "fonte_url"])
    (DEST / "evidencias.csv").write_text(ev_csv, encoding="utf-8")

    elos = [{"hipotese": h["id"], "relacao": rot, "evidencia": e["ev"],
             "peso": e.get("peso"), "justificativa": e.get("como")}
            for h in hips for rot in ("apoia", "contradiz") for e in h.get(rot) or []]
    (DEST / "elos.csv").write_text(
        csv_txt(elos, ["hipotese", "relacao", "evidencia", "peso", "justificativa"]),
        encoding="utf-8")

    hip_csv = csv_txt([{**h, "concorrentes": "|".join(h.get("concorrentes") or []),
                        "n_apoia": len(h.get("apoia") or []),
                        "n_contradiz": len(h.get("contradiz") or [])} for h in hips],
                      ["id", "enunciado", "escopo", "status", "prior", "posterior",
                       "fatia", "n_apoia", "n_contradiz", "concorrentes"])
    (DEST / "hipoteses.csv").write_text(hip_csv, encoding="utf-8")

    # markdown legivel, um arquivo so
    md = [f"# {meta['projeto']} — arquivo completo\n",
          f"\n{meta['descricao']}  \nCapítulo mais recente: {meta['capitulo_mais_recente']} · "
          f"{meta['n_evidencias']} átomos · {meta['n_hipoteses']} hipóteses\n",
          f"\nDados sob {meta['licenca_dados']}. {meta['atribuicao']}\n\n---\n\n## Hipóteses\n"]
    for h in sorted(hips, key=lambda x: (-x["fatia"], x["id"])):
        md.append(f"\n### {h['id']} — {h.get('status')} · fatia {h['fatia']*100:.1f}%\n\n"
                  f"**{h.get('enunciado')}**\n\n")
        for rot, sinal in (("apoia", "+"), ("contradiz", "−")):
            for e in h.get(rot) or []:
                md.append(f"- {sinal} `{e['ev']}` (peso {e.get('peso')}) — {e.get('como')}\n")
        for p in h.get("prediz") or []:
            md.append(f"- prevê [{p.get('status')}]: {p.get('texto')}\n")
    md.append("\n---\n\n## Átomos de evidência\n")
    for e in lista_ev:
        md.append(f"\n### {e['id']} · {e.get('fonte')} · {e.get('confiabilidade')}\n\n"
                  f"{e.get('texto')}\n")
        if e.get("fonte_url"):
            md.append(f"\nFonte: {e['fonte_url']}\n")
    (DEST / "seculo-perdido.md").write_text("".join(md), encoding="utf-8")

    with zipfile.ZipFile(DEST / "seculo-perdido.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for nome in ("tudo.json", "evidencias.json", "hipoteses.json", "meta.json",
                     "evidencias.csv", "hipoteses.csv", "elos.csv",
                     "evidencias.ndjson", "seculo-perdido.md"):
            z.write(DEST / nome, nome)
        z.write(RAIZ / "data" / "LICENSE", "LICENSE-dados.txt")
        z.writestr("LEIA-ME.txt",
                   "Século Perdido — arquivo de evidências sobre One Piece\n"
                   f"{meta['site']}\n\nDados sob CC BY-SA 3.0.\n{meta['atribuicao']}\n\n"
                   "tudo.json      base inteira, com metadados e vocabulário\n"
                   "evidencias.*   os átomos, em json, csv e ndjson\n"
                   "hipoteses.json hipóteses com elos, previsões e red team\n"
                   "elos.csv       cada ligação hipótese↔átomo, com peso e justificativa\n"
                   "seculo-perdido.md  tudo em markdown, para ler ou dar a um LLM\n")

    tam = {p.name: p.stat().st_size for p in sorted(DEST.iterdir()) if p.is_file()}
    print(f"{DEST}")
    for n, s in tam.items():
        print(f"    {n:<24} {s/1024:8.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
