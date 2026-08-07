#!/usr/bin/env python3
"""孤儿 MCP 进程 watchdog —— 清理泄漏的 water_db_mcp.py。

DeerFlow session_pool 在 agent 异常/超时退出时不清理 MCP 子进程，导致
water_db_mcp.py 累积（实测一次累积 256 个 / 7.7GB），压垮新 run 引起间歇超时
（轮次0卡死）。根因见上游 #3797 "synchronize session pool singleton lifecycle"，
待 2.1.0 正式版升级后可移除本脚本。

判定：正常 case 跑完 MCP 子进程即退出；存活超过 --max-age 秒（默认 600s）或
父进程已变成 init(1)（被 reparent 的孤儿）的，视为泄漏，清理掉。

用法：
  python3 cleanup_mcp_orphans.py                 # 清理一次（默认 TERM，阈值600s）
  python3 cleanup_mcp_orphans.py --dry-run       # 只报告
  python3 cleanup_mcp_orphans.py --max-age 900 --signal KILL
  # 挂 cron（每10分钟）：
  # */10 * * * * cd /opt/git/water-resources-skills/skills && python3 scripts/cleanup_mcp_orphans.py >> reports/mcp_watchdog.log 2>&1
"""
import argparse
import os
import signal
import subprocess
from datetime import datetime

PATTERN = "water_db_mcp.py"  # MCP server 进程特征


def parse_etime(etime_str):
    """把 ps 的 etime（如 '1-13:16:34' 或 '15:30' 或 '90'）解析成秒。"""
    days = 0
    s = etime_str
    if "-" in s:
        d, s = s.split("-", 1)
        days = int(d)
    secs = 0
    for p in s.split(":"):
        secs = secs * 60 + int(p)
    return days * 86400 + secs


def find_orphans(max_age):
    """返回 [(pid, ppid, age_sec, etime_str)]，条件：python 进程 + 匹配 PATTERN
    +（运行超过 max_age 或 父进程为 init(1)）。"""
    out = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,etime=,args="], capture_output=True, text=True
    ).stdout
    orphans = []
    for line in out.splitlines():
        if PATTERN not in line or "python" not in line:
            continue  # 只认 python 启动的，排除 grep/自身
        cols = line.split(None, 3)
        if len(cols) < 4:
            continue
        pid, ppid, etime = int(cols[0]), int(cols[1]), cols[2]
        age = parse_etime(etime)
        if age >= max_age or ppid == 1:
            orphans.append((pid, ppid, age, etime))
    return orphans


def main():
    ap = argparse.ArgumentParser(description="清理泄漏的 water_db_mcp.py 孤儿进程")
    ap.add_argument("--max-age", type=int, default=1800, help="运行超过此秒数视为孤儿（默认1800=30min，安全余量防误杀长case）")
    ap.add_argument("--dry-run", action="store_true", help="只报告不杀")
    ap.add_argument("--signal", default="TERM", choices=["TERM", "KILL"], help="信号（默认TERM）")
    args = ap.parse_args()

    orphans = find_orphans(args.max_age)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not orphans:
        print(f"[{ts}] 无孤儿进程（阈值 {args.max_age}s，当前 MCP 进程数 "
              f"{len([l for l in subprocess.run(['ps','-eo','args='],capture_output=True,text=True).stdout.splitlines() if PATTERN in l and 'python' in l])}）")
        return

    sig = signal.SIGTERM if args.signal == "TERM" else signal.SIGKILL
    print(f"[{ts}] 发现 {len(orphans)} 个孤儿进程（阈值 {args.max_age}s）：")
    for pid, ppid, age, etime in orphans:
        action = "DRY-RUN" if args.dry_run else f"KILL-{args.signal}"
        print(f"  PID {pid} (ppid={ppid}, 存活 {etime}={age}s) → {action}")
        if not args.dry_run:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass


if __name__ == "__main__":
    main()
