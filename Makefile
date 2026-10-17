.PHONY: setup check build switch apps apps-check brewfile fmt update
.DEFAULT_GOAL := check

NIX := nix --extra-experimental-features 'nix-command flakes'
LOCK := --no-update-lock-file
CONFIG := .\#darwinConfigurations.macbook

setup: switch

check:
	/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py'
	$(NIX) flake check --no-build $(LOCK)

build:
	$(NIX) build $(LOCK) $(CONFIG).system

switch: build
	@test "$$($(NIX) eval --raw $(LOCK) $(CONFIG).config.system.primaryUser)" = "$$(id -un)" || \
		{ echo 'Set machine.username in flake.nix to your macOS login (id -un) before switching.' >&2; exit 1; }
	sudo /usr/bin/python3 scripts/switch.py --apply

brewfile:
	$(NIX) eval --raw $(LOCK) $(CONFIG).config.homebrew.brewfile > Brewfile.tmp
	mv Brewfile.tmp Brewfile

apps: brewfile
	HOMEBREW_NO_AUTO_UPDATE=1 brew bundle install --no-upgrade --file=Brewfile

apps-check: brewfile
	HOMEBREW_NO_AUTO_UPDATE=1 brew bundle check --no-upgrade --verbose --file=Brewfile

fmt:
	rg --files -g '*.nix' -0 | xargs -0 $(NIX) fmt $(LOCK) --

update:
	$(NIX) flake update
