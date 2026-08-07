# Eval 方案分析：hermes vs deer-flow

> **日期**：2026-07-28
> **触发**：hermes eval 失败（超时+空响应），探索 deer-flow 作为替代方案

---

## 1. 当前问题：hermes eval 失败

### 实测现象

```bash
$ timeout 120 hermes -z "古运河有哪些水位测站" -s water-situation 2>&1
[Exit code 124 - timeout]

$ python3 scripts/evaluate_skills.py --range 1-2
[1/2] Q1 总分=0.12 | SQL:No | 45.9s
[2/2] Q2 总分=0.12 | SQL:No | 16.0s
```

**关键问题**：
- ✅ hermes 命令执行完成（非崩溃）
- ❌ **返回空响应**（响应长度 0，无 SQL）
- ❌ **耗时异常**（45 秒、16 秒但无输出）

### 可能根因

| 假设 | 验证方法 | 状态 |
|------|---------|------|
| **skill 加载失败** | 检查 `~/.hermes/skills/water-resources/` 是否存在 | ✅ 目录存在 |
| **API 调用失败** | 查看 hermes debug log | ❌ 未测试 |
| **响应解析 bug** | 检查 eval 脚本的 `extract_sql_from_response()` | ⚠️ 需验证 |
| **权限/配置问题** | 检查 `~/.hermes/config.yaml` | ✅ 配置存在 |

### 下一步诊断（待执行）

```bash
# 1. 查看 hermes debug log
HERMES_DEBUG=1 timeout 120 hermes -z "test" -s water-situation 2>&1 | tee /tmp/hermes_debug.log

# 2. 检查 skill 文件完整性
ls -la ~/.hermes/skills/water-resources/water-situation/

# 3. 手动测试 hermes（加 verbose）
hermes -z "古运河有哪些水位测站" -s water-situation -v
```

---

## 2. DeerFlow 方案

### 2.1 DeerFlow 架构

```
┌─────────────────────────────────────────────┐
│  Nginx (Port 2026)                          │
│  /api/langgraph/* → Gateway (8001)          │
│  /api/* → Gateway (8001)                    │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  Gateway API (FastAPI, Port 8001)           │
│  - /api/langgraph/runs  (agent 执行)       │
│  - /api/langgraph/threads (会话管理)       │
│  - /api/skills/* (skill 管理)              │
│  - /api/models/* (模型管理)                │
└─────────────────────────────────────────────┘
```

### 2.2 关键发现

| 维度 | 详情 |
|------|------|
| **API 框架** | FastAPI（标准 REST） |
| **Agent 入口** | `/api/langgraph/runs`（POST，streaming） |
| **Skill 配置** | `config.yaml skills.path = /opt/git/water-resources-skills/skills` |
| **当前状态** | **服务未运行**（localhost:2026、8080 无响应） |
| **Python Client** | `deerflow` 包（backend/packages/deerflow） |

### 2.3 DeerFlow Eval 可行性

#### ✅ 优势

1. **标准 FastAPI**：可以直接 `curl` 或 `requests` 调用
2. **Python Client**：有官方 `deerflow` 包（类型安全、 streaming 支持）
3. **更接近生产**：eval 的是实际部署路径（而非 hermes CLI）
4. **更详细轨迹**：LangGraph 的 `thread_runs` 可获取完整 trajectory

#### ❌ 劣势

1. **需要启动服务**：`make dev`（需要 Docker + 4-8 vCPU + 8-16GB 内存）
2. **更复杂**：需要创建 thread、提交 run、等待 completion、解析 streaming 响应
3. **资源消耗**：比 hermes CLI 更重（需要完整 backend + LLM 调用）

#### 🔧 实现复杂度

| 步骤 | 工作量 | 说明 |
|------|--------|------|
| 启动 DeerFlow 服务 | 0.5 天 | `make dev` + 配置验证 |
| 编写 DeerFlow Eval Client | 2-3 天 | Python client 封装 + trajectory 解析 |
| 迁移现有 eval 逻辑 | 1 天 | 复用 `evaluate_skills.py` 的评分/报告逻辑 |
| 集成到 CI/CD | 0.5 天 | 可选，后续自动化 |

### 2.4 DeerFlow Eval 方案设计

```python
# scripts/evaluate_deerflow.py

from deerflow import DeerFlowClient, RunStatus
from evaluate_skills import TestCase, EvalResult, ErrorAttributor

class DeerFlowEvalHarness:
    """针对 DeerFlow 的 eval harness"""

    def __init__(self, base_url: str = "http://localhost:2026"):
        self.client = DeerFlowClient(base_url)

    async def run_case(self, case: TestCase) -> EvalResult:
        """执行单个测试用例"""
        # 1. 创建 thread（或复用）
        thread_id = await self.client.create_thread(
            metadata={"skill": case.skill, "question": case.question}
        )

        # 2. 提交 run（流式）
        run = await self.client.create_run(
            thread_id=thread_id,
            input={"messages": [{"role": "user", "content": case.question}]},
            stream=True,
        )

        # 3. 等待 completion + 收集 trajectory
        trajectory = []
        async for event in run:
            trajectory.append(event)
            if event.type == "run.completed":
                break

        # 4. 提取最终响应 + SQL
        final_response = run.get_final_response()
        actual_sql = extract_sql_from_response(final_response)

        # 5. 评分（复用现有逻辑）
        result = EvalResult(...)
        result.total_score = score(
            case.expected_sql, actual_sql, final_response
        )

        # 6. 错误归因（复用 ErrorAttributor）
        if result.total_score < 0.6:
            result.attribution = ErrorAttributor.attribute(...)

        return result
```

---

## 3. 方案对比

| 维度 | Hermes (当前) | DeerFlow (建议) |
|------|-------------|---------------|
| **当前状态** | ❌ 失败（空响应） | ✅ 未测试（服务未运行） |
| **启动成本** | ✅ 0（CLI 工具） | ❌ 高（需 Docker + 启动服务） |
| **执行速度** | ✅ 快（单进程） | ❌ 慢（网络 + 完整 agent 流程） |
| **准确性** | ❌ 待查（失败原因不明） | ✅ 高（实际生产路径） |
| **Trajectory** | ❌ 无（subprocess 模式） | ✅ 完整（LangGraph events） |
| **维护成本** | ✅ 低 | ❌ 中（服务依赖） |
| **适用场景** | 快速迭代、离线测试 | 最终验证、性能测试 |

### 3.1 推荐策略

**短期（P0 落地阶段）**：修复 hermes eval
- **理由**：hermes 失败原因可能很简单（配置/路径），修复成本 < 启动 DeerFlow
- **行动**：按 1.1 诊断步骤排查

**中期（P0 完成后）**：迁移到 DeerFlow eval
- **理由**：P0 改造后需要验证实际生产效果，deer-flow 更准确
- **行动**：启动 DeerFlow → 编写 DeerFlow eval client → 并行对比 hermes/deerflow

---

## 4. 决策树

```
Hermes eval 修复？
│
├─ ✅ 修复成功（1 天内）
│  └─ 继续用 hermes（快速迭代）
│
└─ ❌ 修复失败（1 天无效）
   └─ 启动 DeerFlow eval（2-3 天）
```

---

## 5. 下一步建议

### 优先级 1：诊断 hermes（30 分钟）

```bash
# A. 检查 skill 加载
ls -la ~/.hermes/skills/water-resources/water-situation/SKILL.md

# B. Debug mode
HERMES_DEBUG=1 timeout 120 hermes -z "test" -s water-situation 2>&1 | grep -i "error\|fail\|skill" | head -20

# C. 检查 stderr
timeout 120 hermes -z "test" -s water-situation 2>&1 > /tmp/hermes_out.txt
cat /tmp/hermes_out.txt | grep -v "^$" | head -20
```

### 优先级 2：如果 hermes 无法修复（2-3 小时）

```bash
# A. 启动 DeerFlow
cd /opt/git/deer-flow
make dev  # 或 docker-start

# B. 验证服务
curl http://localhost:2026/health

# C. 手动测试 DeerFlow API（如果存在）
curl -X POST http://localhost:2026/api/langgraph/runs \
  -H "Content-Type: application/json" \
  -d '{"input": {"messages": [{"role": "user", "content": "古运河有哪些水位测站"}]}}'
```

---

## 6. 结论

**当前建议**：先花 30 分钟诊断 hermes（见优先级 1），如果无法快速修复，再投入 2-3 天启动 DeerFlow eval。

**P0 改造不受影响**：无论 eval 用哪个平台，P0-1（表卡片化）和 P0-2（eval 归因）的改造都是 skill 文件本身，不依赖 eval 平台。

---

## 7. 待回答问题

1. **Hermes 是否需要配置 water-resources skill？**
   - 检查 `~/.hermes/skills/water-resources/` 是否与 `water-resources-skills/skills/` 同步

2. **DeerFlow 是否已配置好 water-resources skill？**
   - `config.yaml` 已配 `skills.path = /opt/git/water-resources-skills/skills`，但服务未启动

3. **Eval 的实际目的是什么？**
   - 获取归因基线（失败用例分类）
   - 验证 P0 改造效果
   - 如果是前者，可以人工标注 20 个失败用例（1 小时）代替全量 eval
