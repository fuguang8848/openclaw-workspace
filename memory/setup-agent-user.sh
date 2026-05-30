#!/bin/bash
# 创建专用 AI 助手用户 agent

# 1. 创建用户
sudo useradd -m -s /bin/bash agent

# 2. 赋予 sudo 免密权限
echo "agent ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/agent
sudo chmod 440 /etc/sudoers.d/agent

# 3. 把当前用户加到 agent 组以便文件共享
sudo usermod -aG $(whoami) agent

echo "✅ agent 用户创建完成！"
echo "验证方法: groups agent"
