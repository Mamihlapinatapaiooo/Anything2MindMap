import json
import logging

from langgraph.graph import StateGraph, END

from anything2mindmap.state import MindMapState
from anything2mindmap.loader import load_document
from anything2mindmap.extractor import extract_structure
from anything2mindmap.content_reviewer import evaluate_content, should_retry_content
from anything2mindmap.layout import evaluate_layout
from anything2mindmap.canvas import generate_canvas
from anything2mindmap.renderer import render_pdf

logger = logging.getLogger(__name__)


def evaluate_and_retry(state: MindMapState) -> MindMapState:
    state = evaluate_layout(state)
    if state['layout_feedback'] == "OK":
        return state
    advice = json.loads(state['layout_feedback'])
    state['level_gap'] = advice.get('level_gap', 250)
    state['min_y_gap'] = advice.get('min_y_gap', 20)
    logger.info(
        f"🔄 新布局参数：level_gap={state['level_gap']}, min_y_gap={state['min_y_gap']}")
    return state


def should_retry(state: MindMapState) -> str:
    if state['layout_feedback'] == "OK":
        return "render"
    if state.get('retry_count', 0) >= state.get('max_retries', 3):
        logger.warning("已达到最大重试次数，强制渲染")
        return "render"
    return "regenerate"


def build_workflow():
    workflow = StateGraph(MindMapState)

    workflow.add_node("load_document", load_document)
    workflow.add_node("extract_structure", extract_structure)
    workflow.add_node("evaluate_content", evaluate_content)
    workflow.add_node("generate_canvas", generate_canvas)
    workflow.add_node("evaluate_and_retry", evaluate_and_retry)
    workflow.add_node("render_pdf", render_pdf)

    workflow.set_entry_point("load_document")
    workflow.add_edge("load_document", "extract_structure")
    workflow.add_edge("extract_structure", "evaluate_content")

    workflow.add_conditional_edges(
        "evaluate_content",
        should_retry_content,
        {
            "pass": "generate_canvas",
            "retry": "extract_structure",
        }
    )

    workflow.add_edge("generate_canvas", "evaluate_and_retry")

    workflow.add_conditional_edges(
        "evaluate_and_retry",
        should_retry,
        {
            "regenerate": "generate_canvas",
            "render": "render_pdf"
        }
    )
    workflow.add_edge("render_pdf", END)

    return workflow.compile()
