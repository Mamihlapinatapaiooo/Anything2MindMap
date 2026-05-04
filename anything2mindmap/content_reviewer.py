import json
import logging

from anything2mindmap.state import MindMapState
from anything2mindmap.config import llm, CONTENT_EVAL_PROMPT

logger = logging.getLogger(__name__)


def evaluate_content(state: MindMapState) -> MindMapState:
    """调用 LLM 评委对思维导图内容质量打分，写回 state。"""
    logger.info("🎯 步骤 2.5：评委评估内容质量...")

    tree = state.get('mindmap_tree', {})
    if not tree:
        logger.warning("思维导图为空，跳过内容评估")
        state['content_quality_score'] = 10.0
        state['content_feedback'] = ""
        return state

    original_text = state['raw_text'][:5000]
    mindmap_json = json.dumps(tree, ensure_ascii=False, indent=2)

    try:
        resp = llm.invoke(CONTENT_EVAL_PROMPT.format(
            original_text=original_text,
            mindmap_json=mindmap_json,
        ))
        content = resp.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()

        result = json.loads(content)
        total = float(result.get('total', 0))
        state['content_quality_score'] = total
        state['content_feedback'] = result.get('suggestions', '')

        scores = result.get('scores', {})
        score_detail = ' | '.join(f"{k}={v}" for k, v in scores.items())
        threshold = state.get('quality_threshold', 7.0)
        passed = total >= threshold
        status = '✅ 通过' if passed else '❌ 未通过'
        logger.info(f"评委评分: {score_detail} | 总分={total:.1f}/10 {status} (阈值={threshold})")

        if not passed:
            issues = result.get('issues', [])
            for issue in issues:
                logger.warning(f"  ⚠️ {issue}")

    except Exception as e:
        logger.error(f"评委评估失败：{e}，视为通过")
        state['content_quality_score'] = 10.0
        state['content_feedback'] = ""

    state['content_retry_count'] = state.get('content_retry_count', 0) + 1
    return state


def should_retry_content(state: MindMapState) -> str:
    """决定内容质量是否需要重试。返回 'pass' 或 'retry'。"""
    score = state.get('content_quality_score', 0)
    threshold = state.get('quality_threshold', 7.0)

    if score >= threshold:
        state['content_retry_count'] = 0  # 重置计数
        return "pass"

    max_retries = state.get('max_content_retries', 3)
    current = state.get('content_retry_count', 0)
    if current >= max_retries:
        logger.warning(f"内容质量重试已达上限 ({max_retries})，按当前结果继续")
        return "pass"

    logger.info(f"🔄 准备第 {current} 次内容重试（最高 {max_retries} 次）")
    return "retry"
