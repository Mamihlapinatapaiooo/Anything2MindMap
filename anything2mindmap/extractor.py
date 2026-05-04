import json
import os
import logging

from anything2mindmap.state import MindMapState
from anything2mindmap.config import llm, EXTRACT_PROMPT

logger = logging.getLogger(__name__)


def extract_structure(state: MindMapState) -> MindMapState:
    logger.info("🤖 步骤 2/5：LLM 提炼思维导图结构...")
    text = state['raw_text']
    if not text.strip():
        raise ValueError("文档为空，无法生成思维导图")

    custom_prompt = state.get('custom_prompt', '').strip()
    template = custom_prompt if custom_prompt else EXTRACT_PROMPT
    if custom_prompt:
        logger.info("使用用户定制的提取提示词")

    feedback = state.get('content_feedback', '').strip()
    if feedback:
        score = state.get('content_quality_score', 0)
        template += (
            f"\n\n【质量改进提示 — 上一轮评分 {score:.1f}/10，未通过】"
            f"\n评委反馈：\n{feedback}\n"
            f"\n请务必在本次提取中修正上述问题。"
        )
        logger.info("检测到评委反馈，已附加到提取提示词中")

    try:
        truncated = text[:100000]
        resp = llm.invoke(template.replace("{text}", truncated))
        content = resp.content.strip()

        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()

        tree = json.loads(content)
        state['mindmap_tree'] = tree

        output_path = os.path.join(state['output_dir'], "mindmap_tree.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)
        logger.info("思维导图树已保存 → mindmap_tree.json")
    except Exception as e:
        logger.error(f"LLM 调用或解析失败：{e}")
        raise
    return state
