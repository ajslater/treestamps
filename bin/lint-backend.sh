#!/bin/bash
# Lint checks
set -euxo pipefail

####################
###### Python ######
####################
poetry run ruff .
poetry run black --check .
poetry run pyright
poetry run vulture .
if [ "$(uname)" = "Darwin" ]; then
    # Radon is only of interest to development
    poetry run radon mi --min B .
    poetry run radon cc --min C .
fi
# poetry run djlint templates --profile=django --lint

############################################
##### Javascript, JSON, Markdown, YAML #####
############################################
npm run lint
npm run remark-check

################################
###### Docker, Shell, Etc ######
################################
if [ "$(uname)" = "Darwin" ]; then
    # Hadolint & shfmt are difficult to install on linux
    # shellcheck disable=2035
    hadolint *Dockerfile
    shellharden ./**/*.sh
    # subdirs aren't copied into docker builder
    # .env files aren't copied into docker
    shellcheck --external-sources ./**/*.sh
    circleci config check .circleci/config.yml
fi
./bin/roman.sh -i .gitignore .
poetry run codespell .
