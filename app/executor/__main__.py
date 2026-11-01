"""CLI:python -m app.executor "SQL" → 校验后执行并展示结果表格。"""

import argparse
from .executor import execute

def main() -> None:
    ap = argparse.ArgumentParser(description="给出SQL进行最终执行")
    ap.add_argument("sql", nargs="?", default="SELECT * FROM orders LIMIT 5")
    args = ap.parse_args()

    try:
        result = execute(args.sql)
    except ValueError as e:
        print(f"[失败] {e}")
        return
    except Exception as e:
        print(f"[失败] 执行出错: {type(e).__name__}: {e}")
        return

    print("[通过]")
    print("列:", ", ".join(result.columns))
    print(f"行数: {len(result.rows)}")
    if result.truncated:
        print(f"[截断] 仅显示前 {len(result.rows)} 行, 总行数 {result.total}")
    for row in result.rows[:10]:
        print(row)

if __name__ == "__main__":
    main()

