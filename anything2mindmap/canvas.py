import json
import os
import logging

from anything2mindmap.state import MindMapState
from anything2mindmap.layout import assign_positions

logger = logging.getLogger(__name__)


def generate_canvas(state: MindMapState) -> MindMapState:
    level_gap = state.get('level_gap', 250)
    min_y_gap = state.get('min_y_gap', 20)
    logger.info(f"🎨 步骤 3/5：生成 Canvas（gap={level_gap}, y_gap={min_y_gap}）")
    canvas = assign_positions(state['mindmap_tree'], x=0, y=0,
                              level_gap=level_gap, min_y_gap=min_y_gap)
    state['canvas_json'] = canvas
    output_path = os.path.join(state['output_dir'], "mindmap.canvas")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(canvas, f, ensure_ascii=False, indent=2)
    logger.info(f"Canvas 已保存 → mindmap.canvas（节点数：{len(canvas['nodes'])}）")
    return state


def build_html(canvas_json, output_path):
    """根据 Canvas JSON 生成 Obsidian 风格的 HTML 文件"""
    nodes = canvas_json["nodes"]
    edges = canvas_json["edges"]

    all_x = [n["x"] for n in nodes] + [n["x"] + n["width"] for n in nodes]
    all_y = [n["y"] for n in nodes] + [n["y"] + n["height"] for n in nodes]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    canvas_w = max_x - min_x + 200
    canvas_h = max_y - min_y + 200

    node_divs = []
    for i, node in enumerate(nodes):
        left = node["x"] - min_x + 100
        top = node["y"] - min_y + 100
        w, h = node["width"], node["height"]
        hue = (i * 37) % 360
        bg = f"hsl({hue}, 70%, 90%)"
        border = f"hsl({hue}, 60%, 60%)"
        node_divs.append(
            f'<div class="card" style="left:{left}px; top:{top}px; width:{w}px; height:{h}px; '
            f'background:{bg}; border-color:{border};">'
            f'<span>{node["text"]}</span></div>'
        )

    svg_edges = []
    node_pos = {n["id"]: (n["x"] - min_x + 100, n["y"] - min_y + 100,
                          n["width"], n["height"]) for n in nodes}
    for edge in edges:
        fid, tid = edge["fromNode"], edge["toNode"]
        if fid not in node_pos or tid not in node_pos:
            continue
        fx, fy, fw, fh = node_pos[fid]
        tx, ty, tw, th = node_pos[tid]
        x1, y1 = fx + fw, fy + fh / 2
        x2, y2 = tx, ty + th / 2
        mx = (x1 + x2) / 2
        d = f"M {x1},{y1} Q {mx},{y1} {mx},{(y1+y2)/2} Q {mx},{y2} {x2},{y2}"
        svg_edges.append(
            f'<path d="{d}" fill="none" stroke="#555" stroke-width="1.8" opacity="0.7" />'
        )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{
      size: {canvas_w * 0.75}pt {canvas_h * 0.75}pt;
      margin: 0;
  }}
  body {{
      margin: 0; padding: 0;
      font-family: 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS', sans-serif;
      background: #ffffff;
  }}
  .canvas {{
      position: relative;
      width: {canvas_w}px;
      height: {canvas_h}px;
  }}
  .card {{
      position: absolute;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 10px;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
      border: 1.5px solid;
      padding: 8px;
      box-sizing: border-box;
      text-align: center;
      font-size: 14px;
      color: #222;
      overflow: hidden;
      word-break: break-word;
      background-clip: padding-box;
  }}
  .card span {{
      line-height: 1.3;
  }}
  svg {{
      position: absolute;
      top: 0; left: 0;
      width: {canvas_w}px;
      height: {canvas_h}px;
      pointer-events: none;
  }}
</style>
</head>
<body>
<div class="canvas">
    <svg xmlns="http://www.w3.org/2000/svg">
        {''.join(svg_edges)}
    </svg>
    {''.join(node_divs)}
</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"HTML 已保存 → {output_path}")
    return canvas_w, canvas_h
