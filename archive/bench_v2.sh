#!/bin/bash
# no set -u: sandbox env may not have LD_LIBRARY_PATH
export ROCM_PATH=/opt/rocm-7.2.4
export HIP_PATH=/opt/rocm-7.2.4
export LD_LIBRARY_PATH="$HOME/bin/llama.cpp-b9442:$ROCM_PATH/lib:$ROCM_PATH/lib/llvm/lib"
export HSA_OVERRIDE_GFX_VERSION=11.5.1
export PATH="$HOME/bin/llama.cpp-b9442:$PATH"

LOG=/home/fuguang/.openclaw/workspace/bench-deepseek-r1-70b.log
: > "$LOG"
exec >> "$LOG" 2>&1
echo "=== TEST 1 (-p mode, with verbose) start $(date '+%H:%M:%S') ==="
echo "ROCM_PATH=$ROCM_PATH"
echo "HIP_PATH=$HIP_PATH"
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "PATH=$PATH"
which llama-cli
echo "---"
llama-cli \
  -m "$HOME/.cache/ollama/models/deepseek-r1-70b-q4.gguf" \
  -p "Write a Python quicksort." \
  -c 256 -n 256 -ngl 99 -tb 8 -t 16 2>&1
echo "=== TEST 1 end $(date '+%H:%M:%S') exit=$? ==="
