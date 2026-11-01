"""stub 执行器：A6 链路联调用，返回固定假数据。

返回形状与 executor._run 一致：(columns, rows, truncated, total)。
真库到位后删除本文件与 executor.execute 中的 stub 分支即可。
"""


def fetch_stub(sql: str) -> tuple[list[str], list[tuple], bool, int]:
    """忽略传入 SQL，返回固定假数据。"""
    return (["city", "total"],
            [("上海", 665.0), ("北京", 532.0), ("深圳", 398.0), ("杭州", 275.0)],
            False, 4)
