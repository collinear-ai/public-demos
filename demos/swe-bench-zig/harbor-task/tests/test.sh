#!/bin/bash
# Harbor verification script for ZLS Code Actions Enhancement
# Runs structural checks and optional Zig tests, outputs reward to /logs/verifier/
set -uo pipefail

REPO="/testbed"
LOGS="/logs/verifier"

mkdir -p "$LOGS"

echo "=== ZLS Code Actions Enhancement: Verification ===" | tee "$LOGS/verifier.log"

# Run the Python structural + functional verification script
python3 /tests/verify.py "$REPO" > "$LOGS/report.json" 2> >(tee -a "$LOGS/verifier.log" >&2)
VERIFY_EXIT=$?

# Extract scores from the JSON report
if [ -f "$LOGS/report.json" ]; then
    STRUCTURAL=$(python3 -c "import json; print(json.load(open('$LOGS/report.json'))['structural_score'])" 2>/dev/null || echo "0")
    FUNCTIONAL=$(python3 -c "import json; print(json.load(open('$LOGS/report.json'))['functional_score'])" 2>/dev/null || echo "0")
    OVERALL=$(python3 -c "import json; print(json.load(open('$LOGS/report.json'))['overall_score'])" 2>/dev/null || echo "0")
    PASSED=$(python3 -c "import json; print(json.load(open('$LOGS/report.json'))['passed_checks'])" 2>/dev/null || echo "0")
    TOTAL=$(python3 -c "import json; print(json.load(open('$LOGS/report.json'))['total_checks'])" 2>/dev/null || echo "0")
else
    STRUCTURAL="0"
    FUNCTIONAL="0"
    OVERALL="0"
    PASSED="0"
    TOTAL="0"
fi

echo "" | tee -a "$LOGS/verifier.log"
echo "Structural: $STRUCTURAL" | tee -a "$LOGS/verifier.log"
echo "Functional: $FUNCTIONAL" | tee -a "$LOGS/verifier.log"
echo "Overall:    $OVERALL" | tee -a "$LOGS/verifier.log"
echo "Passed:     $PASSED / $TOTAL" | tee -a "$LOGS/verifier.log"

# Write reward.json with detailed metrics
cat > "$LOGS/reward.json" <<EOF
{
    "overall_score": $OVERALL,
    "structural_score": $STRUCTURAL,
    "functional_score": $FUNCTIONAL,
    "checks_passed": $PASSED,
    "checks_total": $TOTAL
}
EOF

# Also write reward.txt (overall score as single number)
echo "$OVERALL" > "$LOGS/reward.txt"

echo "" | tee -a "$LOGS/verifier.log"
echo "Reward written to $LOGS/reward.txt ($OVERALL)" | tee -a "$LOGS/verifier.log"
echo "Detailed report at $LOGS/report.json" | tee -a "$LOGS/verifier.log"

exit 0
