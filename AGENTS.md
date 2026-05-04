# AGENTS.md

## Setup & run

```bash
# uv is the package manager (uv.lock present)
uv sync

# Required: create .env with DeepSeek API key
echo "DEEPSEEK_API_KEY=sk-..." > .env

# Create working directories (gitignored, not tracked)
mkdir inputs outputs

# Place a .docx or .txt file in inputs/, or point to a directory, then run:
uv run python -m anything2mindmap ./inputs/your_file.docx

# Or via the script entrypoint:
uv run anything2mindmap ./inputs/your_file.docx --output-dir ./my_outputs

# Directory analysis (recursively scans code/docs):
uv run anything2mindmap ./src/my_project -p "分析架构" --include ".py,.md"

# With custom extraction prompt (interactive refinement):
uv run anything2mindmap ./inputs/your_file.docx -p "只分析第三章，聚焦技术架构"
```

## Architecture

- **Package**: `anything2mindmap/` — generates mindmap Canvas/PDF from documents or code directories via LLM extraction.
- **Input**: Single file (`.docx`/`.txt`) or directory (recursive scan, auto-skip `.venv`/`node_modules`/`.git`/etc.).
- **LangGraph pipeline**: `load_document → extract_structure → evaluate_content → generate_canvas → evaluate_and_retry → render_pdf`
  - `evaluate_content` may loop back to `extract_structure` (up to `--max-quality-retries`, default 3) if the content quality falls below `--quality-threshold` (default 7.0/10). A separate LLM "judge" scores the mindmap tree on 5 dimensions (coverage, logic, balance, accuracy, conciseness) and provides specific improvement feedback.
  - `evaluate_and_retry` may loop back to `generate_canvas` (up to `--max-retries`, default 3) if the LLM detects node overlaps.
- **LLM**: DeepSeek `deepseek-v4-pro` via `langchain-openai` with base URL `https://api.deepseek.com`.
- **PDF rendering**: Generates HTML, then prints to PDF via headless browser (Edge or Chrome). `find_browser()` has Windows-hardcoded paths; macOS/Linux fall back to `shutil.which`.
- **Custom prompt**: When `-p` is provided, the system loads the document, calls the LLM to generate a tailored extraction prompt, then enters an interactive loop where the user can accept/edit/regenerate the prompt before the pipeline runs.

### Module map

```
anything2mindmap/
├── __init__.py       # package marker
├── state.py          # MindMapState TypedDict + make_initial_state()
├── config.py         # logging, LLM instance, prompts
├── loader.py         # load_document(), _load_document_text()
├── extractor.py      # extract_structure()
├── content_reviewer.py # evaluate_content(), should_retry_content()
├── layout.py         # assign_positions(), check_overlap(), evaluate_layout()
├── canvas.py         # generate_canvas(), build_html()
├── renderer.py       # find_browser(), canvas_to_pdf(), render_pdf()
├── prompt_builder.py # generate_initial_prompt(), run_prompt_refinement()
├── graph.py          # retry logic + build_workflow() → compiled StateGraph
└── __main__.py       # argparse CLI entrypoint
```

Dependencies flow: `state → config → {loader, extractor, layout, prompt_builder, content_reviewer} → canvas → renderer → graph → __main__` (no cycles).

## CLI

```
uv run python -m anything2mindmap <file_path> [--output-dir DIR] [--max-retries N] [--max-quality-retries N] [--quality-threshold F] [--level-gap N] [--min-y-gap N] [-p MESSAGE] [--include EXTS]
```

## Conventions

- Python 3.12+ only (`.python-version`).
- No tests, no CI, no lint/formatter config, no pre-commit hooks.
- `inputs/` and `outputs/` are gitignored; expect to create them on first run.
- Input text is truncated to 100,000 characters before sending to the LLM.
- Directory scanning auto-skips `.venv`, `node_modules`, `__pycache__`, `.git`, `dist`, `build`, etc.
- File count > 500 triggers a direct error suggesting a narrower scope.
- Content quality is evaluated by a GAN-style judge LLM scoring 5 dimensions; extractor retries with specific feedback when below threshold.
