#!/bin/sh
set -eu

: "${VITE_API_URL:?VITE_API_URL must contain the public Backend URL}"
: "${VITE_BENCHMARK_BM:=2.99}"

exec node server.js
