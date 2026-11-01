"""从执行结果生成人话摘要。"""
from collections import Counter

# 列名 → 中文标签（命中用中文，未命中退回原列名）
_LABELS = {
    "city": "城市",
    "total": "总额",
    "name": "名称",
    "category": "品类",
    "status": "状态",
    "level": "会员等级",
    "payment_method": "支付方式",
}


def _label(col: str) -> str:
    return _LABELS.get(col, col)


def summarize(columns: list[str], rows: list[tuple]) -> str:
    """生成摘要文本，例如"共 4 个城市有订单，合计 ¥1870，最高是上海 ¥665（占 35.6%）"。

    空结果返回"无数据"；按首行数据识别文本列/数字列，不写死列名。
    """
    if not rows:
        return "无数据"

    col_index = {col: i for i, col in enumerate(columns)}
    first_row = rows[0]

    # 按首行识别列型：数字列 / 文本列
    column_type = {}
    for col, val in zip(columns, first_row):
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            column_type[col] = "number"
        else:
            column_type[col] = "text"

    text_results = {}
    number_results = {}
    for col in columns:
        idx = col_index[col]
        if column_type[col] == "text":
            values = [row[idx] for row in rows if row[idx] is not None]
            text_results[col] = Counter(values).most_common(3)
        else:
            values = [row[idx] for row in rows
                      if row[idx] is not None and isinstance(row[idx], (int, float))]
            number_results[col] = round(sum(values), 2)

    has_text = bool(text_results)
    has_number = bool(number_results)

    if has_text and has_number:
        number_col = list(number_results.keys())[0]
        text_col = list(text_results.keys())[0]
        label = _label(text_col)
        total_sum = number_results[number_col]

        # 按文本列聚合数值，找最高分组
        text_idx = col_index[text_col]
        number_idx = col_index[number_col]
        groups = {}
        for row in rows:
            key = row[text_idx]
            val = row[number_idx]
            if key is not None and val is not None and isinstance(val, (int, float)):
                groups[key] = groups.get(key, 0) + val

        if groups:
            top_key = max(groups, key=groups.get)
            top_val = groups[top_key]
            pct = round(top_val / total_sum * 100, 1) if total_sum != 0 else 0
            return f"共 {len(groups)} 个{label}有订单，合计 ¥{total_sum:,.2f}，最高是 {top_key} ¥{top_val:,.2f}（占 {pct}%）"
        return f"合计 ¥{total_sum:,.2f}"

    if has_number:
        number_col = list(number_results.keys())[0]
        return f"合计 ¥{number_results[number_col]:,.2f}"

    if has_text:
        text_col = list(text_results.keys())[0]
        parts = [f"{val}({count}次)" for val, count in text_results[text_col]]
        return f"主要分布：{'，'.join(parts)}"

    return "无数据"
