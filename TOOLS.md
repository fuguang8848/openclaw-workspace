# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)

## WinApps + KVM

### 启动 Windows 桌面
```bash
export DISPLAY=:0 && ~/.local/bin/winapps windows
```
或直接 xfreerdp:
```bash
DISPLAY=:0 xfreerdp 192.168.122.60 /u:rdpuser /p:Rdp123456 /cert:ignore /sec:tls +clipboard +dynamic-resolution
```

### VM 管理
```bash
sudo -u agent virsh --connect qemu:///system start WinApps   # 启动
sudo -u agent virsh --connect qemu:///system shutdown WinApps # 关机
sudo -u agent virsh --connect qemu:///system destroy WinApps # 强制断电
```

### DISPLAY 环境变量
- 当前 Linux 桌面: GNOME Wayland, DISPLAY=:0
- 已写入 ~/.bashrc: `export DISPLAY=:0`
