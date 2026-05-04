import json
import uuid
import logging

from anything2mindmap.state import MindMapState
from anything2mindmap.config import llm, LAYOUT_EVAL_PROMPT

logger = logging.getLogger(__name__)


def assign_positions(
    tree: dict,
    x: float = 0,
    y: float = 0,
    level_gap: float = 250,
    min_y_gap: float = 20,
    min_node_height: float = 60,
    node_width: float = 200
):
    nodes, edges = [], []

    def subtree_h(node):
        children = node.get("children", [])
        if not children:
            return min_node_height
        total = 0
        for c in children:
            total += subtree_h(c)
        total += min_y_gap * (len(children) - 1)
        return total

    def _walk(node, x, y, parent_id=None, allocated=None):
        h = subtree_h(node)
        if allocated is None:
            allocated = h
        center_y = y + allocated / 2
        nx, ny = x, center_y - min_node_height / 2

        nid = str(uuid.uuid4())[:8]
        nodes.append({
            "id": nid,
            "type": "text",
            "text": node["title"],
            "x": nx,
            "y": ny,
            "width": node_width,
            "height": min_node_height
        })
        if parent_id:
            edges.append({
                "id": str(uuid.uuid4())[:8],
                "fromNode": parent_id,
                "toNode": nid,
                "fromSide": "right",
                "toSide": "left"
            })

        children = node.get("children", [])
        if not children:
            return
        child_y = y
        for c in children:
            ch = subtree_h(c)
            _walk(c, x + level_gap, child_y, nid, allocated=ch)
            child_y += ch + min_y_gap

    total_h = subtree_h(tree)
    _walk(tree, x, y, allocated=total_h)
    return {"nodes": nodes, "edges": edges}


def check_overlap(nodes, threshold=0.5):
    overlaps = []
    for i in range(len(nodes)):
        a = nodes[i]
        ax1, ay1 = a["x"], a["y"]
        ax2, ay2 = a["x"] + a["width"], a["y"] + a["height"]
        for j in range(i + 1, len(nodes)):
            b = nodes[j]
            bx1, by1 = b["x"], b["y"]
            bx2, by2 = b["x"] + b["width"], b["y"] + b["height"]
            ix1, ix2 = max(ax1, bx1), min(ax2, bx2)
            iy1, iy2 = max(ay1, by1), min(ay2, by2)
            if ix1 < ix2 and iy1 < iy2:
                overlap_area = (ix2 - ix1) * (iy2 - iy1)
                area_a = (ax2 - ax1) * (ay2 - ay1)
                area_b = (bx2 - bx1) * (by2 - by1)
                min_area = min(area_a, area_b)
                if min_area > 0 and overlap_area / min_area > threshold:
                    overlaps.append((a["id"], b["id"], overlap_area))
    return overlaps


def evaluate_layout(state: MindMapState) -> MindMapState:
    logger.info("🔍 评估布局质量...")
    canvas = state['canvas_json']
    nodes = canvas['nodes']
    overlaps = check_overlap(nodes)
    if not overlaps:
        logger.info("✅ 无重叠")
        state['layout_feedback'] = "OK"
        state['retry_count'] = 0
        return state

    logger.warning(f"⚠️ 发现 {len(overlaps)} 对重叠，交由 LLM 分析...")
    nodes_info = json.dumps(nodes[:20], ensure_ascii=False, indent=2)
    overlap_str = "\n".join(
        [f"{a} <-> {b} (面积={o:.1f})" for a, b, o in overlaps[:10]]
    )
    prompt = LAYOUT_EVAL_PROMPT.format(
        nodes_info=nodes_info, overlaps=overlap_str)

    try:
        resp = llm.invoke(prompt)
        content = resp.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        advice = json.loads(content)
        state['layout_feedback'] = json.dumps(advice, ensure_ascii=False)
        logger.info(f"💡 LLM 建议：{advice}")
    except Exception as e:
        logger.error(f"评估失败：{e}，使用默认缓解参数")
        state['layout_feedback'] = json.dumps({
            "reason": "评估失败",
            "level_gap": 300,
            "min_y_gap": 50
        }, ensure_ascii=False)

    state['retry_count'] = state.get('retry_count', 0) + 1
    return state
