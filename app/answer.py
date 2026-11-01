"""编排五段管线：schema → prompt → LLM → validate → execute → summary。"""
import json

from app import config
from app.schema.extract import ensure_schema_json
from app.llm.prompt import format_m_schema, build_prompt
from app.llm.client import chat
from app.llm.json_parse import extract_json
from app.validate.validator import validate
from app.executor.executor import execute
from app.summary import summarize


def answer(question: str) -> dict:
    """问题 → 五段管线 → 结果 dict。

    返回字段：question / success / sql / brief / chart_type / errors /
              final_sql / result / summary。任何情况都返回 dict，不抛异常。
    """
    result_dict = {
        "question": question,
        "success": False,
        "sql": None,
        "brief": None,
        "chart_type": None,
        "errors": [],
        "final_sql": None,
        "result": None,
        "summary": "生成失败",
    }

    try:
        mysql = {
            "host": config.MYSQL_HOST,
            "port": config.MYSQL_PORT,
            "user": config.MYSQL_USER,
            "password": config.MYSQL_PASSWORD,
            "db": config.MYSQL_DB,
        }
        schema = ensure_schema_json(mysql, config.SCHEMA_SQL, config.SCHEMA_JSON)

        knowledge = json.loads(config.KNOWLEDGE_JSON.read_text(encoding="utf-8"))
        prompt = build_prompt(
            question,
            format_m_schema(schema),
            terms="\n".join(knowledge.get("terms", [])),
            business_rules="\n".join(knowledge.get("business_rules", [])),
            examples="\n".join(knowledge.get("examples", [])),
        )

        raw = chat(
            prompt,
            mode=config.LLM_MODE,
            base_url=config.LLM_BASE_URL,
            api_key=config.LLM_API_KEY,
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
        )
        obj = extract_json(raw)
        if obj is None:
            result_dict["errors"].append("LLM 输出解析失败")
            return result_dict
        if not obj.get("success"):
            result_dict["errors"].append(obj.get("brief", "LLM 判定无法回答"))
            result_dict["brief"] = obj.get("brief")
            return result_dict
        if not obj.get("sql"):
            result_dict["errors"].append("LLM 未返回 SQL")
            return result_dict

        result_dict["sql"] = obj["sql"]
        result_dict["brief"] = obj.get("brief")
        result_dict["chart_type"] = obj.get("chart-type")

        ok, errors, final_sql = validate(obj["sql"], schema["tables"])
        if not ok:
            result_dict["errors"] = errors
            result_dict["summary"] = "校验未通过"
            return result_dict
        result_dict["final_sql"] = final_sql

        result = execute(final_sql, engine=config.EXEC_ENGINE)
        result_dict["result"] = result
        result_dict["summary"] = summarize(result.columns, result.rows)
        result_dict["success"] = True
        return result_dict
    except Exception as e:
        result_dict["errors"].append(f"{type(e).__name__}: {e}")
        return result_dict
