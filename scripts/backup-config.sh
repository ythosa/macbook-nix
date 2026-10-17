#!/bin/sh

if [ "$#" -ne 1 ]; then
  echo 'Usage: backup-config.sh PATH' >&2
  exit 2
fi

backup=$(mktemp -d "${1}.before-home-manager.XXXXXX") || exit 1
if ! mv -- "$1" "$backup/"; then
  rmdir -- "$backup"
  exit 1
fi
printf 'Backed up %s in %s\n' "$1" "$backup" >&2
