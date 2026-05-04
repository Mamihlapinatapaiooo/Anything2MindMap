import argparse
import os

from anything2mindmap.state import make_initial_state
from anything2mindmap.graph import build_workflow


def main():
    parser = argparse.ArgumentParser(
        description="从任意文本/代码生成思维导图（Canvas + PDF）"
    )
    parser.add_argument(
        "file_path",
        help="输入路径（.docx / .txt / .pdf 文件或目录）"
    )
    parser.add_argument(
        "-p", "--prompt", default="",
        help="用户对提取的补充说明（如'只分析第三章'、'聚焦认证模块'）"
    )
    parser.add_argument(
        "--output-dir", default="./outputs",
        help="输出目录（默认 ./outputs）"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3,
        help="布局重试最大次数（默认 3）"
    )
    parser.add_argument(
        "--level-gap", type=int, default=250,
        help="层级水平间距（默认 250）"
    )
    parser.add_argument(
        "--min-y-gap", type=int, default=20,
        help="兄弟节点垂直间距（默认 20）"
    )
    parser.add_argument(
        "--include", default="",
        help="目录模式下匹配的文件扩展名，逗号分隔（如 '.py,.md'，默认涵盖大部分代码/文本类型）"
    )
    parser.add_argument(
        "--max-quality-retries", type=int, default=3,
        help="内容质量重试最大次数（默认 3）"
    )
    parser.add_argument(
        "--quality-threshold", type=float, default=7.0,
        help="内容质量通过阈值 0-10（默认 7.0）"
    )
    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        print(f"❌ 路径不存在: {args.file_path}")
        return

    is_dir = os.path.isdir(args.file_path)
    os.makedirs(args.output_dir, exist_ok=True)

    custom_prompt = ""
    if args.prompt.strip():
        from anything2mindmap.loader import _load_document_text, _load_directory_text
        from anything2mindmap.prompt_builder import run_prompt_refinement

        try:
            if is_dir:
                print(f"\n📁 检测到目录，正在扫描...")
                doc_text, file_list = _load_directory_text(args.file_path, args.include)
                print(f"   共 {len(file_list)} 个文件，总字符数 {len(doc_text)}")
                print("📝 正在根据您的要求生成定制提取提示词...")
                custom_prompt = run_prompt_refinement(doc_text, args.prompt.strip())
            else:
                print(f"\n📄 正在加载文档: {args.file_path}")
                doc_text = _load_document_text(args.file_path)
                print(f"   字符数：{len(doc_text)}")
                print("📝 正在根据您的要求生成定制提取提示词...")
                custom_prompt = run_prompt_refinement(doc_text, args.prompt.strip())
        except RuntimeError as e:
            print(f"\n❌ {e}")
            return

    state = make_initial_state(
        file_path=args.file_path,
        level_gap=args.level_gap,
        min_y_gap=args.min_y_gap,
        max_retries=args.max_retries,
        output_dir=args.output_dir,
        custom_message=args.prompt.strip(),
        custom_prompt=custom_prompt,
        include_exts=args.include,
        max_content_retries=args.max_quality_retries,
        quality_threshold=args.quality_threshold,
    )

    print("\n🚀 开始执行思维导图自动生成流水线...")
    app = build_workflow()
    final_state = app.invoke(state)

    print("\n🎉 流水线执行完毕！输出文件：")
    print(f"  1. LLM 摘要树  → {os.path.join(args.output_dir, 'mindmap_tree.json')}")
    print(f"  2. Obsidian Canvas → {os.path.join(args.output_dir, 'mindmap.canvas')}")
    print(f"  3. 浏览器渲染的 PDF → {os.path.join(args.output_dir, 'output_mindmap.pdf')}")


if __name__ == "__main__":
    main()
