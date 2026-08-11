<div align="center">

# Século Perdido

**O que é o One Piece? Uma resposta que pode estar errada — e que diz onde.**

### [→ seculo-perdido.vercel.app](https://seculo-perdido.vercel.app)

[![site](https://img.shields.io/badge/site-seculo--perdido.vercel.app-ffb703?style=for-the-badge)](https://seculo-perdido.vercel.app)
[![dados](https://img.shields.io/badge/dados-CC%20BY--SA%203.0-2f9e6e?style=for-the-badge)](data/LICENSE)
[![código](https://img.shields.io/badge/código-MIT-1a7fb5?style=for-the-badge)](LICENSE)

</div>

---

Todo fandom tem teorias. O problema é que elas são **elásticas**: se moldam a
qualquer capítulo novo, nunca podem estar erradas, e por isso nunca ensinam nada.

Este repositório tenta o contrário. Toda afirmação sobre a obra aponta para um
**átomo de evidência** com fonte e capítulo. Toda hipótese arrisca **previsões que
podem dar errado**. Cada uma é atacada por um **red team que não vê os argumentos
a favor**. E um validador sem IA recusa o commit se uma citação não corresponder
ao texto citado.

Hoje são **289 átomos**, **17 hipóteses** e **17 relatórios de ataque** — cobrindo
até o capítulo 1190.

> Nenhuma hipótese sobreviveu intacta ao red team. Cinco foram refutadas e estão
> no cemitério, com o motivo escrito. Isso é o produto, não o defeito.

---

## O que tem no site

| | |
|---|---|
| **[Hipóteses](https://seculo-perdido.vercel.app/)** | as alternativas ranqueadas, cada uma com elos, previsões e o ataque que sofreu |
| **[Grafo](https://seculo-perdido.vercel.app/grafo)** | 434 nós e 1457 relações tipadas, no espírito do Neo4j — a aresta carrega peso e justificativa |
| **[Cronologia](https://seculo-perdido.vercel.app/cronologia)** | a linha do tempo do mundo, com a fonte de cada marco |
| **[Evidências](https://seculo-perdido.vercel.app/evidencias)** | os 289 átomos, com busca e as hipóteses que citam cada um |
| **[Histórico](https://seculo-perdido.vercel.app/historico)** | o rastro: cada rodada, o que entrou e o que mudou de posição |
| **[Método](https://seculo-perdido.vercel.app/metodo)** | como funciona, e o que o próprio arquivo não sabe |
| **[Dados & API](https://seculo-perdido.vercel.app/dados)** | a base inteira em JSON, CSV e Markdown, e o servidor MCP |

## Pergunte à base pelo Claude Code

O repositório traz um **servidor MCP** sem nenhuma dependência além da biblioteca
padrão. Funciona sem clonar nada:

```bash
curl -O https://seculo-perdido.vercel.app/mcp/servidor.py
```

```json
{
  "mcpServers": {
    "seculo-perdido": {
      "command": "python3",
      "args": ["/caminho/servidor.py", "--remoto"]
    }
  }
}
```

Seis ferramentas: `estado_do_arquivo`, `buscar_evidencia`, `obter_evidencia`,
`listar_hipoteses`, `obter_hipotese` e `comparar_hipoteses` — esta última mostra
onde a mesma evidência puxa duas hipóteses para lados opostos.

Junto vai uma [skill](skill/seculo-perdido/SKILL.md) que ensina o assistente a
citar o id de cada átomo, nunca afirmar de memória e não repetir a porcentagem
sem a ressalva de que ela assume exaustividade.

## As três regras que sustentam tudo

**1. Nada sai da memória do modelo.** Os átomos são escritos por agentes de LLM a
partir de fontes permitidas — One Piece Wiki, SBS, databooks, entrevistas. Se uma
cena não tem átomo, ela não pode ser afirmada, nem por quem escreve. Alucinar um
painel é o único erro fatal do projeto.

**2. Sem previsão falseável, não entra.** É a única barreira contra a teoria que
se molda a qualquer desfecho.

**3. O red team ataca no escuro.** Ele recebe o enunciado, as previsões e a base
de evidência — nunca os argumentos a favor. O relatório fica publicado junto da
hipótese, inclusive quando ela sobrevive.

## O que este arquivo admite não saber

Está publicado, não escondido no código:

- A porcentagem **assume que a resposta certa está entre as listadas**. É a
  premissa mais frágil, e nenhum teste estatístico a alcança.
- **71% do apoio da hipótese líder** vem de átomos que também alimentam rivais.
  Contando só evidência exclusiva, ela cai da 1ª para a 6ª posição.
- Onze átomos apoiam pares de hipóteses **declaradamente concorrentes**.
- Boa parte da evidência vem do arco em publicação, e leitura recente pesa mais
  do que deveria. Há teto por capítulo e por arco justamente por isso.
- Os átomos que não pertencem a hipótese nenhuma já fizeram **cinco hipóteses
  nascerem** — o acúmulo é tratado como sintoma, não como sobra.

```bash
make sensibilidade     # o ranking sobrevive a mexer nos pesos? e sem o arco atual?
```

## Rodar

Só precisa de Python 3 e PyYAML.

```bash
make check      # o portão: recusa citação sem lastro
make web        # gera o site em web/
make score      # log-odds das hipóteses
python3 tools/buscar.py "roger laugh tale"
```

O ciclo de um capítulo novo:

```
make extract CAP=1191   →  extrator lê a fonte e escreve átomos
make link               →  vinculador conecta aos existentes
make redteam            →  red team ataca as hipóteses afetadas
make curate             →  curador atualiza status e priors, e assina
make check && make web  →  valida e republica
```

## Estrutura

```
data/evidencias/         289 átomos EV-<capítulo>-<seq>.md
data/hipoteses/          17 hipóteses + os relatórios de red team
data/cronologia.md       os marcos datados, cada um citando seus átomos
agents/                  os prompts dos quatro papéis
tools/validate.py        o portão, determinístico e sem IA
tools/score.py           log-odds, com teto por capítulo e por arco
tools/independencia.py   quanto do apoio de cada hipótese é emprestado
tools/sensibilidade.py   o ranking é do dado ou dos pesos?
tools/site.py            gera o site — estático, sem framework
mcp/servidor.py          servidor MCP, sem dependências
```

## Licenças e fontes

O **código** é MIT. Os **dados** são CC BY-SA 3.0, porque são paráfrases de
material da [One Piece Wiki](https://onepiece.fandom.com), que é CC BY-SA — e a
cláusula share-alike obriga. A atribuição está no campo `fonte_url` de cada
átomo. Algumas análises de tradução vêm do
[The Library of Ohara](https://thelibraryofohara.com), igualmente atribuídas.

**Nenhum scan ou scanlation é usado**, por decisão de projeto. E o site não
reproduz arte, páginas nem diálogo íntegro da obra — as ilustrações são
originais, porque as imagens da wiki são material protegido da Shueisha e da Toei
e o *fair use* que ampara a wiki não se transfere.

*One Piece* é obra de Eiichiro Oda, publicada pela Shueisha. Este é um projeto de
fã, sem vínculo com os detentores dos direitos. **Spoilers até o capítulo 1190.**
