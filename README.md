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

108 átomos, 13 hipóteses, quatro rodadas de curadoria. Onze hipóteses disputam o
escopo `one_piece` (mutuamente exclusivas); duas são de escopo auxiliar.

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
| H-08 | gatilho de um evento agendado (Terceiro Mundo do Harley) | viva, ferida | 25% |
| H-04 | registro completo do Século Vazio | viva, ferida | 19% |
| H-11 | objeto comum cujo valor está no ato de partilhá-lo | viva, ferida | 14% |
| H-03 | artefato funcional do Reino Antigo | viva, ferida | 7% |
| H-02 | valor relacional; o efeito veio do anúncio | viva, ferida | 4% |
| H-06 | a arma ancestral Uranus | viva, ferida | 1% |
| H-12 | *Binks' Sake* é o registro; Laugh Tale é a chave | **refutada** | — |
| H-13 | "One Piece" nomeia o estado final do mundo | **refutada** | — |
| H-01 | tesouro material de ouro e joias | **refutada** | — |
| H-07 | o Reino Antigo submerso reaparecendo | **refutada** | — |

A fatia é a repartição do posterior dentro do escopo, e assume que a resposta
certa está entre as hipóteses listadas — o que é exatamente o que o repositório
não pode garantir. Leia `data/hipoteses/_orfaos.md` antes de confiar nela: átomo
órfão acumulado é o sintoma de uma nona alternativa que ninguém formulou.

Nenhuma hipótese sobreviveu intacta ao Red Team. Os relatórios de ataque estão em
`data/hipoteses/H-*.redteam.md` e valem mais que as fatias.

## Leia isto antes de citar o ranking

`make sensibilidade` roda três testes contra o próprio resultado:

- **perturbar** — sacode todos os pesos (±0,15) e prioris (±0,05) em 2000
  sorteios. H-05 lidera em **82,1%**: a ordem não é artefato dos números
  digitados, mas não é confortável. Na rodada 2 eram 97,9%; a desambiguação do
  Harley e a entrada de H-11 encurtaram a distância.
- **remover** — tira um átomo por vez. **`EV-1190-03` derruba a liderança
  sozinho**: sem ele, quem lidera é H-08. É exatamente o ponto único de falha que
  o Red Team de H-05 apontou na primeira rodada. Vale registrar que na rodada 2
  esse mesmo teste dizia que nenhum átomo isolado trocava o líder — o átomo
  também contradiz H-03 e H-07, e enquanto essas contradições compensavam, o
  efeito ficava escondido. Um teste que passa não é prova de robustez; é prova de
  que a base ainda não tinha as concorrentes certas.
- **recencia** — 41% dos átomos vêm dos capítulos 1101-1200. H-05 tira **62,8%**
  do seu apoio do arco atual, H-08 tira 61,7%, H-03 tira 54,5% — e H-04 apenas
  12,4%. Cortando tudo acima do cap. 1100, o ranking vira
  `H-04 > H-02 > H-05 > H-03 > H-11 > H-08`.

Juntando os três: a liderança de H-05 depende de um único capítulo publicado há
poucas semanas, e o segundo e o terceiro colocados dependem do mesmo arco. O
`TETO_POR_FONTE` do `score.py` freia um capítulo que empurra sozinho, mas não
freia quinze capítulos do mesmo arco empurrando juntos. Enquanto Elbaf não
fechar, o topo da tabela diz mais sobre o que estamos lendo agora do que sobre o
que o One Piece é.
