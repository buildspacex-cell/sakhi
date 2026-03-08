#!/usr/bin/env bash
# Codebase context audit for Sakhi
# Usage: ./scripts/context-audit.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v rg >/dev/null 2>&1; then
  echo "error: rg is required for context-audit.sh" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required for context-audit.sh" >&2
  exit 1
fi

count_cmd() {
  local cmd="$1"
  eval "$cmd" | wc -l | tr -d ' '
}

echo "Sakhi Context Audit"
echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%SZ")"
echo

echo "[Codebase]"
echo "tracked_files=$(count_cmd 'rg --files')"
echo "python_files=$(count_cmd 'rg --files -g "*.py"')"
echo "ts_files=$(count_cmd 'rg --files -g "*.ts" -g "*.tsx"')"
echo "api_route_modules=$(count_cmd 'find sakhi/apps/api/routes -name "*.py" ! -name "__init__.py" ! -name "*.bak"')"
echo "api_service_modules=$(count_cmd 'find sakhi/apps/api/services -name "*.py" ! -name "__init__.py"')"
echo "worker_modules=$(count_cmd 'find sakhi/apps/worker -name "*.py" ! -name "__init__.py"')"
echo "worker_task_modules=$(count_cmd 'find sakhi/apps/worker/tasks -name "*.py" ! -name "__init__.py" ! -name "_stubs.py"')"
echo "engine_modules=$(count_cmd 'find sakhi/apps/engine -name "*.py" ! -name "__init__.py"')"
echo "web_pages=$(count_cmd 'find apps/web/app -name "page.tsx"')"
echo "web_api_routes=$(count_cmd 'find apps/web/app/api -name "route.ts"')"
echo "mobile_screens=$(count_cmd 'find apps/mobile/app -name "*.tsx"')"
echo "kala_source_modules=$(count_cmd 'find kala -name "*.py" ! -path "kala/tests/*"')"
echo "kala_test_files=$(count_cmd 'find kala/tests -name "*.py"')"
echo "kala_test_functions=$(rg '\bdef test_' kala/tests -g '*.py' | wc -l | tr -d ' ')"
echo

echo "[API Wiring]"
echo "main_include_router_calls=$(rg 'include_router\(' sakhi/apps/api/main.py | wc -l | tr -d ' ')"
echo "duplicate_import_focus_path=$(rg -n 'from sakhi.apps.api.routes.focus_path import router as focus_path_router' sakhi/apps/api/main.py | wc -l | tr -d ' ')"
echo "duplicate_import_micro_momentum=$(rg -n 'from sakhi.apps.api.routes.micro_momentum import router as micro_momentum_router' sakhi/apps/api/main.py | wc -l | tr -d ' ')"
echo "duplicate_include_person_router=$(rg -n 'app.include_router\(person_router\.router\)' sakhi/apps/api/main.py | wc -l | tr -d ' ')"
echo "duplicate_include_micro_momentum=$(rg -n 'app.include_router\(micro_momentum_router\)' sakhi/apps/api/main.py | wc -l | tr -d ' ')"
echo

echo "[Test Harness]"
quick_test_files="$(
  awk '
    BEGIN { in_target=0 }
    /^quick-test:/ { in_target=1; next }
    in_target && /^[^ \t].*:/ { in_target=0 }
    in_target { print }
  ' Makefile | rg -o 'sakhi/tests[^ \\]+' || true
)"
if [ -z "$quick_test_files" ]; then
  echo "quick_test_target=unknown (no explicit test files found in Makefile quick-test target)"
else
  missing_quick_targets=0
  total_quick_targets=0
  while IFS= read -r test_path; do
    [ -z "$test_path" ] && continue
    total_quick_targets=$((total_quick_targets + 1))
    if [ ! -f "$test_path" ]; then
      missing_quick_targets=$((missing_quick_targets + 1))
    fi
  done <<< "$quick_test_files"
  if [ "$missing_quick_targets" -eq 0 ]; then
    echo "quick_test_target=present (${total_quick_targets} files)"
  else
    echo "quick_test_target=missing (${missing_quick_targets}/${total_quick_targets} files not found)"
  fi
fi
echo "sakhi_tests_prefix=$(count_cmd 'find sakhi/tests -name "test_*.py"')"
echo "sakhi_tests_name_contains=$(count_cmd 'find sakhi/tests -name "*test*.py"')"
echo "integration_tests=$(count_cmd 'find sakhi/tests/integration -name "test_*.py"')"
echo "unit_tests=$(count_cmd 'find sakhi/tests/unit -name "test_*.py"')"
echo

echo "[Observability]"
if rg -q 'PrometheusMiddleware' sakhi/apps/api/main.py && rg -q 'app.add_route\("/metrics", handle_metrics\)' sakhi/apps/api/main.py; then
  echo "metrics_endpoint=present"
else
  echo "metrics_endpoint=missing"
fi
if rg -q 'async def _build_health_payload' sakhi/apps/api/main.py && rg -q '@app.get\("/health"\)' sakhi/apps/api/main.py; then
  echo "health_readiness=present"
else
  echo "health_readiness=missing"
fi
if rg -q 'INSERT INTO request_logs' sakhi/apps/api/middleware/telemetry.py; then
  echo "request_telemetry=present"
else
  echo "request_telemetry=missing"
fi
if [ -f sakhi/apps/api/core/monitoring.py ] \
  && rg -q 'setup_monitoring' sakhi/apps/api/main.py \
  && rg -q 'report_exception_to_sink' sakhi/apps/api/main.py \
  && rg -q 'setup_monitoring' sakhi/apps/worker/main.py \
  && rg -q 'report_exception_sync' sakhi/apps/worker/main.py; then
  echo "external_alerting_sink=present"
else
  echo "external_alerting_sink=missing"
fi
echo

echo "[Simulation Data Health]"
echo -e "file\tdays\tentries\tcoherence\talignment\tidentity\tthemes\tpatterns\tworker_failures"
for f in apps/web/public/simulation/{vidhya,diya,bigd,anxious_achiever,hormonal_harmony,stuck_creative}.json; do
  if [ ! -f "$f" ]; then
    continue
  fi
  metrics="$(jq -r '[.total_days,.total_entries,([.snapshots[]?|select(.brain_states.coherence_state!=null)]|length),([.snapshots[]?|select(.brain_states.alignment_state!=null)]|length),([.snapshots[]?|select(.brain_states.identity_momentum_state!=null)]|length),([.snapshots[]?|select((.themes|type=="array") and (.themes|length>0))]|length),([.snapshots[]?|select((.crystallized_patterns|type=="array") and (.crystallized_patterns|length>0))]|length)]|@tsv' "$f")"
  failures="$(jq -r '.snapshots[-1].worker_results // {} | to_entries | map(select(.value.ok != true) | (.key + ":" + (.value.error // ""))) | join(" | ")' "$f")"
  if [ -z "$failures" ]; then
    failures="none"
  fi
  echo -e "$(basename "$f")\t${metrics}\t${failures}"
done
