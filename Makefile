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

## Start the zellij dev workspace
.PHONY: workspace
workspace:
	@echo "Starting dev workspace..."
	@if zellij list-sessions 2>/dev/null | grep -q "youtube-transcripts"; then \
		zellij attach youtube-transcripts; \
	else \
		zellij --session youtube-transcripts --new-session-with-layout dev; \
	fi

## Kill the zellij dev workspace
.PHONY: kill
kill:
	@echo "Killing workspace..."
	@zellij kill-session youtube-transcripts 2>/dev/null || echo "No active session 'youtube-transcripts' to kill."

## Build the Python app without Whisper (YouTube transcripts only)
.PHONY: build-lite
build-lite:
	LITE=1 $(CONDA_RUN) pyinstaller build.spec --noconfirm

## Build the Rust port (release)
.PHONY: rs-build
rs-build:
	cd vanscript-rs && cargo build --release
	@ls -lh vanscript-rs/target/release/vanscript-rs

## Cross-compile the Rust port for Windows (needs cargo-xwin)
.PHONY: rs-build-win
rs-build-win:
	cd vanscript-rs && cargo xwin build --release --target x86_64-pc-windows-msvc

## Lint and test the Rust port
.PHONY: rs-test
rs-test:
	cd vanscript-rs && cargo clippy --all-targets -- -D warnings && cargo test
