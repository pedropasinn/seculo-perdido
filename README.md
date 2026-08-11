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

## Escopo inicial

Século Vazio, Joy Boy, Laugh Tale, Imu, Poneglyphs, D. — cerca de 300 átomos.
Só escale depois que o ciclo rodar limpo nesse recorte.

## Estado (2026-08-11, mangá no cap. 1191)

83 átomos, 10 hipóteses. O ciclo completo — extrair, vincular, red team, curar —
rodou uma vez sobre o recorte inicial. Oito hipóteses disputam o escopo
`one_piece` (mutuamente exclusivas); duas são de escopo auxiliar.

| id | o que afirma | status | fatia |
|----|--------------|--------|-------|
| H-05 | legado dirigido de Joy Boy: palavras e uma condição | viva, ferida | 42% |
| H-08 | gatilho de um evento agendado (Terceiro Mundo do Harley) | viva, ferida | 23% |
| H-04 | registro completo do Século Vazio | viva, ferida | 19% |
| H-03 | artefato funcional do Reino Antigo | viva, ferida | 8% |
| H-02 | valor relacional; o efeito veio do anúncio | viva, ferida | 6% |
| H-06 | a arma ancestral Uranus | viva, ferida | 1% |
| H-01 | tesouro material de ouro e joias | **refutada** | — |
| H-07 | o Reino Antigo submerso reaparecendo | **refutada** | — |

A fatia é a repartição do posterior dentro do escopo, e assume que a resposta
certa está entre as hipóteses listadas — o que é exatamente o que o repositório
não pode garantir. Leia `data/hipoteses/_orfaos.md` antes de confiar nela: átomo
órfão acumulado é o sintoma de uma nona alternativa que ninguém formulou.

Nenhuma hipótese sobreviveu intacta ao Red Team. Os relatórios de ataque estão em
`data/hipoteses/H-*.redteam.md` e valem mais que as fatias.
