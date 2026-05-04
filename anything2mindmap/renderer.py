import os
import subprocess
import shutil
import logging

from anything2mindmap.state import MindMapState
from anything2mindmap.canvas import build_html

logger = logging.getLogger(__name__)


def find_browser():
    """查找系统可用的浏览器（Edge 或 Chrome）"""
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in edge_paths:
        if os.path.exists(p):
            return p
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for p in chrome_paths:
        if os.path.exists(p):
            return p
    for browser in ["msedge", "chrome", "chromium"]:
        path = shutil.which(browser)
        if path:
            return path
    return None


def canvas_to_pdf(canvas_json, html_path, pdf_path):
    logger.info("🖨️ 使用系统浏览器无头模式打印 PDF ...")

    build_html(canvas_json, html_path)

    browser_path = find_browser()
    if not browser_path:
        raise RuntimeError("未找到可用的 Edge 或 Chrome 浏览器，请安装其中之一。")

    abs_html = os.path.abspath(html_path)
    abs_pdf = os.path.abspath(pdf_path)
    cmd = [
        browser_path,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={abs_pdf}",
        "--no-pdf-header-footer",
        abs_html
    ]
    logger.info(f"执行命令：{' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"浏览器打印失败：{result.stderr}")
        raise RuntimeError(f"PDF 生成失败：{result.stderr}")
    logger.info(f"PDF 已生成 → {pdf_path}")
    return pdf_path


def render_pdf(state: MindMapState) -> MindMapState:
    logger.info("📊 步骤 5/5：渲染 PDF（系统浏览器）")
    output_dir = state['output_dir']
    html_path = os.path.join(output_dir, "mindmap.html")
    pdf_path = os.path.join(output_dir, "output_mindmap.pdf")
    canvas_to_pdf(state['canvas_json'], html_path, pdf_path)
    state['pdf_path'] = pdf_path
    return state
