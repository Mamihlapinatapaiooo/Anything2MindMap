from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict


class MindMapState(TypedDict):
    raw_text: str
    chunks: List[str]
    mindmap_tree: Dict[str, Any]
    canvas_json: Dict[str, Any]
    pdf_path: Optional[str]
    file_path: str
    file_list: List[str]
    retry_count: int
    max_retries: int
    layout_feedback: str
    level_gap: int
    min_y_gap: int
    output_dir: str
    custom_message: str
    custom_prompt: str
    include_exts: str
    content_quality_score: float
    content_feedback: str
    content_retry_count: int
    max_content_retries: int
    quality_threshold: float


def make_initial_state(
    file_path: str,
    level_gap: int = 250,
    min_y_gap: int = 20,
    max_retries: int = 3,
    output_dir: str = "./outputs",
    custom_message: str = "",
    custom_prompt: str = "",
    include_exts: str = "",
    max_content_retries: int = 3,
    quality_threshold: float = 7.0,
) -> MindMapState:
    return {
        "raw_text": "",
        "chunks": [],
        "mindmap_tree": {},
        "canvas_json": {},
        "pdf_path": None,
        "file_path": file_path,
        "file_list": [],
        "retry_count": 0,
        "max_retries": max_retries,
        "layout_feedback": "",
        "level_gap": level_gap,
        "min_y_gap": min_y_gap,
        "output_dir": output_dir,
        "custom_message": custom_message,
        "custom_prompt": custom_prompt,
        "include_exts": include_exts,
        "content_quality_score": 0.0,
        "content_feedback": "",
        "content_retry_count": 0,
        "max_content_retries": max_content_retries,
        "quality_threshold": quality_threshold,
    }
