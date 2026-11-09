.PHONY: run test

run:
	python3 src/main.py $(ARGS)

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
