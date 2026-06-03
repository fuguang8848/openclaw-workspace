#!/bin/bash
# DeepSeek R1 70B Q4 GPU benchmark — 5 个 -ngl/-tb 配置
# 5月31日任务被 abort 后续跑

set -u
export ROCM_PATH=/opt/rocm-7.2.4
export HIP_PATH=/opt/rocm-7.2.4
export LD_LIBRARY_PATH=$HOME/bin/llama.cpp-b9442:$ROCM_PATH/lib:$ROCM_PATH/lib/llvm/lib:$LD_LIBRARY_PATH
export HSA_OVERRIDE_GFX_VERSION=11.5.1
export PATH=$HOME/bin/llama.cpp-b9442:$PATH

LOG=/home/fuguang/.openclaw/workspace/bench-deepseek-r1-70b.log
MODEL=~/.cache/ollama/models/deepseek-r1-70b-q4.gguf
PROMPT="Write a Python quicksort."

exec > >(tee -a "$LOG") 2>&1

echo "=========================================="
echo "DeepSeek R1 70B Q4 GPU Benchmark"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Model: $MODEL ($(du -h "$MODEL" | cut -f1))"
echo "Binary: $(/usr/bin/which llama-cli)"
echo "ROCm: $ROCM_PATH"
echo "Gfx override: $HSA_OVERRIDE_GFX_VERSION"
echo "Log: $LOG"
echo "=========================================="
echo ""

run_test() {
  local ngl=$1; local tb=$2; local idx=$3
  echo ""
  echo "========== TEST $idx: -ngl $ngl -tb $tb =========="
  echo "Start: $(date '+%H:%M:%S')"
  local start=$(date +%s)
  echo "$PROMPT" | llama-cli \
    -m "$MODEL" -c 256 -ngl "$ngl" -tb "$tb" -t 16 --log-disable
  local rc=$?
  local end=$(date +%s)
  echo "End:   $(date '+%H:%M:%S')"
  echo "Elapsed: $((end-start))s, exit=$rc"
  echo "----"
}

# 5 个配置按 5月31日原任务顺序
run_test 99 8  1
run_test 99 16 2
run_test 99 32 3
run_test 80 8  4
run_test 60 8  5

echo ""
echo "=========================================="
echo "ALL DONE at $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
