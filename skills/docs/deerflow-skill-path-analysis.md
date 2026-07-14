# DeerFlow Skill 路径解析机制深度分析（修正版）

**分析时间**: 2026-07-14
**分析对象**: /opt/git/deer-flow/backend/packages/harness/deerflow/
**本项目**: /opt/git/water-resources-skills

---

## 目录

1. [实际项目结构](#实际项目结构)
2. [架构概览](#架构概览)
3. [路径解析完整流程](#路径解析完整流程)
4. [关键组件源码分析](#关键组件源码分析)
5. [LLM 如何读取 Skill 文件](#llm-如何读取-skill-文件)
6. [共享目录引用机制](#共享目录引用机制)
7. [Python 代码中的路径](#python-代码中的路径)
8. [常见问题与解决方案](#常见问题与解决方案)

---

## 实际项目结构

### 本项目的真实目录布局

```
/opt/git/water-resources-skills/skills/          ← DeerFlow config.yaml 中的 host_path
├── water-situation/          ← 数据 skill（有 SKILL.md）
│   ├── SKILL.md
│   └── references/
├── rainfall/                 ← 数据 skill
├── water-quality/
├── water-forecast/
├── gate-pump-operation/
├── water-warning/
├── water-fusion/             ← 融合 skill
├── water-visualization/
├── build-dashboard/          ← 无 SKILL.md，未被 DeerFlow 识别
├── create-viz/               ← 无 SKILL.md
├── data-context-extractor/   ← 无 SKILL.md
├── lib/                      ← 共享 Python 库 ❌ 无 SKILL.md
├── shared/                   ← 共享文档 ❌ 无 SKILL.md
└── scripts/                  ← 共享脚本 ❌ 无 SKILL.md

# public/ 是软链接集合（指向本仓库内部）
/opt/git/water-resources-skills/skills/public/
├── water-situation -> ../water-situation
├── rainfall -> ../rainfall
├── lib -> ../lib
├── shared -> ../shared
└── scripts -> ../scripts
```

### DeerFlow 实际使用的配置

**真实配置**（`/opt/git/deer-flow/config.yaml:100-103`）：
```yaml
skills:
  path: /opt/git/water-resources-skills/skills  # host_path ← 直接指向本项目
  container_path: /mnt/skills  # 虚拟路径
```

**关键发现**：
- ✅ DeerFlow **直接遍历** `/opt/git/water-resources-skills/skills/`（本项目）
- ❌ **不经过** `/opt/git/deer-flow/skills/public/`（那是另一个 DeerFlow 安装的无关目录）

---

## 架构概览

### 2.1 两层路径结构

```
┌─────────────────────────────────────────────────────────┐
│                      LLM / Agent                          │
│  看到的路径: /mnt/skills/water-situation/               │
└───────────────────────┬─────────────────────────────────┘
                        │ 虚拟容器路径 (container_path)
┌───────────────────────▼─────────────────────────────────┐
│              DeerFlow PathMapping                        │
│  映射: /mnt/skills → /opt/git/water-resources-skills    │
└───────────────────────┬─────────────────────────────────┘
                        │ Host 实际路径 (host_path)
┌───────────────────────▼─────────────────────────────────┐
│              Git 仓库实际文件                             │
│  /opt/git/water-resources-skills/skills/                │
│  ├── water-situation/SKILL.md                           │
│  ├── lib/db.py                                           │
│  └── shared/db_connection.md                             │
└─────────────────────────────────────────────────────────┘
```

**重要说明**：
- ❌ **无** `/mnt/skills/public/` 中间层（之前分析有误）
- ✅ 直接映射：`/mnt/skills/<name>/` → `/opt/git/water-resources-skills/skills/<name>/`
- ✅ 本项目的 `public/` 是**内部软链接**，不影响路径映射

### 2.2 关键组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **LocalSkillStorage** | `skills/storage/local_skill_storage.py` | 管理本地文件系统的 skill 存储 |
| **SkillParser** | `skills/parser.py` | 解析 SKILL.md 的 YAML frontmatter |
| **SkillCatalog** | `skills/catalog.py` | Skill 搜索和发现 |
| **read_file_tool** | `sandbox/tools.py` | 文件读取工具（含路径解析） |
| **Prompt** | `agents/lead_agent/prompt.py` | LLM system prompt 生成 |

---

## 路径解析完整流程

### 3.1 初始化阶段

#### Step 1: 配置加载

```yaml
# /opt/git/deer-flow/config.yaml
skills:
  path: /opt/git/water-resources-skills/skills  # host_path
  container_path: /mnt/skills  # 虚拟路径
```

**源码**: `deerflow/config/skills_config.py`
```python
def get_skills_path(self) -> Path:
    """返回 host_path: /opt/git/water-resources-skills/skills"""
    return Path(self.path)
```

#### Step 2: LocalSkillStorage 初始化

**源码**: `skills/storage/local_skill_storage.py:39-52`
```python
class LocalSkillStorage(SkillStorage):
    def __init__(self, host_path=None, container_path=DEFAULT_SKILLS_CONTAINER_PATH):
        if host_path is None:
            config = get_app_config()
            self._host_root = config.skills.get_skills_path()  # /opt/git/water-resources-skills/skills
        else:
            self._host_root = resolve_path(host_path)
        self._container_root = container_path  # /mnt/skills
```

**结果**：
- `_host_root` = `/opt/git/water-resources-skills/skills`
- `_container_root` = `/mnt/skills`

#### Step 3: Skill 发现

**源码**: `skills/storage/local_skill_storage.py:68-79`
```python
def _iter_skill_files(self):
    if not self._host_root.exists():
        return
    for category in SkillCategory:
        category_path = self._host_root / category.value
        # e.g., /opt/git/water-resources-skills/skills/public
        for current_root, dir_names, file_names in os.walk(category_path, followlinks=True):
            dir_names[:] = sorted(name for name in dir_names if not name.startswith("."))
            if SKILL_MD_FILE not in file_names:
                continue
            yield category, category_path, Path(current_root) / SKILL_MD_FILE
```

**遍历结果**（本项目实际发现）：
```
/opt/git/water-resources-skills/skills/public/water-situation/SKILL.md
  → 解析为: category=public, skill_name=water-situation
  → 实际路径: /opt/git/water-resources-skills/skills/water-situation/SKILL.md (通过软链接解析)

/opt/git/water-resources-skills/skills/rainfall/SKILL.md
/opt/git/water-resources-skills/skills/water-quality/SKILL.md
...
```

**注意**：`lib/`、`shared/`、`scripts/` 无 `SKILL.md`，**不会被识别为 skill**，但仍可通过 `read_file()` 读取。

#### Step 4: Skill 对象创建

**源码**: `skills/parser.py:122-207`
```python
def parse_skill_file(skill_file: Path, category, relative_path=None):
    content = skill_file.read_text(encoding="utf-8")
    # 解析 YAML frontmatter
    front_matter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    metadata = yaml.safe_load(front_matter_match.group(1))

    return Skill(
        name=metadata['name'],  # 'water-situation'
        description=metadata['description'],
        skill_dir=skill_file.parent,  # /opt/git/.../water-situation/
        skill_file=skill_file,  # /opt/git/.../water-situation/SKILL.md
        relative_path=relative_path or Path(skill_file.parent.name),
        category=category,
    )
```

---

## LLM 如何读取 Skill 文件

### 4.1 System Prompt 中的路径信息

**源码**: `agents/lead_agent/prompt.py:162-180`
```python
def get_skill_index_prompt_section(...):
    return f"""<skill_system>
You have access to skills that provide optimized workflows.

**Skills are located at:** {container_base_path}
<skill_index>
{names}
</skill_index>
</skill_system>"""
```

**LLM 看到的 Prompt**：
```
<skill_system>
Skills are located at: /mnt/skills
<skill_index>
water-situation, rainfall, ...
</skill_index>
</skill_system>
```

### 4.2 describe_skill 工具

**源码**: `skills/describe.py:62-96`
```python
@tool
def describe_skill(name: str, tool_call_id) -> Command:
    """Fetch usage metadata for installed skills so you can decide
    whether to load the SKILL.md via read_file."""
    matched = catalog.search(name)
    if matched:
        content = _render_skill_metadata(matched, container_base_path)
        # 返回 skill 位置
        # Location: /mnt/skills/water-situation/SKILL.md
```

**LLM 调用流程**：
```
User: "查询古运河水位"
  → LLM: describe_skill("water-situation")
  → DeerFlow: 返回 Location: /mnt/skills/water-situation/SKILL.md
  → LLM: read_file("/mnt/skills/water-situation/SKILL.md")
  → DeerFlow: 读取 /opt/git/water-resources-skills/skills/public/water-situation/SKILL.md
              → 软链接解析 → /opt/git/water-resources-skills/skills/water-situation/SKILL.md
  → LLM: 看到 SKILL.md 内容
```

### 4.3 read_file 工具与路径解析

**源码**: `sandbox/tools.py`

#### Step 1: 路径验证

```python
@tool("read_file")
def read_file_tool(runtime, description, path, start_line=None, end_line=None):
    sandbox = ensure_sandbox_initialized(runtime)
    if is_local_sandbox(runtime):
        thread_data = get_thread_data(runtime)
        validate_local_tool_path(path, thread_data, read_only=True)

        # 关键: 识别 skill 路径并解析
        if _is_skills_path(path):
            path = _resolve_skills_path(path)
```

#### Step 2: 识别 Skill 路径

```python
def _is_skills_path(path: str) -> bool:
    """检查路径是否在 skill 容器下"""
    skills_prefix = _get_skills_container_path()  # "/mnt/skills"
    return path == skills_prefix or path.startswith(f"{skills_prefix}/")
```

#### Step 3: 解析到 Host 路径

```python
def _resolve_skills_path(path: str) -> str:
    """将虚拟路径解析为实际 host 路径"""
    skills_container = _get_skills_container_path()  # "/mnt/skills"
    skills_host = _get_skills_host_path()  # "/opt/git/water-resources-skills/skills"

    # 替换前缀: /mnt/skills → /opt/git/water-resources-skills/skills
    relative = path[len(skills_container):].lstrip("/")

    # 构建实际路径
    return str(Path(skills_host) / relative)
```

**路径映射示例**：
```
/mnt/skills/water-situation/SKILL.md
  → /opt/git/water-resources-skills/skills/water-situation/SKILL.md

/mnt/skills/shared/db_connection.md
  → /opt/git/water-resources-skills/skills/shared/db_connection.md

/mnt/skills/lib/db.py
  → /opt/git/water-resources-skills/skills/lib/db.py
```

---

## 共享目录引用机制

### 5.1 lib/shared/scripts 目录的特性

**关键特征**：
- ❌ **无 SKILL.md** → 不会被 DeerFlow 识别为独立 skill
- ✅ **可通过 read_file() 读取** → DeerFlow 允许读取任何路径
- ✅ **可从 Python 代码 import** → 需要正确配置 sys.path

### 5.2 在 SKILL.md 中引用共享文档

**示例**（本项目的 water-situation/SKILL.md）：
```markdown
## Prerequisites

- **数据库:** MySQL 数据库 sl323（只读）
- **连接配置:** 通过环境变量配置（`SL323_DB_HOST`, `SL323_DB_PORT`, `SL323_DB_USER`, `SL323_DB_PASSWORD`），详见 `shared/db_connection.md`。
- **pymysql:** execute_code 环境可能未安装，首次使用需先运行 `pip install pymysql`
- **DB 助手模块:** 使用 `from db import query, query_multi`（见 shared/db_connection.md），自动处理连接管理、30s 超时、空结果提示。
```

**LLM 的推理过程**：
1. LLM 看到 `shared/db_connection.md`（相对路径）
2. LLM 通过 `describe_skill("water-situation")` 获取 skill 位置
3. LLM 构建完整虚拟路径：`/mnt/skills/water-situation/shared/db_connection.md` ❌ **错误！**
4. **正确做法**：LLM 应该读取 `/mnt/skills/shared/db_connection.md` ✅

**关键理解**：
- `shared/`、`lib/`、`scripts/` 是**独立的顶层目录**（和 `water-situation/` 同级）
- ❌ 不是 `water-situation/shared/`（嵌套在 skill 内）
- ✅ 应该直接用 `/mnt/skills/shared/xxx`、`/mnt/skills/lib/xxx`

### 5.3 LLM 读取共享文件的正确路径

**目录结构**：
```
/mnt/skills/                    ← 虚拟路径根目录
├── water-situation/
│   ├── SKILL.md
│   └── references/
├── lib/
│   └── db.py
├── shared/
│   └── db_connection.md
└── scripts/
    └── config.py
```

**正确路径示例**：
```
/mnt/skills/shared/db_connection.md        ✅
/mnt/skills/lib/db.py                       ✅
/mnt/skills/scripts/config.py              ✅

/mnt/skills/water-situation/shared/xxx.md  ❌ 错误（不存在这个路径）
```

### 5.4 Python 代码如何引用共享库

#### 问题：`Path(__file__)` 不可靠

**原因**：
- DeerFlow 在 `/mnt/user-data/workspace/` 执行代码
- LLM 生成的临时脚本在 workspace
- `__file__` 指向 workspace 中的文件

#### ✅ 解决方案

**方案 1：使用虚拟路径（推荐）**
```python
# LLM 生成代码时硬编码虚拟路径
import sys
sys.path.insert(0, '/mnt/skills/lib')
from db import query, query_multi
```

**方案 2：从环境变量获取 skill 目录**
```python
import os
import sys
from pathlib import Path

# 从环境变量获取当前 skill 的虚拟路径
current_skill = os.environ.get('CURRENT_SKILL', '/mnt/skills/water-situation')
skill_dir = Path(current_skill)

# 引用共享库（相对于 skills 根目录）
skills_root = skill_dir.parent  # /mnt/skills/
sys.path.insert(0, str(skills_root / 'lib'))

from db import query
```

**方案 3：通过 bash cd 到 skill 目录执行**
```bash
# bash 工具执行
cd /mnt/skills/water-situation && python3 query.py
# 此时 Path(__file__).parent / 'lib' 能正确解析（如果在 skill 目录下）
```

**方案 4：直接修改 PYTHONPATH**
```python
import os
import sys

# 在脚本开头设置
os.environ['PYTHONPATH'] = '/mnt/skills/lib:' + os.environ.get('PYTHONPATH', '')
sys.path.insert(0, '/mnt/skills/lib')

from db import query
```

---

## Python 代码中的路径

### 6.1 skill 规范：必须使用相对路径

**skill 规范要求**：
- ❌ **禁止**硬编码绝对路径（如 `/opt/git/water-resources-skills/...`）
- ✅ **必须**使用相对路径或虚拟路径
- ✅ **原因**：同一套 skill 可在不同环境（开发/测试/生产）运行

### 6.2 执行方式对 `__file__` 的影响

#### 执行方式 1：脚本在 workspace 中（默认）

```python
# ❌ 错误示例
# __file__ = /mnt/user-data/workspace/temp_query.py
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))
# → /mnt/user-data/workspace/lib ❌ 不存在
```

#### 执行方式 2：脚本在 skill 目录中

```python
# ✅ 正确示例
# __file__ = /mnt/skills/water-situation/scripts/temp_query.py
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))
# → /mnt/skills/water-situation/lib ✅ 正确（通过软链接 → /opt/git/.../lib）
```

#### 执行方式 3：通过 bash 执行（推荐）

```bash
# DeerFlow bash 工具
cd /mnt/skills/water-situation && python3 << 'PYEOF'
import sys
sys.path.insert(0, '/mnt/skills/lib')  # ✅ 使用虚拟路径
from db import query
PYEOF
```

---

## 常见问题与解决方案

### 7.1 为什么 `Path(__file__)` 有时不可靠？

**原因**:
- DeerFlow 在 `/mnt/user-data/workspace/` 执行代码
- LLM 生成的临时脚本位于 workspace，不在 skill 目录
- `__file__` 指向 workspace 中的临时文件

**解决方案**:
```python
# 方案1: 使用虚拟路径（推荐）
sys.path.insert(0, '/mnt/skills/lib')

# 方案2: 确保脚本在 skill 目录中执行
# 通过 bash 工具 cd 到 skill 目录
cd /mnt/skills/water-situation && python3 script.py

# 方案3: 使用环境变量
import os
skills_root = os.environ.get('SKILLS_ROOT', '/mnt/skills')
sys.path.insert(0, f'{skills_root}/lib')
```

### 7.2 如何读取共享文档（shared/）？

**正确方式**:
```python
# LLM 使用 read_file 工具
read_file('/mnt/skills/shared/db_connection.md')
read_file('/mnt/skills/lib/db.py')
```

**错误方式**:
```python
# ❌ 不要假设实际路径
with open('/opt/git/water-resources-skills/skills/shared/db_connection.md') as f:
    # LLM 不知道实际路径
```

**在 SKILL.md 中的引用方式**:
```markdown
详见 `shared/db_connection.md`。
# LLM 看到后，应该读取: /mnt/skills/shared/db_connection.md
```

### 7.3 如何读取 skill 内部的 references/？

**正确方式**:
```python
# LLM 知道 skill 目录后，构建 references 路径
skill_dir = '/mnt/skills/water-situation'
read_file(f'{skill_dir}/references/water_classification.md')
```

### 7.4 PathMapping 如何工作？

**源码**: `sandbox/local/local_sandbox.py`

```python
class LocalSandbox(Sandbox):
    def read_file(self, path: str) -> str:
        # PathMapping 自动映射虚拟路径到 host 路径
        resolved = self._path_mapping.map_path(path)
        # /mnt/skills/... → /opt/git/water-resources-skills/skills/...
        return Path(resolved).read_text(encoding="utf-8")
```

**PathMapping 配置**:
```python
{
    "/mnt/skills": "/opt/git/water-resources-skills/skills",  # skills
    "/mnt/user-data/workspace": "/path/to/workspace",  # 工作区
    "/mnt/user-data/uploads": "/path/to/uploads",  # 上传
    "/mnt/user-data/outputs": "/path/to/outputs",  # 输出
}
```

### 7.5 public/ 软链接的作用

**本项目的 public/ 目录**：
```bash
/opt/git/water-resources-skills/skills/public/
├── water-situation -> ../water-situation  # 软链接
├── lib -> ../lib
├── shared -> ../shared
└── scripts -> ../scripts
```

**作用**：
1. **兼容 DeerFlow 的 category 机制**：DeerFlow 期望 `public/<skill>/SKILL.md` 结构
2. **统一入口**：所有 skill 可通过 `public/` 访问（实际指向同级目录）
3. **路径透明**：LLM 看到 `/mnt/skills/public/water-situation/`，实际指向 `/opt/git/.../water-situation/`

**对 LLM 的影响**：
- ✅ LLM **可以**使用 `/mnt/skills/public/water-situation/`（通过软链接解析）
- ✅ LLM **也可以**使用 `/mnt/skills/water-situation/`（直接目录，如果存在）

---

## 关键源码位置

### 8.1 Skill 加载

| 功能 | 文件 | 行号 |
|------|------|------|
| Skill 发现 | `skills/storage/local_skill_storage.py` | 68-79 |
| Skill 解析 | `skills/parser.py` | 122-207 |
| Skill 对象 | `skills/types.py` | 38-93 |
| 加载所有 Skills | `skills/storage/skill_storage.py` | 242-279 |

### 8.2 路径解析

| 功能 | 文件 | 行号 |
|------|------|------|
| 获取容器路径 | `sandbox/tools.py` | `_get_skills_container_path()` |
| 获取 Host 路径 | `sandbox/tools.py` | `_get_skills_host_path()` |
| 识别 Skill 路径 | `sandbox/tools.py` | `_is_skills_path()` |
| 解析 Skill 路径 | `sandbox/tools.py` | `_resolve_skills_path()` |
| PathMapping | `sandbox/local/local_sandbox.py` | 完整类 |

### 8.3 LLM 提示

| 功能 | 文件 | 行号 |
|------|------|------|
| Skill System Prompt | `agents/lead_agent/prompt.py` | 162-180 |
| Working Directory | `agents/lead_agent/prompt.py` | 546-561 |
| describe_skill | `skills/describe.py` | 62-96 |

---

## 总结

### DeerFlow Skill 路径机制的核心要点

1. **两层路径，无中间层**：
   - 虚拟路径 `/mnt/skills/<name>/`（LLM 看到）
   - Host 路径 `/opt/git/water-resources-skills/skills/<name>/`（实际文件）
   - ❌ **无** `/mnt/skills/public/<name>/` 这一层

2. **自动解析**：
   - `read_file` 自动识别 `/mnt/skills` 前缀
   - 自动映射到 host 路径
   - LLM 无需知道实际路径

3. **共享目录（lib/shared/scripts）**：
   - ❌ 不是 skill（无 SKILL.md）
   - ✅ 可通过 `read_file('/mnt/skills/shared/xxx')` 读取
   - ✅ 可通过 `sys.path.insert(0, '/mnt/skills/lib')` 导入
   - ✅ LLM 需要使用**顶层虚拟路径**（不是 skill 内相对路径）

4. **Skill 内部引用**：
   - `references/xxx.md` → 相对 skill 目录
   - LLM 构建：`/mnt/skills/<skill>/references/xxx.md`

5. **Python 代码中的路径**：
   - **问题**: `__file__` 不可靠（workspace 执行）
   - **解决**: 使用虚拟路径 `/mnt/skills/lib`
   - **前提**: 代码需要显式添加 `/mnt/skills/lib` 到 sys.path

6. **public/ 软链接的作用**：
   - ✅ 兼容 DeerFlow 的 category 机制
   - ✅ 统一入口，LLM 可以使用 `/mnt/skills/public/<skill>/`
   - ✅ 不影响路径映射（仍映射到 `/opt/git/water-resources-skills/skills/`）

7. **与 /opt/git/deer-flow/skills/public/ 的关系**：
   - ❌ **完全无关**（那是另一个 DeerFlow 安装的 skills）
   - ✅ 本项目只使用 `/opt/git/water-resources-skills/`

---

**维护说明**: 本文档基于实际项目结构和 DeerFlow commit 3a7572e 源码分析，如架构变动需更新。
