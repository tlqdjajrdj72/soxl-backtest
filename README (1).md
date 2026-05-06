# SOXL 백테스트 - Google Cloud Run 자동화

GitHub Actions를 통해 Google Cloud Run에서 SOXL 백테스트를 자동으로 실행하고, 결과를 Telegram으로 받아봅니다.

## 🚀 빠른 시작

### 1. GitHub 저장소 설정

```bash
# 저장소 클론 또는 생성
git clone https://github.com/YOUR_USERNAME/soxl-backtest.git
cd soxl-backtest

# 다음 파일들을 저장소 루트에 추가
# - soxl_main.py
# - requirements.txt
# - Dockerfile
# - .github/workflows/cloud-run.yml
```

### 2. Google Cloud 설정

#### 2-1. GCP 프로젝트 생성
```bash
# Cloud 콘솔에서 또는 CLI로
gcloud projects create soxl-backtest --name="SOXL Backtest"
gcloud config set project soxl-backtest

# Cloud Run API 활성화
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

#### 2-2. 서비스 계정 생성
```bash
# Cloud Run 배포 권한이 있는 서비스 계정
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Deployment"

# 필요한 권한 부여
gcloud projects add-iam-policy-binding soxl-backtest \
    --member=serviceAccount:github-actions@soxl-backtest.iam.gserviceaccount.com \
    --role=roles/run.admin

gcloud projects add-iam-policy-binding soxl-backtest \
    --member=serviceAccount:github-actions@soxl-backtest.iam.gserviceaccount.com \
    --role=roles/storage.admin

gcloud projects add-iam-policy-binding soxl-backtest \
    --member=serviceAccount:github-actions@soxl-backtest.iam.gserviceaccount.com \
    --role=roles/artifactregistry.admin

gcloud projects add-iam-policy-binding soxl-backtest \
    --member=serviceAccount:github-actions@soxl-backtest.iam.gserviceaccount.com \
    --role=roles/cloudbuild.builds.editor

gcloud iam service-accounts add-iam-policy-binding \
    github-actions@soxl-backtest.iam.gserviceaccount.com \
    --role=roles/iam.serviceAccountUser \
    --member=serviceAccount:github-actions@soxl-backtest.iam.gserviceaccount.com
```

#### 2-3. 서비스 계정 JSON 키 생성
```bash
gcloud iam service-accounts keys create key.json \
    --iam-account=github-actions@soxl-backtest.iam.gserviceaccount.com

# key.json 파일을 텍스트 에디터로 열어서 내용 복사
```

### 3. GitHub Secrets 설정

GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

다음 secrets 추가:

| Secret 이름 | 값 |
|------------|---|
| `GCP_PROJECT_ID` | `soxl-backtest` |
| `GCP_SA_KEY` | key.json의 전체 내용 (JSON) |
| `TELEGRAM_BOT_TOKEN` | Telegram 봇 토큰 |
| `TELEGRAM_CHAT_ID` | Telegram 채팅 ID |

#### Telegram 토큰 & Chat ID 확인

1. **Telegram에서 봇 생성**
   - Telegram에서 `@BotFather` 검색 및 대화 시작
   - `/newbot` 입력
   - 봇 이름 설정 → 토큰 받음

2. **Chat ID 확인**
   - 자신의 Telegram 계정 확인: `@userinfobot` 검색 → `/start`
   - 또는 봇에 메시지 보낸 후:
   ```bash
   curl https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
   - `"chat":{"id":987654321}` 형태로 표시

### 4. GitHub Actions Workflow 생성

`.github/workflows/cloud-run.yml` 파일 생성:

```yaml
name: Deploy to Cloud Run and Run Backtest

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 10 * * 0'  # 매주 일요일 10시 UTC
  workflow_dispatch:       # 수동 트리거

jobs:
  deploy-and-run:
    runs-on: ubuntu-latest
    
    permissions:
      contents: read
      id-token: write
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}
      
      - name: Configure Docker
        run: |
          gcloud auth configure-docker us-central1-docker.pkg.dev
      
      - name: Build and push Docker image
        run: |
          docker build -t us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/docker-repo/soxl-backtest:latest .
          docker push us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/docker-repo/soxl-backtest:latest
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy soxl-backtest \
            --image=us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/docker-repo/soxl-backtest:latest \
            --region=us-central1 \
            --memory=2Gi \
            --timeout=1800 \
            --set-env-vars="TELEGRAM_BOT_TOKEN=${{ secrets.TELEGRAM_BOT_TOKEN }},TELEGRAM_CHAT_ID=${{ secrets.TELEGRAM_CHAT_ID }}" \
            --no-allow-unauthenticated
      
      - name: Run backtest
        run: |
          CLOUD_RUN_URL=$(gcloud run services describe soxl-backtest --region=us-central1 --format='value(status.url)')
          curl -X POST "$CLOUD_RUN_URL" \
            -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
            --max-time 1800
```

단, Cloud Run은 HTTP 서비스를 위해 설계되었으므로, 직접 실행하려면 main.py를 HTTP 서버로 변경해야 합니다.

### 5-1. 간단한 방법: Cloud Scheduler + Cloud Functions

대신 **Cloud Scheduler + Cloud Run Job** 사용:

```bash
gcloud run jobs create soxl-backtest \
  --image=us-central1-docker.pkg.dev/$PROJECT_ID/docker-repo/soxl-backtest:latest \
  --region=us-central1 \
  --memory=2Gi \
  --timeout=1800 \
  --set-env-vars="TELEGRAM_BOT_TOKEN=$TOKEN,TELEGRAM_CHAT_ID=$CHAT_ID"

# 주간 실행 스케줄 (매주 일요일 10시 UTC)
gcloud scheduler jobs create app-engine soxl-weekly \
  --schedule="0 10 * * 0" \
  --location=us-central1 \
  --http-method=POST \
  --uri=https://YOUR_REGION-run.googleapis.com/soxl-backtest \
  --oidc-service-account-email=scheduler@$PROJECT_ID.iam.gserviceaccount.com
```

## 📂 저장소 구조

```
soxl-backtest/
├── soxl_main.py              # 백테스트 메인 코드
├── requirements.txt          # Python 의존성
├── Dockerfile               # Cloud Run 컨테이너 정의
├── README.md               # 이 파일
└── .github/
    └── workflows/
        └── cloud-run.yml   # GitHub Actions 워크플로우
```

## 🔄 실행 방식

### 옵션 1: 수동 실행 (GitHub UI)
- GitHub 저장소 → **Actions** → **Deploy to Cloud Run** → **Run workflow**

### 옵션 2: 정기 실행 (Cron)
- workflow 파일의 `schedule` 설정으로 자동 실행
- 기본값: 매주 일요일 10시 UTC

### 옵션 3: Push 트리거
- main 브랜치에 push하면 자동 실행

## 📊 결과 확인

1. **Telegram**: 자동으로 요약 + 그래프 수신
2. **Google Cloud Storage**: CSV 파일 저장
3. **Cloud Run 로그**: `gcloud run services logs read soxl-backtest --region=us-central1`

## 💡 비용 추정

- **Cloud Run**: 첫 180,000 vCPU-초 무료, 초과 시 ~$0.00002/초
- **Artifact Registry**: 월 0.50 GB 무료 스토리지
- **Cloud Scheduler**: 월 3개 작업 무료

**월 1회 실행 기준**: 거의 무료 (~$0.01 미만)

## 🆘 문제 해결

### Cloud Run 배포 실패
```bash
gcloud run services describe soxl-backtest --region=us-central1 --format=json
```

### 로그 확인
```bash
gcloud run services logs read soxl-backtest --region=us-central1 --limit=100
```

### Telegram 메시지 미수신
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 확인
- API 키 유효성 테스트:
```bash
curl https://api.telegram.org/bot$TOKEN/getMe
```

## 📝 주의사항

- Cloud Run은 15분 이내 완료되는 작업에 최적화됨
- 더 긴 작업은 Cloud Run Jobs 사용
- 환경변수는 GitHub Secrets에 반드시 저장
