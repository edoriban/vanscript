# VanScript — development commands
# Requires: conda activate vanscript

CONDA_RUN = conda run -n vanscript
PYTHON    = $(CONDA_RUN) python
PIP       = $(CONDA_RUN) pip

.PHONY: run build install clean check

## Run the app
run:
	$(PYTHON) main.py

## Build macOS/Windows executable with PyInstaller
build:
	$(CONDA_RUN) pyinstaller build.spec --noconfirm

## Install/update dependencies
install:
	$(PIP) install -r requirements.txt

## Remove build artifacts
clean:
	rm -rf build dist __pycache__ ui/__pycache__ *.pyc

## Verify imports resolve correctly
check:
	$(PYTHON) -c "from app import TranscriptDownloaderApp; print('All imports OK')"
