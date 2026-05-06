# Google Cloud Run을 위한 Python 이미지
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (matplotlib 등을 위해 필요)
RUN apt-get update && apt-get install -y \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY soxl_main.py .

# Cloud Run은 PORT 환경변수를 사용하지만, 이 스크립트는 HTTP 서버가 아님
# 따라서 직접 스크립트를 실행
CMD ["python", "soxl_main.py"]
