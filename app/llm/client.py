from openai import OpenAI
import json

def chat(prompt: str, *, mode: str, base_url: str = "", api_key: str = "",
         model: str = "", temperature: float = 0.0):
    if mode == "mock":
        return json.dumps({
              "success": True,
              "sql": "SELECT s.city, SUM(o.total_amount) AS total "
                     "FROM orders o JOIN store s ON o.store_id = s.id "
                     "WHERE o.status = '已完成' "
                     "AND o.order_date >= '2026-07-01' AND o.order_date < '2026-08-01' "
                     "GROUP BY s.city ORDER BY total DESC",
              "tables": ["orders", "store"],
              "chart-type": "bar",
              "brief": "各城市订单总额汇总",
          }, ensure_ascii=False)

    # 接真实LLM情况，client.chat.completion.create发出请求
    client = OpenAI(api_key=api_key, base_url=base_url or None)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    # 提取出回答文本
    return resp.choices[0].message.content or ""