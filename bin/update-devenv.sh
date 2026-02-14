#!/usr/bin/env bash
# Update a project by merging the devenv templates
set -euo pipefail

DEVENV_SRC=../devenv

# Prepare
mkdir -pv bin cfg

# Update
bin/copy-new-files.sh "$DEVENV_SRC"/bin bin
bin/copy-new-files.sh "$DEVENV_SRC"/cfg cfg
bin/merge-dotfiles.sh "$DEVENV_SRC"/templates .
bin/merge_package_json.py "$DEVENV_SRC"/templates/package.json package.json -o package.json
bin/merge_toml.py "$DEVENV_SRC"/templates/pyproject-template.toml pyproject.toml -o pyproject.toml
bin/merge_yaml.py "$DEVENV_SRC"/templates/.readthedocs.yaml .readthedocs.yaml -o .readthedocs.yaml
bin/merge_yaml.py "$DEVENV_SRC"/templates/mkdocs.yml mkdocs.yml -o mkdocs.yml

# Fix Merged
npx eslint_d --cache --fix package.json pyproject.toml .readthedocs.yaml mkdocs.yml
npx prettier --write package.json pyproject.toml .readthedocs.yaml mkdocs.yml

# Report
git status --short package.json pyproject.toml .readthedocs.yaml mkdocs.yml
