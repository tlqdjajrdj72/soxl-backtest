import os
import sys
import time
import requests
import pandas as pd
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import warnings

warnings.filterwarnings("ignore")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
OUTPUT_DIR = "/tmp"

STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "TSLA", "META", "NFLX", "ADBE", "CRM",
    "INTC", "AMD", "QCOM", "CSCO", "ORCL",
    "AVGO", "ASML", "LRCX", "AMAT", "MCHP",
    "MU", "MRVL", "KLAC", "SNPS", "CDNS",
    "TEAM", "DXCM", "SPLK", "OKTA", "CRWD",
    "SNOW", "FTNT", "PALO", "NET", "PANW",
    "CHKP", "CYBR", "AVNT", "WDAY", "VEEV",
    "RPD", "ZM", "DOCN", "DDOG", "HUBS",
    "MSTR", "COIN", "MARA", "RIOT", "HOOD"
]

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("Chrome WebDriver OK")
        return driver
    except Exception as e:
        print(f"WebDriver Error: {e}")
        return None

def crawl_quarterly_revenue(driver, stock):
    url = f"https://www.financecharts.com/stocks/{stock}/income-statement/revenue"
    
    try:
        print(f"[{stock}] Crawling...", end=" ", flush=True)
        driver.get(url)
        
        wait = WebDriverWait(driver, 10)
        try:
            wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "table")))
        except:
            print("Table load failed")
            return None
        
        time.sleep(1)
        table_data = extract_table_data(driver)
        
        if table_data is None or len(table_data) == 0:
            print("Data extraction failed")
            return None
        
        print(f"OK - {len(table_data)} rows")
        return {
            "stock": stock,
            "data": table_data,
            "timestamp": datetime.now().isoformat(),
            "url": url
        }
        
    except Exception as e:
        print(f"Error: {str(e)[:50]}")
        return None

def extract_table_data(driver):
    try:
        tables = driver.find_elements(By.TAG_NAME, "table")
        if not tables:
            return None
        
        table = tables[0]
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        data = []
        headers = []
        
        for idx, row in enumerate(rows):
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                cells = row.find_elements(By.TAG_NAME, "th")
                if cells and idx == 0:
                    headers = [cell.text.strip() for cell in cells]
            else:
                row_data = [cell.text.strip() for cell in cells]
                if row_data:
                    data.append(row_data)
        
        if headers and data:
            df = pd.DataFrame(data, columns=headers)
            return df.to_dict("records")
        
        return data if data else None
        
    except Exception as e:
        print(f"Extraction error: {e}")
        return None

def main():
    print("=" * 80)
    print("FinanceCharts Quarterly Revenue Crawler")
    print("=" * 80)
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Stocks: {len(STOCKS)}\n")
    
    driver = setup_driver()
    if driver is None:
        print("Driver setup failed")
        return
    
    all_results = []
    success_count = 0
    fail_count = 0
    
    try:
        for idx, stock in enumerate(STOCKS, 1):
            print(f"[{idx:2d}/{len(STOCKS)}] ", end="")
            result = crawl_quarterly_revenue(driver, stock)
            
            if result:
                all_results.append(result)
                success_count += 1
            else:
                fail_count += 1
            
            time.sleep(1)
    
    finally:
        driver.quit()
        print("\nDriver closed")
    
    print("\n" + "=" * 80)
    print("Saving results...")
    print("=" * 80)
    
    json_path = f"{OUTPUT_DIR}/quarterly_revenue_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"JSON saved: {json_path}")
    
    csv_data = []
    for result in all_results:
        if result["data"]:
            for row in result["data"]:
                csv_data.append({
                    "Stock": result["stock"],
                    **row
                })
    
    if csv_data:
        df_csv = pd.DataFrame(csv_data)
        csv_path = f"{OUTPUT_DIR}/quarterly_revenue_summary.csv"
        df_csv.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"CSV saved: {csv_path}")
    
    print("\n" + "=" * 80)
    print("Results Summary")
    print("=" * 80)
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total: {len(all_results)} stocks")
    print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("\nSending Telegram notification...")
        telegram_msg = f"""
FinanceCharts Crawler Complete

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Success: {success_count}/50
Failed: {fail_count}/50

Total stocks: {len(all_results)}
Total records: {sum(len(r["data"]) if r["data"] else 0 for r in all_results)}

Stocks: {", ".join(STOCKS[:10])}... (50 total)
"""
        
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": telegram_msg},
                timeout=10
            )
            print("Telegram sent OK")
        except Exception as e:
            print(f"Telegram failed: {e}")
    
    print("\n" + "=" * 80)
    print("Crawler complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
