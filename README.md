# Text2SQL(COFFEE 示例库)— 全量注入 + 硬校验

> 中文提问 → 生成 SQL → AST 硬校验 → 只读执行 → 表格 + 人话摘要。
> 设计取舍、踩坑与已知限制见 [docs/DEVNOTES.md](docs/DEVNOTES.md)。

```
问题 "上月各城市订单总额"
   │
   ▼
┌─────────────┐   ┌──────────────────────┐   ┌──────────────────┐
│ schema 抽取  │──▶│ prompt(M-Schema 全量 │──▶│ LLM(mock/api)    │
│ DDL / 真库   │   │  + 术语 + 口径 + 示例)│   │ 生成 {success,sql}│
└─────────────┘   └──────────────────────┘   └──────────────────┘
                                                     │ extract_json 容错
                                                     ▼
┌─────────────┐   ┌──────────────────────┐   ┌──────────────────┐
│ 摘要 + 表格  │◀──│ 只读执行(超时/截断    │◀──│ sqlglot 硬校验 7 项│
│ summarize() │   │ 可见化 + COUNT 总数)  │   │ 拒绝+改写 LIMIT   │
└─────────────┘   └──────────────────────┘   └──────────────────┘
```

**安全底线**:LLM 原始输出绝不直接执行 —— 必须过 7 项校验(只读/单语句/表白名单/联表数/危险函数/列校验/LIMIT 分级),执行器只接收改写后的 `final_sql`,并以只读连接(SQLite `mode=ro` / MySQL 只读账号)+ 超时(MySQL `MAX_EXECUTION_TIME` / SQLite `progress_handler`)兜底。

## 快速开始

```bash
pip install sqlglot openai pymysql     # 运行依赖(测试仅用标准库)
python ask.py "上月各城市订单总额"
```

默认**零配置可跑**(`LLM_MODE=mock` 假 LLM + `EXEC_ENGINE=sqlite` 读 `coffee_db/coffee.db` 真数据),输出:

```
[生成 SQL] SELECT s.city, SUM(o.total_amount) AS total ...
[校验] 通过
[结果] 列: city, total
  上海 | 665.0
  北京 | 519.0
  杭州 | 440.0
  深圳 | 358.0
[摘要] 共 4 个城市有订单，合计 ¥1,982.00，最高是 上海 ¥665.00（占 33.6%）
```

> `EXEC_ENGINE=stub` 可切回固定假数据,仅用于链路联调。
> Windows 直接 `python ask.py` 时控制台是 GBK,摘要里的 `¥` 会报编码错;用根目录的 `run.bat`(自动切 UTF-8)或先 `set PYTHONIOENCODING=utf-8`。

### 接真 LLM(可选)

`config.py` 只读环境变量,Windows PowerShell 设一次:

```powershell
$env:LLM_MODE="api"
$env:LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"  # 需以 /v1 结尾
$env:LLM_API_KEY="sk-..."
$env:LLM_MODEL="qwen-turbo"
```

### 接真 MySQL(可选)

```powershell
$env:MYSQL_USER="xxx"
$env:MYSQL_PASSWORD="xxx"      # 建议只读账号
$env:EXEC_ENGINE="mysql"       # 默认 sqlite,切真库只需这一个变量(方言随之切到 mysql)
```

> `config.py` **不加载 .env 文件**,只读进程环境变量。

### 跑测试

```bash
python -m unittest discover -s tests -v   # 80 个用例
```

## 项目结构

```
wen2sql/
├── ask.py                  # CLI 入口:python ask.py "问题"
├── coffee_db/              # 示例库 DDL + 造数脚本 + coffee.db
├── data/
│   ├── schema.json         # 抽取产物
│   └── knowledge.json      # 业务术语/口径/示例(注入 prompt)
├── app/
│   ├── answer.py           # 五段管线编排
│   ├── summary.py          # 结果 → 人话摘要
│   ├── config.py           # 环境变量配置
│   ├── constants.py        # DEFAULT_LIMIT / MAX_ROWS / EXEC_TIMEOUT
│   ├── schema/             # DDL / information_schema → Schema
│   ├── llm/                # prompt / client / json 容错解析
│   ├── validate/           # sqlglot 硬校验 7 项(方言参数化)
│   └── executor/           # 引擎分发(sqlite/mysql/stub)+ 方言归一 + 截断 + 超时
├── tests/                  # unittest 自动化测试
└── docs/DEVNOTES.md        # 开发笔记:设计取舍 / 踩坑 / 已知限制
```

## 关键特性

| 特性 | 落点 | 一句话 |
|---|---|---|
| 全量注入 | `app/llm/prompt.py` | M-Schema(含枚举取值 + 外键)全量进 prompt |
| 业务口径 | `data/knowledge.json` | 术语/口径/示例注入,模型不靠猜 |
| 硬校验 | `app/validate/validator.py` | 7 项,拒绝型 + LIMIT 分级改写,按目标方言解析 |
| 方言归一 | `app/executor/dialect.py` | LLM 写 MySQL 语法也能在 SQLite 上跑(`DATE_FORMAT`→`STRFTIME`、`CONCAT`→`\|\|`) |
| 截断可见化 | `app/executor/` | 超 1000 行 → truncated + COUNT(*) 真实总数 |
| 双层超时 | `app/executor/` | 线程池 timeout(MySQL `MAX_EXECUTION_TIME`)+ SQLite `progress_handler` 中断 |
| 人话摘要 | `app/summary.py` | "共 N 个城市有订单,合计 ¥X,最高是 ..." |
