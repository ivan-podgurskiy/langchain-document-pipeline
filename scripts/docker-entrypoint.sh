#!/bin/sh
set -e
# Fix ownership of data directory for appuser (app runs as non-root)
mkdir -p /app/data/documents
chown -R appuser:appuser /app/data
exec gosu appuser "$@"
