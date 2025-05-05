from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
from gevent import pywsgi
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import requests
import os
import shutil
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from repository.mongo_repo import *
from crawler.crawler_csv import *
from crawler.csv2pg import *
import time as t
import pandas as pd
from pytz import timezone


# 設定時區為 Asia/Taipei
local_tz = timezone("Asia/Taipei")
local_time = datetime.now(local_tz)
print("Local time:", local_time)

# 加載 .env 文件中的環境變數
load_dotenv()

# 確保 logs 資料夾存在
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 設定日誌，使用 RotatingFileHandler
LOG_FILE = os.path.join(LOG_DIR, "app.log")
handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[handler, logging.StreamHandler()]
)

app = Flask(__name__)
CORS(app)  # 啟用 CORS 支持

# 配置 ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)


# 文件保存路徑
folder_path = 'downloads/'
SAVE_DIR = "downloads"
SAVE_DIR_BAK = "downloads_bak"
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(SAVE_DIR_BAK, exist_ok=True)


@app.after_request
def add_log_separator(response):
    """
    在每次 API 呼叫結束後，於日誌中加入分隔線。
    """
    logging.info("-" * 100)
    return response

@app.route('/', methods=['GET'])
def index():
    logging.info("訪問首頁路由 '/'")
    return "HRI API..."

@app.route('/api/csv/search', methods=['GET'])
def search():
    """
    接收使用者輸入的查詢參數，訪問目標網站並返回結果。
    :param query: 使用者輸入的查詢字串，例如 "IAM-20680"
    """
    query = request.args.get('query')
    if not query:
        logging.warning("缺少查詢參數 'query'")
        return jsonify({"error": "缺少查詢參數 'query'"}), 400

    try:
        response, status_code = crawler_csv(query)  # 解構回傳值
        response_data = response.json  # 直接取得 JSON 資料
        status = response_data.get("status")  # 取得 status 的值
        print(f"Status: {status}")

        if status != "OK":
            logging.error(f"message: {response_data.get('message')}")
            return jsonify({"message": response_data.get("message")}), 500
        else:
            # CSV 下載成功，開始寫入 PostgreSQL
            import_csvs_to_pg()

            # 移動 csv 檔案到 downloads_bak
            for file_name in os.listdir(SAVE_DIR):
                if file_name.endswith(".csv"):
                    src_path = os.path.join(SAVE_DIR, file_name)
                    dst_path = os.path.join(SAVE_DIR_BAK, f"{file_name}")
                    shutil.move(src_path, dst_path)
                    logging.info(f"移動檔案 {src_path} 到 {dst_path}")
        
        return jsonify({
            "message": f"{file_name} 文件已成功下載並保存在 '{SAVE_DIR_BAK}', 寫入 PostgreSQL 成功",
            "status": "OK"
        }), 200

    except requests.exceptions.Timeout:
        logging.error(f"[{query}] 請求超時")
        return jsonify({"error": "請求超時，請稍後重試"}), 504
    except Exception as e:
        logging.error(f"[{query}] 發生錯誤: {str(e)}")
        return jsonify({"error": f"發生錯誤: {str(e)}"}), 500

if __name__ == '__main__':
    logging.info("伺服器啟動中，監聽 0.0.0.0:9980")
    server = pywsgi.WSGIServer(('0.0.0.0', 9980), app)
    server.serve_forever()