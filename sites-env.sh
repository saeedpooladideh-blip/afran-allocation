#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${project_root}"

export SITES_ENV_READY=1
export SITES_PROJECT_ROOT="${project_root}"

runtime_root="${SITES_RUNTIME_ROOT:-${project_root}/.sites-runtime}"

mkdir -p \
  "${runtime_root}/home" \
  "${runtime_root}/npm-cache" \
  "${runtime_root}/xdg-config" \
  "${runtime_root}/tmp" \
  "${runtime_root}/wrangler/logs"

export HOME="${runtime_root}/home"
export XDG_CONFIG_HOME="${runtime_root}/xdg-config"
export TMPDIR="${runtime_root}/tmp"
export WRANGLER_LOG_PATH="${runtime_root}/wrangler/logs"
export MINIFLARE_REGISTRY_PATH="${runtime_root}/wrangler/registry"

export npm_config_cache="${runtime_root}/npm-cache"
export npm_config_audit=false
export npm_config_fund=false
export npm_config_update_notifier=false

unset npm_config_proxy || true
unset npm_config_http_proxy || true
unset npm_config_https_proxy || true
unset NPM_CONFIG_PROXY || true
unset NPM_CONFIG_HTTP_PROXY || true
unset NPM_CONFIG_HTTPS_PROXY || true

if [[ $# -eq 0 ]]; then
  echo "usage: sites-env.sh -- command [args...]" >&2
  exit 64
fi

if [[ "${1:-}" == "--" ]]; then
  shift
fi

if [[ $# -eq 0 ]]; then
  echo "No command provided." >&2
  exit 64
fi

# If the requested command is a local shell script, run it explicitly
# through bash so Docker/Git executable permissions do not block the build.
if [[ "$1" == "build-verified.sh" || "$1" == "./build-verified.sh" ]]; then
  shift
  exec bash "${project_root}/build-verified.sh" "$@"
fi

exec "$@"
