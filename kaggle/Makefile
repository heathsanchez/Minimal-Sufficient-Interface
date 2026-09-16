PYTHON ?= python3.12
VENV := .venv
VENV_PY := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
KAGGLE := KAGGLE_API_TOKEN=$$(cat .kaggle/access_token) $(VENV)/bin/kaggle

.PHONY: help setup test build-agent notebook submit status clean _check-kaggle

help:
	@echo "ARC3 Kaggle integration"
	@echo "  make setup        create Python 3.12 venv + install Kaggle/local deps"
	@echo "  make test         run all offline integration contracts"
	@echo "  make build-agent  compile modular source to agent/my_agent.py"
	@echo "  make notebook     build the self-contained CPU/offline Kaggle notebook"
	@echo "  make submit       push notebooks/ to Kaggle (requires local token + username)"
	@echo "  make status       show latest Kaggle kernel status"

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install "arc-agi>=0.9.9" "kaggle>=2.2" python-dotenv pandas pyarrow

# Tests intentionally use stdlib only; the generated agent imports ARC framework
# modules only when executed by the official framework/Kaggle runtime.
test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

build-agent:
	$(PYTHON) scripts/build_agent.py

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

status: _check-kaggle
	@KERNEL_ID=$$($(PYTHON) -c "import json; print(json.load(open('notebooks/kernel-metadata.json'))['id'])"); \
	$(KAGGLE) kernels status $$KERNEL_ID

clean:
	rm -rf $(VENV) agent/my_agent.py notebooks/submission.ipynb __pycache__ tests/__pycache__ src/metalogic_arc3/__pycache__
