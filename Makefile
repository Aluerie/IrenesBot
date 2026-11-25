# Recipes are PowerShell (`Write-Host`, `rm -Recurse`, `&&` chains), on every OS.
ifeq ($(OS),Windows_NT)
    SHELL := pwsh.exe
else
    SHELL := pwsh
endif
.SHELLFLAGS := -NoProfile -Command

# Removes `make[1]: Entering directory 'D:/CODE/IreBot' messages` https://stackoverflow.com/a/71371359/19217368
# Allowing for nested makes without annoyance of that message.
MAKEFLAGS += --no-print-directory

# Sources to run type-checkers / linters against
sources = src tests templates
# Default commit message for `make commit` and `make com`
m = 🔨 Various fixes and updates
# SSH destination of the VPS: a `Host` alias from ~/.ssh/config or user@host.
# Override it per command, e.g. make logs VPS=ubuntu@1.2.3.4, or with a VPS environment variable.
VPS ?= vps

default: help

.PHONY: help
.SILENT: help
# Prints every target that has a `# description` comment, under the `##@ Section` line above it.
# Make joins these lines into one PowerShell command; `\#` is a literal `#` (a bare one would start a make comment).
HELP_SCRIPT = \
	Write-Host 'Usage: make <command>'; \
	foreach ($$line in Get-Content '$(firstword $(MAKEFILE_LIST))') { \
		if ($$line -match '^\#\#@ (.+)') { \
			Write-Host ([Environment]::NewLine + $$Matches[1] + ':') -ForegroundColor Magenta \
		} elseif ($$line -match '^([\w-]+):[^=\#]*\#\s*(.+)') { \
			Write-Host ('    {0,-12}{1}' -f $$Matches[1], $$Matches[2]) \
		} \
	}

help:  # Show this help
	$(HELP_SCRIPT)


##@ Environment and Setup

.PHONY: setup
.SILENT: setup
setup:  # Set up the repository, recommended right after cloning
	git submodule update --init --recursive
	make sync
	uv run prek install


.PHONY: sync
.SILENT: sync
sync:  # Install dependencies
	uv sync --group docs --all-extras


.PHONY: update
.SILENT: update
update:  # Update dependencies and pre-commit hooks
	uv lock --upgrade
	make sync
	uv run prek autoupdate


##@ Running the bot

.PHONY: run
.SILENT: run
run:  # Run the bot in the subset-mode
	uv run src/main.py --subset-mode --adapter=local --test-account


.PHONY: ride
.SILENT: ride
ride:  # Run (ride) the bot with all components
	uv run src/main.py --adapter=local --test-account


.PHONY: scopes
.SILENT: scopes
scopes:  # Run the bot in the scopes-only mode
	uv run src/main.py --subset-mode --adapter=local --test-account --scopes-only


##@ Linters, type-checkers, formatters and tests

.PHONY: ruff
.SILENT: ruff
ruff:  # Run Ruff's linter and format check
	uv run ruff check $(sources)
	uv run ruff format --check $(sources)


.PHONY: lint
lint: ruff  # Same as "make ruff"


.PHONY: format
.SILENT: format
format:  # Format the code with Ruff
	uv run ruff check $(sources) --fix
	uv run ruff format $(sources)


.PHONY: ty
.SILENT: ty
ty:  # Run the type-checker (ty)
	uv run ty check .


.PHONY: check
.SILENT: check
check:  # Run both "make ruff" and "make ty"
	Write-Host 'Running "make ruff"' -ForegroundColor Magenta
	make ruff
	Write-Host 'Running "make ty"' -ForegroundColor Magenta
	make ty


.PHONY: tests
.SILENT: tests
tests:  # Run the tests with pytest
	uv run pytest


.PHONY: ci
.SILENT: ci
ci:  # Run what CI runs: "make ruff", "make ty" and "make tests"
	Write-Host 'Running "make ruff"' -ForegroundColor Magenta
	make ruff
	Write-Host 'Running "make ty"' -ForegroundColor Magenta
	make ty
	Write-Host 'Running "make tests"' -ForegroundColor Magenta
	make tests


##@ Documentation

.PHONY: docs
.SILENT: docs
# Clearing `_build` first avoids random unobvious issues, like the left sidebar not updating for "old" pages.
docs:  # Build the docs with Sphinx
	-cd docs && rm -Recurse _build
	cd docs && uv run sphinx-build . _build


.PHONY: docs-serve
.SILENT: docs-serve
# `--watch ../src` rebuilds on code changes too, since the docs pull command docstrings from it.
docs-serve:  # Serve the docs in the browser, rebuilding them on every change
	cd docs && uv run sphinx-autobuild . _build --watch ../src --port 0 --open-browser


##@ GitHub

.PHONY: commit
.SILENT: commit
# Lazy commit and push of both the "src/shared" submodule and IreBot, all with the same message.
# Only `git commit` may fail (it does when there's nothing to commit); any other failure stops here,
# so IreBot is never pushed pointing at a "src/shared" commit that isn't on GitHub.
commit:  # Commit and push both "src/shared" and IreBot, e.g. make commit m="💚 Fix CI"
	Write-Host 'Committing "src/shared" submodule' -ForegroundColor Magenta
	cd src/shared && git add .
	-cd src/shared && git commit -m "$(m)"
	cd src/shared && git push
	Write-Host 'Committing IrenesBot' -ForegroundColor Magenta
	git add .
	-git commit -m "$(m)"
	git push


.PHONY: com
.SILENT: com
com:  # Commit and push only IreBot
	git add .
	-git commit -m "$(m)"
	git push


##@ VPS

.PHONY: scp
.SILENT: scp
scp:  # Copy .env to the VPS
	scp .env $(VPS):~/IrenesBot/.env


.PHONY: logs
.SILENT: logs
logs:  # Follow the bot's log on the VPS live (Ctrl+C to stop)
	ssh -t $(VPS) sudo journalctl -u irebot -f


.PHONY: status
.SILENT: status
# `-`: systemctl exits non-zero when the bot isn't running, which isn't a make error here.
status:  # Show whether the bot is running on the VPS
	-ssh $(VPS) systemctl status irebot --no-pager


.PHONY: restart
.SILENT: restart
restart:  # Restart the bot on the VPS
	ssh $(VPS) sudo systemctl restart irebot
