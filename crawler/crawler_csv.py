from flask import jsonify
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import pandas as pd
import time
import random
import urllib3
import shutil


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_csv_file(url, session, file_path, headers, retries=3):
    """
    通用下載函式，用於下載文件並保存到指定路徑，帶有重試機制。
    """
    for attempt in range(retries):
        try:
            logging.info(f"開始下載文件，URL: {url}，嘗試次數: {attempt + 1}")
            response = session.get(url, headers=headers, timeout=30, verify=False)
            if response.status_code == 200:
                with open(file_path, 'wb') as file:
                    file.write(response.content)
                logging.info(f"文件已成功保存到: {file_path}")
                return True
            else:
                logging.error(f"下載失敗，狀態碼: {response.status_code}")
        except Exception as e:
            logging.error(f"下載過程中發生錯誤: {str(e)}")
        time.sleep(2)  # 每次重試間隔
    return False

def crawler_csv(query: str) -> dict:
    SAVE_DIR = "downloads"
    SAVE_DIR_BAK = "downloads_bak"
    os.makedirs(SAVE_DIR, exist_ok=True)
    os.makedirs(SAVE_DIR_BAK, exist_ok=True)

    # Chrome headers
    chrome_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.mouser.tw/",
        "Sec-CH-UA": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Host": "www.mouser.tw"
    }
    
    url = f"https://www.mouser.tw/c/?q={query}"  # 184.30.10.45
    logging.info(f"[{query}] 組合目標 URL: {url}")

    session = requests.Session()
    session.headers.update(chrome_headers)
    session.cookies.set('cookieconsent_status', 'allow')
    session.cookies.set('language', 'zh-TW')

    initial_response = None

    try:
        # 隨機延遲
        time.sleep(random.uniform(2, 5))

        logging.info(f"[{query}] 正在訪問 URL: {url}")
        initial_response = session.get(url, timeout=30, verify=False)

        if initial_response.status_code == 200:

            text = initial_response.text

            # 判斷內容是否疑似被擋（如只有 script 或內容過短或含有 challenge script）
            is_html = "<html" in text
            is_too_short = len(text) < 1000
            is_challenge = (
                "<script" in text and
                "window.XMLHttpRequest.prototype.send" in text and
                "location.reload(true);" in text
            )
            if is_html and not is_too_short and not is_challenge:
                html_ok = True
            else:
                logging.warning(f"[{query}] 取得的 HTML 內容異常或被反爬蟲擋住，請稍後重試...")
                return jsonify({
                    "message": "取得的 HTML 內容異常或被反爬蟲擋住，請稍後重試...",
                    "status": "NG"
                }), 500

            logging.info(f"[{query}] 初始頁面請求成功")
            soup = BeautifulSoup(initial_response.text, 'html.parser')
            download_link = soup.find('a', id='btn3')            

            if download_link:
                href_value = download_link.get('href')
                # 若 href 是相對路徑，需補上主機
                if href_value.startswith("http"):
                    download_url = href_value
                else:
                    download_url = f"https://www.mouser.tw{href_value}"  # 184.30.10.45
                logging.info(f"[{query}] 找到下載連結: {download_url}")

                current_time = datetime.now().strftime("%Y%m%d%H%M%S")
                csv_file_name = f"{query}_{current_time}.csv"
                csv_file_path = os.path.join(SAVE_DIR, csv_file_name)

                # 下載 CSV
                if download_csv_file(download_url, session, csv_file_path, chrome_headers):
                    logging.info(f"[{query}] CSV 文件已成功下載並保存在 '{csv_file_path}'")
                    logging.info(f"[{query}] 完整的下載連結為: {download_url}")
                    return jsonify({
                        "message": f"CSV 文件已成功下載並保存在 '{csv_file_path}'",
                        "status": "OK"
                    }), 200
                else:
                    logging.error(f"[{query}] 下載 CSV 文件失敗")
                    return jsonify({
                        "message": f"CSV 文件下載失敗",
                        "status": "NG"
                    }), 500
            else:
                logging.warning(f"[{query}] 未找到 id='btn3' 的下載按鈕")
                return jsonify({
                    "message": f"未找到 id='btn3' 的下載按鈕",
                    "status": "NG"
                }), 404
        else:
            logging.error(f"[{query}] 無法訪問頁面，狀態碼: {initial_response.status_code}")
            return jsonify({
                "message": f"無法訪問頁面，狀態碼: {initial_response.status_code}",
                "status": "NG"
            }), initial_response.status_code
    except requests.exceptions.Timeout:
        logging.error(f"[{query}] 請求超時")
        return jsonify({
            "message": "請求超時，請稍後重試",
            "status": "NG"
        }), 504
    except Exception as e:
        logging.error(f"[{query}] 發生錯誤: {str(e)}")
        return jsonify({
            "message": f"發生錯誤: {str(e)}",
            "status": "NG"
        }), 500
    finally:
        initial_response.close()
        session.close()