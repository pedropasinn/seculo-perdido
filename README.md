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

91 átomos, 10 hipóteses, três rodadas de curadoria. Oito hipóteses disputam o
escopo `one_piece` (mutuamente exclusivas); duas são de escopo auxiliar.

| id | o que afirma | status | fatia |
|----|--------------|--------|-------|
| H-05 | legado dirigido de Joy Boy: palavras e uma condição | viva, ferida | 36% |
| H-08 | gatilho de um evento agendado (Terceiro Mundo do Harley) | viva, ferida | 29% |
| H-04 | registro completo do Século Vazio | viva, ferida | 19% |
| H-03 | artefato funcional do Reino Antigo | viva, ferida | 9% |
| H-02 | valor relacional; o efeito veio do anúncio | viva, ferida | 5% |
| H-06 | a arma ancestral Uranus | viva, ferida | 1% |
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

- **perturbar** — sacode todos os pesos (±0,15) e prioris (±0,05) em milhares de
  sorteios. H-05 lidera em **83,8%**: a ordem não é artefato dos números
  digitados, mas deixou de ser confortável. Na rodada 2 eram 97,9%; a
  desambiguação do Harley encurtou a distância para H-08.
- **remover** — tira um átomo por vez. Nenhum átomo isolado troca o líder, o que
  contraria em parte o Red Team de H-05, que apontou `EV-1190-03` como ponto
  único de falha. Os dois estão certos sobre coisas diferentes: o score não
  desaba sem esse átomo, mas o *enunciado* deixa de ser distinguível de H-04.
- **recencia** — e aqui está o problema. 41% dos átomos vêm dos capítulos
  1101-1200, e H-05 tira **62,8%** do seu apoio do arco atual. Cortando tudo
  acima do cap. 1100, o ranking vira `H-04 > H-02 > H-05`.

Ou seja: a liderança de H-05 é propriedade do arco de Elbaf. O `TETO_POR_FONTE`
do `score.py` freia um capítulo que empurra sozinho, mas não freia quinze
capítulos do mesmo arco empurrando juntos. Enquanto Elbaf não fechar, trate a
ordem como provisória — e trate 62,8% como uma medida de quanto o entusiasmo
com o capítulo da semana está entrando no resultado.
