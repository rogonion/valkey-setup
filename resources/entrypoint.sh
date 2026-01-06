#!/bin/sh
set -e

if [ "$#" -eq 0 ]; then
    set -- valkey-server /usr/share/valkey/config/valkey.conf
fi

# Prepend 'valkey-server' if the first argument is a flag (starts with -)
if [ "${1#-}" != "$1" ]; then
    set -- valkey-server "$@"
fi

exec "$@"