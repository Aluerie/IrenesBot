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

Commands:
	setup               Setup the repository - recommended to use right after cloning
	sync                Install dependencies
	update              Update dependencies
	run                 Run the bot
	lint                Run the linter
	format              Format the code
	format-check        Check code formatting
	tests               Run the tests
	pages               Locally run the github pages website
	ty                  Run ty (beta testing ty typechecker)
	basedpyright        Run basedpyright
	commit              Lazy git commit and push+
	com                 This creates and pushes commits to IreBot repository
	echo                Testing stuff with make, why don't we test it with echo
	sphinx				Sphinx
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
	uv sync
	prek install

.PHONY: sync
.SILENT: sync
sync:  # Install dependencies
	uv sync

.PHONY: update
.SILENT: update
update:  # Update dependencies
	uv lock --upgrade
	uv sync
	prek autoupdate

.PHONY: run
.SILENT: run
run:  # Run the bot in the subset-mode
	uv run src/main.py --subset-mode --local-adapter

.PHONY: lint
.SILENT: lint
lint:  # Run the linter
	uv run ruff check $(sources)
	uv run ruff format --check $(sources)

.PHONY: format
.SILENT: format
format:  # Format the code
	uv run ruff check $(sources) --fix
	uv run ruff format $(sources)

.PHONY: tests
.SILENT: tests
tests:  # Run the tests
	uv run pytest

.PHONY: pages
.SILENT: pages
pages:  # Run the pages
	cd docs && bundle exec jekyll serve

.PHONY: ty
.SILENT: ty
ty:  # Run ty (beta testing ty typechecker)
	uv run ty check .

.PHONY: basedpyright
.SILENT: basedpyright
basedpyright:  # Run basedpyright
	uv run basedpyright $(sources)

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

.PHONY: echo
.SILENT: echo
echo:  # Testing stuff with make, why don't we test it with echo
	[console]::OutputEncoding
	echo $(SHELL)
	echo "$(m)"
	echo $(LANG)
	@Write-Output $(m)


.PHONY: sphinx
.SILENT: sphinx
sphinx:  # sphinx
	-cd docs && rm -Recurse _build
	cd docs && uv run sphinx-build . _build
# It's recommended to clear `_build` folder before running the docs
# to avoid random unobvious issues, like left sidebar not properly updating for "old" pages.


.PHONY: scp
.SILENT: scp
scp:  # Commands to copy required files into the VPS
	scp -i "${SSH_PRIVATE_KEY}" .env ${SSH_USERNAME}@${SSH_HOST}:~/IreBot/.env