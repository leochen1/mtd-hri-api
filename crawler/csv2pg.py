import os
import pandas as pd
import logging
from glob import glob
from repository.pg_repo import fn_GetEnv
import psycopg2
from datetime import datetime

def import_csvs_to_pg():
    # 設定 logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # 取得 PostgreSQL 連線資訊
    fn_GetEnv()
    pg_host = os.environ.get('PGHOST')
    pg_port = os.environ.get('PGPORT')
    pg_user = os.environ.get('PGUSER')
    pg_password = os.environ.get('PGPASSWORD')
    pg_database = os.environ.get('PGDATABASE')

    # 欄位對應
    keep_columns = ['Mfr 部件編號', '製造商', '規格書', '供貨情況', '定價', '產品明細']
    pg_columns = ['mfr_part_number', 'manufacturer', 'datasheet_url', 'availability', 'price', 'product_details']

    # 取得所有 csv 檔案
    csv_files = glob(os.path.join('downloads', '*.csv'))
    logging.info(f"發現 {len(csv_files)} 個 CSV 檔案")

    conn = psycopg2.connect(
        host=pg_host,
        port=pg_port,
        user=pg_user,
        password=pg_password,
        dbname=pg_database
    )
    cur = conn.cursor()

    for file_path in csv_files:
        try:
            # 讀取 csv
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='big5', errors='ignore')
        except Exception as e:
            logging.error(f"{file_path} 讀取失敗: {e}")
            continue

        # 只保留指定欄位
        df = df[[col for col in keep_columns if col in df.columns]]
        df.columns = pg_columns[:len(df.columns)]  # 欄位名稱對應
        df['system_date'] = datetime.now()  # 新增 system_date 欄位

        # 寫入 PostgreSQL
        for _, row in df.iterrows():
            sql_delete = """
                DELETE FROM hri.manufacturer_parts_list
                WHERE mfr_part_number = %s
            """
            sql_insert = """
                INSERT INTO hri.manufacturer_parts_list
                (mfr_part_number, manufacturer, datasheet_url, availability, price, product_details, system_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = [row.get(col, None) for col in pg_columns] + [row['system_date']]
            try:
                # 先刪除相同的 mfr_part_number
                cur.execute(sql_delete, (row['mfr_part_number'],))
                # 再插入新資料
                cur.execute(sql_insert, values)
            except Exception as e:
                logging.error(f"寫入失敗: {e}，資料: {values}")

        conn.commit()
        logging.info(f"{file_path} 匯入完成，共 {len(df)} 筆")

    cur.close()
    conn.close()
    logging.info("所有 CSV 匯入完成")
