# ⚡ SOXL 백테스트 × Google Cloud Run - 웹사이트 방법 (5분 시작)

> **GitHub 웹사이트에서 모든 파일을 업로드하고, GCP는 웹 콘솔에서 설정하는 방법**

---

## 📋 준비물

- ✅ GitHub 계정
- ✅ Google Cloud 계정
- ✅ Telegram 계정 (봇 토큰 & Chat ID)
- ✅ 9개 파일 (다운로드된 것들)

---

## 🚀 3단계 실행 플로우

```
1️⃣ GitHub에 파일 업로드 (3분)
     ↓
2️⃣ GCP 웹 콘솔에서 설정 (5분)
     ↓
3️⃣ GitHub Secrets 추가 (2분)
     ↓
4️⃣ GitHub Actions 실행 (1분)
     ↓
✅ Telegram으로 결과 수신!
```

---

# 1️⃣ GitHub에 파일 업로드 (3분)

## Step 1: 저장소 생성

```
1. github.com 접속 → 우상단 + 아이콘
2. "New repository" 클릭
3. Repository name: soxl-backtest
4. Description: "SOXL Backtest with Cloud Run"
5. Public 선택 (Private도 가능)
6. "Create repository" 클릭
```

## Step 2: 8개 파일 업로드

```
저장소 홈 → "Add file" 버튼 → "Upload files"
```

**9개 파일 모두 선택해서 드래그앤드롭:**
- ✅ soxl_main.py
- ✅ requirements.txt
- ✅ Dockerfile
- ✅ README.md
- ✅ GUIDE_KR.md
- ✅ QUICK_START.md
- ✅ setup-gcp.sh
- ✅ .gitignore

**그 후 "Commit changes" 클릭**

## Step 3: cloud-run.yml 파일 따로 생성

```
저장소 홈 → "Add file" → "Create new file"

파일 경로 입력:
.github/workflows/cloud-run.yml

아래 내용 복사해서 붙여넣기:
```

```yaml
name: SOXL Backtest on Cloud Run

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 10 * * 0'  # 매주 일요일 10:00 UTC
  workflow_dispatch:      # 수동 트리거

env:
  GCP_REGION: us-central1
  GCP_SERVICE_NAME: soxl-backtest

jobs:
  deploy-and-run:
    runs-on: ubuntu-latest
    
    permissions:
      contents: read
      id-token: write
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}
      
      - name: Configure Docker authentication
        run: |
          gcloud auth configure-docker ${{ env.GCP_REGION }}-docker.pkg.dev
      
      - name: Build Docker image
        run: |
          docker build -t ${{ env.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/docker-repo/${{ env.GCP_SERVICE_NAME }}:latest .
      
      - name: Push Docker image
        run: |
          docker push ${{ env.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/docker-repo/${{ env.GCP_SERVICE_NAME }}:latest
      
      - name: Deploy to Cloud Run Job
        run: |
          gcloud run jobs create ${{ env.GCP_SERVICE_NAME }} \
            --image=${{ env.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/docker-repo/${{ env.GCP_SERVICE_NAME }}:latest \
            --region=${{ env.GCP_REGION }} \
            --memory=2Gi \
            --cpu=1 \
            --timeout=1800 \
            --set-env-vars="TELEGRAM_BOT_TOKEN=${{ secrets.TELEGRAM_BOT_TOKEN }},TELEGRAM_CHAT_ID=${{ secrets.TELEGRAM_CHAT_ID }}" \
            --no-wait \
            --overwrite 2>/dev/null || echo "Job already exists, updating..."
      
      - name: Execute Cloud Run Job
        run: |
          gcloud run jobs execute ${{ env.GCP_SERVICE_NAME }} \
            --region=${{ env.GCP_REGION }} \
            --wait
      
      - name: Show execution logs
        if: always()
        run: |
          echo "=== Cloud Run Job Logs ==="
          gcloud run jobs logs read ${{ env.GCP_SERVICE_NAME }} \
            --region=${{ env.GCP_REGION }} \
            --limit=50
```

**"Commit new file" 클릭**

---

# 2️⃣ GCP 웹 콘솔에서 설정 (5분)

## Step 1: Google Cloud 콘솔 접속

```
https://console.cloud.google.com
→ Google 계정으로 로그인
```

## Step 2: 프로젝트 생성

```
우상단 "Select a project" → "NEW PROJECT"
Project name: soxl-backtest
→ "CREATE"
```

## Step 3: API 활성화 (Cloud Shell에서)

```
우상단 ">_" 아이콘 (Cloud Shell) 클릭
→ 아래 명령어 복사해서 붙여넣기:
```

```bash
# 한 줄씩 실행
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

**Enter 눌러서 실행**

## Step 4: Artifact Registry 생성 (Cloud Shell에서)

```bash
gcloud artifacts repositories create docker-repo \
  --repository-format=docker \
  --location=us-central1 \
  --quiet
```

## Step 5: 서비스 계정 생성 (Cloud Shell에서)

```bash
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions for SOXL" \
  --quiet
```

## Step 6: 권한 설정 (Cloud Shell에서)

```bash
PROJECT_ID=$(gcloud config get-value project)

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/run.admin \
  --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/artifactregistry.repositoryAdmin \
  --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/cloudbuild.builds.editor \
  --quiet
```

## Step 7: 서비스 계정 키 생성 (Cloud Shell에서)

```bash
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@$(gcloud config get-value project).iam.gserviceaccount.com

cat key.json
```

**출력된 JSON 전체를 복사해두세요!**

---

# 3️⃣ GitHub Secrets 추가 (2분)

## 위치

```
GitHub 저장소 → Settings 탭 → 좌측 "Secrets and variables" 
→ "Actions" → "New repository secret"
```

## 4개 Secret 추가

### Secret 1: GCP_PROJECT_ID
```
Name: GCP_PROJECT_ID
Value: soxl-backtest (또는 생성한 프로젝트명)
```

### Secret 2: GCP_SA_KEY
```
Name: GCP_SA_KEY
Value: (위에서 복사한 key.json 전체 내용)
```

### Secret 3: TELEGRAM_BOT_TOKEN
```
Name: TELEGRAM_BOT_TOKEN
Value: (Telegram Bot 토큰)

📱 토큰 얻는 방법:
1. Telegram에서 @BotFather 검색
2. /newbot 입력
3. 봇 이름 설정
4. 토큰 복사
```

### Secret 4: TELEGRAM_CHAT_ID
```
Name: TELEGRAM_CHAT_ID
Value: (자신의 Telegram Chat ID)

📱 Chat ID 얻는 방법:
1. Telegram에서 @userinfobot 검색
2. /start 입력
3. 출력된 "id: 12345678" 복사
```

---

# 4️⃣ GitHub Actions 실행 (1분)

## 첫 번째 실행 (수동)

```
GitHub 저장소 → "Actions" 탭
→ 좌측 "SOXL Backtest on Cloud Run" 선택
→ "Run workflow" 버튼 클릭
→ "Run workflow" 다시 클릭

✅ 자동으로 실행됨!
```

## 실행 상태 확인

```
Actions 탭에서 최신 실행 보기
→ "deploy-and-run" 클릭
→ 각 단계별 로그 확인
```

---

# ✅ 확인 사항

실행 후 확인:

- ✅ **GitHub Actions 성공**: 파란색 체크 표시
- ✅ **Telegram 메시지**: 자동으로 요약 + 그래프 수신
- ✅ **실행 로그**: Actions → 최신 실행 → 로그 확인

---

# 📊 받을 Telegram 메시지 예시

```
🎯 SOXL 백테스트 완료

⏰ 기간: 2015-01-01 ~ 2025-01-15
💰 초기자본: ₩10,000,000

━━━━━━━━━━━━━━━━━━━━━
📊 최고 수익률 전략
━━━━━━━━━━━━━━━━━━━━━
전략: 200일선 전략
수익률: 485.32%
CAGR: 18.92%
최종자산: ₩48,532,000

[그래프 자동 전송]
```

---

# 🔄 이후 운영 (모바일에서!)

## 코드 수정하고 싶을 때

```
GitHub 저장소 → soxl_main.py
→ ✏️ 연필 아이콘 (Edit)
→ 코드 수정
→ "Commit changes" 클릭

✅ 자동으로:
  - GitHub Actions 실행
  - Cloud Run에 배포
  - 백테스트 실행
  - Telegram으로 결과 전송
```

## 수동으로 실행하고 싶을 때

```
GitHub 저장소 → Actions
→ "SOXL Backtest on Cloud Run"
→ "Run workflow"
→ "Run workflow" 클릭

✅ 즉시 실행 + Telegram 결과 수신
```

## 자동 정기 실행 (모바일 필요 없음)

```
workflow 파일에 이미 설정됨:
매주 일요일 10:00 UTC에 자동 실행
→ Telegram으로 자동 알림
```

---

# 🆘 문제 해결

## ❌ GitHub Actions 실패 - 오류: "GCP_SA_KEY 형식"
```
확인사항:
1. key.json 내용이 올바른 JSON인지 확인
2. Secret에 공백이 포함되지 않았는지 확인
3. Secret을 다시 생성해서 복사
```

## ❌ Telegram 메시지 미수신
```
확인사항:
1. TELEGRAM_BOT_TOKEN 유효성 확인
2. TELEGRAM_CHAT_ID 정확성 확인
3. 봇이 Telegram에서 이미 실행 중인지 확인
```

## ❌ Cloud Run 배포 실패
```
GitHub Actions 로그 확인:
Actions → 최신 실행 → "deploy-and-run"
→ 빨간색 X인 단계 확인
→ 오류 메시지 읽기
```

---

# 💰 월간 비용

| 항목 | 비용 |
|------|------|
| Cloud Run (월 1회) | 거의 무료 |
| Artifact Registry | 무료 (0.5GB) |
| **합계** | **~$0.01 미만** |

---

# 📚 다음 단계

### 정기 실행 시간 변경
```
.github/workflows/cloud-run.yml 수정
schedule:
  - cron: '0 9 * * *'  # 매일 9시
```

### 코드 수정 및 확장
```
GitHub에서 soxl_main.py 수정
→ 새로운 지표, 전략 추가 가능
→ 수정 후 자동 실행
```

### Slack/이메일 알림 추가
```
soxl_main.py에 추가 코드 작성
(현재는 Telegram만 지원)
```

---

# 🎉 완료!

**체크리스트:**
- ✅ GitHub에 9개 파일 + cloud-run.yml 업로드
- ✅ GCP 프로젝트 생성
- ✅ GitHub Secrets 4개 추가
- ✅ GitHub Actions 성공 실행
- ✅ Telegram에 결과 수신

---

## 📞 지금부터

1. **첫 번째 실행 후 오류 발생 시** → GitHub Actions 로그 확인
2. **Telegram 미수신 시** → Token/Chat ID 재확인
3. **코드 수정 후 자동 실행** → 모바일에서 GitHub에서 수정 + push

---

**이제 준비 완료! 행운을 빕니다! 🚀**

질문이 있으면 언제든 말씀해주세요!
