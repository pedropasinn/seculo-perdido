# Wiki de Evidências — One Piece

Sistema de raciocínio baseado em evidências sobre o mistério central de One Piece.
Não é um blog de teorias: toda afirmação aponta para um átomo verificável, toda
hipótese arrisca previsões falseáveis, e um validador determinístico bloqueia
qualquer coisa que o LLM tenha inventado.

## Começar

```bash
make check                      # portão de fundamentação
make site                       # gera site/index.html
python3 tools/score.py H-03     # log-odds de uma hipótese
make sensibilidade              # o ranking sobrevive a mexer nos pesos?
python3 tools/buscar.py "roger laugh tale"
```

Nenhuma dependência além de PyYAML.

## Estrutura

```
CLAUDE.md              regras mestras — o Claude Code lê isso primeiro
schema/                contratos JSON dos dois tipos de documento
data/evidencias/       átomos EV-<cap>-<seq>.md
data/hipoteses/        hipóteses H-##.md  +  H-##.redteam.md
agents/                prompts dos quatro papéis
tools/validate.py      portão de fundamentação (determinístico)
tools/score.py         log-odds — insumo, não decisão
tools/sensibilidade.py o ranking é do dado ou dos pesos?
tools/coletar.py       baixa wikitext preservando as refs de capítulo
tools/buscar.py        busca lexical
tools/render.py        site estático
```

## Fluxo de um capítulo novo

```
make extract CAP=1191   →  átomos novos
make link               →  elos de apoio/contradição
make redteam            →  ataque hostil às hipóteses afetadas
make curate             →  status e prioris atualizados
make check && make site →  valida e publica
git commit              →  o histórico é o registro da teoria evoluindo
```

## Fontes

Permitido: One Piece Wiki (CC BY-SA), SBS, databooks, entrevistas, anotações
próprias feitas a partir de cópias legais.
Proibido: scans e scanlations.

### The Library of Ohara

`thelibraryofohara.com` é veículo de fonte permitida, não fonte em si. Ele
publica traduções de SBS e de databook (que o `CLAUDE.md` autoriza) e análises
gramaticais do japonês original. A regra de uso:

- **Tradução/glosa do japonês** — vira átomo, com confiabilidade `ambiguo`
  quando a afirmação é identidade lexical verificável (ex.: o Harley usa
  literalmente 約束の日, *Dia da Promessa*) e `traducao_disputada` quando depende
  da leitura do analista (ex.: a lua crescente designar o clã Kouzuki).
- **SBS e Vivre Card traduzidos** — átomo com `tipo: sbs` ou `tipo: databook`.
- **Chapter Secrets** — mistura fato e interpretação na mesma frase. Serve para
  achar o que extrair, nunca para citar direto.
- **The True History / MEGA-Theory** — teoria de fã. Não é fonte de átomo em
  nenhuma hipótese. Uso legítimo: testar se o nosso conjunto de hipóteses é
  exaustivo, que é a premissa mais frágil das fatias acima.

A API REST do site é aberta: `/wp-json/wp/v2/posts?categories=<id>&_fields=…`.
Categorias úteis: `the-true-history` (1070851), `sbs` (139757),
`vivre-card-databook` (648324575).

## Escopo inicial

Século Vazio, Joy Boy, Laugh Tale, Imu, Poneglyphs, D. — cerca de 300 átomos.
Só escale depois que o ciclo rodar limpo nesse recorte.

## Estado (2026-08-11, último capítulo publicado: 1190)

197 átomos, 15 hipóteses, seis rodadas de curadoria. Doze hipóteses disputam o
escopo `one_piece` (mutuamente exclusivas); três são de escopo auxiliar.

As três últimas — H-11, H-12, H-13 — não nasceram aqui. Vieram de um teste de
exaustividade: nove agentes leram a série *True History* do Library of Ohara
procurando alternativas que o repositório não tivesse formulado, e acharam três.
Isso importa porque a fatia assume que a resposta está entre as listadas, e essa
premissa é a única que os testes de sensibilidade não conseguem medir. Das
três, duas foram refutadas no mesmo dia pelo Red Team; H-11 sobreviveu ferida e
ficou em quarto lugar.

| id | o que afirma | status | fatia |
|----|--------------|--------|-------|
| H-05 | legado dirigido de Joy Boy: palavras e uma condição | viva, ferida | 31% |
| H-08 | gatilho de um evento agendado (Terceiro Mundo do Harley) | viva, ferida | 22% |
| H-11 | objeto comum cujo valor está no ato de partilhá-lo | viva, ferida | 20% |
| H-04 | registro completo do Século Vazio | viva, ferida | 13% |
| H-03 | artefato funcional do Reino Antigo | viva, ferida | 10% |
| H-02 | valor relacional; o efeito veio do anúncio | viva, ferida | 4% |
| H-06 | a arma ancestral Uranus | viva, ferida | 1% |
| H-01, H-07, H-12, H-13, H-15 | ver cemitério abaixo | **refutadas** | — |

Fora do escopo do tesouro: **H-09** (Imu usurpou soberania anterior, prior 0,32),
**H-10** (a fruta Nika seleciona quem a come, 0,32) e **H-14** (houve um ciclo
industrial anterior ao Reino Antigo, 0,38, ferida).

A fatia é a repartição do posterior dentro do escopo, e assume que a resposta
certa está entre as hipóteses listadas — o que é exatamente o que o repositório
não pode garantir. Leia `data/hipoteses/_orfaos.md` antes de confiar nela: átomo
órfão acumulado é o sintoma de uma nona alternativa que ninguém formulou.

Nenhuma hipótese sobreviveu intacta ao Red Team. Os relatórios de ataque estão em
`data/hipoteses/H-*.redteam.md` e valem mais que as fatias.

## Leia isto antes de citar o ranking

`make sensibilidade` roda três testes contra o próprio resultado:

- **perturbar** — sacode todos os pesos (±0,15) e prioris (±0,05) em 2000
  sorteios. H-05 lidera em **100%**. Nas rodadas anteriores o primeiro colocado
  ficou em 97,9%, depois 82,1%, depois 66,5%; a extração dos arcos antigos
  inverteu a tendência.
- **remover** — tira um átomo por vez. Nenhum troca o líder. Leia isso com a
  ressalva que a própria história deste arquivo impõe: na rodada 2 este teste
  também não acusava nada, e o motivo era que a base ainda não tinha as
  concorrentes certas. Um teste que passa mede o conjunto atual de hipóteses,
  não a realidade.
- **recencia** — e aqui está o resultado que justifica a sessão inteira. H-05
  tirava 62,8% do apoio do arco atual; agora tira **29,7%**. H-04 tira 6,2%.
  Cortando tudo acima do cap. 1100, o ranking vira
  `H-05 > H-04 > H-03 > H-02 > H-11 > H-08` — **a mesma hipótese lidera antes e
  depois do corte**, pela primeira vez desde que o teste existe.

O que mudou não foi o modelo, foi a base: 74 átomos novos de Ohara/Enies Lobby e
da Ilha dos Homens-Peixe. Enquanto o repositório só tinha lido o arco em
publicação, o topo da tabela media entusiasmo com o capítulo da semana. Agora
mede evidência distribuída ao longo da obra.

Duas ressalvas permanecem. H-08 ainda tira 48,3% do apoio de Elbaf e o segundo
ataque mostrou que seu enunciado não descreve a evidência — o gatilho observado é
co-presença de pessoas, não chegada a um lugar. E `_orfaos.md` abriu um cluster
novo: nenhuma hipótese viva trata de **como** o Governo suprime, só do que ele
esconde.
