"""CLI:python -m app.validate "SQL" → 校验结果(读 config 的 schema.json)。"""
import argparse
import json

from app import config
from .validator import validate


def main() -> None:
    ap = argparse.ArgumentParser(description="sqlglot 硬校验")
    ap.add_argument("sql")
    args = ap.parse_args()

    tables = json.loads(config.SCHEMA_JSON.read_text(encoding="utf-8"))["tables"]
    ok, errors, final = validate(args.sql, tables, dialect=config.DB_DIALECT)
    print("[通过]" if ok else "[拦截]")
    for e in errors:
        print("  -", e)
    if final != args.sql:
        print("改写后:", final)


if __name__ == "__main__":
    main()
