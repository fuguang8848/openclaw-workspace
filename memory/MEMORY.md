# MEMORY.md - Long-term Memory

## 机器信息

### ASUS ProArt PX13 HN7306EA
- **CPU**: AMD Ryzen AI MAX+ 395 (Strix Point)
- **GPU**: AMD Radeon 890M 集成显卡（无独显）
- **内存**: 128GB
- **硬盘**: 953GB NVMe
- **内核**: 6.17.0-29-generic (Ubuntu 24.04 HWE)
- **用户**: fuguang
- **桌面**: GNOME Wayland（tty2）
- **WiFi**: 10.13.125.220

### 音频问题（未解决）
- AMD ACP70 声卡 + NAU88L21 codec
- 只有麦克风能用（DMIC capture）
- 蓝牙耳机可以出声（但有线耳机和扬声器不行）
- 解决方案：暂时用蓝牙耳机，或买 USB 外置声卡

---

## ✅ WinApps + KVM 完整配置（已完成）

### Windows 11 VM 信息
- **VM 名称**: WinApps
- **IP**: 192.168.122.60（NAT 模式，virbr0 网桥）
- **内存**: 16GB（动态）
- **磁盘**: 200GB SATA (win11.qcow2)
- **网卡**: e1000e（NAT，libvirt 默认网络）
- **机器名**: fulantelin
- **RDP 用户**: rdpuser / Rdp123456（本地账户，管理员）
- **微软账户**: 1966152237@qq.com / Ty521566（VM 本地登录用）

### 宿主机访问 VM 的方式

**方式一：xfreerdp 直接连接（推荐）**
```bash
DISPLAY=:0 xfreerdp 192.168.122.60 /u:rdpuser /p:Rdp123456 /cert:ignore /sec:tls +clipboard +dynamic-resolution
```

**方式二：WinApps**
```bash
export DISPLAY=:0 && ~/.local/bin/winapps windows
```
前提：`~/.bashrc` 里已加 `export DISPLAY=:0`

### WinApps 详情
- **源码位置**: ~/winapps-main/
- **配置**: ~/.config/winapps/winapps.conf
- **RDP 账户**: rdpuser / Rdp123456
- **RDP 端口**: 3389
- **WinApps 命令**:
  - `~/.local/bin/winapps windows` — 启动完整 Windows 桌面
  - `~/.local/bin/winapps killrdp` — 关闭 RDP 会话
  - `~/.local/bin/winapps cleanrdp` — 清理孤立进程

### VM 运维命令
```bash
# 启动 VM
sudo -u agent virsh --connect qemu:///system start WinApps

# 关闭 VM
sudo -u agent virsh --connect qemu:///system shutdown WinApps

# 强制关闭 VM
sudo -u agent virsh --connect qemu:///system destroy WinApps

# 查看 VM 状态
sudo -u agent virsh --connect qemu:///system list --all

# 查看 VM IP（需等 VM 启动后）
sudo -u agent virsh --connect qemu:///system domifaddr WinApps
```

### 网络打通细节（重要）
- **问题**: 宿主机无法通过 NAT 访问 VM（ping 不通，TCP 3389 超时）
- **原因**: libvirt 的 iptables LIBVIRT_FWI 链默认阻止入站新连接
- **解决**: 在 LIBVIRT_FWI 链最前面插入放行规则
```bash
# 临时加规则（重启 libvirtd 后需重新添加）
sudo -u agent sudo iptables -I LIBVIRT_FWI 1 -o virbr0 -d 192.168.122.60 -p tcp --dport 3389 -j ACCEPT
sudo -u agent sudo iptables -I LIBVIRT_FWI 1 -o virbr0 -d 192.168.122.60 -p tcp -j ACCEPT
```
- **RDP 连接问题**: Windows 默认开启 NLA（网络级别认证），需要 `/sec:tls` 参数绕过
- **多用户冲突**: VM 本地已登录时 RDP 会提示"另一个用户已登录"，需点"是"强制断开

### xfreerdp 连接 Windows 桌面（FreeRDP 3.x 语法）
- **命令**: `DISPLAY=:0 xfreerdp 192.168.122.60 /u:rdpuser /p:Rdp123456 /cert:ignore /sec:tls +clipboard +dynamic-resolution`
- **参数说明**:
  - `/cert:ignore` — 忽略自签名证书警告
  - `/sec:tls` — 使用 TLS 安全层（绕过 NLA）
  - `+clipboard` — 启用剪贴板互通
  - `+dynamic-resolution` — 窗口缩放时动态调整分辨率
  - **不要用 `/f`** — 全屏模式会隐藏 Linux 侧边栏
- **注意**: FreeRDP 3.x 语法和旧版 1.0 不兼容，winapps 生成的是 1.0 语法

### WinApps 配置
```
~/.config/winapps/winapps.conf 内容：
- RDP_USER="rdpuser"
- RDP_PASS="Rdp123456"
- VM_NAME="WinApps"
- RDP_IP=""
- RDP_PORT="3389"
- RDP_SCALE=100
- RDP_FLAGS="/cert:ignore /sec:tls"
- DEBUG="true"
```

---

## 已安装软件

| 软件 | 状态 | 备注 |
|------|------|------|
| 微信 for Linux | ✅ 已装 | x86_64 deb |
| QQ for Linux | ✅ 已装 | QQ_3.2.28_amd64.deb |
| freerdp3-x11 | ✅ 已装 | xfreerdp 3.x |
| WinApps | ✅ 已配置 | 源码在 ~/winapps-main/ |

---

## 配置备忘

### sudo 免密
- **agent 用户**: 密码 20051101，NOPASSWD
- **fuguang 使用 agent**: `sudo -u agent <命令>`
- **fuguang 免密配置**: `/etc/sudoers.d/fuguang-agent-nopass`
  - `fuguang ALL=(agent) NOPASSWD: *`

### GitHub 加速
- 代理前缀: `https://ghproxy.net/`
- 示例: `git clone https://ghproxy.net/https://github.com/user/repo.git`

### Watt Toolkit
- 路径: `/home/fuguang/WattToolkit/`
- 启动: `bash /home/fuguang/WattToolkit/Steam++.sh`
- 代理端口: 26561
- 需要手动启动才能加速 GitHub

### KVM 虚拟机存储池
- 名称: vmpool
- 路径: /home/fuguang/vmpool
- 卷: win11.qcow2 (200G)
- Windows ISO: /var/lib/libvirt/images/win11.iso

---

## 内核

| 版本 | 状态 |
|------|------|
| 6.17.0-29-generic | ✅ 当前在用（HWE） |
| 6.8.0-xx-generic | ⚠️ touchpad 坏了 |
| 6.19.x | ⚠️ NVMe 不认 |

---

## 待解决

- [ ] iptables 规则持久化（重启 libvirtd 后规则会丢）
- [ ] VM 开机自启（Linux 登录后自动启动 VM）
- [ ] 音频问题（AMD ACP70 + NAU88L21 无解，暂时用蓝牙耳机）
- [ ] SPICE clipboard 配置（暂无）

---

## 大模型部署计划

- 目标：本地部署 70B 量化模型（Qwen 2.5 / Llama 3）
- 显存需求：约 40GB（70B Q4 量化）
- 内存分配：约 68GB 留给大模型

---

## agent交响乐家族升级计划

- 目标：使agent技能家族（四个技能+交响乐工作流）成为强大易用的技能
- 要求：不断要结合我们自己使用openclaw的经验来对其进行升级。要不断调试使用使其能够真正落地应用。代码质量要好，解决方案要优雅。每次升级前都要联网到github上查看本地版本是否是最新版的，以免重复造轮子，如果不是最新版的，就静默更新。
- 原则：开发原则应该是适配性，可移植性，易用性，功能（完整，正确）性，可靠（成熟，容错，易恢复）性，效率（时间特性，资源利用率），可维护性（易分析，易修改，稳定），安全性（保密性，完整性，抗依赖性），兼容性（兼任各种操作系统和agent框架），合规性
- 应该支持多平台，多框架，兼容性好
- 应该能够不断升级，做好可移植性和说明
- 本地升级之后应该主动提交至主分支
- 确保所有技能都在fuguang8848github账号的星标内。
- 优先级较高，如果空闲应该第一个关注此事
- push之后要自动尝试合并到上游或者提交PR（重要，必须，时刻自动检查）
- 应该单独设立清晰的工作文件夹给这个项目，确保记忆不错乱，这是一个长期项目，要注重好文档质量
- agent交响乐技能家族的思路是分支的技能组合起来就是一个工作流（agentsymphony），而分开又独立能作为强大的该领域的技能来使用，所以要做好这一点。
- 四个技能在github上的仓库：https://github.com/YintaTriss/AgentSearch；https://github.com/YintaTriss/AgentTeam；https://github.com/YintaTriss/Agent-superthinking；https://github.com/YintaTriss/AgentSymphony；https://github.com/YintaTriss/AgentMemory

