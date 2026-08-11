.PHONY: check score buscar site novo-atomo nova-hipotese

check:
	@python3 tools/validate.py --raiz .

score:
	@python3 tools/score.py $(H)

buscar:
	@python3 tools/buscar.py "$(Q)"

site:
	@python3 tools/render.py

# ciclo de capitulo novo — rode cada etapa como sub-agente no Claude Code
extract:
	@echo "Claude Code: use agents/extrator.md com a fonte do cap $(CAP)"
link:
	@echo "Claude Code: use agents/vinculador.md sobre os atomos novos"
redteam:
	@echo "Claude Code: use agents/redteam.md em cada hipotese viva afetada"
curate:
	@echo "Claude Code: use agents/curador.md"
