from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import should_use_code_gen, should_use_exercise_gen, normalize_followup
from src.ingest import split_text


def test_router():
    assert should_use_code_gen("请用 C++ 实现单链表逆置")
    assert not should_use_code_gen("什么是栈？它有哪些基本操作？")
    assert should_use_exercise_gen("根据知识库生成几道选择题和填空题")


def test_followup():
    context = [{"role": "user", "content": "什么是快速排序？"}]
    rewritten = normalize_followup("它的时间复杂度是多少？", context)
    assert "快速排序" in rewritten


def test_split_text():
    chunks = split_text("栈是一种后进先出的线性表。" * 100, chunk_size=80, overlap=10)
    assert len(chunks) > 1


if __name__ == "__main__":
    test_router()
    test_followup()
    test_split_text()
    print("smoke tests passed")
