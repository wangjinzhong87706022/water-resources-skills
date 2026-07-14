# DeerFlow db 模块路径问题 - 完整修复方案

**修复时间**: 2026-07-14
**问题**: LLM agent 在 DeerFlow 中执行水情查询时无法找到 `db` 模块

---

## 问题现象

在 DeerFlow 中执行智能问数时，agent 生成的代码尝试了多个错误路径：

```python
# 尝试1: 错误的 hermes-agent 路径
sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')

# 尝试2: DeerFlow backend 路径
sys.path.insert(0, '/opt/git/deer-flow/backend/packages/harness')

# 尝试3: 在 workspace 中查找
find /mnt/user-data/workspace -name "db.py"
```

最终导致找不到 `db` 模块，查询失败。

---

## 问题根因分析

### 1. 软链接配置正确，但文档错误

**软链接结构**（正确）：
```
/opt/git/deer-flow/skills/public/water-situation/
├── lib -> /opt/git/water-resources-skills/skills/lib/  ✅
├── references -> /opt/git/water-resources-skills/skills/water-situation/references/  ✅
└── shared -> /opt/git/water-resources-skills/skills/shared/  ✅
```

**文档问题**（错误）：
- `shared/db_connection.md` 第30行：硬编码 hermes-agent 路径
- `lib/db.py` 注释：硬编码 hermes-agent 路径
- LLM 看到错误示例 → 生成错误代码

### 2. DeerFlow 执行环境

**工作目录**：
- DeerFlow agent 在 `/mnt/user-data/workspace/<thread_id>/user-data/workspace/` 执行代码
- Bash 命令自动添加 `cd <workspace> &&` 前缀
- Python 代码如果写入临时文件，`__file__` 指向 workspace

**路径解析**：
```python
# LLM 生成的代码（错误）
script_path = '/mnt/user-data/workspace/temp_query.py'
lib_path = Path(script_path).parent / 'lib'
# → /mnt/user-data/workspace/lib ❌ 不存在

# 正确的 lib 路径
lib_path = '/opt/git/deer-flow/skills/public/water-situation/lib'
# → /opt/git/deer-flow/skills/public/water-situation/lib ✅ 存在（软链接）
```

---

## 修复方案

### 1. `shared/db_connection.md` - 多平台支持

**修复前**（硬编码 hermes-agent）：
```python
sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')
```

**修复后**（三平台支持）：
```markdown
=== "DeerFlow 平台"
    sys.path.insert(0, '/opt/git/deer-flow/skills/public/water-situation/lib')

=== "hermes-agent 平台"
    sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')

=== "Git 仓库直接使用"
    sys.path.insert(0, str(Path(__file__).parent / 'lib'))
```

新增 **"平台适配说明"** 表格：
| 平台 | lib 路径 |
|------|---------|
| DeerFlow | `/opt/git/deer-flow/skills/public/<skill-name>/lib` |
| hermes-agent | `/opt/git/hermes-agent/skills/water-resources/lib` |
| Git 仓库 | `Path(__file__).parent / 'lib'` |

### 2. `lib/db.py` - 移除硬编码路径

**修复前**：
```python
"""Shared DB helper for water-resources skills.

Usage:
    import sys
    sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')  # ❌
    from db import query, query_multi
"""
```

**修复后**：
```python
"""Shared DB helper for water-resources skills.

Platform-specific import paths:

=== "DeerFlow"
    sys.path.insert(0, '/opt/git/deer-flow/skills/public/water-situation/lib')

=== "hermes-agent"
    sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')

=== "Git repository"
    sys.path.insert(0, str(Path(__file__).parent / 'lib'))
"""
```

### 3. `water-situation/SKILL.md` - 恢复相对路径说明

**第一次错误修复**（不应硬编码绝对路径）：
```markdown
- **db 模块路径:** 使用绝对路径 `/opt/git/deer-flow/skills/public/water-situation/lib`
```

**第二次正确修复**（平台无关说明）：
```markdown
- **db 模块路径:** 使用 `lib/db.py` 助手模块，导入前需将 lib 目录加入 `sys.path`。
  不同平台的路径不同，详见 `shared/db_connection.md`。**推荐做法：根据部署平台选择对应的绝对路径**，
  避免使用 `Path(__file__)`（DeerFlow 执行环境中 `__file__` 不可靠）。
```

### 4. `description` 简化

**修复前**：
```yaml
description: "水情综合查询 — 河道水位、水库水位、防洪指标、超警戒判断。核心表: sl323.st_river_r, sl323.st_rsvr_r, sl323.st_stbprp_b, sl323.st_rvfcch_b。"
```

**修复后**：
```yaml
description: "水情综合查询 — 河道水位、水库水位、防洪指标、超警戒判断。"
```

---

## 关键教训

### ❌ 不要做的

1. **不要在共享库中硬编码特定平台路径**
   - `db.py` 注释中使用 hermes-agent 路径
   - `db_connection.md` 中硬编码绝对路径

2. **不要在 SKILL.md description 中添加无意义的"核心表"说明**
   - 表名是技术细节，不应出现在 description

3. **不要假设 LLM 理解软链接机制**
   - 软链接对 LLM 是透明的
   - LLM 看到错误路径示例就会复制

### ✅ 要做的

1. **在共享文档中明确区分平台**
   - 使用 tabbed code blocks（=== "平台名"）
   - 提供清晰的"平台适配说明"表格

2. **指向权威文档**
   - SKILL.md → shared/db_connection.md
   - 避免重复和维护负担

3. **提供查找方法**
   ```bash
   find /opt/git -name "db.py" -path "*/lib/*" 2>/dev/null
   ```

4. **解释为什么**
   - 说明 `__file__` 为什么不可靠
   - 说明 DeerFlow 执行环境的工作目录
   - 说明软链接的实际位置

---

## 测试验证

修复后，LLM agent 应该：

1. **读取 `shared/db_connection.md`**
2. **根据实际部署平台选择正确路径**
3. **生成正确的导入代码**

**期望结果**：
```python
# DeerFlow 环境
sys.path.insert(0, '/opt/git/deer-flow/skills/public/water-situation/lib')
from db import query

# hermes-agent 环境
sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')
from db import query
```

**不再出现**：
```python
# ❌ 错误路径
sys.path.insert(0, '/opt/git/hermes-agent/skills/water-resources/lib')  # 在 DeerFlow 中
```

---

## 适用场景

本修复方案适用于：

1. **多平台部署**：同一套 skill 代码在 DeerFlow/hermes-agent/Git 等不同环境运行
2. **路径配置差异**：不同平台的技能容器路径不同
3. **共享库文档**：`lib/db.py`、`shared/db_connection.md` 等被多个 skill 引用的文档

---

## 提交记录

- `50ec90a` fix(skill): 修复 db 模块路径问题，支持多平台
  - `skills/lib/db.py` (多平台注释)
  - `skills/shared/db_connection.md` (三平台代码块 + 说明表格)
  - `skills/water-situation/SKILL.md` (指向 shared 文档 + description 简化)
