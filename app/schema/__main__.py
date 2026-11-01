"""CLI:python -m app.schema → 抽/刷新 schema.json(MySQL 优先,文件回退)"""
import argparse

from app import config
from .extract import ensure_schema_json


def main() -> None:
    ap = argparse.ArgumentParser(description="抽取 schema → schema.json")
    # 如果命令行里包含了-f 或--force，args.force 的值就会被设为 True；否则默认为 False。
    ap.add_argument("-f", "--force", action="store_true", help="强制重抽,忽略缓存")
    args = ap.parse_args()
    # 用户申请强制刷新，则删除旧缓存，更新schema.json
    if args.force and config.SCHEMA_JSON.exists():
        config.SCHEMA_JSON.unlink()

    mysql = dict(host=config.MYSQL_HOST, port=config.MYSQL_PORT,
                 user=config.MYSQL_USER,password=config.MYSQL_PASSWORD, db=config.MYSQL_DB)
    data = ensure_schema_json(mysql, config.SCHEMA_SQL, config.SCHEMA_JSON)
    print(f"schema.json: {len(data['tables'])} 张表")
    print("表:", ", ".join(data["tables"].keys()))

if __name__ == "__main__":
    main()