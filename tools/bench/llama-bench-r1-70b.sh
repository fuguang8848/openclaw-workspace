#!/bin/bash
export ROCM_PATH=/opt/rocm-7.2.4
export HIP_PATH=/opt/rocm-7.2.4
export LD_LIBRARY_PATH="$HOME/bin/llama.cpp-b9442:$ROCM_PATH/lib:$ROCM_PATH/lib/llvm/lib"
export HSA_OVERRIDE_GFX_VERSION=11.5.1
export PATH="$HOME/bin/llama.cpp-b9442:$PATH"
LOG=/home/fuguang/.openclaw/workspace/bench-deepseek-r1-70b.log
exec >> "$LOG" 2>&1
echo ""
echo "=========================================="
echo "llama-bench DeepSeek R1 70B Q4"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "5 configs: -ngl 99,99,99,80,60 -ub 8,16,32,8,8"
echo "=========================================="
~/bin/llama.cpp-b9442/llama-bench \
  -m "$HOME/.cache/ollama/models/deepseek-r1-70b-q4.gguf" \
  -ngl 99,99,99,80,60 \
  -ub 8,16,32,8,8 \
  -p 256 -n 256 \
  -t 16 \
  -r 1 \
  -o md \
  --progress 2>&1
echo "=========================================="
echo "DONE at $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
