import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timezone
import os
from glob import glob
import chardet
import logging

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    logging.info(f"檢測檔案 {file_path} 的編碼為: {result['encoding']}")
    return result['encoding']

# 將 MongoDB 連線邏輯獨立出來
def get_mongo_client(mongo_uri):
    try:
        client = MongoClient(mongo_uri, connectTimeoutMS=20000, socketTimeoutMS=20000)
        logging.info("成功連接到 MongoDB")
        return client
    except Exception as e:
        logging.error(f"無法連接到 MongoDB: {e}")
        return None

def import_all_csvs_to_mongodb(folder_path, mongo_uri, db_name, log_collection_name):
    csv_files = glob(os.path.join(folder_path, '*.csv'))
    logging.info(f"發現 {len(csv_files)} 個 CSV 檔案於 {folder_path}")

    if not csv_files:
        logging.warning("沒有找到任何 CSV 檔案")
        return

    # 使用 get_mongo_client 獲取 MongoDB 客戶端
    client = get_mongo_client(mongo_uri)
    if not client:
        logging.error("MongoDB 連線失敗，停止匯入")
        return

    db = client[db_name]
    log_col = db[log_collection_name]

    for file_path in csv_files:
        source_file = os.path.basename(file_path)
        collection_name_part = source_file.split('_')[0]
        data_collection_name = f"mtd.hri.{collection_name_part}"

        if data_collection_name in db.list_collection_names():
            logging.info(f"資料集合 {data_collection_name} 已存在，將刪除並重新建立")
            db[data_collection_name].drop()
            delete_result = log_col.delete_many({"source_file": {"$regex": f"^{collection_name_part}"}})
            logging.info(f"已刪除 {delete_result.deleted_count} 筆與 {collection_name_part} 相關的日誌紀錄")

        data_col = db[data_collection_name]

        try:
            # 自動檢測編碼
            encoding = detect_encoding(file_path)
            logging.info(f"檢測到檔案 {source_file} 的編碼為: {encoding}")
            df = pd.read_csv(file_path, encoding=encoding)
            records = df.to_dict(orient='records')

            # 寫入資料庫
            if records:
                result = data_col.insert_many(records)
                inserted_count = len(result.inserted_ids)

                # 成功的匯入紀錄
                log_col.insert_one({
                    "source_file": source_file,
                    "import_time": datetime.now(timezone.utc),
                    "status": "success",
                    "inserted_count": inserted_count,
                    "error": None
                })

                logging.info(f"[{source_file}] 匯入 {inserted_count} 筆成功")
            else:
                log_col.insert_one({
                    "source_file": source_file,
                    "import_time": datetime.now(timezone.utc),
                    "status": "empty",
                    "inserted_count": 0,
                    "error": "No data rows"
                })
                logging.warning(f"[{source_file}] 無資料可匯入")
        except Exception as e:
            # 錯誤紀錄
            log_col.insert_one({
                "source_file": source_file,
                "import_time": datetime.now(timezone.utc),
                "status": "error",
                "inserted_count": 0,
                "error": str(e)
            })
            logging.error(f"[{source_file}] 發生錯誤: {e}")
