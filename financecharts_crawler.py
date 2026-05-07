import os
import sys
import time
import requests
import pandas as pd
import json
from datetime import datetime
from bs4 import BeautifulSoup
import warnings

warnings.filterwarnings(“ignore”)

TELEGRAM_BOT_TOKEN = os.getenv(“TELEGRAM_BOT_TOKEN”, “”)
TELEGRAM_CHAT_ID = os.getenv(“TELEGRAM_CHAT_ID”, “”)
OUTPUT_DIR = “/tmp”

STOCKS = [
“AAPL”, “MSFT”, “GOOGL”, “AMZN”, “NVDA”,
“TSLA”, “META”, “NFLX”, “ADBE”, “CRM”,
“INTC”, “AMD”, “QCOM”, “CSCO”, “ORCL”,
“AVGO”, “ASML”, “LRCX”, “AMAT”, “MCHP”,
“MU”, “MRVL”, “KLAC”, “SNPS”, “CDNS”,
“TEAM”, “DXCM”, “SPLK”, “OKTA”, “CRWD”,
“SNOW”, “FTNT”, “PALO”, “NET”, “PANW”,
“CHKP”, “CYBR”, “AVNT”, “WDAY”, “VEEV”,
“RPD”, “ZM”, “DOCN”, “DDOG”, “HUBS”,
“MSTR”, “COIN”, “MARA”, “RIOT”, “HOOD”
]

def scrape_quarterly_revenue(stock):
“””
BeautifulSoup을 사용한 분기별 매출액 웹 스크래핑
“””
url = f”https://www.financecharts.com/stocks/{stock}/income-statement/revenue”

```
try:
    print(f"[{stock}] Scraping...", end=" ", flush=True)
    
    # HTTP 요청 (User-Agent 포함)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    # HTML 파싱
    soup = BeautifulSoup(response.content, "html.parser")
    
    # 테이블 찾기: div.overflow-x-auto > table
    table_container = soup.find("div", class_="overflow-x-auto")
    if not table_container:
        print("Table container not found")
        return None
    
    table = table_container.find("table")
    if not table:
        print("Table not found")
        return None
    
    # tbody에서 데이터 추출
    tbody = table.find("tbody")
    if not tbody:
        print("Table body not found")
        return None
    
    rows = tbody.find_all("tr")
    if not rows:
        print("No data rows found")
        return None
    
    # 각 행 데이터 추출
    table_data = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 2:
            # td[0]: 날짜, td[1]: 매출액, td[2]: 변화율
            date = cells[0].get_text(strip=True)
            revenue = cells[1].get_text(strip=True)
            
            # 변화율 (있으면)
            change = ""
            if len(cells) >= 3:
                change_span = cells[2].find("span")
                if change_span:
                    change = change_span.get_text(strip=True)
            
            table_data.append({
                "Date": date,
                "Quarterly Revenue": revenue,
                "% Change": change
            })
    
    if not table_data:
        print("No data extracted")
        return None
    
    print(f"OK - {len(table_data)} rows")
    return {
        "stock": stock,
        "data": table_data,
        "timestamp": datetime.now().isoformat(),
        "url": url
    }
    
except requests.exceptions.Timeout:
    print("Timeout")
    return None
except requests.exceptions.RequestException as e:
    print(f"Request error: {str(e)[:50]}")
    return None
except Exception as e:
    print(f"Error: {str(e)[:50]}")
    return None
```

def main():
print(”=” * 80)
print(“FinanceCharts Quarterly Revenue Web Scraper”)
print(”=” * 80)
print(f”Start: {datetime.now().strftime(’%Y-%m-%d %H:%M:%S’)}”)
print(f”Stocks: {len(STOCKS)}\n”)

```
all_results = []
success_count = 0
fail_count = 0

for idx, stock in enumerate(STOCKS, 1):
    print(f"[{idx:2d}/{len(STOCKS)}] ", end="")
    result = scrape_quarterly_revenue(stock)
    
    if result:
        all_results.append(result)
        success_count += 1
    else:
        fail_count += 1
    
    # Rate limiting (0.5초 대기)
    time.sleep(0.5)

print("\n" + "=" * 80)
print("Saving results...")
print("=" * 80)

# JSON으로 저장
json_path = f"{OUTPUT_DIR}/quarterly_revenue_data.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print(f"JSON saved: {json_path}")

# CSV로 저장
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

# 요약 출력
print("\n" + "=" * 80)
print("Results Summary")
print("=" * 80)
print(f"Success: {success_count}")
print(f"Failed: {fail_count}")
print(f"Total: {len(all_results)} stocks")
print(f"Total records: {sum(len(r['data']) if r['data'] else 0 for r in all_results)}")
print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Telegram 알림
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    print("\nSending Telegram notification...")
    telegram_msg = f"""
```

FinanceCharts Web Scraper Complete

Time: {datetime.now().strftime(’%Y-%m-%d %H:%M:%S’)}

Success: {success_count}/50
Failed: {fail_count}/50

Total stocks: {len(all_results)}
Total records: {sum(len(r[“data”]) if r[“data”] else 0 for r in all_results)}

Stocks: {”, “.join(STOCKS[:10])}… (50 total)
“””

```
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
print("Web scraper complete!")
print("=" * 80)
```

if **name** == “**main**”:
main()