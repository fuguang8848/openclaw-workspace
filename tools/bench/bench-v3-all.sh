#!/bin/bash
# DeepSeek R1 70B Q4 GPU benchmark — 5 个 -ngl/-tb 配置
export ROCM_PATH=/opt/rocm-7.2.4
export HIP_PATH=/opt/rocm-7.2.4
export LD_LIBRARY_PATH="$HOME/bin/llama.cpp-b9442:$ROCM_PATH/lib:$ROCM_PATH/lib/llvm/lib"
export HSA_OVERRIDE_GFX_VERSION=11.5.1
export PATH="$HOME/bin/llama.cpp-b9442:$PATH"

LOG=/home/fuguang/.openclaw/workspace/bench-deepseek-r1-70b.log
MODEL="$HOME/.cache/ollama/models/deepseek-r1-70b-q4.gguf"
PROMPT="Write a Python quicksort."

exec >> "$LOG" 2>&1

echo ""
echo "=========================================="
echo "DeepSeek R1 70B Q4 GPU Benchmark v3"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Model: $MODEL ($(du -h "$MODEL" | cut -f1))"
echo "Binary: $(which llama-cli)"
echo "=========================================="

run_test() {
  local ngl=$1; local tb=$2; local idx=$3
  echo ""
  echo "========== TEST $idx: -ngl $ngl -tb $tb =========="
  local start=$(date +%s)
  echo "Start: $(date '+%H:%M:%S')"
  timeout 300 llama-cli \
    -m "$MODEL" \
    -p "$PROMPT" \
    -c 256 -n 256 -ngl "$ngl" -tb "$tb" -t 16 \
    --single-turn 2>&1
  local rc=$?
  local end=$(date +%s)
  echo "End:   $(date '+%H:%M:%S')"
  echo "Elapsed: $((end-start))s, exit=$rc"
  echo "----"
}

run_test 99 8  1
run_test 99 16 2
run_test 99 32 3
run_test 80 8  4
run_test 60 8  5

echo ""
echo "=========================================="
echo "ALL DONE at $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
