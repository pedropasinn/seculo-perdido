# One Piece — Wiki de Evidências

Este repositório é um **sistema de raciocínio baseado em evidências** sobre o mistério
central de One Piece. Não é um blog de teorias. A diferença está nas regras abaixo.

## Regra zero — nada sai da sua memória

Você (Claude) tem conhecimento prévio de One Piece. **Esse conhecimento não é fonte.**
Toda afirmação factual sobre a obra precisa apontar para um átomo de evidência que
existe em `data/evidencias/`. Se você "lembra" de uma cena mas não existe átomo para
ela, o caminho é criar o átomo a partir de uma fonte real — nunca afirmar direto.

Alucinar um painel que não existe é o único erro fatal deste projeto.

## Fontes permitidas

- One Piece Wiki (Fandom) — licença CC BY-SA, resumos e transcrições
- SBS traduzidas e databooks (Vivre Card, Blue Deep, etc.)
- Entrevistas do Oda publicadas
- Anotações de leitura próprias do usuário, feitas a partir de cópias legais
  (Manga Plus / Viz / volumes comprados)

**Proibido:** ingerir scans ou scanlations. Além do problema legal, traduções piratas
são a maior fonte de teoria morta do fandom.

## A tradução é a superfície de ataque mais barata

Três dos erros já corrigidos neste repositório vieram de a paráfrase em inglês ter
uma palavra que o japonês não tem. Antes de dar peso alto a um átomo, pergunte se a
afirmação sobrevive à troca do tradutor.

Casos já documentados, que valem como regra de leitura:

- **笑う cobre rir e sorrir com o mesmo verbo.** "Roger sorriu", "Oden riu",
  "a tripulação gargalhou" podem ser o mesmo lexema no original. Não construa
  distinção entre sorrir e gargalhar sem checar o raw.
- **A obra não diz que o relato de Laugh Tale era engraçado**, diz que causou riso.
  "Hilário" era interpolação da wiki (ver `EV-0972-01`).
- **"Funny tale" era escolha de tradutor**: a última linha de *Binks' Sake* é
  笑い話, os mesmos caracteres de *Laugh Tale* (ver `EV-0488-01`).
- **"Great Kingdom" pode não ser nome próprio** — 巨大な王国 é adjetivo comum
  ("um reino imenso"). Pendência aberta em `EV-0395-03`.

Quando a afirmação depender da escolha do tradutor, `confiabilidade:
traducao_disputada` e peso ≤ 0.4. O validador avisa acima disso.

## As duas entidades

**Átomo de evidência** (`data/evidencias/EV-*.md`) — uma afirmação verificável,
com fonte e nível de confiabilidade. Não interpreta.

**Hipótese** (`data/hipoteses/H-*.md`) — uma proposição sobre o que é o One Piece
(ou sobre uma peça do mistério), ligada a átomos que a apoiam e a contradizem,
com **previsões falseáveis**.

Uma hipótese sem previsão falseável não entra no repositório. É a única barreira
contra o problema clássico do fandom: teorias infinitamente elásticas que nunca
podem estar erradas.

## Os quatro papéis

Rode cada um como sub-agente separado, num contexto limpo. Os prompts estão em
`agents/`. A separação é deliberada: o Red Team **não pode ver** os argumentos a
favor antes de tentar destruir a hipótese.

1. `agents/extrator.md` — fonte → átomos. Não teoriza.
2. `agents/vinculador.md` — átomos novos → links de apoio/contradição.
3. `agents/redteam.md` — hipótese → tentativa hostil de refutação.
4. `agents/curador.md` — recalcula status, escreve o markdown final.

## Dois tetos, não um

`score.py` limita a força de cada capítulo (`TETO_POR_FONTE`) **e** a de cada arco
(`TETO_POR_ARCO`). O segundo foi acrescentado em 2026-08-11, depois que
`tools/sensibilidade.py recencia` mostrou a hipótese líder tirando 69% do apoio de
um arco só: o teto por capítulo não vê quinze capítulos publicados juntos
empurrando na mesma direção.

O efeito não é cosmético — ele trocou o primeiro colocado. Se você discordar da
correlação por arco, mexa em `ARCOS` e no teto, não nos pesos dos elos.

## Camada narrativa é a terceira deflação

`confiabilidade` responde "a fonte de fato diz isto". `tipo` responde "que camada
da obra é essa". Eram coisas diferentes e só a primeira pesava.

Os sete átomos `tipo: capa` do repositório vêm todos da mesma história de capa
(*Enel's Great Space Operations*) e estão marcados `canonico` — corretamente, os
murais realmente dizem o que dizem. Só que `PESO_CONF` dava 1.0 a `canonico` e
nada olhava `tipo`, então um mural lido numa página de título valia, log-odds por
log-odds, o mesmo que o discurso de Clover. Medido em 11/08/2026: esses sete
átomos sozinhos somavam +3.7 log-odds, levando um prior neutro de 0.50 a 0.977.
O posterior 0.98 de H-16 **era a história de capa, e mais nada**.

`PESO_TIPO` deflaciona capa a 0.4 — o mesmo teto de `traducao_disputada`, e pela
mesma razão estrutural: a afirmação não sobrevive à troca da camada. Com isso e
com as contra-evidências que o ataque trouxe, H-16 caiu de 0.98 para 0.28.

Na mesma rodada, `arco()` foi corrigida. Ela concatenava os dígitos da fonte:
"historia de capa caps 470-472" virava 470472, fora de qualquer faixa de `ARCOS`,
e ganhava um balde de arco só dele com teto próprio. O átomo que escapava era o
mais carregado de H-16. Um bug de parser com efeito de tese — passe `arco()` por
um caso de teste antes de confiar em qualquer teto.

## A independência dos elos é falsa de dois jeitos

`score.py` trata cada elo como fator de Bayes independente. Isso falha por duas
vias, e por muito tempo só uma estava tratada:

- **correlação de fonte** — átomos do mesmo capítulo ou arco andam juntos. Freada
  por `TETO_POR_FONTE` e `TETO_POR_ARCO`.
- **correlação de átomo** — o *mesmo* átomo alimenta hipóteses concorrentes.
  Medida por `tools/independencia.py`, e **é maior que a primeira**.

Em 11/08/2026 a medição mostrou que a líder tirava **71% do apoio de átomos
compartilhados com rivais**, enquanto H-14 tirava 0%. Ordenando só por evidência
exclusiva, a líder caía do 1º para o 6º lugar. Onze átomos apoiam pares de
hipóteses que se *declaram concorrentes* — evidência que não discrimina, contada
como positiva dos dois lados.

Isso não invalida o ranking, mas muda o que ele significa: uma hipótese com base
emprestada sobe junto com as rivais em vez de vencer delas. Rode
`python3 tools/independencia.py` antes de afirmar que alguma lidera.

## Portão de fundamentação

Antes de qualquer commit: `make check`.

`tools/validate.py` é determinístico, sem LLM. Ele rejeita:
- referência a `EV-` ou `H-` que não existe
- citação cujo texto não bate com o átomo citado (similaridade abaixo do limiar)
- hipótese viva sem previsão falseável
- campos de enum inválidos

Se o validador reclamar, **conserte o dado, não o validador**.

## Escopo inicial

Não tente cobrir 1190 capítulos. O recorte de partida é: Século Perdido, Joy Boy,
Laugh Tale, Imu, Poneglyphs, D. Cerca de 300 átomos. Só escale depois que o ciclo
completo rodar limpo nesse recorte.

## Ciclo semanal (capítulo novo)

```
make extract  CAP=1191   # extrator gera átomos novos
make link                # vinculador conecta aos existentes
make redteam             # red team ataca as hipóteses vivas afetadas
make curate              # curador atualiza status e prioris
make check && make site  # valida e regenera o site
git commit               # o histórico vira o registro da teoria evoluindo
```

O git é parte do design: o valor do projeto não é a teoria final, é **o rastro** de
uma hipótese subindo e caindo ao longo dos capítulos.
