# 📚 SOXL 백테스트 - 실행 가이드

## 전체 순서

```
1. GitHub 저장소 생성
   ↓
2. 코드 & 파일 push
   ↓
3. GCP 프로젝트 설정
   ↓
4. GitHub Secrets 추가
   ↓
5. GitHub Actions 실행
   ↓
6. Telegram으로 결과 수신
```

---

## 단계별 가이드

### 1️⃣ GitHub 저장소 생성

**방법 A: GitHub 웹사이트 (추천)**
```
1. github.com 접속 → 우상단 + 아이콘 → New repository
2. Repository name: soxl-backtest
3. Public 또는 Private 선택
4. Create repository 클릭
```

**방법 B: GitHub CLI**
```bash
gh repo create soxl-backtest --public
```

### 2️⃣ 로컬에서 GitHub에 Push

```bash
# 저장소 클론 (로컬에 다운로드)
git clone https://github.com/YOUR_USERNAME/soxl-backtest.git
cd soxl-backtest

# 파일 추가 (다음 파일들을 여기에 복사)
# - soxl_main.py
# - requirements.txt
# - Dockerfile
# - README.md
# - .gitignore

# Git 커밋 & 푸시
git add .
git commit -m "Initial commit: Add SOXL backtest with Cloud Run"
git push origin main
```

또는 GitHub 웹사이트에서 직접 파일 업로드:
```
저장소 홈 → Add file → Upload files → 드래그앤드롭
```

### 3️⃣ Google Cloud Platform 설정

#### 3-1. GCP 계정 준비
- Google Cloud 콘솔 접속: https://console.cloud.google.com
- 프로젝트 생성 또는 기존 프로젝트 선택

#### 3-2. 자동 설정 스크립트 실행

```bash
# 이 파일들을 다운로드한 디렉토리에서
chmod +x setup-gcp.sh
./setup-gcp.sh
```

스크립트가 다음을 자동으로 해줍니다:
- GCP 프로젝트 생성
- 필요한 APIs 활성화
- Artifact Registry 저장소 생성
- 서비스 계정 생성
- 권한 설정
- GitHub Secrets 정보 출력

#### 3-3 수동 설정 (스크립트 사용 불가 시)

```bash
# 1. 프로젝트 ID 설정
gcloud config set project soxl-backtest

# 2. 필요한 APIs 활성화
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# 3. Artifact Registry 저장소 생성
gcloud artifacts repositories create docker-repo \
  --repository-format=docker \
  --location=us-central1

# 4. 서비스 계정 생성
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions"

# 5. 권한 설정
gcloud projects add-iam-policy-binding soxl-backtest \
  --member=serviceAccount:github-actions@soxl-backtest.iam.gserviceaccount.com \
  --role=roles/run.admin

# 6. 키 파일 생성
gcloud iam service-accounts keys create gcp-key.json \
  --iam-account=github-actions@soxl-backtest.iam.gserviceaccount.com
```

### 4️⃣ GitHub Secrets 추가

GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions**

**4개의 Secret 추가:**

#### Secret 1: GCP_PROJECT_ID
- Name: `GCP_PROJECT_ID`
- Value: `soxl-backtest` (또는 자신의 프로젝트 ID)

#### Secret 2: GCP_SA_KEY
- Name: `GCP_SA_KEY`
- Value: gcp-key.json 파일의 전체 내용 (JSON)
  ```bash
  cat gcp-key.json  # 내용 복사
  ```

#### Secret 3: TELEGRAM_BOT_TOKEN
- Name: `TELEGRAM_BOT_TOKEN`
- Value: Telegram 봇 토큰

**Telegram 봇 토큰 받기:**
1. Telegram에서 `@BotFather` 검색
2. `/newbot` 입력
3. 봇 이름 입력
4. 토큰 복사

#### Secret 4: TELEGRAM_CHAT_ID
- Name: `TELEGRAM_CHAT_ID`
- Value: 자신의 Telegram Chat ID

**Chat ID 확인하기:**
```bash
# 1. 봇에 메시지 보낸 후
# 2. 다음 실행:
curl https://api.telegram.org/botYOUR_TOKEN/getUpdates

# 3. 응답에서 "chat":{"id":12345678} 형태로 표시
```

### 5️⃣ GitHub Actions 워크플로우 설정

```bash
# 저장소 루트에 다음 디렉토리 & 파일 생성
mkdir -p .github/workflows
# cloud-run.yml을 .github/workflows/ 로 복사
```

또는 GitHub 웹사이트에서:
```
Actions → Set up a workflow yourself
→ 파일명: cloud-run.yml
→ 내용 붙여넣기 → Commit
```

---

## 🚀 실행 방법

### 방법 1: 수동 실행 (추천 - 첫 테스트)

1. GitHub 저장소 → **Actions** 탭
2. **SOXL Backtest on Cloud Run** 선택
3. **Run workflow** 버튼 클릭
4. 잠깐 기다렸다가 로그 확인

### 방법 2: 자동 실행 (매주)

workflow 파일에 이미 설정됨:
```yaml
schedule:
  - cron: '0 10 * * 0'  # 매주 일요일 10:00 UTC
```

### 방법 3: Code Push 트리거

코드를 push하면 자동으로 실행:
```bash
git add .
git commit -m "Update backtest code"
git push origin main
# → 자동으로 GitHub Actions 실행!
```

---

## 📊 결과 확인

### 1️⃣ Telegram 확인 (가장 편함!)
- 봇이 자동으로 요약 메시지 + 그래프 전송
- 스마트폰에서 즉시 확인 가능

### 2️⃣ GitHub Actions 로그
1. GitHub 저장소 → Actions
2. 최신 실행 선택
3. **deploy-and-run** 작업 클릭
4. 각 단계별 로그 확인

### 3️⃣ Google Cloud Run 로그
```bash
gcloud run jobs logs read soxl-backtest \
  --region=us-central1 \
  --limit=100
```

### 4️⃣ 출력 파일 확인

실행 후 생성되는 파일:
- `soxl_backtest_result.png` - 그래프
- `soxl_backtest_detail.csv` - 상세 데이터
- `soxl_backtest_summary.csv` - 요약 결과

(Cloud Storage에 저장되거나 Telegram으로 전송됨)

---

## 🆘 문제 해결

### ❌ GitHub Actions 실패

**오류: GCP_SA_KEY 형식 오류**
```
솔루션: gcp-key.json 파일의 전체 JSON을 그대로 복사
(공백, 줄바꿈 포함)
```

**오류: 권한 부족**
```bash
# 권한 다시 부여
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/run.admin
```

### ❌ Telegram 메시지 미수신

**확인 사항:**
1. TELEGRAM_BOT_TOKEN 유효성
   ```bash
   curl https://api.telegram.org/botTOKEN/getMe
   ```
2. TELEGRAM_CHAT_ID 정확성
   ```bash
   curl https://api.telegram.org/botTOKEN/getUpdates
   ```
3. 봇이 채팅에 초대되어 있는지 확인

### ❌ Cloud Run 타임아웃

백테스트가 너무 오래 걸리면:
```bash
# Dockerfile에서 timeout 증가
--timeout=3600  # 1시간으로 변경
```

### ❌ Docker 빌드 실패

```bash
# 로컬에서 먼저 테스트
docker build -t soxl-backtest .
docker run soxl-backtest
```

---

## 💰 비용 (월)

| 항목 | 무료 한도 | 초과 비용 |
|------|---------|---------|
| Cloud Run | 180,000 vCPU-초 | $0.00002/초 |
| Artifact Registry | 0.5GB | $0.50/GB |
| **월 1회 실행 기준** | **거의 무료** | **~$0.01** |

---

## 📚 추가 자료

- [Google Cloud Run 문서](https://cloud.google.com/run/docs)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

## 🎉 완료!

이제 모든 준비가 끝났습니다.

**다음을 확인하세요:**
- ✅ GitHub 저장소에 모든 파일 있음
- ✅ GCP 프로젝트 생성 및 APIs 활성화
- ✅ GitHub Secrets 4개 모두 추가
- ✅ GitHub Actions 워크플로우 파일 있음

**이제 실행하면 됩니다!**
```bash
# GitHub Actions → Run workflow 클릭
# 또는 매주 자동 실행
```

질문이 있으면 README.md 또는 로그를 확인하세요! 🚀
