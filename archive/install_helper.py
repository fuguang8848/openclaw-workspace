#!/usr/bin/env python3
import pexpect
import sys

tasks = [
    ('WeChat', ['sudo', 'apt', 'install', '-y', '/home/fuguang/下载/WeChatLinux_x86_64.deb']),
    ('freerdp3-x11', ['sudo', 'apt', 'install', '-y', 'freerdp3-x11']),
]

for name, cmd in tasks:
    print(f'Installing {name}...')
    child = pexpect.spawn(cmd[0], cmd[1:], encoding='utf-8', timeout=120)
    try:
        child.expect(['password', '[sudo]', '密码', 'Password'], timeout=10)
        child.sendline('20051101')
        child.expect(pexpect.EOF, timeout=120)
        print(f'{name}: OK')
    except Exception as e:
        print(f'{name}: FAILED - {e}')
        try:
            child.kill()
        except:
            pass

print('All done')
