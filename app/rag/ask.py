from __future__ import annotations

import sys
import re
from llama_cpp import Llama

from app.config import LLM_GGUF_PATH
from app.retrieval.retrieve import retrieve_evidence

"""
RAG 问答核心模块
负责构造 Prompt、调用本地 LLM、管理对话历史。
"""

def _clean_snippet(text: str, max_len: int = 220) -> str:
    """清理并截断文本片段，用于展示"""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) > max_len:
        t = t[:max_len] + "…"
    return t

def build_context_for_llm(evidence, per_doc_max_chars: int = 1200, max_total_chars: int = 6000) -> str:
    """
    将检索到的证据列表转换为 LLM 可读的上下文 Prompt。
    格式示例：
    [Doc1] source=a.pdf, page=1 chunk_id=10 score=0.8
    ...content...
    
    [Doc2] ...
    """
    blocks = []
    total = 0
    for i, e in enumerate(evidence, start=1):
        content = (e["content"] or "").strip()
        content = re.sub(r"\s+\n", "\n", content)

        if len(content) > per_doc_max_chars:
            content = content[:per_doc_max_chars] + "…"

        page = e.get("page")
        page_info = f", page={page}" if page is not None else ""
        
        block = (
            f"[Doc{i}] source={e['filename']}{page_info} "
            f"chunk_id={e['chunk_id']} score={e['score']:.4f}\n{content}"
        )
        if total + len(block) > max_total_chars:
            break
        blocks.append(block)
        total += len(block)

    return "\n\n---\n\n".join(blocks)

def create_llm() -> Llama:
    """
    初始化 llama.cpp 模型实例。
    """
    if not LLM_GGUF_PATH.exists():
        raise FileNotFoundError(f"找不到模型文件: {LLM_GGUF_PATH}")

    # n_ctx=4096: 上下文窗口大小
    # n_threads=8: CPU 推理线程数
    llm = Llama(
        model_path=str(LLM_GGUF_PATH),
        n_ctx=4096,
        n_threads=8,
        verbose=False,
    )
    return llm


def build_system_message() -> dict:
    """构建系统提示词，规定引用格式"""
    return {
        "role": "system",
        "content": (
            "你是一个本地知识库助手，只能根据我提供的资料回答，禁止编造。"
            "【硬性要求】每句话末尾必须标注引用，格式只能是 [1] 或 [2] 或 [1][2]…（对应 Doc 编号）。"
            "如果资料不足，直接回答“资料中没有/不确定”，并同样给出引用（引用最相关的 Doc）。"
            "这是一个多轮对话场景，你需要在保证基于当前轮资料的前提下，结合对话历史保持答案连贯。"
        ),
    }

def answer_once(llm: Llama, query: str, history: list[dict] | None = None, top_k: int = 5) -> tuple[str, list[dict]]:
    """
    执行单次问答交互。
    
    1. 检索 Top K 证据。
    2. 构造 Prompt（System + History + Current User Input with Context）。
    3. 调用 LLM 生成回答。
    
    :return: (回答文本, 证据列表)
    """
    if history is None:
        history = []

    evidence = retrieve_evidence(query, top_k=top_k)
    context = build_context_for_llm(evidence)

    user_content = (
        "下面是当前轮检索到的资料，请严格基于这些资料回答当前问题。"
        "可以参考之前的对话历史以保持上下文连贯，但不得臆造资料。"
        "\n\n资料如下：\n\n"
        f"{context}\n\n当前问题：{query}"
    )

    messages = [build_system_message()]
    messages.extend(history)
    messages.append({"role": "user", "content": user_content})

    out = llm.create_chat_completion(
        messages=messages,
        temperature=0.2, # 低温度以减少幻觉
        max_tokens=512,
    )
    answer = out["choices"][0]["message"]["content"]
    return answer, evidence

def print_answer_and_refs(answer: str, evidence: list[dict]) -> None:
    """格式化打印回答和引用"""
    print("\n=== Answer ===\n")
    print(answer)

    print("\n=== References (Doc 映射与证据) ===\n")
    for i, e in enumerate(evidence, start=1):
        page = e.get("page")
        page_str = f", page={page}" if page is not None else ""
        print(f"[{i}] (Doc{i}) {e['filename']}{page_str} (score={e['score']:.4f}, chunk_id={e['chunk_id']})")
        print(f"    {_clean_snippet(e['content'], 240)}\n")

def run_single_turn(query: str) -> None:
    """单轮命令行模式"""
    llm = create_llm()
    answer, evidence = answer_once(llm, query, history=[])
    print_answer_and_refs(answer, evidence)


def run_chat() -> None:
    """交互式多轮对话模式"""
    print("进入多轮对话模式。输入内容后回车提问，输入 exit/quit 退出。")
    llm = create_llm()
    history: list[dict] = []

    while True:
        try:
            user_input = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            break

        if not user_input:
            continue

        lower = user_input.lower()
        if lower in {"exit", "quit", "q"}:
            print("已退出。")
            break

        answer, evidence = answer_once(llm, user_input, history=history)
        print_answer_and_refs(answer, evidence)

        # 更新历史（仅保留原始问答，不包含庞大的 Context，防止 Prompt 爆炸）
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": answer})


def main():
    if len(sys.argv) < 2:
        run_chat()
        return

    query = " ".join(sys.argv[1:])
    run_single_turn(query)


if __name__ == "__main__":
    main()
