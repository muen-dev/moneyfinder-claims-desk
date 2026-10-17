.PHONY: setup run test fixtures smoke prism
setup:
	uv venv .venv
	uv pip install --python .venv/bin/python -r requirements.txt
run:
	.venv/bin/python run.py
test:
	.venv/bin/python -m pytest -q
fixtures:
	.venv/bin/python scripts/make_fixtures.py
prism:
	.venv/bin/python scripts/prism_smoke.py
