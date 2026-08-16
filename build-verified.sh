#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${script_dir}"

echo "Starting Afran frontend production build..."

if [[ ! -f "package.json" ]]; then
  echo "ERROR: package.json not found"
  exit 1
fi

if [[ ! -d "node_modules" ]]; then
  echo "ERROR: node_modules not found"
  exit 1
fi

if [[ ! -x "node_modules/.bin/vinext" ]]; then
  echo "ERROR: vinext executable not found"
  exit 1
fi

echo "Running vinext build..."

./node_modules/.bin/vinext build

echo "Frontend build completed successfully."
