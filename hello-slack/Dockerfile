FROM python:3.10-slim

WORKDIR /app

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY . .

# Bolt SDKが使用するポート（FastAPIアダプター経由）
EXPOSE 3000

CMD ["python", "app.py"] 