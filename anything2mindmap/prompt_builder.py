import sys
import logging

from anything2mindmap.config import llm, PROMPT_GENERATOR_TEMPLATE, PROMPT_REFINE_TEMPLATE

logger = logging.getLogger(__name__)


def generate_initial_prompt(doc_text: str, user_message: str) -> str:
    """调用 LLM 根据文档摘要和用户原始要求全新生成提取提示词。"""
    logger.info("📝 正在全新生成提取提示词...")
    summary = doc_text[:5000]
    try:
        resp = llm.invoke(PROMPT_GENERATOR_TEMPLATE.format(
            document_summary=summary,
            user_message=user_message,
        ))
        prompt = resp.content.strip()
        logger.info("提示词生成完成")
        return prompt
    except Exception as e:
        logger.error(f"提示词生成失败：{e}，回退到默认提示词")
        from anything2mindmap.config import EXTRACT_PROMPT
        return EXTRACT_PROMPT.replace("{text}", "")


def refine_prompt(current_prompt: str, user_feedback: str) -> str:
    """根据用户反馈在当前提示词基础上进行定向修改，不从头生成。"""
    logger.info("🔧 正在根据反馈微调提示词...")
    try:
        resp = llm.invoke(PROMPT_REFINE_TEMPLATE.format(
            current_prompt=current_prompt,
            user_feedback=user_feedback,
        ))
        prompt = resp.content.strip()
        logger.info("提示词微调完成")
        return prompt
    except Exception as e:
        logger.error(f"提示词微调失败：{e}，保持当前提示词不变")
        return current_prompt


def read_multiline() -> str:
    """读取多行输入，以 /END 单独一行结束。返回拼接后的字符串。"""
    print('（输入 /END 单独一行结束）')
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "/END":
            break
        lines.append(line)
    return "\n".join(lines)


def run_prompt_refinement(doc_text: str, user_message: str) -> str:
    """交互式提示词优化循环。用户必须显式按 a 接受才能进入流水线。"""
    prompt = generate_initial_prompt(doc_text, user_message)

    while True:
        print()
        print("─" * 60)
        print(prompt)
        print("─" * 60)
        print()
        choice = input("操作: [a]接受  [e]提意见微调  [r]LLM重新生成  [w]手动重写  [q]退出 > ").strip().lower()

        if choice == 'a':
            print("✅ 已确认提示词，开始执行流水线...")
            return prompt

        elif choice == 'e':
            print("\n请输入修改意见（描述你想怎么改当前提示词）：")
            feedback = read_multiline()
            if not feedback.strip():
                print("未输入修改意见，保持当前提示词不变。")
                continue
            print("🔧 根据反馈微调中...")
            prompt = refine_prompt(prompt, feedback)

        elif choice == 'r':
            print("🔄 正在根据文档全新生成...")
            prompt = generate_initial_prompt(doc_text, user_message)

        elif choice == 'w':
            print("\n请直接输入完整的新提示词：")
            new_prompt = read_multiline()
            if new_prompt.strip():
                prompt = new_prompt
                print("✅ 提示词已替换为手动输入版本。")
            else:
                print("未输入内容，保持当前提示词不变。")

        elif choice == 'q':
            print("👋 已退出。")
            sys.exit(0)

        else:
            print(f"未知操作: {choice}，请输入 a / e / r / w / q")
