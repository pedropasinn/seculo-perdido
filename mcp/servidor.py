#!/usr/bin/env python3
"""Servidor MCP do Século Perdido — consulta a base de evidências.

Fala JSON-RPC 2.0 por stdio, sem nenhuma dependência além da biblioteca padrão
e do PyYAML que o repositório já usa. É de propósito: um servidor MCP que exige
`pip install` de meia dúzia de pacotes não é instalado por ninguém.

Duas formas de rodar:

  local   aponta para um clone do repositório e lê data/ direto
  remoto  sem clone, baixa https://seculo-perdido.vercel.app/dados/tudo.json

Configuração no Claude Code (~/.claude.json ou .mcp.json do projeto):

    {
      "mcpServers": {
        "seculo-perdido": {
          "command": "python3",
          "args": ["/caminho/para/seculo-perdido/mcp/servidor.py"]
        }
      }
    }

Sem clone nenhum, usando os dados publicados:

    {
      "mcpServers": {
        "seculo-perdido": {
          "command": "python3",
          "args": ["/caminho/servidor.py", "--remoto"]
        }
      }
    }
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

FONTE_REMOTA = "https://seculo-perdido.vercel.app/dados/tudo.json"
RAIZ = Path(__file__).resolve().parent.parent
VERSAO = "1.0.0"

BASE: dict = {"evidencias": [], "hipoteses": [], "meta": {}}


# --------------------------------------------------------------------- dados
def carregar(remoto: bool) -> None:
    global BASE
    if not remoto and (RAIZ / "data" / "evidencias").is_dir():
        try:
            import yaml
        except ImportError:
            remoto = True
        else:
            def ler(p):
                _, fm, corpo = p.read_text(encoding="utf-8").split("---", 2)
                d = yaml.safe_load(fm) or {}
                d["contexto"] = corpo.strip()
                return d
            ev = [ler(p) for p in sorted((RAIZ / "data" / "evidencias").glob("EV-*.md"))]
            hp = []
            for p in sorted((RAIZ / "data" / "hipoteses").glob("H-*.md")):
                if p.name.endswith(".redteam.md"):
                    continue
                d = ler(p)
                rt = p.with_suffix("").with_suffix(".redteam.md")
                d["redteam"] = rt.read_text(encoding="utf-8") if rt.exists() else ""
                hp.append(d)
            # posterior e fatia nao moram no .md: sao calculados por score.py,
            # e sem eles o ranking sai vazio no modo local
            try:
                sys.path.insert(0, str(RAIZ / "tools"))
                import score
                idx = {e["id"]: e for e in ev}
                for h in hp:
                    h["posterior"] = round(score.pontuar(h, idx)["posterior"], 4)
                vivas = [h for h in hp if h.get("escopo") == "one_piece"
                         and h.get("status") in {"viva", "confirmada"}]
                soma = sum(h["posterior"] for h in vivas) or 1.0
                ids = {h["id"] for h in vivas}
                for h in hp:
                    h["fatia"] = round(h["posterior"] / soma, 4) if h["id"] in ids else 0.0
            except Exception:
                pass
            BASE = {"evidencias": ev, "hipoteses": hp,
                    "meta": {"origem": "clone local", "n_evidencias": len(ev),
                             "n_hipoteses": len(hp)}}
            return
    with urllib.request.urlopen(FONTE_REMOTA, timeout=30) as r:
        BASE = json.loads(r.read().decode("utf-8"))
        BASE["meta"]["origem"] = "dados publicados"


def normal(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def ev_por_id(i: str):
    return next((e for e in BASE["evidencias"] if e["id"] == i.upper()), None)


def hip_por_id(i: str):
    return next((h for h in BASE["hipoteses"] if h["id"] == i.upper()), None)


# -------------------------------------------------------------------- tools
def t_buscar(termo="", confiabilidade=None, tema=None, capitulo=None,
             so_orfaos=False, limite=25):
    termos = normal(termo).split()
    citados = {e["ev"] for h in BASE["hipoteses"]
               for r in ("apoia", "contradiz") for e in h.get(r) or []}
    saida = []
    for e in BASE["evidencias"]:
        alvo = normal(" ".join([e["id"], e.get("texto", ""), e.get("fonte", ""),
                                " ".join(e.get("temas") or []),
                                " ".join(e.get("atores") or [])]))
        if not all(t in alvo for t in termos):
            continue
        if confiabilidade and e.get("confiabilidade") != confiabilidade:
            continue
        if tema and tema not in (e.get("temas") or []):
            continue
        if capitulo and not e["id"].startswith(f"EV-{int(capitulo):04d}"):
            continue
        if so_orfaos and e["id"] in citados:
            continue
        saida.append({"id": e["id"], "fonte": e.get("fonte"),
                      "confiabilidade": e.get("confiabilidade"),
                      "texto": e.get("texto"), "temas": e.get("temas"),
                      "fonte_url": e.get("fonte_url"),
                      "orfao": e["id"] not in citados})
    return {"total": len(saida), "mostrando": min(limite, len(saida)),
            "resultados": saida[:limite]}


def t_evidencia(id):
    e = ev_por_id(id)
    if not e:
        return {"erro": f"não existe átomo {id}"}
    refs = [{"hipotese": h["id"], "relacao": r, "peso": x.get("peso"),
             "justificativa": x.get("como")}
            for h in BASE["hipoteses"] for r in ("apoia", "contradiz")
            for x in h.get(r) or [] if x["ev"] == e["id"]]
    return {**e, "citado_por": refs}


def t_hipoteses(status=None, escopo=None):
    saida = []
    for h in BASE["hipoteses"]:
        if status and h.get("status") != status:
            continue
        if escopo and h.get("escopo") != escopo:
            continue
        saida.append({"id": h["id"], "enunciado": h.get("enunciado"),
                      "status": h.get("status"), "escopo": h.get("escopo"),
                      "prior": h.get("prior"), "posterior": h.get("posterior"),
                      "fatia": h.get("fatia"),
                      "apoios": len(h.get("apoia") or []),
                      "contradicoes": len(h.get("contradiz") or []),
                      "ferida": "ferida" in (h.get("redteam") or "").lower()})
    return {"total": len(saida),
            "hipoteses": sorted(saida, key=lambda x: -(x.get("fatia") or 0))}


def t_hipotese(id, incluir_redteam=True):
    h = hip_por_id(id)
    if not h:
        return {"erro": f"não existe hipótese {id}"}
    def elos(rot):
        return [{"evidencia": x["ev"], "peso": x.get("peso"),
                 "justificativa": x.get("como"),
                 "texto": (ev_por_id(x["ev"]) or {}).get("texto"),
                 "confiabilidade": (ev_por_id(x["ev"]) or {}).get("confiabilidade")}
                for x in h.get(rot) or []]
    r = {k: h.get(k) for k in ("id", "enunciado", "status", "escopo", "prior",
                               "posterior", "fatia", "prediz", "concorrentes")}
    r["apoia"] = elos("apoia")
    r["contradiz"] = elos("contradiz")
    r["corpo"] = h.get("corpo", "")
    if incluir_redteam:
        r["redteam"] = h.get("redteam", "")
    return r


def t_comparar(a, b):
    ha, hb = hip_por_id(a), hip_por_id(b)
    if not ha or not hb:
        return {"erro": "hipótese inexistente"}
    def mapa(h):
        return {x["ev"]: r for r in ("apoia", "contradiz") for x in h.get(r) or []}
    ma, mb = mapa(ha), mapa(hb)
    comuns = sorted(set(ma) & set(mb))
    return {
        "a": {"id": ha["id"], "enunciado": ha.get("enunciado"), "fatia": ha.get("fatia")},
        "b": {"id": hb["id"], "enunciado": hb.get("enunciado"), "fatia": hb.get("fatia")},
        "base_compartilhada": len(comuns),
        "so_de_a": sorted(set(ma) - set(mb)),
        "so_de_b": sorted(set(mb) - set(ma)),
        "em_comum": [{"evidencia": i, "em_a": ma[i], "em_b": mb[i],
                      "divergem": ma[i] != mb[i],
                      "texto": (ev_por_id(i) or {}).get("texto")} for i in comuns],
        "nota": "evidência que apoia uma e contradiz a outra é onde as duas se separam; "
                "base muito compartilhada significa que elas não são tão independentes "
                "quanto a repartição de probabilidade assume",
    }


def t_estado():
    vivas = [h for h in BASE["hipoteses"] if h.get("status") == "viva"]
    citados = {e["ev"] for h in BASE["hipoteses"]
               for r in ("apoia", "contradiz") for e in h.get(r) or []}
    caps = [int(e["id"].split("-")[1]) for e in BASE["evidencias"]]
    return {
        "meta": BASE.get("meta", {}),
        "capitulo_mais_recente": max(caps) if caps else 0,
        "n_evidencias": len(BASE["evidencias"]),
        "orfaos": len([e for e in BASE["evidencias"] if e["id"] not in citados]),
        "hipoteses_vivas": len(vivas),
        "refutadas": [h["id"] for h in BASE["hipoteses"] if h.get("status") == "refutada"],
        "ranking": [{"id": h["id"], "fatia": h.get("fatia"),
                     "enunciado": h.get("enunciado")}
                    for h in sorted(vivas, key=lambda x: -(x.get("fatia") or 0))
                    if h.get("escopo") == "one_piece"],
        "aviso": "a fatia assume que a resposta certa está entre as hipóteses listadas — "
                 "é a premissa mais frágil do arquivo",
    }


TOOLS = [
    ("buscar_evidencia",
     "Busca átomos de evidência por texto, tema, capítulo ou confiabilidade. "
     "Cada átomo é uma afirmação verificável sobre a obra, com fonte.",
     {"type": "object", "properties": {
         "termo": {"type": "string", "description": "palavras a buscar (conjunção, ignora acento)"},
         "confiabilidade": {"type": "string", "enum": ["canonico", "sbs", "ambiguo", "traducao_disputada"]},
         "tema": {"type": "string"}, "capitulo": {"type": "integer"},
         "so_orfaos": {"type": "boolean", "description": "só átomos que nenhuma hipótese cita"},
         "limite": {"type": "integer", "default": 25}}}, t_buscar),
    ("obter_evidencia", "Devolve um átomo pelo id (ex.: EV-1190-03) com quem o cita.",
     {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}, t_evidencia),
    ("listar_hipoteses", "Lista as hipóteses com probabilidade, apoios e contradições.",
     {"type": "object", "properties": {
         "status": {"type": "string", "enum": ["viva", "refutada", "confirmada", "dormente"]},
         "escopo": {"type": "string"}}}, t_hipoteses),
    ("obter_hipotese",
     "Dossiê completo de uma hipótese: elos com justificativa, previsões falseáveis "
     "e o relatório do red team.",
     {"type": "object", "properties": {
         "id": {"type": "string"},
         "incluir_redteam": {"type": "boolean", "default": True}}, "required": ["id"]}, t_hipotese),
    ("comparar_hipoteses",
     "Compara duas hipóteses: base compartilhada e onde a mesma evidência puxa para lados opostos.",
     {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
      "required": ["a", "b"]}, t_comparar),
    ("estado_do_arquivo",
     "Panorama: capítulo coberto, ranking atual, órfãos e o aviso de exaustividade.",
     {"type": "object", "properties": {}}, t_estado),
]
MAPA = {n: f for n, _, _, f in TOOLS}


# ------------------------------------------------------------------ protocolo
def responde(pedido: dict):
    m, pid = pedido.get("method"), pedido.get("id")
    if m == "initialize":
        return {"protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "seculo-perdido", "version": VERSAO}}
    if m == "tools/list":
        return {"tools": [{"name": n, "description": d, "inputSchema": s}
                          for n, d, s, _ in TOOLS]}
    if m == "tools/call":
        p = pedido.get("params", {})
        fn = MAPA.get(p.get("name"))
        if not fn:
            return {"content": [{"type": "text", "text": f"tool desconhecida: {p.get('name')}"}],
                    "isError": True}
        try:
            r = fn(**(p.get("arguments") or {}))
        except Exception as exc:  # noqa: BLE001
            return {"content": [{"type": "text", "text": f"erro: {exc}"}], "isError": True}
        return {"content": [{"type": "text",
                             "text": json.dumps(r, ensure_ascii=False, indent=1)}]}
    if m in ("notifications/initialized", "notifications/cancelled"):
        return None
    return {"__erro__": {"code": -32601, "message": f"método não suportado: {m}"}}


def main() -> int:
    carregar("--remoto" in sys.argv)
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            ped = json.loads(linha)
        except json.JSONDecodeError:
            continue
        r = responde(ped)
        if r is None or ped.get("id") is None:
            continue
        msg = {"jsonrpc": "2.0", "id": ped["id"]}
        msg.update({"error": r["__erro__"]} if "__erro__" in r else {"result": r})
        sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
