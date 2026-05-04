import os
import logging

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
if not deepseek_api_key:
    raise EnvironmentError("请在 .env 文件中设置 DEEPSEEK_API_KEY")

llm = ChatOpenAI(
    model="deepseek-v4-pro",
    api_key=deepseek_api_key,
    base_url="https://api.deepseek.com",
    temperature=0,
    max_tokens=8192
)

# ========== Prompts ==========

EXTRACT_PROMPT = """
你是一个知识整理专家。请阅读以下文档内容，提取核心主题和子主题，形成一个多层次的思维导图结构。
输出要求：
- 用严格的 JSON 格式，只包含一个顶层节点，字段说明：
  - "title": 节点标题
  - "children": 子节点列表（如果没有子节点则为空数组[]）
- 层级深度不超过4层，每个节点标题简洁（不超过20字）。

示例输出：
{
  "title": "LangGraph 概述",
  "children": [
    {
      "title": "核心概念",
      "children": [
        {"title": "状态图", "children": []},
        {"title": "节点与边", "children": []}
      ]
    },
    {
      "title": "应用场景",
      "children": [
        {"title": "多步推理", "children": []},
        {"title": "人机协同", "children": []}
      ]
    }
  ]
}

文档内容：
{text}

JSON 输出：
"""

PROMPT_GENERATOR_TEMPLATE = """
你是一位专业的提示词工程师。用户想从一份文档中提取思维导图结构，并提供了特定的分析要求。
请根据用户要求和文档摘要，生成一个完整、可用的提取提示词。

生成的提示词应包含：
1. 明确的分析范围——严格遵循用户的限定（如只分析某章节、只看某主题），忽略无关内容
2. 输出格式要求——严格 JSON 树形结构，字段为 "title" 和 "children"，无子节点时 children 为空数组 []
3. 层级限制——默认不超过 4 层，除非用户另有要求
4. 节点标题——简洁，不超过 20 字
5. 如果用户要求关注特定方面（如技术架构、人物关系等），在提示词中明确要求 LLM 以该视角提取

文档摘要（前 5000 字符）：
{document_summary}

用户的分析要求：
{user_message}

请直接输出生成好的提取提示词，不要包含任何解释、前缀或后缀。输出将直接作为 LLM 的系统提示词使用。
"""

PROMPT_REFINE_TEMPLATE = """
你是一位提示词优化专家。下面是当前的提取提示词，以及用户提出的修改建议。
请根据用户的建议直接在当前提示词上修改，输出修改后的完整版本。

当前提示词：
{current_prompt}

用户修改建议：
{user_feedback}

请直接输出修改后的完整提示词，不要包含任何解释、前缀或后缀。不要添加"修改说明"或"改进点"等额外内容，只输出修改后的提示词本身。
"""

CONTENT_EVAL_PROMPT = """
你是一位严格的思维导图质量评审专家。请审阅以下从文档中提取的思维导图结构，
从以下五个维度逐一评分（每项 0-10 分）：

1. 覆盖度 — 文档的核心主题是否被覆盖？有无重大遗漏？
2. 逻辑性 — 父子层级关系是否正确？同级节点是否真正并列？概念归属有无错误？
3. 平衡性 — 各分支的展开深度是否均衡？有无某个分支过深而其他过浅？
4. 准确性 — 每个节点标题是否准确概括了文档中对应的内容？
5. 简洁度 — 有无冗余、重复的节点？层级总数是否在合理范围？

请输出严格的 JSON（不要包含任何其他文字）：
{{
  "scores": {{
    "覆盖度": 8,
    "逻辑性": 7,
    "平衡性": 6,
    "准确性": 8,
    "简洁度": 7
  }},
  "total": 7.2,
  "pass": true,
  "issues": ["具体问题1", "具体问题2"],
  "suggestions": "具体的改进建议，逐条列出，供提取器在下一轮参考修正。"
}}

判断标准：total 需要达到阈值（由用户设定，通常 7.0），且每项不低于 5.0。

文档原文（前 5000 字符作为评审参考）：
{original_text}

当前生成的思维导图树：
{mindmap_json}
"""

LAYOUT_EVAL_PROMPT = """
你是一名信息图布局专家。当前思维导图的某些节点出现了重叠（已在下方列出）。请分析原因，并给出具体的参数调整建议。

可调整的参数及其当前值：
- level_gap: 父子节点间的水平距离（默认 250）
- min_y_gap: 兄弟节点间的最小垂直间距（默认 20）

要求：
1. 简要说明导致重叠的主要原因。
2. 给出新的参数建议值（只能是数值），格式如下（JSON）：
{{
  "reason": "简要原因",
  "level_gap": 350,
  "min_y_gap": 60
}}
只输出 JSON，不要其他文字。

节点样本（前20个，带坐标和尺寸）：
{nodes_info}

重叠对（id1 <-> id2，重叠面积）：
{overlaps}
"""
