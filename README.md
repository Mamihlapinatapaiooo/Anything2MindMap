# Anything2MindMap

从任意文本、文档、代码或论文自动生成**多层思维导图**，输出 Obsidian Canvas + PDF 两种格式。

基于 LangGraph 工作流编排，使用 DeepSeek LLM 提炼知识结构，并引入 GAN 式评委节点对内容质量把关。

## 环境要求

| 项目 | 说明 |
|------|------|
| Python | 3.12+ |
| 包管理器 | [uv](https://docs.astral.sh/uv/) |
| LLM | DeepSeek API Key（模型 `deepseek-v4-pro`） |
| 浏览器 | Edge 或 Chrome（用于无头打印 PDF） |
| 系统 | Windows（已验证）/ macOS / Linux |

## 快速开始

```bash
# 1. 安装依赖
uv sync

# 2. 配置 DeepSeek API Key
echo "DEEPSEEK_API_KEY=sk-你的密钥" > .env

# 3. 创建输入输出目录（已纳入 .gitignore）
mkdir inputs outputs

# 4. 将待分析文件放入 inputs/，运行
uv run anything2mindmap ./inputs/你的文档.docx

# 或使用脚本入口
uv run anything2mindmap ./inputs/你的文档.docx --output-dir ./my_outputs
```

## 命令行参考

```
uv run anything2mindmap <file_path> [OPTIONS]
```

### 完整参数列表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_path` | 必填 | — | 单文件（`.docx` / `.txt` / `.pdf`）或目录路径 |
| `-p`, `--prompt` | str | `""` | 用户补充说明，限定提取范围或分析角度 |
| `--output-dir` | str | `./outputs` | 输出目录 |
| `--max-retries` | int | `3` | 布局重叠时的最大重试次数 |
| `--level-gap` | int | `250` | 父→子节点的水平间距（像素） |
| `--min-y-gap` | int | `20` | 兄弟节点间的垂直最小间距（像素） |
| `--include` | str | `""` | 目录模式下限定文件扩展名，逗号分隔（如 `.py,.md`） |
| `--max-quality-retries` | int | `3` | 内容质量不达标时的最大重试次数 |
| `--quality-threshold` | float | `7.0` | 内容质量通过阈值（0–10），越高越严格 |

---

## 输入支持

### 单文件模式

| 格式 | 加载方式 | 场景 |
|------|---------|------|
| `.docx` | 提取段落文本 | Word 文档、技术方案、会议纪要 |
| `.txt` | UTF-8 全文读取 | 纯文本笔记、日志、导出文件 |
| `.pdf` | 逐页提取文字 | 论文、报告、书籍章节 |

### 目录模式

传入一个目录路径时，程序会递归扫描并拼接所有匹配文件，格式化为带文件路径标注的文本块提交给 LLM。

**默认支持的格式**（30+ 种）：`.py`、`.js`、`.ts`、`.tsx`、`.go`、`.rs`、`.java`、`.c`、`.h`、`.md`、`.pdf`、`.txt`、`.json`、`.yaml`、`.html`、`.css`、`.sql` 等。

**自动跳过的内容**：
- 虚拟环境：`.venv`、`venv`、`env`
- 缓存目录：`__pycache__`、`.mypy_cache`、`.pytest_cache`
- 依赖目录：`node_modules`
- 版本控制：`.git`、`.svn`、`.hg`
- 构建产物：`dist`、`build`、`target`
- 二进制文件（通过 null 字节检测）

**三层容量保护**：

| 条件 | 行为 |
|------|------|
| 文件数 > 500 | 直接报错退出，提示缩小范围 |
| 总字符 ≤ 100,000 | 所有文件完整传入 |
| 总字符 > 100,000 | 优先保中小文件完整，大文件截断并标注省略 |

---

## 使用示例

### 基础用法

```bash
# 分析 Word 文档
uv run anything2mindmap ./inputs/技术方案.docx

# 分析纯文本
uv run anything2mindmap ./inputs/会议纪要.txt

# 指定输出目录
uv run anything2mindmap ./inputs/周报.txt --output-dir ./my_outputs
```

### 分析论文

```bash
# 逐页提取 PDF 全文并生成思维导图
uv run anything2mindmap ./inputs/paper.pdf

# 聚焦论文的特定方面
uv run anything2mindmap ./inputs/paper.pdf -p "提取研究方法、实验设计、主要结论和创新点"

# 批量对比多篇论文
uv run anything2mindmap ./papers --include ".pdf" -p "比较各篇的核心贡献和方法的异同"
```

### 分析代码项目

```bash
# 分析整个项目架构
uv run anything2mindmap ./src -p "分析整体模块结构和依赖关系"

# 限定文件类型
uv run anything2mindmap ./src --include ".py,.md" -p "只分析核心业务逻辑和文档"

# 分析前端项目
uv run anything2mindmap ./frontend --include ".tsx,.ts,.css" -p "梳理组件树和数据流"
```

### 自定义提取范围

```bash
# 只分析文档中的特定章节
uv run anything2mindmap ./inputs/研究报告.docx -p "只分析第三章，聚焦技术架构，忽略背景介绍"

# 以特定视角分析
uv run anything2mindmap ./inputs/产品文档.docx -p "从用户视角提取功能清单和操作流程"
```

### 质量与布局调优

```bash
# 提高质量门槛（对学术产出更严格的审核）
uv run anything2mindmap ./inputs/论文.pdf --quality-threshold 8.5

# 快速模式（降低门槛减少 LLM 调用）
uv run anything2mindmap ./inputs/周报.txt --quality-threshold 5.0 --max-quality-retries 1

# 节点密集时增大布局间距
uv run anything2mindmap ./inputs/大型报告.docx --level-gap 350 --min-y-gap 60

# 减少布局重试以加快执行
uv run anything2mindmap ./inputs/日报.txt --max-retries 1
```

---

## 输出文件

程序在 `--output-dir`（默认 `./outputs`）生成以下文件：

| 文件 | 格式 | 用途 |
|------|------|------|
| `mindmap_tree.json` | JSON | LLM 提炼的完整思维导图树（`title` + `children` 嵌套结构） |
| `mindmap.canvas` | JSON | Obsidian Canvas 格式，可拖入 Obsidian 直接编辑 |
| `output_mindmap.pdf` | PDF | 浏览器无头渲染的最终可视化成品 |

---

## 流水线架构

```
                        ┌─────────────┐
                        │ load_document│ ← 文件/目录 → raw_text
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                  ┌─────│  extract    │← feedback on retry
                  │     └──────┬──────┘
                  │            │
                  │     ┌──────▼──────────┐
                  │     │ evaluate_content │ ← GAN 式评委
                  │     └──────┬──────────┘
                  │            │
                  │    ┌───────▼────────┐
                  └────┤ score < 阈值?  │
                  NO   └───┬────────────┘  YES
                       │          └───→ 回到 extract
                       │
                ┌──────▼──────┐
                │   canvas    │ ← 递归坐标分配
                └──────┬──────┘
                       │
                ┌──────▼──────────┐
           ┌────│ evaluate_layout │ ← 重叠检测
           │    └──────┬──────────┘
           │           │
           │   ┌───────▼────────┐
           └───┤  有重叠且未    │
          YES  │  达上限？      │  NO
               └───┬────────────┘
                   │          └───→ 前进
                   └──→ 回到 canvas

                ┌──────▼──────┐
                │  render_pdf  │ ← HTML → 浏览器无头打印
                └──────────────┘
```

### 各步骤详解

**步骤 1 — 文档加载（`loader.py`）**
单文件根据扩展名选择 Loader（`Docx2txtLoader` / `TextLoader` / `pdfplumber`）。目录则递归扫描、拼接为带相对路径头标注的格式化文本，并对超大目录实施容量保护。

**步骤 2 — LLM 结构提炼（`extractor.py`）**
将文档文本（截断至 100,000 字符）提交给 DeepSeek LLM，要求输出严格的 JSON 树形结构。如果用户通过 `-p` 提供了定制提示词，优先使用；重试时会在提示词末尾附加上一轮评委的改进反馈。

**步骤 3 — 内容质量评审（`content_reviewer.py`）**  🆕
独立的评委 LLM 从 5 个维度对提取结果打分（详见下文），给出通过/不通过判定及具体改进建议。不通过时反馈回步骤 2 重新提取。

**步骤 4 — Canvas 布局生成（`canvas.py`）**
递归计算每个节点的画布坐标，生成带节点位置和贝塞尔连线的 Canvas JSON。

**步骤 5 — 布局评估与重试（`layout.py` + `graph.py`）**
检测节点是否重叠；若重叠，让 LLM 建议调整 `level_gap` / `min_y_gap` 参数后重新生成布局。

**步骤 6 — PDF 渲染（`renderer.py`）**
生成 HTML 页面，调用系统浏览器（Edge/Chrome）以无头模式打印为 PDF。

---

## 内容质量评审系统

GAN（生成对抗网络）思想的文本等价实现：提取器（Generator）产出思维导图，评委（Discriminator）审阅打分，不合格时带反馈重试。

### 评委评分维度

| 维度 | 说明 | 权重 |
|------|------|------|
| 覆盖度 | 文档的核心主题是否被涵盖？是否存在重大遗漏？ | 等权 |
| 逻辑性 | 父子层级关系是否正确？同级节点是否真正并列？概念归属有无错误？ | 等权 |
| 平衡性 | 各分支的展开深度是否均衡？是否存在某个分支过深而其他过浅？ | 等权 |
| 准确性 | 每个节点标题是否准确概括了文档中对应的内容？ | 等权 |
| 简洁度 | 是否存在冗余、重复的节点？层级总数是否在合理范围内？ | 等权 |

### 评判流程

```
评委取原文前 5000 字符 + 完整思维导图树 → 逐维打分 → 输出 JSON
                                                    │
                                              total ≥ 阈值?
                                              ┌─ YES → pass → 进入布局阶段
                                              └─ NO  → 输出 issues + suggestions → 回 extract
```

评委输出的 JSON 结构：
```json
{
  "scores": {
    "覆盖度": 8,
    "逻辑性": 7,
    "平衡性": 6,
    "准确性": 8,
    "简洁度": 7
  },
  "total": 7.2,
  "pass": true,
  "issues": ["结论部分完全遗漏", "第三层过于深入细节"],
  "suggestions": "1. 补充结论节点的提取；2. 第三层可合并为更概括的节点；3. ..."
}
```

### 成本估算

| 场景 | LLM 调用次数 |
|------|------------|
| 无 `-p`，一次通过 | 1 提取 + 1 评委 + 1 布局评估 = 3 |
| 有 `-p`，一次通过 | 1 提示词生成 + 1 提取 + 1 评委 + 1 布局评估 = 4 |
| 内容重试 2 次后通过 | 额外 +4（每次重试 = 评委 + 提取） |
| 布局重试 2 次后通过 | 额外 +4（每次重试 = 评估 + 生成） |

实际使用中，绝大多数输入在 1 次评委后就通过。

---

## 自定义提取提示词交互

当使用 `-p` 参数时，程序会在流水线启动前进入交互式提示词优化循环：

```
$ uv run anything2mindmap ./inputs/论文.pdf -p "提取方法、实验、结论"

📄 正在加载文档: ./inputs/论文.pdf
   字符数：45231
📝 正在根据您的要求生成定制提取提示词...

────────────────────────────────────────────────────────
你是一个知识整理专家。请阅读以下文档内容，仅关注研究方法、
实验设计、主要结论和创新点部分，忽略背景介绍和文献综述...
────────────────────────────────────────────────────────

操作: [a]接受  [e]提意见微调  [r]LLM重新生成  [w]手动重写  [q]退出
```

| 操作 | 行为 | 调用 LLM |
|------|------|:--------:|
| `a` | 接受当前提示词，进入流水线 | 否 |
| `e` | 提一句修改意见，LLM 基于**当前提示词**定向修改 | 是 |
| `r` | LLM 忽略当前提示词，从文档**从头生成** | 是 |
| `w` | 完全手动输入新提示词（多行，`/END` 结束） | 否 |
| `q` | 退出程序 | — |

> **设计原则**：无论走 `e` / `r` / `w` 哪条路径，修改后都会回到确认界面。必须由人显式按 `a` 才会进入流水线。LLM 永远不会未经确认就覆盖你的编辑。

---

## 调优指南

### 内容质量

| 目标 | 建议 |
|------|------|
| 学术/正式场景 | `--quality-threshold 8.0` 或更高 |
| 快速预览 | `--quality-threshold 5.0 --max-quality-retries 1` |
| 默认均衡 | `--quality-threshold 7.0 --max-quality-retries 3` |

### 布局外观

| 问题 | 解决方案 |
|------|---------|
| 节点太密、文字挤在一起 | 增大 `--level-gap` 到 350–400 |
| 同一层节点上下粘连 | 增大 `--min-y-gap` 到 50–80 |
| 大文档 PDF 被截断 | 增大间距后重试 |
| 想关掉布局重试加速 | `--max-retries 1` 或 `0` |

### 速度与成本

| 目标 | 建议 |
|------|------|
| 最快速度 | `--max-quality-retries 1 --max-retries 1` |
| 最高质量 | `--quality-threshold 8.5 --max-quality-retries 5` |
| 节省 API 费用 | 不传 `-p`（跳过提示词生成），降低两个 retries |

---

## 项目结构

```
anything2mindmap/
├── __init__.py         # 包标记
├── __main__.py         # argparse CLI 入口
├── state.py            # MindMapState TypedDict + make_initial_state()
├── config.py           # 日志、LLM 实例、全部 5 个提示词模板
├── loader.py           # 单文件加载 + 目录递归扫描
├── extractor.py        # LLM 结构提炼（含反馈重试）
├── content_reviewer.py # GAN 式评委：评分 + 路由
├── layout.py           # 坐标分配、重叠检测、布局评估
├── canvas.py           # Canvas JSON 生成 + HTML 构建
├── renderer.py         # 浏览器查找 + 无头 PDF 打印
├── prompt_builder.py   # 定制提示词生成 + 交互优化
└── graph.py            # LangGraph 工作流编排 + 两类 retry 路由
```

### 依赖关系

```
state → config → {loader, extractor, layout, prompt_builder, content_reviewer}
                           ↓
                       canvas → renderer → graph → __main__
```

无循环依赖。`extractor` / `layout` / `canvas` / `renderer` / `prompt_builder` / `content_reviewer` 之间相互独立，仅通过 `state` 共享数据。

---

## 许可

MIT
