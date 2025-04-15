
⸻

:pushpin: PRD（プロダクト要件定義）

:white_check_mark: 目的
	•	Slack上でメンションされたとき、ボットが応答する。
	•	音声ファイルをSlackでアップロードすると、Whisperで書き起こしを実施し、結果をSlackに投稿する。
	•	毎日指定の時刻（例: 18:00）にSlackチャンネルの当日のメッセージを要約して投稿する。

:white_check_mark: 技術スタック
	•	フロントエンド：Next.js（Firebase App Hostingで公開）
	•	バックエンド：Python（FastAPI＋Bolt SDK＋OpenAI API）
	•	デプロイ先：Google Cloud Run（コンテナ化）

⸻

:triangular_flag_on_post: 作業手順とサンプルコード

以下のステップで構築を進めます。

Step 1. ローカルでSlackイベントを受信（Bolt SDKを使う）

準備
	•	Slack Appを作成（https://api.slack.com/apps）
	•	ボットトークン (xoxb-...) と Signing Secret を取得

Python環境準備

pip install slack_bolt fastapi uvicorn openai python-dotenv

.env ファイル作成

SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
OPENAI_API_KEY=...

最小構成 (app.py)

import os
from dotenv import load_dotenv
from slack_bolt import App
from fastapi import FastAPI
from slack_bolt.adapter.fastapi import SlackRequestHandler

load_dotenv()
slack_app = App(token=os.getenv("SLACK_BOT_TOKEN"), signing_secret=os.getenv("SLACK_SIGNING_SECRET"))
app = FastAPI()
handler = SlackRequestHandler(slack_app)

@slack_app.event("app_mention")
def handle_app_mention(event, say):
    user = event["user"]
    say(f"<@{user}> メンションありがとう！")

@app.post("/slack/events")
async def slack_events(req):
    return await handler.handle(req)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)

ローカルで実行

python app.py

Slack AppのイベントURLに ngrok 等を通じて公開URLを設定し、メンションして動作確認。

⸻

Step 2. Whisperで音声ファイルを文字起こしする処理を追加

Whisper導入

pip install openai-whisper

Whisper連携コード（services/transcription.py）

import whisper

model = whisper.load_model("base")

def transcribe_audio(file_path):
    result = model.transcribe(file_path, language="ja")
    return result["text"]

Slackイベントにファイル処理追加（app.pyに追加）

@slack_app.event("file_shared")
def handle_file_shared(event, client, say):
    file_id = event["file_id"]
    file_info = client.files_info(file=file_id)
    url_private = file_info["file"]["url_private_download"]

    # ファイルダウンロード（認証ヘッダを付ける）
    headers = {"Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}"}
    response = requests.get(url_private, headers=headers)
    with open("temp_audio.mp3", "wb") as f:
        f.write(response.content)

    text = transcribe_audio("temp_audio.mp3")
    say(f"書き起こし結果:\n{text}")

これでSlackに音声をアップロードすると、Whisperで書き起こしが行われる。

⸻

Step 3. Slack履歴を取得して要約を投稿（定期実行ジョブ）

GPTによる要約処理（services/summarizer.py）

from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def summarize(text):
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"以下を要約してください：\n{text}"}]
    )
    return completion.choices[0].message.content

Slack履歴取得と投稿（app.pyに追加）

from datetime import datetime
import schedule, time

def daily_summary():
    response = slack_app.client.conversations_history(channel="チャンネルID", oldest=str(datetime.now().timestamp() - 86400))
    messages = [msg["text"] for msg in response["messages"]]
    summary = summarize("\n".join(messages))
    slack_app.client.chat_postMessage(channel="チャンネルID", text=f"本日の要約:\n{summary}")

schedule.every().day.at("18:00").do(daily_summary)

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=3000)).start()
    while True:
        schedule.run_pending()
        time.sleep(60)



⸻

Step 4. Docker化＆Cloud Runにデプロイ

Dockerfile作成

FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]

requirements.txt

slack_bolt
fastapi
uvicorn
openai
openai-whisper
python-dotenv
schedule
requests

Cloud Runへのデプロイ

gcloud builds submit --tag gcr.io/[PROJECT_ID]/slack-bot
gcloud run deploy slack-bot --image gcr.io/[PROJECT_ID]/slack-bot --platform managed --region asia-northeast1 --allow-unauthenticated

Cloud Run URLをSlackイベントURLに再設定すれば、完成。

⸻

:bookmark: Next.js（Firebase App Hosting）

フロント側は、Next.jsアプリをFirebase Hostingで提供し、将来的にユーザーが操作するUIや認証を提供する。

npx create-next-app frontend
cd frontend
firebase init hosting
firebase deploy



⸻

:pushpin: まとめ（やること順序）
ローカル環境構築（Slack Boltでメンション処理）
Whisper連携（ファイルアップロード→書き起こし）
日次要約機能実装
Docker化・Cloud Runデプロイ
Next.js フロント構築



⸻

:pushpin: PythonアプリをDockerで動かす手順

以下のステップでローカルでの環境構築をDockerベースで進めます。

ディレクトリ構成

.
├── Dockerfile
├── app.py
├── requirements.txt
└── .env



⸻

Dockerfile（Python用）

以下を使用して、Python環境をDocker化します。

FROM python:3.10-slim

WORKDIR /app

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY . .

# FastAPIのデフォルトポートは8000、Boltは3000
EXPOSE 3000

CMD ["python", "app.py"]



⸻

requirements.txt（Pythonライブラリ一覧）

slack_bolt
fastapi
uvicorn
openai
openai-whisper
python-dotenv
schedule
requests



⸻

Dockerコンテナの起動（ローカル）

Dockerイメージをビルド:

docker build -t slack-bot-app .

Dockerコンテナを起動（ローカルポート3000をDocker内の3000にマッピング）:

docker run -p 3000:3000 slack-bot-app

これでPython環境をDocker内で起動できます。

⸻

:pushpin: ngrok とは？

ngrok は、ローカルで動かしているサーバー（例えば、上記のDockerコンテナで起動したサーバー）を、インターネット上に公開できるツールです。

Slackなど外部サービスのWebhookを受ける場合、Slackは公開されているURLにしかリクエストを送れないため、ローカル環境を一時的に公開したい場合に ngrok を利用します。

ngrok の使い方（簡易版）

① インストール
	•	https://ngrok.com でアカウントを作成し、ダウンロード後インストール。

② 起動方法

以下のコマンドで、Dockerで起動したローカルの3000番ポートをインターネットに公開します。

ngrok http 3000

実行すると、以下のような画面が表示され、HTTPSのURLが発行されます。

Forwarding   https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:3000

これをSlackのWebhook設定画面に登録すれば、ローカル環境へのリクエストがSlackから飛んできます。

⸻

:pushpin: 最終的な流れまとめ
PythonバックエンドをDocker化
Dockerコンテナをローカルで起動
ngrokでローカル環境をインターネットに一時的に公開
SlackイベントURLに ngrok の公開URLを指定し、ローカルで動作テスト
動作確認が完了したらCloud RunにDockerイメージをデプロイ