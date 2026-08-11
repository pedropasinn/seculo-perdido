.PHONY: check score buscar site web coletar novo-atomo nova-hipotese

check:
	@python3 tools/validate.py --raiz .

score:
	@python3 tools/score.py $(H)

buscar:
	@python3 tools/buscar.py "$(Q)"

site:
	@python3 tools/render.py

web:
	@python3 tools/site.py

coletar:
	@python3 tools/coletar.py $(P)

# o ranking e do dado ou dos pesos? rode antes de reportar qualquer ordem
sensibilidade:
	@python3 tools/sensibilidade.py perturbar
	@echo
	@python3 tools/sensibilidade.py remover
	@echo
	@python3 tools/sensibilidade.py recencia

# ciclo de capitulo novo — rode cada etapa como sub-agente no Claude Code
extract:
	@python3 tools/coletar.py "Chapter $(CAP)"
	@echo "Claude Code: use agents/extrator.md sobre .cache/wiki/Chapter_$(CAP).txt"
link:
	@echo "Claude Code: use agents/vinculador.md sobre os atomos novos"
redteam:
	@echo "Claude Code: use agents/redteam.md em cada hipotese viva afetada"
curate:
	@echo "Claude Code: use agents/curador.md"
