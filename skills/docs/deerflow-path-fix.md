# DeerFlow 路径问题诊断与修复

**问题时间**: 2026-07-14
**问题**: DeerFlow 执行智能问数时无法找到 `db.py` 模块

---

## 问题现象

在 DeerFlow 中执行水情查询时，agent 尝试多种路径查找 `db` 模块，最终失败：

```
1. sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')  # ❌ 错误
2. 尝试 /opt/git/deer-flow/backend/packages/harness
3. 尝试 /opt/git/deer-flow/backend
4. 在 /mnt/user-data/workspace/ 中查找
```

**根本原因**：
- DeerFlow agent 在 `/mnt/user-data/workspace/` 执行 Python 代码
- `db.py` 注释中使用 hermes-agent 路径导致 LLM 生成错误路径
- SKILL.md 中使用 `Path(__file__).parent / 'lib'`，但 LLM 无法确定 `__file__` 的实际位置

---

## 诊断过程

### 1. 查看 DeerFlow 日志

```bash
tail -f /opt/git/deer-flow/logs/gateway.log | grep "sandbox_audit"
```

发现 agent 生成的代码：
```python
sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')  # 错误！
```

### 2. 检查软链接状态

```bash
ls -la /opt/git/deer-flow/skills/public/water-situation/
```

结果：软链接正确
- `lib -> /opt/git/water-resources-skills/skills/lib`
- `references -> /opt/git/water-resources-skills/skills/water-situation/references`
- `shared -> /opt/git/water-resources-skills/skills/shared`

### 3. 检查 db.py 注释

发现 `db.py` 文件中的注释使用了 hermes-agent 的路径：
```python
"""Shared DB helper for water-resources skills.

Usage:
    import sys
    sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')  # ❌ 错误！
    from db import query, query_multi
"""
```

### 4. 检查 SKILL.md 路径指令

```markdown
- **db 模块路径:** `sys.path.insert(0, str(Path(__file__).parent / 'lib'))`。不要用其他路径。
```

**问题**：LLM 无法确定 `__file__` 的实际位置，因为：
- DeerFlow 在 `/mnt/user-data/workspace/` 执行代码
- SKILL.md 可能通过软链接加载
- `__file__` 解析会因执行方式不同而变化

---

## 解决方案

### 1. 修改 SKILL.md

**修改前**：
```markdown
- **db 模块路径:** `sys.path.insert(0, str(Path(__file__).parent / 'lib'))`。不要用其他路径。
```

**修改后**：
```markdown
- **db 模块路径:** 使用绝对路径 `sys.path.insert(0, '/opt/git/deer-flow/skills/public/water-situation/lib')` 然后 `from db import query, query_multi`。**不要使用相对路径或 `Path(__file__)`**，因为执行环境工作目录是 `/mnt/user-data/workspace/`，`__file__` 不可靠。
```

### 2. 修改 db.py 注释

**修改前**：
```python
"""Shared DB helper for water-resources skills.

Usage:
    import sys
    sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')  # ❌ 错误路径！
    from db import query, query_multi
"""
```

**修改后**：
```python
"""Shared DB helper for water-resources skills.

Usage (DeerFlow):
    import sys
    sys.path.insert(0, '/opt/git/deer-flow/skills/public/water-situation/lib')
    from db import query, query_multi

Usage (hermes-agent):
    import sys
    sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')
    from db import query, query_multi
"""
```

---

## 验证方法

修改后，在 DeerFlow 中执行查询，检查日志中的路径是否正确：

```bash
tail -f /opt/git/deer-flow/logs/gateway.log | grep "sandbox_audit"
```

**期望看到**：
```python
sys.path.insert(0, '/opt/git/deer-flow/skills/public/water-situation/lib')
from db import query
```

而不是尝试多个错误路径。

---

## 关键教训

### ❌ 不要做的

1. **不要在共享库注释中使用特定平台的路径**
2. **不要在 SKILL.md 中使用 `Path(__file__)`**（LLM 无法解析）
3. **不要假设 LLM 理解文件系统的软链接机制**

### ✅ 要做的

1. **在 SKILL.md 中使用绝对路径**（硬编码实际路径）
2. **在 db.py 注释中支持多平台**（通过条件区分）
3. **在文档中明确说明执行环境**（如 `/mnt/user-data/workspace/`）
4. **提供复制粘贴即用的代码片段**（避免 LLM 推理路径）

---

## 适用场景

本修复适用于所有在 DeerFlow 中使用外部技能库的场景：

- ✅ **DeerFlow**: `/opt/git/deer-flow/skills/public/<skill-name>/`
- ✅ **hermes-agent**: `/opt/git/hermes-agent/skills/water-resources/`
- ✅ **本地开发**: 直接在 Git 仓库中使用

每个平台的路径都不同，需要在文档中明确区分。

---

**维护说明**: 如果 DeerFlow 的技能路径配置改变（`config.yaml` 中的 `skills.path`），需要同步更新 SKILL.md 中的绝对路径。
