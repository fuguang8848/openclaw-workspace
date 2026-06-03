#!/bin/bash
# 4 个 config 串行 -ngl/-ub benchmark（避免 -r 1 无效的 50 个测试问题）
export ROCM_PATH=/opt/rocm-7.2.4
export HIP_PATH=/opt/rocm-7.2.4
export LD_LIBRARY_PATH="/home/fuguang/bin/llama.cpp-b9442:$ROCM_PATH/lib:$ROCM_PATH/lib/llvm/lib"
export HSA_OVERRIDE_GFX_VERSION=11.5.1
export PATH="/home/fuguang/bin/llama.cpp-b9442:$PATH"
LOG=/home/fuguang/.openclaw/workspace/bench-deepseek-r1-70b.log
exec >> "$LOG" 2>&1

run_one() {
  local ngl=$1; local ub=$2; local label=$3
  echo ""
  echo "========== $label: -ngl $ngl -ub $ub =========="
  echo "Start: $(date '+%H:%M:%S')"
  timeout 300 llama-bench \
    -m "/home/fuguang/.cache/ollama/models/deepseek-r1-70b-q4.gguf" \
    -ngl "$ngl" -ub "$ub" \
    -p 64 -n 64 -t 16 \
    -o md 2>&1
  echo "End:   $(date '+%H:%M:%S')"
  echo "----"
}

run_one 99 16 "TEST 2"
run_one 99 32 "TEST 3"
run_one 80 8  "TEST 4"
run_one 60 8  "TEST 5"

echo ""
echo "ALL DONE $(date '+%H:%M:%S')"
