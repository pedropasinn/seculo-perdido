---
name: seculo-perdido
description: Consulta o arquivo de evidências do Século Perdido — hipóteses sobre o que é o One Piece, átomos verificáveis com fonte, relatórios de red team. Use quando a conversa envolver o mistério central de One Piece, o Século Perdido, Joy Boy, Laugh Tale, Imu, os Poneglyphs, a Vontade de D., ou quando pedirem para checar se uma teoria tem base. Também use para adicionar evidência nova depois de um capítulo.
---

# Século Perdido — arquivo de evidências sobre One Piece

Base pública com átomos de evidência verificável e hipóteses ranqueadas sobre o
mistério central de *One Piece*. Site: https://seculo-perdido.vercel.app

## A regra que faz este arquivo valer alguma coisa

**Seu conhecimento prévio de One Piece não é fonte.** Ao responder com esta
skill, toda afirmação factual sobre a obra precisa vir de um átomo da base, e o
átomo precisa ser citado pelo id (`EV-1190-03`). Se você lembra de uma cena mas
não existe átomo, diga que não existe átomo — não afirme.

Isso não é preciosismo: é o que separa este arquivo de um blog de teorias, e o
projeto trata alucinar um painel como o único erro fatal.

## Como consultar

Há três caminhos. Prefira o MCP se estiver configurado; ele é o mais direto.

### 1. Servidor MCP (recomendado)

Se `seculo-perdido` estiver nos servidores MCP, use as tools:

| tool | para quê |
|---|---|
| `estado_do_arquivo` | panorama: ranking atual, capítulo coberto, órfãos |
| `buscar_evidencia` | busca por texto, tema, capítulo ou confiabilidade |
| `obter_evidencia` | um átomo pelo id, com quem o cita |
| `listar_hipoteses` | todas, com probabilidade e contagem de elos |
| `obter_hipotese` | dossiê: elos com justificativa, previsões e red team |
| `comparar_hipoteses` | base compartilhada e onde a evidência diverge |

Comece por `estado_do_arquivo` quando a pergunta for ampla — ele já traz o
ranking e o aviso de exaustividade.

### 2. Sem MCP: os dados publicados

Tudo está em JSON, CSV e Markdown sob `https://seculo-perdido.vercel.app/dados/`:

```
tudo.json          base inteira com metadados e vocabulário  (~600 KB)
evidencias.json    os átomos                                  (~240 KB)
hipoteses.json     hipóteses com elos, previsões e red team    (~350 KB)
elos.csv           cada ligação, com peso e justificativa
seculo-perdido.md  tudo em markdown, bom para ler de uma vez
meta.json          só os metadados, leve — comece por aqui
```

Busque `meta.json` primeiro para saber o tamanho e o capítulo coberto, depois o
arquivo específico. Não baixe `tudo.json` se a pergunta for sobre uma hipótese só.

### 3. Com o repositório clonado

```bash
python3 tools/buscar.py "roger laugh tale"   # busca lexical
python3 tools/score.py H-05                  # log-odds de uma hipótese
python3 tools/sensibilidade.py recencia      # o ranking depende do arco atual?
make check                                   # o portão de fundamentação
```

## Como responder bem

**Cite sempre o id.** "Roger riu ao chegar a Laugh Tale (`EV-0967-11`)" é útil;
"Roger riu ao chegar" não é verificável.

**Diga o nível de confiabilidade quando importar.** `canonico` é cena da obra;
`ambiguo` é leitura de painel ou de resumo; `traducao_disputada` significa que a
afirmação depende da escolha do tradutor e tem peso limitado a 0,4. Muita
discussão de fandom morre quando se descobre que a frase era escolha de tradutor.

**Não reporte a porcentagem sem a ressalva.** A fatia reparte probabilidade entre
hipóteses mutuamente exclusivas e **assume que a resposta certa está entre as
listadas** — a premissa mais frágil do arquivo. E boa parte da evidência vem do
arco em publicação; `tools/sensibilidade.py recencia` mede isso.

**"Ferida" ≠ "refutada".** Ferida sobreviveu ao ataque com custo; refutada saiu
do páreo e está no cemitério, com o motivo escrito. O cemitério costuma ser mais
informativo que o topo do ranking.

**Ofereça o contra.** Toda hipótese tem `contradiz` preenchido. Uma resposta que
só mostra o que apoia está reproduzindo o vício que o arquivo existe para evitar.

## Para adicionar evidência nova

Só com o repositório clonado, e seguindo `agents/extrator.md`:

1. `python3 tools/coletar.py "Chapter 1191"` — baixa o wikitext preservando as
   referências de capítulo, que é o que permite datar o átomo
2. um átomo = uma afirmação, texto parafraseado, nunca diálogo copiado
3. `python3 tools/buscar.py "<termo>"` antes de criar, para não duplicar
4. `make check` — o validador recusa citação que não bate com o átomo citado
5. o red team roda em contexto limpo, **sem ver os argumentos a favor**

Fontes permitidas: One Piece Wiki (CC BY-SA), SBS, databooks, entrevistas.
**Proibido:** scans e scanlations.

## Configuração

Copie o bloco para `~/.claude.json` ou para o `.mcp.json` do projeto:

```json
{
  "mcpServers": {
    "seculo-perdido": {
      "command": "python3",
      "args": ["/caminho/para/seculo-perdido/mcp/servidor.py"]
    }
  }
}
```

Sem clonar nada, acrescente `"--remoto"` aos `args` — o servidor passa a ler os
dados publicados. Só precisa de Python 3; o modo local usa PyYAML.

## Ajustes

Esta skill funciona sem configuração, mas dá para adaptar:

- **Spoilers.** A base vai até o capítulo 1190. Para limitar, filtre por capítulo
  na busca e diga ao assistente para ignorar átomos acima do seu ponto de leitura.
- **Só canônico.** Passe `confiabilidade: "canonico"` na busca para descartar
  leitura de painel e tradução disputada.
- **Foco.** Se só interessa um eixo (Imu, Joy Boy, Poneglyphs), use `tema` na
  busca ou `escopo` ao listar hipóteses.
- **Modo cético.** Peça explicitamente o `redteam` de cada hipótese citada; é
  onde estão os furos que o autor do arquivo já admitiu.
