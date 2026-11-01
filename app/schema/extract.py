"""schema抽取优先MySQL，失败则解析文件"""
import json
from pathlib import Path

from app import config
from .ddl_parser import parse_ddl

# 指纹函数，使用文件的纳秒级修改时间作为唯一标识，用于判断文件是否被修改
def _source_fingerprint(path: Path) -> str:
    return str(path.stat().st_mtime_ns)

# 写进 _meta.source 的路径：优先相对仓库根，避免把本机用户名/盘符带进产物
# (schema.json 是要提交的,绝对路径等于把个人目录结构发出去)
def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(config.ROOT).as_posix()
    except ValueError:
        return path.name

# 写入函数，创建父目录并写入
def _write(json_path: Path, data: dict) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# 当不存在真实mysql库时，直接读指定sql文件，转化成schema字典
def extract_from_sql_file(path: Path) -> dict:
    schema = parse_ddl(path.read_text(encoding="utf-8"))
    return schema.to_dict(source=_display_path(path))

# 直接读真实库得到schema
def extract_from_mysql(host, port, user, password, db) -> dict:
    from .mysql_extractor import extract_from_mysql as _raw
    schema = _raw(host, port, user, password, db)
    return schema.to_dict(source=f"mysql://{host}:{port}/{db}")

def ensure_schema_json(mysql: dict, sql_path: Path, json_path: Path) -> dict:
    # MySQL 已配置 → 直接抽取真库,MySQL 是活的，每次调用都会重新抽取
    if mysql.get("user"):
        data = extract_from_mysql(**mysql)
        _write(json_path, data)
        print(f"[schema] 已从 MySQL 刷新 → {json_path}")
        return data
    # 无 MySQL，但 JSON 缓存存在且未过期
    if json_path.exists():
        meta = json.loads(json_path.read_text(encoding="utf-8")).get("_meta", {})
        # 指纹相同，直接返回缓存内容无需解析
        if meta.get("source_fingerprint") == _source_fingerprint(sql_path):
            return json.loads(json_path.read_text(encoding="utf-8"))
    # 无 MySQL，且缓存不存在或指纹过期
    data = extract_from_sql_file(sql_path)
    data["_meta"]["source_fingerprint"] = _source_fingerprint(sql_path)
    _write(json_path, data)
    print(f"[schema] 已刷新 → {json_path}")
    return data