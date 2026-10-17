.PHONY: setup check build switch apps apps-check plugins brewfile fmt update
.DEFAULT_GOAL := check

NIX := nix --extra-experimental-features 'nix-command flakes'
NIX_FLAGS := --impure --no-update-lock-file
CONFIG := .\#darwinConfigurations.macbook
export MACBOOK_NIX_USERNAME := $(shell /usr/bin/id -un)

setup:
	/bin/bash setup.sh

check:
	/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py'
	$(NIX) flake check --no-build $(NIX_FLAGS)

build:
	$(NIX) build $(NIX_FLAGS) $(CONFIG).system

switch: build
	@test "$$($(NIX) eval --raw $(NIX_FLAGS) $(CONFIG).config.system.primaryUser)" = "$$(id -un)" || \
		{ echo 'Run make switch as your macOS user, without sudo or username overrides.' >&2; exit 1; }
	sudo /usr/bin/python3 scripts/switch.py --apply

brewfile:
	$(NIX) eval --raw $(NIX_FLAGS) $(CONFIG).config.homebrew.brewfile > Brewfile.tmp
	mv Brewfile.tmp Brewfile

apps: brewfile
	HOMEBREW_NO_AUTO_UPDATE=1 brew bundle install --no-upgrade --file=Brewfile

apps-check: brewfile
	HOMEBREW_NO_AUTO_UPDATE=1 brew bundle check --no-upgrade --verbose --file=Brewfile

plugins:
	/bin/bash scripts/plugins.sh

fmt:
	rg --files -g '*.nix' -0 | xargs -0 $(NIX) fmt $(NIX_FLAGS) --

update:
	$(NIX) flake update
