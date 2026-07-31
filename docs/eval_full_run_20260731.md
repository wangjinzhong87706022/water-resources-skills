# 全量评估任务（98 题）后台运行说明

启动时间：2026-07-31 18:44:15
输出目录：`skills/reports/eval_full_20260731_184415/`
运行日志：`skills/reports/eval_full_20260731_184415/run.log`
进程：PID `3832085`，独立会话（`setsid`，无控制终端），断开 shell 后继续运行。

## 执行命令（后台、断连不被杀）

```bash
cd /opt/git/water-resources-skills
OUT="skills/reports/eval_full_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"
setsid nohup python3 skills/scripts/evaluate_deerflow_gateway.py \
  --all-skills --range 1-98 --timeout 900 --output "$OUT" \
  > "$OUT/run.log" 2>&1 < /dev/null &
disown
echo "OUT=$OUT"
```

- `setsid`：脱离当前会话，断开 SSH/shell 后进程不被杀。
- `nohup ... < /dev/null`：忽略挂断信号并断开标准输入。
- `--range 1-98`：全部 98 题；`--timeout 900`：单题超时 900 秒。

## 查看命令

```bash
cd /opt/git/water-resources-skills

# 1. 是否仍在运行 + 已跑多久
pgrep -af evaluate_deerflow_gateway
ps -o pid,pgid,sid,tty,etime,cmd -p 3832085

# 2. 实时日志
tail -f skills/reports/eval_full_20260731_184415/run.log

# 3. 已产出的结果文件（按时间倒序）
ls -t skills/reports/eval_full_20260731_184415/

# 4. 读取汇总结果 JSON（跑完后）
ls -t skills/reports/eval_full_20260731_184415/gateway_eval_all_*.json | head -1
```

## 停止命令（如需中止）

```bash
kill 3832085                      # 优雅停止
# 或按进程组：
kill -TERM -3832085
```
