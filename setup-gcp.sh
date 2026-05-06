#!/bin/bash
# Google Cloud Platform 자동 설정 스크립트

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 SOXL Backtest - Google Cloud 자동 설정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. 사전 확인
echo -e "\n✓ 사전 확인"
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI가 설치되지 않았습니다."
    echo "다음에서 설치하세요: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되지 않았습니다."
    echo "다음에서 설치하세요: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "✓ gcloud CLI 설치됨"
echo "✓ Docker 설치됨"

# 2. 프로젝트 정보 입력
echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 프로젝트 정보 입력"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

read -p "GCP 프로젝트 ID (예: soxl-backtest): " PROJECT_ID
read -p "Telegram Bot Token: " TELEGRAM_BOT_TOKEN
read -p "Telegram Chat ID: " TELEGRAM_CHAT_ID

# 3. GCP 프로젝트 생성 및 API 활성화
echo -e "\n🔧 GCP 프로젝트 설정..."

gcloud config set project $PROJECT_ID

echo "✓ APIs 활성화 중..."
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable logging.googleapis.com

# 4. Artifact Registry 저장소 생성
echo -e "\n📦 Artifact Registry 저장소 생성..."
gcloud artifacts repositories create docker-repo \
  --repository-format=docker \
  --location=us-central1 \
  --quiet 2>/dev/null || echo "✓ 저장소가 이미 존재합니다"

# 5. 서비스 계정 생성
echo -e "\n🔐 서비스 계정 생성..."
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions for SOXL Backtest" \
  --quiet 2>/dev/null || echo "✓ 서비스 계정이 이미 존재합니다"

SERVICE_ACCOUNT_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# 6. 역할(Role) 부여
echo -e "\n👥 권한 설정 중..."

ROLES=(
    "roles/run.admin"
    "roles/artifactregistry.repositoryAdmin"
    "roles/storage.admin"
    "roles/cloudbuild.builds.editor"
    "roles/iam.serviceAccountUser"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
      --role=$role \
      --quiet 2>/dev/null || true
done

echo "✓ 권한 설정 완료"

# 7. 서비스 계정 JSON 키 생성
echo -e "\n🔑 서비스 계정 키 생성..."
rm -f ~/gcp-key.json
gcloud iam service-accounts keys create ~/gcp-key.json \
  --iam-account=$SERVICE_ACCOUNT_EMAIL

KEY_JSON=$(cat ~/gcp-key.json | jq -c .)

# 8. GitHub Secrets 설정 정보 출력
echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 GitHub Secrets 설정 정보"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -e "\n다음을 GitHub 저장소에 추가하세요:"
echo "저장소 → Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "1️⃣  Secret Name: GCP_PROJECT_ID"
echo "   Value: $PROJECT_ID"
echo ""
echo "2️⃣  Secret Name: GCP_SA_KEY"
echo "   Value: (아래 내용 복사)"
cat ~/gcp-key.json | jq .
echo ""
echo "3️⃣  Secret Name: TELEGRAM_BOT_TOKEN"
echo "   Value: $TELEGRAM_BOT_TOKEN"
echo ""
echo "4️⃣  Secret Name: TELEGRAM_CHAT_ID"
echo "   Value: $TELEGRAM_CHAT_ID"

# 9. GitHub Actions 워크플로우 디렉토리 생성
echo -e "\n📁 GitHub Actions 디렉토리 구조 생성..."
mkdir -p .github/workflows
cp cloud-run.yml .github/workflows/

echo "✓ .github/workflows/cloud-run.yml 생성됨"

# 10. 최종 확인
echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ GCP 설정 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -e "\n📝 다음 단계:"
echo ""
echo "1. GitHub Secrets 추가 (위의 정보 사용)"
echo ""
echo "2. 저장소에 push:"
echo "   git add ."
echo "   git commit -m 'Add SOXL backtest with Cloud Run'"
echo "   git push origin main"
echo ""
echo "3. GitHub 저장소에서 Actions 확인:"
echo "   저장소 → Actions → SOXL Backtest on Cloud Run"
echo ""
echo "4. 수동으로 첫 실행:"
echo "   Actions → SOXL Backtest on Cloud Run → Run workflow"
echo ""
echo "5. 정기 실행 (매주 일요일 10:00 UTC):"
echo "   자동으로 스케줄됨"
echo ""
echo "💡 주의: gcp-key.json은 절대 GitHub에 commit하지 마세요!"
echo "    (이미 .gitignore에 추가되어야 함)"

# 정리
rm -f ~/gcp-key.json
echo -e "\n✓ 임시 키 파일 삭제 완료"
