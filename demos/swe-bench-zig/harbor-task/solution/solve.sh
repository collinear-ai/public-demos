#!/bin/bash
# Oracle solution: applies the gold patch from the reference implementation
set -euo pipefail

cd /testbed

# Apply the full reference patch
git apply /solution/full_patch.diff

echo "Gold patch applied successfully"
