import re

# 冒号(:/：)或括号((/（)后跟 2+ 个"逗号分隔的值",才认定为枚举列表。
# 值 = 中文 / 英文 / 数字(中文字面值与英文字面值都支持);
# "逗号分隔"才是关键信号,避免误抓"使用 HTTP API"这类空格分隔的无关词。
_ENUM_LIST = re.compile(
    r"[:：\(（]\s*"  # 中英冒号或左括号 + 可选空白
    # 2+ 个逗号分隔的值:值由中文/英文/数字/下划线组成
    r"([一-龥A-Za-z0-9_]+(?:\s*[,，]\s*[一-龥A-Za-z0-9_]+)+)"
)


def extract_enums_from_comment(comment: str) -> list:
    """从列注释提取枚举值。

    规则:冒号(:/：)或括号((/（)后跟至少 2 个逗号分隔的值(中文/英文/数字),
    才认定为枚举列表;否则返回空。
    例子:"会员等级：普通, 银卡, 金卡, 黑金" → ['普通','银卡','金卡','黑金']
    """
    if not comment:
        return []
    m = _ENUM_LIST.search(comment)
    if not m:
        return []
    return [v.strip() for v in re.split(r"[,，]", m.group(1))]
