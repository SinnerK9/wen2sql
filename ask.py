"""CLI 端到端入口：python ask.py "问题" → SQL + 校验 + 表格 + 摘要。"""
import argparse

from app import config
from app.answer import answer


def main() -> None:
    ap = argparse.ArgumentParser(description="端到端 Text2SQL 问答")
    ap.add_argument("question", nargs="?", default="上月各城市订单总额")
    args = ap.parse_args()

    result = answer(args.question)

    print(f"问题: {result['question']}")
    print("-" * 50)

    if not result["success"]:
        print("[失败]")
        for e in result["errors"]:
            print(f"  - {e}")
        return

    print("[生成 SQL]")
    print(result["sql"])
    if result["brief"]:
        print(f"说明: {result['brief']}")
    if result["chart_type"]:
        print(f"建议图表: {result['chart_type']}")
    print("-" * 50)
    print("[校验] 通过")
    print("-" * 50)

    res = result["result"]
    print("[结果] 列: " + ", ".join(res.columns))
    for row in res.rows[:10]:
        print("  " + " | ".join(str(v) for v in row))
    if res.truncated:
        print(f"[截断] 仅显示前 {len(res.rows)} 行, 总行数 {res.total}")
    print("-" * 50)
    print(f"[摘要] {result['summary']}")

    if config.EXEC_ENGINE == "stub":
        print("[stub 模式] 当前执行段返回假数据，仅用于链路联调")


if __name__ == "__main__":
    main()
