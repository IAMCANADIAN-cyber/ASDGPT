.PHONY: install test replay clean all

install:
	pip install -r requirements.txt

test:
	python -m pytest

replay:
	python tools/replay_harness.py

clean:
	python tools/cleanup.py

all: install test replay
