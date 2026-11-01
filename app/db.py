import pymysql

def query(host: str, port: int, password: str, user: str, 
          question: str, db: str, sql: str, max_rows: int = 100):
    conn = pymysql.connect(user=user,password=password, host=host, port=port, 
                    database=db, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = (d[0] for d in cur.description)
            rows = cur.fetchmany(max_rows)
            return columns, rows
    finally:
        conn.close()