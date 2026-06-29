# 可观测性指引(Observability)

> 让水利 skill 的每次执行"被看见、被回放"。**本文件是指引(runtime/配置层),不是 skill 指令本身**——skill 层做不到 runtime 监控。skill 层的轻量溯源见 `provenance_footer.md`。

## 三层可观测(从轻到重)

### 1. Provenance footer ✅(已在 skill 层落地)
每次查询结果带溯源 footer(见 `provenance_footer.md`)。零成本,立即生效。给**用户/下游**看的轻量溯源。

### 2. Trajectory 持久化(Hermes 已有能力,需开启)
`agent/trajectory.py` 的 `save_trajectory()` 已能把 ShareGPT 对话写到 JSONL(成功→`trajectory_samples.jsonl`,失败→`failed_trajectories.jsonl`)。给**开发者**看的完整回放。
- **现状**:由 `batch_runner.py` 在批处理时调用;单次交互默认不保存。
- **开启方式**(对接任务 #1):在 `scripts/evaluate_skills.py` 的每个 eval run 里调用 `save_trajectory` 落盘,并附 `task_id` / `skill_version` / `score` / `tool_calls` / `tool_results`(大结果走 `tools/tool_result_storage.py`,不要塞回上下文)。
- **价值**:结果不对时,完整回放"模型看到什么 → 调了什么工具 → SQL → 返回什么",定位失败发生在理解/检索/工具/验证哪一环(对应 APMPlus"回答不对时回放完整上下文"场景)。

### 3. 全链路 APMPlus(可选,需火山账号)
火山引擎 APMPlus Hermes Plugin:Trace/Metrics/Logs/Alerts 一键接入,覆盖"谁慢(模型 vs SQL 耗时拆分)、token 涨、工具失败、轨迹回放、日志-链路关联"。
- 接入:`curl -fsSL "https://apmplus-hermes-plugin.tos-cn-beijing.volces.com/install.sh" | bash`(输 region/appkey/service-name)
- 隐私:正文采集可设 `trace_content: false`,敏感字段(token/password/secret/authorization/api_key)默认脱敏。
- **取舍**:有火山账号且需生产级监控 → 接入;否则先做 #1 的 trajectory 持久化(自建轻量,够用)。

## 与其他任务的关系
- **#1 Eval Harness** 会实现第 2 层(trajectory 落盘 + 结构化事件)。
- **provenance footer**(第 1 层)已随本任务落地。
- 第 3 层(APMPlus)是运维决策,不在 skill 范围。
