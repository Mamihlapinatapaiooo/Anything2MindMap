import os
import logging
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, TextLoader

from anything2mindmap.state import MindMapState

logger = logging.getLogger(__name__)

# ----- directory scan config -----

DEFAULT_INCLUDE_EXTS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.vue', '.svelte',
    '.md', '.txt', '.pdf', '.rst', '.mdx',
    '.rs', '.go', '.java', '.c', '.h', '.cpp', '.hpp', '.cs', '.swift', '.kt',
    '.css', '.scss', '.less', '.html', '.xml', '.svg',
    '.json', '.yaml', '.yml', '.toml', '.cfg', '.ini',
    '.sh', '.bash', '.zsh', '.ps1', '.bat',
    '.sql', '.graphql', '.proto',
    '.r', '.rmd', '.tex',
}

SKIP_DIRS = {
    '__pycache__', '.venv', 'venv', 'env', '.env',
    'node_modules', '.git', '.svn', '.hg',
    'dist', 'build', 'target', 'out',
    '.egg-info', '.mypy_cache', '.pytest_cache', '.ruff_cache', '.tox',
    'inputs', 'outputs',
}

SKIP_FILES = {
    '.DS_Store', 'Thumbs.db',
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'uv.lock', 'poetry.lock', 'Pipfile.lock',
    '.eslintcache',
}

MAX_CHARS_TOTAL = 100_000
MAX_FILES = 500

# ----- single file loader -----

def _load_document_text(file_path: str) -> str:
    """加载单个文档并返回纯文本（不依赖 state）。"""
    if file_path.endswith('.docx'):
        loader = Docx2txtLoader(file_path)
        docs = loader.load()
        return '\n'.join([d.page_content for d in docs])
    elif file_path.endswith('.pdf'):
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n'.join(text_parts)
    else:
        loader = TextLoader(file_path, encoding='utf-8')
        docs = loader.load()
        return '\n'.join([d.page_content for d in docs])


# ----- directory loader -----

def _parse_extensions(spec: str) -> set[str]:
    """将逗号分隔的扩展名列表转为集合。空串返回默认集合。"""
    if not spec.strip():
        return DEFAULT_INCLUDE_EXTS
    exts = set()
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        if not part.startswith('.'):
            part = '.' + part
        exts.add(part)
    return exts


def _is_binary(file_path: str) -> bool:
    """快速检测文件是否为二进制（读取开头 1024 字节）。PDF 视为文本。"""
    if file_path.lower().endswith('.pdf'):
        return False
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
        # 常见文本编码不会出现 null 字节
        return b'\x00' in chunk
    except OSError:
        return True


def _load_directory_text(directory: str, include_exts: str) -> tuple[str, list[str]]:
    """递归扫描目录，返回 (格式化后的文本, 文件路径列表)。

    返回值中文本格式：
        ### relative/path.py
        <文件内容>

        ### relative/path2.py
        <文件内容>

    三层防御：
        1. 文件数 > MAX_FILES 则报错
        2. 总字符 > MAX_CHARS_TOTAL 则截断并标记
        3. 单个文件读取失败则跳过并日志
    """
    root = Path(directory).resolve()
    exts = _parse_extensions(include_exts)

    # 收集所有匹配文件
    all_files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过黑名单目录
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        rel_dir = Path(dirpath).relative_to(root)
        for fname in sorted(filenames):
            if fname in SKIP_FILES:
                continue
            fpath = Path(dirpath) / fname
            suffix = fpath.suffix.lower()
            # 无后缀但文件名全大写匹配 (如 Dockerfile, Makefile)
            if not suffix and fname.upper() not in {'DOCKERFILE', 'MAKEFILE'}:
                continue
            if suffix not in exts and fname != 'Dockerfile' and fname != 'Makefile':
                continue
            all_files.append(fpath)

    if len(all_files) > MAX_FILES:
        raise RuntimeError(
            f"目录过于庞大（包含 {len(all_files)} 个匹配文件，超过上限 {MAX_FILES}）。\n"
            f"建议：\n"
            f"  1. 使用 -p 参数限定分析范围\n"
            f"  2. 单独分析某个子目录\n"
            f"  3. 使用 --include 缩小文件类型范围"
        )

    if not all_files:
        raise RuntimeError(f"目录中未找到可分析的文件（扩展名: {sorted(exts)}）")

    # 读取文件内容
    file_list: list[str] = []
    chunks: list[tuple[str, str]] = []  # (rel_path, content)
    total_chars = 0

    for fpath in all_files:
        rel_path = str(fpath.relative_to(root)).replace('\\', '/')
        file_list.append(rel_path)

        if _is_binary(str(fpath)):
            logger.info(f"  ✗ {rel_path}  (二进制，已跳过)")
            continue

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, OSError) as e:
            logger.info(f"  ✗ {rel_path}  (读取失败: {e})")
            continue

        # 单文件截断在最后统一处理，先收集
        char_count = len(content)
        total_chars += char_count
        logger.info(f"  ✓ {rel_path}  ({char_count} 字符)")
        chunks.append((rel_path, content))

    # 构建格式化文本
    lines: list[str] = []
    # 目录结构概览
    lines.append("## 目录结构")
    _append_tree(lines, root, [str(f.relative_to(root)).replace('\\', '/') for f in all_files])

    # 文件内容
    lines.append("")
    char_used = sum(len(l) + 1 for l in lines)  # initial overhead
    omitted: list[str] = []
    full_files: list[str] = []

    for rel_path, content in chunks:
        header = f"\n### {rel_path}\n"
        body = content
        block = header + body
        if char_used + len(block) <= MAX_CHARS_TOTAL:
            lines.append(header)
            lines.append(body)
            char_used += len(block)
            full_files.append(rel_path)
        else:
            # 尝试截断：只保留文件头部
            remaining = MAX_CHARS_TOTAL - char_used - 200  # 留 200 给截断标记
            if remaining > 500:
                truncated_body = body[:remaining] + f"\n\n... （文件已截断，原文件 {len(body)} 字符）"
                truncated_block = header + truncated_body
                lines.append(header)
                lines.append(truncated_body)
                char_used += len(truncated_block)
                omitted.append(f"{rel_path}  (截断: {len(body)} → {remaining} 字符)")
            else:
                omitted.append(f"{rel_path}  (省略: {len(body)} 字符)")

    if omitted:
        lines.append("\n--- 以下文件因超出上下文限制被省略或截断 ---")
        for item in omitted:
            lines.append(f"# {item}")

    return '\n'.join(lines), file_list


def _append_tree(lines: list[str], root: Path, rel_paths: list[str]):
    """生成缩进目录树。"""
    # 构建路径集合用于判断目录
    path_set = set(rel_paths)
    # 提取所有涉及目录
    dirs: set[str] = set()
    for p in rel_paths:
        parts = p.split('/')
        for i in range(len(parts) - 1):
            dirs.add('/'.join(parts[:i+1]) + '/')

    # 按层级排序输出
    sorted_all = sorted(set(list(dirs) + rel_paths))
    entries: list[str] = []
    for p in rel_paths:
        entries.append(('file', p))
    for d in sorted(dirs):
        entries.append(('dir', d))
    # 按路径排序，文件优先于目录
    entries.sort(key=lambda x: x[1])

    for kind, path in sorted(entries):
        depth = path.count('/')
        indent = '    ' * depth
        if kind == 'dir':
            name = path.rstrip('/').split('/')[-1] + '/'
            lines.append(f"{indent}{name}")
        else:
            name = path.split('/')[-1]
            # 估算行数和大小
            size_hint = ''
            # 如果从 chunks 有数据可加，这里简化处理
            lines.append(f"{indent}{name}{size_hint}")


# ----- pipeline node -----

def load_document(state: MindMapState) -> MindMapState:
    file_path = state['file_path']
    include_exts = state.get('include_exts', '')
    logger.info(f"📄 步骤 1/5：读取 → {file_path}")

    if os.path.isdir(file_path):
        logger.info(f"📁 检测到目录，开始扫描...")
        text, file_list = _load_directory_text(file_path, include_exts)
        state['raw_text'] = text
        state['file_list'] = file_list
    else:
        state['raw_text'] = _load_document_text(file_path)
        state['file_list'] = [os.path.basename(file_path)]

    logger.info(f"加载完成，字符数：{len(state['raw_text'])}，文件数：{len(state['file_list'])}")
    return state
