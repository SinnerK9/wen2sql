"""构建 COFFEE 咖啡连锁示例库(SQLite)。

个人求职项目用。数据用固定随机种子(42)确定性地生成 → 可复现,评测结果稳定。
用法:python build_coffee.py   → 生成 coffee.db

说明:表结构 = 本脚本里的 SQLite DDL(与 coffee_schema.sql 的 MySQL 版结构一致,
类型做映射:INT→INTEGER、VARCHAR→TEXT、DECIMAL→REAL、DATE/DATETIME→TEXT);
coffee_schema.sql 保留给 A2 的 schema 抽取用。
"""
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "coffee.db"

# ---------- SQLite 建表(结构对齐 coffee_schema.sql) ----------
SQLITE_DDL = """
CREATE TABLE store (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    city      TEXT NOT NULL,
    district  TEXT NOT NULL,
    open_date TEXT NOT NULL
);
CREATE TABLE category (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
CREATE TABLE product (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name        TEXT NOT NULL,
    price       REAL NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE customer (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    phone         TEXT NOT NULL,
    level         TEXT NOT NULL DEFAULT '普通',
    registered_at TEXT NOT NULL
);
CREATE TABLE orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id       INTEGER NOT NULL,
    customer_id    INTEGER NOT NULL,
    order_date     TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT '已完成',
    total_amount   REAL NOT NULL,
    payment_method TEXT NOT NULL DEFAULT '微信'
);
CREATE TABLE order_item (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity   INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    amount     REAL NOT NULL
);
CREATE TABLE promotion (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    discount   REAL NOT NULL DEFAULT 1.0,
    start_date TEXT NOT NULL,
    end_date   TEXT NOT NULL
);
"""

# ---------- 固定基础数据 ----------
STORES = [
    ("北京朝阳店", "北京", "朝阳"),
    ("北京海淀店", "北京", "海淀"),
    ("上海静安店", "上海", "静安"),
    ("上海浦东店", "上海", "浦东"),
    ("深圳南山店", "深圳", "南山"),
    ("杭州西湖店", "杭州", "西湖"),
]

CATEGORIES = ["经典咖啡", "特调咖啡", "茶饮", "甜品", "轻食"]

# (名称, 品类下标, 售价)
PRODUCTS = [
    ("美式咖啡", 0, 18.00), ("拿铁", 0, 26.00), ("卡布奇诺", 0, 28.00), ("澳白", 0, 30.00),
    ("生椰拿铁", 1, 32.00), ("厚乳拿铁", 1, 33.00), ("抹茶拿铁", 1, 31.00),
    ("茉莉绿茶", 2, 16.00), ("桂花乌龙", 2, 18.00),
    ("芝士蛋糕", 3, 32.00), ("提拉米苏", 3, 35.00), ("蓝莓可颂", 3, 22.00),
    ("鸡肉三明治", 4, 28.00), ("牛角包", 4, 15.00),
]

CUSTOMER_NAMES = [
    "张伟", "李娜", "王强", "刘敏", "陈杰", "杨静", "赵磊", "黄丽", "周勇", "吴婷",
    "徐斌", "孙芳", "马超", "朱霞", "胡军", "郭丹", "林峰", "何雪", "高翔", "罗燕",
]
LEVELS = ["普通", "普通", "普通", "银卡", "银卡", "金卡", "黑金"]  # 加权,黑金最少
PAYMENTS = ["微信", "微信", "支付宝", "支付宝", "银行卡", "现金"]
STATUS = ["已完成", "已完成", "已完成", "已完成", "已完成", "已取消", "已取消", "退款中"]

PROMOTIONS = [
    ("夏日冰咖第二杯半价", 0.50, "2026-06-01", "2026-06-30"),
    ("会员周三会员日", 0.80, "2026-07-01", "2026-07-31"),
    ("开学季早餐套餐", 0.85, "2026-08-01", "2026-08-31"),
]

# 订单时间范围:2026-05-01 ~ 2026-07-31(让"上月/近一个月"查询有数据)
ORDER_START = date(2026, 5, 1)
ORDER_END = date(2026, 7, 31)


def main() -> None:
    rng = random.Random(42)

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SQLITE_DDL)

    # 1. 门店
    conn.executemany(
        "INSERT INTO store (name, city, district, open_date) VALUES (?,?,?,?)",
        [(n, c, d, "2025-03-01") for n, c, d in STORES],
    )

    # 2. 品类 + 商品
    for c in CATEGORIES:
        conn.execute("INSERT INTO category (name) VALUES (?)", (c,))
    for name, cidx, price in PRODUCTS:
        conn.execute(
            "INSERT INTO product (category_id, name, price) VALUES (?,?,?)",
            (cidx + 1, name, price),
        )

    # 3. 会员(20 位,等级加权,注册时间 2025 年)
    for i, name in enumerate(CUSTOMER_NAMES, 1):
        level = rng.choice(LEVELS)
        reg = datetime(2025, rng.randint(1, 12), rng.randint(1, 28), 10, 0, 0)
        conn.execute(
            "INSERT INTO customer (name, phone, level, registered_at) VALUES (?,?,?,?)",
            (name, f"138{rng.randint(10000000, 99999999)}", level, reg.isoformat(" ")),
        )

    # 4. 订单 + 明细(90 单,跨 5-7 月,时间/状态/支付都分布好)
    order_id = 0
    for _ in range(90):
        order_id += 1
        store_id = rng.randint(1, len(STORES))
        customer_id = rng.randint(1, len(CUSTOMER_NAMES))
        day = ORDER_START + timedelta(days=rng.randint(0, (ORDER_END - ORDER_START).days))
        order_date = datetime(day.year, day.month, day.day,
                              rng.randint(8, 21), rng.randint(0, 59), 0)
        status = rng.choice(STATUS)
        payment = rng.choice(PAYMENTS)

        # 1~3 件商品
        n_items = rng.randint(1, 3)
        total = 0.0
        item_rows = []
        for _ in range(n_items):
            product_id = rng.randint(1, len(PRODUCTS))
            unit_price = float(PRODUCTS[product_id - 1][2])
            qty = rng.randint(1, 2)
            amount = round(unit_price * qty, 2)
            total += amount
            item_rows.append((order_id, product_id, qty, unit_price, amount))

        conn.execute(
            "INSERT INTO orders (id, store_id, customer_id, order_date, status, total_amount, payment_method) "
            "VALUES (?,?,?,?,?,?,?)",
            (order_id, store_id, customer_id, order_date.isoformat(" "),
             status, round(total, 2), payment),
        )
        conn.executemany(
            "INSERT INTO order_item (order_id, product_id, quantity, unit_price, amount) "
            "VALUES (?,?,?,?,?)",
            item_rows,
        )

    # 5. 促销
    conn.executemany(
        "INSERT INTO promotion (name, discount, start_date, end_date) VALUES (?,?,?,?)",
        PROMOTIONS,
    )

    conn.commit()

    # 6. 校验:各表行数 + 几条验证查询
    print("=== 各表行数 ===")
    for t in ["store", "category", "product", "customer", "orders", "order_item", "promotion"]:
        print(f"  {t}: {conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
    print("=== 验证查询 ===")
    print("上月各城市订单总额(已完成):")
    for row in conn.execute(
        "SELECT s.city, SUM(o.total_amount) FROM orders o "
        "JOIN store s ON o.store_id=s.id "
        "WHERE o.status='已完成' AND o.order_date >= '2026-07-01' AND o.order_date < '2026-08-01' "
        "GROUP BY s.city ORDER BY 2 DESC"):
        print("  ", row)
    conn.close()


if __name__ == "__main__":
    main()
