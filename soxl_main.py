import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import os
import json
import requests
from io import BytesIO

warnings.filterwarnings('ignore')

# ==================== 환경 변수 설정 ====================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
OUTPUT_DIR = '/tmp'  # Cloud Run 임시 디렉토리

# ==================== 데이터 설정 ====================
def get_soxl_data():
    """
    SOXL 데이터 다운로드
    인터넷 연결이 없으면 샘플 데이터 생성
    """
    print("SOXL 데이터 다운로드 중...")
    try:
        soxl = yf.download('SOXL', start='2015-01-01', end=datetime.now().strftime('%Y-%m-%d'), progress=False)
        if soxl is None or len(soxl) == 0:
            raise Exception("Empty data")
        return soxl
    except Exception as e:
        print(f"⚠ 데이터 다운로드 실패 ({type(e).__name__})")
        print(" 샘플 데이터로 진행합니다...\n")
        return generate_sample_data()

def generate_sample_data():
    """
    시뮬레이션 데이터 생성 (실제 테스트용)
    SOXL의 특성을 반영한 현실적인 데이터
    """
    dates = pd.date_range('2015-01-01', periods=2800, freq='D')
    np.random.seed(42)
    
    # SOXL: 반도체 ETF - 높은 변동성, 우상향 추세
    returns = np.random.normal(0.0005, 0.025, 2800)  # 일일 수익률
    price = 20 * np.exp(np.cumsum(returns))  # 기하 브라운 운동
    
    data = pd.DataFrame({
        'Open': price * (1 + np.random.normal(0, 0.002, len(price))),
        'High': price * (1 + np.abs(np.random.normal(0, 0.015, len(price)))),
        'Low': price * (1 - np.abs(np.random.normal(0, 0.015, len(price)))),
        'Close': price,
        'Volume': np.random.randint(1000000, 10000000, len(price))
    }, index=dates)
    
    return data

# ==================== 기본 설정 ====================
INITIAL_CAPITAL = 10000000  # 1천만원
WEEKLY_BASE_INVESTMENT = INITIAL_CAPITAL / 52  # 주 1회 투자 기본 금액

# 데이터 로드
soxl = get_soxl_data()

# 기술 지표 계산
data = soxl[['Close']].copy()
data['SMA200'] = data['Close'].rolling(window=200).mean()
data['Daily_Return'] = data['Close'].pct_change()
data['Volatility'] = data['Daily_Return'].rolling(window=20).std()  # 20일 변동성

print(f"✓ 백테스트 기간: {data.index[0].date()} ~ {data.index[-1].date()}")
print(f"✓ 총 거래일: {len(data)}")
print(f"✓ 초기 자본: ₩{INITIAL_CAPITAL:,.0f}")
print(f"✓ 주간 기본 투자액: ₩{WEEKLY_BASE_INVESTMENT:,.0f}")

# ==================== 전략 1: 200일선 기준 매수/매도 ====================
def strategy_sma200(data, initial_capital=INITIAL_CAPITAL):
    """
    200일선을 기준으로 한 추세 추종 전략
    - 가격이 SMA200 위: 풀포지션 매수 유지
    - 가격이 SMA200 아래: 전량 매도
    """
    portfolio_value = [initial_capital]
    shares_held = 0
    position_value = [0]
    trades = []
    cash = initial_capital
    
    for i in range(1, len(data)):
        close = data['Close'].iloc[i]
        sma200 = data['SMA200'].iloc[i]
        
        if pd.isna(sma200):
            portfolio_value.append(portfolio_value[-1])
            position_value.append(shares_held * close)
            continue
        
        # 이전 상태
        prev_price = data['Close'].iloc[i-1]
        prev_sma200 = data['SMA200'].iloc[i-1]
        
        # 골든크로스: 가격이 SMA200을 아래서 위로 돌파
        if pd.notna(prev_sma200) and (prev_price <= prev_sma200) and (close > sma200):
            if cash > 0:
                shares_to_buy = cash / close
                shares_held += shares_to_buy
                trades.append({
                    'date': data.index[i], 
                    'type': 'BUY', 
                    'price': close, 
                    'shares': shares_to_buy,
                    'amount': cash
                })
                cash = 0
        
        # 데드크로스: 가격이 SMA200을 위에서 아래로 돌파
        elif pd.notna(prev_sma200) and (prev_price >= prev_sma200) and (close < sma200):
            if shares_held > 0:
                cash = shares_held * close
                trades.append({
                    'date': data.index[i], 
                    'type': 'SELL', 
                    'price': close, 
                    'shares': shares_held,
                    'amount': cash
                })
                shares_held = 0
        
        # 포트폴리오 가치
        current_value = cash + (shares_held * close)
        portfolio_value.append(current_value)
        position_value.append(shares_held * close)
    
    return pd.Series(portfolio_value, index=data.index), trades

# ==================== 전략 2: 고정 DCA ====================
def strategy_fixed_dca(data, initial_capital=INITIAL_CAPITAL, weekly_investment=WEEKLY_BASE_INVESTMENT):
    """
    Dollar Cost Averaging - 매주 일정 금액 투자
    """
    portfolio_value = [initial_capital]
    shares_held = 0
    cash = initial_capital
    last_investment_date = data.index[0]
    investment_history = []
    
    for i in range(1, len(data)):
        close = data['Close'].iloc[i]
        current_date = data.index[i]
        
        # 7일(1주) 마다 투자
        days_since = (current_date - last_investment_date).days
        
        if days_since >= 7 and cash >= weekly_investment:
            shares_bought = weekly_investment / close
            shares_held += shares_bought
            cash -= weekly_investment
            investment_history.append({
                'date': current_date,
                'price': close,
                'shares': shares_bought,
                'amount': weekly_investment
            })
            last_investment_date = current_date
        
        current_value = cash + (shares_held * close)
        portfolio_value.append(current_value)
    
    return pd.Series(portfolio_value, index=data.index), investment_history

# ==================== 전략 3: Inverse Volatility DCA ====================
def strategy_inv_volatility_dca(data, initial_capital=INITIAL_CAPITAL, weekly_base=WEEKLY_BASE_INVESTMENT):
    """
    변동성 기반 DCA
    - 변동성 낮음 → 더 많이 투자 (좋은 매수 기회)
    - 변동성 높음 → 적게 투자 (위험)
    """
    portfolio_value = [initial_capital]
    shares_held = 0
    cash = initial_capital
    last_investment_date = data.index[0]
    investment_history = []
    
    for i in range(1, len(data)):
        close = data['Close'].iloc[i]
        current_date = data.index[i]
        vol = data['Volatility'].iloc[i]
        
        days_since = (current_date - last_investment_date).days
        
        if days_since >= 7 and not pd.isna(vol) and vol > 0:
            # 역 변동성 가중치
            inv_vol_weight = 1 / (vol + 0.0001)
            
            # 최근 20일 평균 역변동성으로 정규화
            recent_vols = data['Volatility'].iloc[max(0, i-20):i+1]
            avg_inv_vol = (1 / (recent_vols + 0.0001)).mean()
            normalized_weight = inv_vol_weight / avg_inv_vol if avg_inv_vol > 0 else 1.0
            
            # 극단치 제한
            normalized_weight = np.clip(normalized_weight, 0.5, 1.5)
            
            investment_amount = weekly_base * normalized_weight
            
            if cash >= investment_amount:
                shares_bought = investment_amount / close
                shares_held += shares_bought
                cash -= investment_amount
                investment_history.append({
                    'date': current_date,
                    'price': close,
                    'shares': shares_bought,
                    'amount': investment_amount,
                    'volatility': vol,
                    'weight': normalized_weight
                })
                last_investment_date = current_date
            
            current_value = cash + (shares_held * close)
            portfolio_value.append(current_value)
    
    return pd.Series(portfolio_value, index=data.index), investment_history

# ==================== 성과 지표 계산 ====================
def calculate_metrics(portfolio_values, initial_capital):
    """
    종합 성과 지표 계산
    """
    pv = np.array(portfolio_values)
    
    # 일일 수익률
    daily_returns = np.diff(pv) / pv[:-1]
    daily_returns = daily_returns[~np.isnan(daily_returns)]
    
    # 1. 총 수익률
    total_return = (pv[-1] - initial_capital) / initial_capital
    
    # 2. CAGR
    days = len(pv) - 1
    years = days / 252
    cagr = (pv[-1] / initial_capital) ** (1 / years) - 1 if years > 0 else 0
    
    # 3. 최종 가치 및 수익금
    final_value = pv[-1]
    total_profit = pv[-1] - initial_capital
    
    # 4. MDD (Maximum Drawdown)
    cummax = np.maximum.accumulate(pv)
    drawdown = (pv - cummax) / cummax
    mdd = np.min(drawdown)
    
    # 5. 손실 기간 분석
    is_losing = pv < initial_capital
    losing_periods = []
    start_idx = None
    
    for idx, losing in enumerate(is_losing):
        if losing and start_idx is None:
            start_idx = idx
        elif not losing and start_idx is not None:
            losing_periods.append(idx - start_idx)
            start_idx = None
    
    if start_idx is not None:
        losing_periods.append(len(is_losing) - start_idx)
    
    max_losing_days = max(losing_periods) if losing_periods else 0
    avg_losing_days = np.mean(losing_periods) if losing_periods else 0
    
    # 6. 추가 지표
    sharpe_ratio = (np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) 
                    if np.std(daily_returns) > 0 else 0)
    win_rate = (np.sum(daily_returns > 0) / len(daily_returns) * 100 
                if len(daily_returns) > 0 else 0)
    
    # 7. 복구 시간 (MDD 이후)
    max_dd_idx = np.argmin(drawdown)
    recovery_time = 0
    for idx in range(max_dd_idx, len(pv)):
        if pv[idx] >= cummax[max_dd_idx]:
            recovery_time = idx - max_dd_idx
            break
    
    return {
        'Total Return': total_return,
        'Total Return %': total_return * 100,
        'CAGR': cagr,
        'CAGR %': cagr * 100,
        'Final Value': final_value,
        'Total Profit': total_profit,
        'MDD': mdd,
        'MDD %': mdd * 100,
        'Max Losing Days': int(max_losing_days),
        'Avg Losing Days': avg_losing_days,
        'Sharpe Ratio': sharpe_ratio,
        'Win Rate %': win_rate,
        'Recovery Days': recovery_time,
        'Daily Return Mean': np.mean(daily_returns),
        'Daily Return Std': np.std(daily_returns),
    }

# ==================== 백테스트 실행 ====================
print("\n" + "="*70)
print("백테스트 실행 중...")
print("="*70)

print("\n[1/3] 200일선 전략 실행 중...")
pv_sma200, trades_sma200 = strategy_sma200(data)
metrics_sma200 = calculate_metrics(pv_sma200.values, INITIAL_CAPITAL)
print(f" ✓ 총 {len(trades_sma200)} 회 거래")

print("\n[2/3] 고정 DCA 전략 실행 중...")
pv_fixed_dca, inv_fixed_dca = strategy_fixed_dca(data)
metrics_fixed_dca = calculate_metrics(pv_fixed_dca.values, INITIAL_CAPITAL)
print(f" ✓ 총 {len(inv_fixed_dca)} 회 투자")

print("\n[3/3] Inverse Volatility DCA 전략 실행 중...")
pv_inv_vol_dca, inv_inv_vol_dca = strategy_inv_volatility_dca(data)
metrics_inv_vol_dca = calculate_metrics(pv_inv_vol_dca.values, INITIAL_CAPITAL)
print(f" ✓ 총 {len(inv_inv_vol_dca)} 회 투자")

# ==================== 결과 출력 ====================
print("\n" + "="*80)
print(" 백테스트 결과 요약")
print("="*80)

# 성과 지표 비교 DataFrame
results = pd.DataFrame({
    '200일선 전략': metrics_sma200,
    '고정 DCA': metrics_fixed_dca,
    'Inv Vol DCA': metrics_inv_vol_dca
})

# 1. 수익성 지표
print("\n[수익성 지표]")
print("-" * 80)
print(f"{'지표':<20} {'200일선 전략':>18} {'고정 DCA':>18} {'Inv Vol DCA':>18}")
print("-" * 80)
print(f"{'총 수익률':<20} {metrics_sma200['Total Return %']:>17.2f}% {metrics_fixed_dca['Total Return %']:>17.2f}% {metrics_inv_vol_dca['Total Return %']:>17.2f}%")
print(f"{'CAGR':<20} {metrics_sma200['CAGR %']:>17.2f}% {metrics_fixed_dca['CAGR %']:>17.2f}% {metrics_inv_vol_dca['CAGR %']:>17.2f}%")
print(f"{'최종 자산':<20} ₩{metrics_sma200['Final Value']:>16,.0f} ₩{metrics_fixed_dca['Final Value']:>16,.0f} ₩{metrics_inv_vol_dca['Final Value']:>16,.0f}")
print(f"{'총 수익금':<20} ₩{metrics_sma200['Total Profit']:>16,.0f} ₩{metrics_fixed_dca['Total Profit']:>16,.0f} ₩{metrics_inv_vol_dca['Total Profit']:>16,.0f}")

# 2. 위험 지표
print("\n[위험 지표]")
print("-" * 80)
print(f"{'지표':<20} {'200일선 전략':>18} {'고정 DCA':>18} {'Inv Vol DCA':>18}")
print("-" * 80)
print(f"{'MDD':<20} {metrics_sma200['MDD %']:>17.2f}% {metrics_fixed_dca['MDD %']:>17.2f}% {metrics_inv_vol_dca['MDD %']:>17.2f}%")
print(f"{'Sharpe Ratio':<20} {metrics_sma200['Sharpe Ratio']:>18.3f} {metrics_fixed_dca['Sharpe Ratio']:>18.3f} {metrics_inv_vol_dca['Sharpe Ratio']:>18.3f}")
print(f"{'승률 (일일)':<20} {metrics_sma200['Win Rate %']:>17.2f}% {metrics_fixed_dca['Win Rate %']:>17.2f}% {metrics_inv_vol_dca['Win Rate %']:>17.2f}%")
print(f"{'일일 수익률 표준편차':<20} {metrics_sma200['Daily Return Std']:>18.4f} {metrics_fixed_dca['Daily Return Std']:>18.4f} {metrics_inv_vol_dca['Daily Return Std']:>18.4f}")

# 3. 손실 기간
print("\n[손실 기간 분석]")
print("-" * 80)
print(f"{'지표':<20} {'200일선 전략':>18} {'고정 DCA':>18} {'Inv Vol DCA':>18}")
print("-" * 80)
print(f"{'최장 손실 기간':<20} {metrics_sma200['Max Losing Days']:>17} 일 {metrics_fixed_dca['Max Losing Days']:>17} 일 {metrics_inv_vol_dca['Max Losing Days']:>17} 일")
print(f"{'평균 손실 기간':<20} {metrics_sma200['Avg Losing Days']:>17.1f} 일 {metrics_fixed_dca['Avg Losing Days']:>17.1f} 일 {metrics_inv_vol_dca['Avg Losing Days']:>17.1f} 일")
print(f"{'MDD 복구 기간':<20} {metrics_sma200['Recovery Days']:>17} 일 {metrics_fixed_dca['Recovery Days']:>17} 일 {metrics_inv_vol_dca['Recovery Days']:>17} 일")

# ==================== 시각화 ====================
print("\n[그래프 생성 중...]")
fig = plt.figure(figsize=(16, 12))
gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

# 1. 포트폴리오 가치
ax1 = fig.add_subplot(gs[0, :])
ax1.plot(pv_sma200.index, pv_sma200.values / 1e6, label='200일선 전략', linewidth=2, alpha=0.8)
ax1.plot(pv_fixed_dca.index, pv_fixed_dca.values / 1e6, label='고정 DCA', linewidth=2, alpha=0.8)
ax1.plot(pv_inv_vol_dca.index, pv_inv_vol_dca.values / 1e6, label='Inv Vol DCA', linewidth=2, alpha=0.8)
ax1.axhline(y=10, color='gray', linestyle='--', alpha=0.5, linewidth=1)
ax1.set_title('포트폴리오 가치 추이', fontweight='bold', fontsize=12)
ax1.set_ylabel('가치 (백만원)')
ax1.set_xlabel('날짜')
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)

# 2. 누적 수익률
ax2 = fig.add_subplot(gs[1, 0])
returns_sma200 = (pv_sma200.values / INITIAL_CAPITAL - 1) * 100
returns_fixed_dca = (pv_fixed_dca.values / INITIAL_CAPITAL - 1) * 100
returns_inv_vol = (pv_inv_vol_dca.values / INITIAL_CAPITAL - 1) * 100
ax2.plot(pv_sma200.index, returns_sma200, label='200일선', linewidth=2)
ax2.plot(pv_fixed_dca.index, returns_fixed_dca, label='고정 DCA', linewidth=2)
ax2.plot(pv_inv_vol_dca.index, returns_inv_vol, label='Inv Vol', linewidth=2)
ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
ax2.fill_between(pv_sma200.index, 0, returns_sma200, alpha=0.1)
ax2.set_title('누적 수익률', fontweight='bold', fontsize=12)
ax2.set_ylabel('수익률 (%)')
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3)

# 3. Drawdown
ax3 = fig.add_subplot(gs[1, 1])
def calc_drawdown(pv):
    cummax = np.maximum.accumulate(pv)
    return ((pv - cummax) / cummax) * 100

dd_sma200 = calc_drawdown(pv_sma200.values)
dd_fixed = calc_drawdown(pv_fixed_dca.values)
dd_invvol = calc_drawdown(pv_inv_vol_dca.values)
ax3.fill_between(pv_sma200.index, dd_sma200, alpha=0.5, label='200일선')
ax3.fill_between(pv_fixed_dca.index, dd_fixed, alpha=0.5, label='고정 DCA')
ax3.fill_between(pv_inv_vol_dca.index, dd_invvol, alpha=0.5, label='Inv Vol')
ax3.set_title('Drawdown 추이', fontweight='bold', fontsize=12)
ax3.set_ylabel('Drawdown (%)')
ax3.legend(fontsize=9)
ax3.grid(True, alpha=0.3)

# 4. 성과 지표 비교
ax4 = fig.add_subplot(gs[2, 0])
metrics_to_plot = ['Total Return %', 'CAGR %', 'Sharpe Ratio']
x = np.arange(len(metrics_to_plot))
width = 0.25
values_sma = [metrics_sma200['Total Return %'], metrics_sma200['CAGR %'], metrics_sma200['Sharpe Ratio']]
values_dca = [metrics_fixed_dca['Total Return %'], metrics_fixed_dca['CAGR %'], metrics_fixed_dca['Sharpe Ratio']]
values_inv = [metrics_inv_vol_dca['Total Return %'], metrics_inv_vol_dca['CAGR %'], metrics_inv_vol_dca['Sharpe Ratio']]
ax4.bar(x - width, values_sma, width, label='200일선', alpha=0.8)
ax4.bar(x, values_dca, width, label='고정 DCA', alpha=0.8)
ax4.bar(x + width, values_inv, width, label='Inv Vol', alpha=0.8)
ax4.set_ylabel('값')
ax4.set_title('주요 지표 비교', fontweight='bold', fontsize=12)
ax4.set_xticks(x)
ax4.set_xticklabels(['수익률', 'CAGR', 'Sharpe×100'])
ax4.legend(fontsize=9)
ax4.grid(True, alpha=0.3, axis='y')

# 5. 위험-수익 산점도
ax5 = fig.add_subplot(gs[2, 1])
strategies_list = ['200일선', '고정 DCA', 'Inv Vol']
colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
risks = [abs(metrics_sma200['MDD %']), abs(metrics_fixed_dca['MDD %']), abs(metrics_inv_vol_dca['MDD %'])]
returns_list = [metrics_sma200['Total Return %'], metrics_fixed_dca['Total Return %'], metrics_inv_vol_dca['Total Return %']]
ax5.scatter(risks, returns_list, s=300, alpha=0.6, c=colors)
for i, strategy in enumerate(strategies_list):
    ax5.annotate(strategy, (risks[i], returns_list[i]), 
                xytext=(5, 5), textcoords='offset points', fontsize=9)
ax5.set_xlabel('위험 (MDD %)', fontweight='bold')
ax5.set_ylabel('수익 (총 수익률 %)', fontweight='bold')
ax5.set_title('위험-수익 트레이드오프', fontweight='bold', fontsize=12)
ax5.grid(True, alpha=0.3)

plt.suptitle('SOXL 백테스트 결과 - 3가지 전략 비교', fontsize=16, fontweight='bold', y=0.995)
plt.savefig(f'{OUTPUT_DIR}/soxl_backtest_result.png', dpi=150, bbox_inches='tight')
print(f"✓ 그래프 저장: {OUTPUT_DIR}/soxl_backtest_result.png")

# ==================== 상세 데이터 저장 ====================
print("\n[결과 저장 중...]")
detail_df = pd.DataFrame({
    'Date': data.index,
    'SOXL_Close': data['Close'].values,
    'SMA200': data['SMA200'].values,
    'Volatility': data['Volatility'].values,
    'Strategy1_Portfolio': pv_sma200.values,
    'Strategy2_Portfolio': pv_fixed_dca.values,
    'Strategy3_Portfolio': pv_inv_vol_dca.values,
    'Return1_%': returns_sma200,
    'Return2_%': returns_fixed_dca,
    'Return3_%': returns_inv_vol,
})
detail_df.to_csv(f'{OUTPUT_DIR}/soxl_backtest_detail.csv', index=False)
print(f"✓ 상세 데이터 저장: {OUTPUT_DIR}/soxl_backtest_detail.csv")

results.T.to_csv(f'{OUTPUT_DIR}/soxl_backtest_summary.csv')
print(f"✓ 요약 결과 저장: {OUTPUT_DIR}/soxl_backtest_summary.csv")

# ==================== Telegram 알림 ====================
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    print("\n[Telegram 알림 전송 중...]")
    
    # 요약 메시지
    summary_msg = f"""
🎯 SOXL 백테스트 완료

⏰ 기간: {data.index[0].date()} ~ {data.index[-1].date()}
💰 초기자본: ₩{INITIAL_CAPITAL:,.0f}

━━━━━━━━━━━━━━━━━━━━━
📊 최고 수익률 전략
━━━━━━━━━━━━━━━━━━━━━
전략: 200일선 전략
수익률: {metrics_sma200['Total Return %']:.2f}%
CAGR: {metrics_sma200['CAGR %']:.2f}%
최종자산: ₩{metrics_sma200['Final Value']:,.0f}

━━━━━━━━━━━━━━━━━━━━━
⚖️ 리스크 조정 수익 (Sharpe)
━━━━━━━━━━━━━━━━━━━━━
전략: Inv Vol DCA
Sharpe Ratio: {metrics_inv_vol_dca['Sharpe Ratio']:.3f}
MDD: {metrics_inv_vol_dca['MDD %']:.2f}%

━━━━━━━━━━━━━━━━━━━━━
📈 세부 비교
━━━━━━━━━━━━━━━━━━━━━
[200일선 전략]
├─ 수익률: {metrics_sma200['Total Return %']:.2f}%
├─ MDD: {metrics_sma200['MDD %']:.2f}%
└─ Sharpe: {metrics_sma200['Sharpe Ratio']:.3f}

[고정 DCA]
├─ 수익률: {metrics_fixed_dca['Total Return %']:.2f}%
├─ MDD: {metrics_fixed_dca['MDD %']:.2f}%
└─ Sharpe: {metrics_fixed_dca['Sharpe Ratio']:.3f}

[Inv Vol DCA]
├─ 수익률: {metrics_inv_vol_dca['Total Return %']:.2f}%
├─ MDD: {metrics_inv_vol_dca['MDD %']:.2f}%
└─ Sharpe: {metrics_inv_vol_dca['Sharpe Ratio']:.3f}
"""
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": summary_msg},
            timeout=10
        )
        print("✓ 요약 메시지 전송 완료")
    except Exception as e:
        print(f"✗ 요약 메시지 전송 실패: {e}")
    
    # 그래프 전송
    try:
        with open(f'{OUTPUT_DIR}/soxl_backtest_result.png', 'rb') as graph:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                data={"chat_id": TELEGRAM_CHAT_ID},
                files={"photo": graph},
                timeout=10
            )
        print("✓ 그래프 전송 완료")
    except Exception as e:
        print(f"✗ 그래프 전송 실패: {e}")

print("\n" + "="*80)
print("✅ 백테스트 완료!")
print("="*80)
