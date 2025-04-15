# Hello Slack Bot Project

このプロジェクトは、Slack上で動作するボットを作成し、メンションへの応答、音声ファイルの文字起こし、日次メッセージ要約などの機能を提供します。

## :gear: セットアップ手順

1.  **リポジトリのクローンまたはファイルの準備:**
    ```bash
    git clone <repository_url> # または必要なファイル (app.py, requirements.txt, .env.example) を準備
    cd hello-slack
    ```
2.  **環境変数の設定:**
    `.env.example` ファイルをコピーして `.env` ファイルを作成し、ご自身の Slack Bot Token と Signing Secret、OpenAI API Key を設定してください。
    ```bash
    cp .env.example .env
    ```
    ```dotenv
    # .env ファイルの内容例
    SLACK_BOT_TOKEN=xoxb-...your-token...
    SLACK_SIGNING_SECRET=...your-signing-secret...
    OPENAI_API_KEY=sk-...your-openai-key...
    ```
3.  **Python 仮想環境の作成と有効化 (推奨):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate  # Windows
    ```
4.  **依存関係のインストール:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **ngrok の準備:**
    ローカル開発環境を Slack からアクセス可能にするために [ngrok](https://ngrok.com/) をインストールし、アカウント設定を行ってください。
6.  **ローカルサーバーの起動:**
    ```bash
    python app.py
    ```
    FastAPI サーバーが `http://localhost:3000` で起動します。
7.  **ngrok の起動:**
    別のターミナルを開き、以下のコマンドでローカルサーバーを公開します。
    ```bash
    ngrok http 3000
    ```
    ngrok が `https://xxxx-xxxx-xxxx.ngrok-free.app` のような公開 URL を生成します。
8.  **Slack App の設定:**
    *   [Slack API サイト](https://api.slack.com/apps) で、作成したアプリの設定を開きます。
    *   「Event Subscriptions」に移動し、「Enable Events」をオンにします。
    *   「Request URL」に、ngrok が生成した URL の末尾に `/slack/events` を追加したものを入力します (例: `https://xxxx-xxxx-xxxx.ngrok-free.app/slack/events`)。
    *   「Subscribe to bot events」で `app_mention` イベントを追加します。
    *   変更を保存します。
9.  **動作確認:**
    Slack でボットをチャンネルに招待し、メンション (`@ボット名`) を送信して、ボットが応答するか確認します。

## :whale: Docker での実行手順 (ローカルテスト用)

ローカルでの基本的な動作確認後、または直接 Docker で開発を進めたい場合は、以下の手順で Docker コンテナを起動します。

1.  **Docker イメージのビルド:**
    `hello-slack` ディレクトリで以下のコマンドを実行します。
    ```bash
    docker build -t slack-bot-app .
    ```
2.  **Docker コンテナの起動:**
    `.env` ファイルの環境変数をコンテナに渡しつつ、ローカルのポート 3000 をコンテナのポート 3000 にマッピングして起動します。
    ```bash
    docker run --env-file .env -p 3000:3000 slack-bot-app
    ```
    これで Docker コンテナ内で FastAPI サーバーが起動します。
3.  **ngrok の起動と Slack App 設定:**
    上記「セットアップ手順」のステップ 7〜9 と同様に、ngrok を起動して公開 URL を取得し、Slack App の Event Subscriptions の Request URL に設定します。
    ```bash
    ngrok http 3000
    ```
    **注意:** ngrok が転送する先は `http://localhost:3000` のままです。Docker コンテナはローカルホストのポート 3000 にマッピングされています。
4.  **動作確認:**
    Slack でボットにメンションを送信し、応答が返ってくるか確認します。

## :rocket: 今後の計画 (PRDに基づく)

1.  **Whisper 連携:** Slack にアップロードされた音声ファイルをダウンロードし、OpenAI Whisper API を使用して文字起こしを行い、結果を Slack に投稿する機能を追加します。(`file_shared` イベントの処理)
2.  **日次要約機能:** 指定された時刻に、特定の Slack チャンネルのその日のメッセージを取得し、GPT モデルを使用して要約し、結果を Slack に投稿する定期実行ジョブを実装します。
3.  **Docker 化:** アプリケーションを Docker コンテナで実行できるように `Dockerfile` を作成します。
4.  **Cloud Run デプロイ:** Docker イメージを Google Cloud Build でビルドし、Google Cloud Run にデプロイします。
5.  **Next.js フロントエンド構築:** 必要に応じて、ユーザーインターフェースを提供するための Next.js アプリケーションを構築し、Firebase App Hosting にデプロイします。 


## 現時点でのメモ

sockert modeで動かすときにdockerだと上手くいかない。
httpモードはそもそもなんか動かないし。困った。

## :loud_sound: 機能の使い方

### 1. テキストでのメンション

*   ボットをメンション (`@ボット名`) して質問や指示をテキストで入力すると、ChatGPT (GPT-4o Mini) が応答します。
*   スレッド内で続けてメンションすると、スレッドの文脈を考慮して応答します。

### 2. 音声ファイルの文字起こしと話者分離

*   ボットをメンション (`@ボット名`) する際に、**同時に音声ファイル (MP3, M4A, WAV など) を添付** してメッセージを送信します。
*   ボットは添付された音声ファイルを認識し、「文字起こしと話者分離を開始します...」というメッセージをスレッドに投稿します。
*   処理が完了すると、以下の順番で結果が同じスレッドに投稿されます。
    1.  **文字起こし結果:** 音声全体を文字に起こしたテキスト。
    2.  **話者分離結果:** 話者ごと (`@Speaker_0`, `@Speaker_1` など) に発言を区切り、タイムスタンプを付与したテキスト。
*   ファイルの処理中にエラーが発生した場合は、エラー内容に応じたメッセージがスレッドに投稿されます。