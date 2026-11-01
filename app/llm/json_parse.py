import json
import re

def extract_json(text: str) -> dict | None:
    if not text:
        return None
    # re.sub(pattern, replacement, string)：正则替换函数，将 string 中所有匹配 pattern 的子串替换为 replacement
    # re执行正则化，r"..."表示原始字符串，(?:...)建立非捕获组，匹配"json"，后面的?表示匹配一次或两次
    # 也即：删除开头的 ``` 和可能紧随的 json 前缀
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{" :
            depth += 1
        elif text[i] == "}" :
            depth -= 1
            if depth == 0:
                try: 
                    return json.loads (text[start: i + 1])
                except json.JSONDecodeError:
                    return None
    return None