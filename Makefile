include .env

# Otherwise `make scp` doesn't work, idk.
ifeq ($(OS),Windows_NT)
    SHELL := pwsh.exe
else
    SHELL := pwsh
endif
.SHELLFLAGS := -NoProfile -Command 

# Sources to run type-checkers / linters against
sources = src tests examples
# Default commit message with `make commit`
m = fix(lazy): Various fixes & updates

default: help

define HELP_BODY
Usage:
	make <command>

# Commands list
	
Environment and Setup:
	setup               Setup the repository - recommended to use right after cloning
	sync                Install dependencies
	update              Update dependencies

Running the bot:
	run                 Run the bot
	scopes				Run the bot in the scopes-only mode

Linters, Type-checkers, formatters and tests:
	lint                Run the Ruff's linter
	ruff 			    Run the Ruff's linter (same as "make lint", just an alias)
	format              Format the code
	ty                  Run typechecker (ty)
	check               Run both typechecker and linter
	tests               Run the tests with pytest

Documentation:
	pages              [Deprecated] Locally run the github pages website
	docs				Build the docs with Sphinx
	
Github and VPS:
	commit              Lazy git commit and push+
	com                 This creates and pushes commits to IreBot repository
	scp					Copy required files into the VPS

Other:
	echo                Testing stuff

endef

.PHONY: help
.SILENT: help
# TODO: Look into ways to automatically gather output for this command.
# The struggle is that Windows Terminal doesn't have any normal working `grep`; 
# and vice-versa windows grep-like tools won't work for linux
help:  # Help
	$(info $(HELP_BODY))


.PHONY: setup
.SILENT: setup
setup:  # Setup the repository - recommended to use right after cloning
	git submodule update --init --recursive
	make sync
	prek install


.PHONY: sync
.SILENT: sync
sync:  # Install dependencies
	uv sync --group docs --all-extras


.PHONY: update
.SILENT: update
update:  # Update dependencies
	uv lock --upgrade
	make sync
	prek autoupdate


.PHONY: run
.SILENT: run
run:  # Run the bot in the subset-mode
	uv run --no-dev src/main.py --subset-mode --adapter=local --test-account


.PHONY: scopes
.SILENT: scopes
scopes:  # Run the bot in the scopes-only mode
	uv run --no-dev src/main.py --subset-mode --adapter=local --test-account --scopes-only


.PHONY: lint
.SILENT: lint
lint:  # Run the Ruff's linter
	uv run ruff check $(sources)
	uv run ruff format --check $(sources)


.PHONY: ruff
.SILENT: ruff
ruff:  # Run the Ruff's linter (same as "make lint", just an alias)
	uv run ruff check $(sources)
	uv run ruff format --check $(sources)


.PHONY: format
.SILENT: format
format:  # Format the code with Ruff
	uv run ruff check $(sources) --fix
	uv run ruff format $(sources)


.PHONY: ty
.SILENT: ty
ty:  # Run typechecker (ty)
	uv run ty check .


.PHONY: check
.SILENT: check
check:  # Run both typechecker and linter
	make lint
	make ty


.PHONY: tests
.SILENT: tests
tests:  # Run the tests with pytest
	uv run pytest


.PHONY: pages
.SILENT: pages
pages:  # [Deprecated] Locally run the github pages website
	cd docs && bundle exec jekyll serve


.PHONY: docs
.SILENT: docs
docs:  # Build the docs with Sphinx
	-cd docs && rm -Recurse _build
	cd docs && uv run sphinx-build . _build
# It's recommended to clear `_build` folder before running the docs
# to avoid random unobvious issues, like left sidebar not properly updating for "old" pages.


.PHONY: commit
.SILENT: commit
# Lazy git commit commands, use make commit m="Fix this and that" for custom commit messages.
# This creates and pushes commits to both IreBot and Shared-Bot-Utilities repositories.
# Notice "-" Usage 
# https://stackoverflow.com/a/2670143/19217368) 
# This kinda makes this command unsafe against me being dumb.
commit: 
	-cd src/shared && git add .
	-cd src/shared && git commit -a -m "$(m)"
	-cd src/shared && git push
	-git add .
	-git commit -a -m "$(m)"
	-git push


.PHONY: com
.SILENT: com
# This creates and pushes commits to IreBot repository
com:  
	git add .
	git commit -a -m "$(m)"
	git push


.PHONY: scp
.SILENT: scp
scp:  # Copy required files into the VPS
	scp -i "${SSH_PRIVATE_KEY}" .env ${SSH_USERNAME}@${SSH_HOST}:~/IrenesBot/.env


.PHONY: echo
.SILENT: echo
echo:  # Testing stuff
	[console]::OutputEncoding
	echo $(SHELL)
	echo "$(m)"
	echo $(LANG)
	@Write-Output $(m)
	@echo -e "\e[1;34mBuilding $<\e[0m"