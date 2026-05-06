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

warnings.filterwarnings(‘ignore’)

# ==================== 환경 변수 설정 ====================

TELEGRAM_BOT_TOKEN = os.getenv(‘TELEGRAM_BOT_TOKEN’, ‘’)
TELEGRAM_CHAT_ID = os.getenv(‘TELEGRAM_CHAT_ID’, ‘’)
OUTPUT_DIR = ‘/tmp’

# ==================== 크롤링 대상 주식 (50개) ====================

STOCKS = [
‘AAPL’, ‘MSFT’, ‘GOOGL’, ‘AMZN’, ‘NVDA’,
‘TSLA’, ‘META’, ‘NFLX’, ‘ADBE’, ‘CRM’,
‘INTC’, ‘AMD’, ‘QCOM’, ‘CSCO’, ‘ORCL’,
‘AVGO’, ‘ASML’, ‘LRCX’, ‘AMAT’, ‘MCHP’,
‘MU’, ‘MRVL’, ‘KLAC’, ‘SNPS’, ‘CDNS’,
‘TEAM’, ‘DXCM’, ‘SPLK’, ‘OKTA’, ‘CRWD’,
‘SNOW’, ‘FTNT’, ‘PALO’, ‘NET’, ‘PANW’,
‘CHKP’, ‘CYBR’, ‘AVNT’, ‘WDAY’, ‘VEEV’,
‘RPD’, ‘ZM’, ‘DOCN’, ‘DDOG’, ‘HUBS’,
‘MSTR’, ‘COIN’, ‘MARA’, ‘RIOT’, ‘HOOD’
]

# ==================== Selenium 설정 ====================

def setup_driver():
“””
Selenium WebDriver 설정
GitHub Actions 환경에서도 작동하도록 설정
“””
chrome_options = Options()

```
# GitHub Actions 환경 감지
if os.getenv('GITHUB_ACTIONS'):
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
else:
    chrome_options.add_argument('--headless=new')

chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')

try:
    driver = webdriver.Chrome(options=chrome_options)
    print("✓ Chrome WebDriver 설정 완료")
    return driver
except Exception as e:
    print(f"✗ WebDriver 설정 실패: {e}")
    return None
```

# ==================== 데이터 크롤링 ====================

def crawl_quarterly_revenue(driver, stock):
“””
특정 주식의 5년간 Quarterly Revenue 데이터 크롤링
“””
url = f”https://www.financecharts.com/stocks/{stock}/income-statement/revenue”

```
try:
    print(f"[{stock}] 크롤링 중...", end=" ")
    driver.get(url)
    
    # 페이지 로딩 대기 (최대 10초)
    wait = WebDriverWait(driver, 10)
    
    # 테이블이 로드될 때까지 대기
    try:
        wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "table")))
    except:
        print(f"⚠ 테이블 로드 실패")
        return None
    
    time.sleep(2)  # 추가 로딩 시간
    
    # 테이블 데이터 추출
    table_data = extract_table_data(driver)
    
    if table_data is None or len(table_data) == 0:
        print("✗ 데이터 추출 실패")
        return None
    
    print(f"✓ {len(table_data)} 행 추출")
    return {
        'stock': stock,
        'data': table_data,
        'timestamp': datetime.now().isoformat(),
        'url': url
    }
    
except Exception as e:
    print(f"✗ 오류: {str(e)[:50]}")
    return None
```

def extract_table_data(driver):
“””
페이지에서 테이블 데이터 추출
“””
try:
# 모든 테이블 찾기
tables = driver.find_elements(By.TAG_NAME, “table”)

```
    if not tables:
        return None
    
    # 첫 번째 테이블 선택 (보통 Revenue 데이터)
    table = tables[0]
    
    # 행(row) 데이터 추출
    rows = table.find_elements(By.TAG_NAME, "tr")
    
    data = []
    headers = []
    
    for idx, row in enumerate(rows):
        cells = row.find_elements(By.TAG_NAME, "td")
        if not cells:
            # 헤더 행
            cells = row.find_elements(By.TAG_NAME, "th")
            if cells and idx == 0:
                headers = [cell.text.strip() for cell in cells]
        else:
            # 데이터 행
            row_data = [cell.text.strip() for cell in cells]
            if row_data:
                data.append(row_data)
    
    # DataFrame으로 변환
    if headers and data:
        df = pd.DataFrame(data, columns=headers)
        return df.to_dict('records')
    
    return data if data else None
    
except Exception as e:
    print(f"데이터 추출 오류: {e}")
    return None
```

# ==================== 메인 크롤링 ====================

def main():
print(”=”*80)
print(“📊 FinanceCharts.com - Quarterly Revenue 크롤링”)
print(”=”*80)
print(f”⏰ 시작 시간: {datetime.now().strftime(’%Y-%m-%d %H:%M:%S’)}”)
print(f”📈 크롤링 주식: {len(STOCKS)}개\n”)

```
# WebDriver 설정
driver = setup_driver()
if driver is None:
    print("❌ WebDriver 설정 실패")
    return

all_results = []
success_count = 0
fail_count = 0

try:
    # 50개 주식 크롤링
    for idx, stock in enumerate(STOCKS, 1):
        print(f"[{idx:2d}/{len(STOCKS)}] ", end="")
        
        result = crawl_quarterly_revenue(driver, stock)
        
        if result:
            all_results.append(result)
            success_count += 1
        else:
            fail_count += 1
        
        # Rate limiting (1초 대기)
        time.sleep(1)

finally:
    driver.quit()
    print("\n✓ WebDriver 종료")

# ==================== 결과 저장 ====================
print("\n" + "="*80)
print("📁 결과 저장 중...")
print("="*80)

# JSON으로 저장 (전체 데이터)
json_path = f'{OUTPUT_DIR}/quarterly_revenue_data.json'
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print(f"✓ JSON 저장: {json_path}")

# CSV로 저장 (요약)
csv_data = []
for result in all_results:
    if result['data']:
        for row in result['data']:
            csv_data.append({
                'Stock': result['stock'],
                **row
            })

if csv_data:
    df_csv = pd.DataFrame(csv_data)
    csv_path = f'{OUTPUT_DIR}/quarterly_revenue_summary.csv'
    df_csv.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✓ CSV 저장: {csv_path}")

# ==================== 요약 리포트 ====================
print("\n" + "="*80)
print("📊 크롤링 결과 요약")
print("="*80)
print(f"✓ 성공: {success_count}개")
print(f"✗ 실패: {fail_count}개")
print(f"📈 총 {len(all_results)}개 주식 데이터 수집")
print(f"⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ==================== Telegram 알림 ====================
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    print("\n[Telegram 알림 전송 중...]")
    
    telegram_msg = f"""
```

📊 FinanceCharts Quarterly Revenue 크롤링 완료

⏰ 시간: {datetime.now().strftime(’%Y-%m-%d %H:%M:%S’)}

━━━━━━━━━━━━━━━━━━━━━
📈 크롤링 결과
━━━━━━━━━━━━━━━━━━━━━
✓ 성공: {success_count}/50개
✗ 실패: {fail_count}/50개

📊 수집된 데이터:

- 총 {len(all_results)}개 주식
- {sum(len(r[‘data’]) if r[‘data’] else 0 for r in all_results)}개 Quarterly Records

💾 저장 위치:

- JSON: quarterly_revenue_data.json
- CSV: quarterly_revenue_summary.csv

🎯 크롤링 대상 주식:
{’, ’.join(STOCKS[:10])}… (총 50개)
“””

```
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": telegram_msg},
            timeout=10
        )
        print("✓ Telegram 메시지 전송 완료")
    except Exception as e:
        print(f"✗ Telegram 전송 실패: {e}")

print("\n" + "="*80)
print("✅ 크롤링 완료!")
print("="*80)
```

if **name** == “**main**”:
main()