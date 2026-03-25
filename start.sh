#!/usr/bin/env bash

if [[ -f "$HOME/.profile" ]]; then
    . "$HOME/.profile"
fi

set -euo pipefail

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

logfmt='%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

cd "$(dirname "$0")"
poetry sync
poetry run gunicorn                    \
       -b 0.0.0.0:7818                 \
       --enable-stdio-inheritance      \
       --access-logfile -              \
       --access-logformat "${logfmt}"  \
       app:app
