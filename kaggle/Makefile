PYTHON ?= python3.12
VENV := .venv
VENV_PY := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
KAGGLE := KAGGLE_API_TOKEN=$$(cat .kaggle/access_token) $(VENV)/bin/kaggle
FRAMEWORK_REPO := https://github.com/arcprize/ARC-AGI-3-Agents.git
FRAMEWORK_DIR := vendor/ARC-AGI-3-Agents
GAME ?=
STEPS ?= 200

.PHONY: help setup test build-agent play-local verify-local list-games notebook submit status clean _check-kaggle

help:
	@echo "ARC3 Kaggle integration"
	@echo "  make setup        create venv, install deps, clone/slim official framework"
	@echo "  make test         run all offline integration contracts"
	@echo "  make build-agent  compile modular source to agent/my_agent.py"
	@echo "  make play-local   run generated agent on all games (or GAME=ls20)"
	@echo "  make verify-local run 50-step smoke test on ls20 + vc33"
	@echo "  make list-games   list locally available ARC3 games"
	@echo "  make notebook     build the self-contained CPU/offline Kaggle notebook"
	@echo "  make submit       push notebooks/ to Kaggle (requires local token + username)"
	@echo "  make status       show latest Kaggle kernel status"

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install "arc-agi>=0.9.9" "kaggle>=2.2" python-dotenv pandas pyarrow
	@if [ ! -d "$(FRAMEWORK_DIR)/.git" ]; then \
		mkdir -p vendor && git clone --depth 1 $(FRAMEWORK_REPO) $(FRAMEWORK_DIR); \
	else \
		git -C $(FRAMEWORK_DIR) pull --ff-only; \
	fi
	$(VENV_PY) scripts/slim_framework.py
	@echo "Setup complete. Next: make verify-local"

# Tests intentionally use stdlib only; the generated agent imports ARC framework
# modules only when executed by the official framework/Kaggle runtime.
test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

build-agent:
	$(PYTHON) scripts/build_agent.py

play-local: build-agent
	$(VENV_PY) scripts/play_local.py $(if $(GAME),--game $(GAME)) --max-steps $(STEPS)

verify-local: build-agent
	$(VENV_PY) scripts/play_local.py --game ls20,vc33 --max-steps 50

list-games:
	$(VENV_PY) scripts/play_local.py --list

notebook: build-agent
	$(PYTHON) scripts/build_notebook.py

_check-kaggle:
	@if [ ! -s .kaggle/access_token ]; then \
		echo "ERROR: .kaggle/access_token is missing or empty"; \
		exit 1; \
	fi
	@if grep -q REPLACE_WITH_YOUR_USERNAME notebooks/kernel-metadata.json; then \
		echo "ERROR: replace REPLACE_WITH_YOUR_USERNAME in notebooks/kernel-metadata.json"; \
		exit 1; \
	fi

submit: notebook _check-kaggle
	$(KAGGLE) kernels push -p notebooks/
	@echo "Pushed. Track with: make status"

status: _check-kaggle
	@KERNEL_ID=$$($(PYTHON) -c "import json; print(json.load(open('notebooks/kernel-metadata.json'))['id'])"); \
	$(KAGGLE) kernels status $$KERNEL_ID

clean:
	rm -rf $(VENV) vendor environment_files recordings agent/my_agent.py notebooks/submission.ipynb reference logs.log __pycache__ tests/__pycache__ src/metalogic_arc3/__pycache__
