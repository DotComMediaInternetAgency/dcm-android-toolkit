#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
exec /bin/bash "$(dirname -- "$0")/Launch DCM Android Toolkit.command" --force-update
