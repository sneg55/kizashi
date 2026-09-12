#!/usr/bin/env bash
set -euo pipefail

: "${KIZASHI_BUCKET:?KIZASHI_BUCKET is required}"

kizashi pull-state --bucket "$KIZASHI_BUCKET"
kizashi fetch
kizashi run --portfolio data/demo/portfolio-nj-086.csv --name "Mercer County NJ small nonprofits"
kizashi publish --bucket "$KIZASHI_BUCKET"
