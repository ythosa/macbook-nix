#!/usr/bin/env python3
"""Back up bashrc changed by the upstream Nix installer, then switch.

Without --apply, only print the plan. Arbitrary /etc changes are left for
nix-darwin's own checks; only the exact installer block with a matching
backup-before-nix file is recognized here.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys


NIX_INIT = b"""\n# Nix
if [ -e '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh' ]; then
  . '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh'
fi
# End Nix
"""


def matching_backup(source, backup):
    return (not backup.is_symlink() and backup.is_file()
            and source.read_bytes() == backup.read_bytes())


def backup_plan(etc=Path('/etc')):
    plan = []
    # Only the standard bashrc installer change is handled here.
    for name in ('bashrc',):
        source = etc / name
        original = etc / (name + '.backup-before-nix')
        if (source.is_symlink() or not source.is_file()
                or original.is_symlink() or not original.is_file()):
            continue
        content = source.read_bytes()
        if not content.startswith(NIX_INIT):
            continue
        if content[len(NIX_INIT):].lstrip(b'\n') != original.read_bytes().lstrip(b'\n'):
            continue
        backup = etc / (name + '.before-nix-darwin')
        if (backup.exists() or backup.is_symlink()) and not matching_backup(source, backup):
            raise FileExistsError('Refusing to overwrite backup: ' + str(backup))
        plan.append((source, backup))
    return plan


def switch(plan, command):
    moved = []
    try:
        for source, backup in plan:
            # link() creates an exclusive backup and preserves permissions/ownership.
            # It fails if a backup appeared since the plan was checked.
            try:
                os.link(source, backup)
            except FileExistsError:
                if not matching_backup(source, backup):
                    raise
            source.unlink()
            moved.append((source, backup))
        return subprocess.run(command, check=False).returncode
    finally:
        # If activation stops before replacing a shell file, keep the old shell
        # usable. Leave any links already created by nix-darwin in place.
        for source, backup in moved:
            if not source.exists() and not source.is_symlink():
                os.link(backup, source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    rebuild = repo / 'result/sw/bin/darwin-rebuild'
    if not rebuild.is_file():
        parser.error('Build the configuration first: make build')
    if args.apply and (sys.platform != 'darwin' or os.geteuid() != 0):
        parser.error('--apply must run on macOS as root, via make switch')
    try:
        plan = backup_plan()
        for source, backup in plan:
            print('Back up {} -> {}'.format(source, backup), flush=True)
        command = [str(rebuild), 'switch', '--flake', str(repo) + '#macbook',
                   '--no-update-lock-file']
        if not args.apply:
            print('Then run: ' + ' '.join(command))
            return 0
        return switch(plan, command)
    except OSError as error:
        print('switch: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
