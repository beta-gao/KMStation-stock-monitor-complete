import requests
import time
import csv
import os
from datetime import datetime
import traceback
import re

from config import prod_ids, interval_seconds

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

LOG_FILE = "monitor_log.txt"

def initialize_folder(prod_id):
    folder_name = str(prod_id)
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

def extract_member_name(sku_name):
    match = re.search(r'应募([A-Z]+)', sku_name)
    if match:
        return match.group(1)
    else:
        return "UNKNOWN"

def read_last_stocks(filename):
    try:
        with open(filename, mode='r', encoding='utf-8-sig') as file:
            lines = file.readlines()
            if len(lines) >= 2:
                last_line = lines[-1]
                parts = last_line.strip().split(',')
                last_stocks = int(parts[-2])  # 倒数第二列是Stocks
                return last_stocks
    except Exception:
        pass
    return None

def log_message(message):
    print(message)
    with open(LOG_FILE, mode='a', encoding='utf-8') as file:
        file.write(message + '\n')

def save_per_member(prod_id, now, member_stocks):
    folder_name = str(prod_id)
    for member_name, stocks in member_stocks.items():
        filename = os.path.join(folder_name, f"{member_name}.csv")
        file_exists = os.path.isfile(filename)

        last_stocks = read_last_stocks(filename)
        if last_stocks is not None:
            unit_sales = last_stocks - stocks
        else:
            unit_sales = ""

        with open(filename, mode='a', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Time", "MemberName", "TotalStocks", "UnitSales"])
            writer.writerow([now, member_name, stocks, unit_sales])

def record_data(prod_id):
    try:
        url = f"https://thor.weidian.com/detail/getItemSkuInfo/1.0?param=%7B%22itemId%22%3A%22{prod_id}%22%7D"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sku_list = data['result']['skuInfos']

        member_stocks = {}

        for sku in sku_list:
            sku_name = sku['skuInfo'].get('title', '')
            stocks = sku['skuInfo'].get('stock', 0)
            member_name = extract_member_name(sku_name)

            if member_name in member_stocks:
                member_stocks[member_name] += int(stocks)
            else:
                member_stocks[member_name] = int(stocks)

        save_per_member(prod_id, now, member_stocks)

        log_message(f"[{now}] Successfully recorded {len(member_stocks)} merged members for prodId {prod_id}.")

    except Exception as e:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_message = f"[{now}] Error occurred when recording prodId {prod_id}: {e}"
        log_message(error_message)
        traceback.print_exc()

def main():
    for prod_id in prod_ids:
        initialize_folder(prod_id)

    while True:
        for prod_id in prod_ids:
            record_data(prod_id)
        time.sleep(interval_seconds)

if __name__ == "__main__":
    main()
