import argparse
from app import config
from .json_parse import extract_json
from .prompt import build_prompt, format_m_schema, _clean_comment
from .client import chat
from ..schema.extract import ensure_schema_json

def main() -> None:
    ap = argparse.ArgumentParser(description="LLM 生成 SQL(返回 JSON)")
    ap.add_argument("question", nargs="?", default="上月各城市订单总额")
    args = ap.parse_args()

    schema = ensure_schema_json({"host": config.MYSQL_HOST, "port": config.MYSQL_PORT,
           "user": config.MYSQL_USER, "password": config.MYSQL_PASSWORD,
           "db": config.MYSQL_DB},config.SCHEMA_SQL, config.SCHEMA_JSON)
    prompt = build_prompt(args.question,format_m_schema(schema))
    raw = chat(prompt, mode = config.LLM_MODE, base_url=config.LLM_BASE_URL,
               api_key=config.LLM_API_KEY, model=config.LLM_MODEL, temperature=config.LLM_TEMPERATURE)
    obj = extract_json(raw)
    if obj is None:
        print("解析失败,LLM 原始输出:\n", raw)
        return
    print("解析结果:", obj)


if __name__ == "__main__":
    main()