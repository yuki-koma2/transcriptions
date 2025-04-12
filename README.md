# transcriptions
Slack上から音声ファイルを送信 → 文字起こし → 要約 → 結果をSlackに投稿

## 開発メモ

slack CLIのセットアップ

```
curl -fsSL https://downloads.slack-edge.com/slack-cli/install.sh | bash
slack login
```





新しいプロジェクトを作成

```
slack create-project --name=project-name
```

sandbox
- koma2aibot
- koma2bot2

## 開発context
slack cli   を使って開発しようとおもったけど、まだ使えないと出てきてしまった。
一旦諦めて音声を文字起こしするところだけ先に作る。

`This workspace is not eligible for the next generation Slack platform.`

会社のやつは使えるので、課金プランでの利用実績なのかな。

- https://tools.slack.dev/deno-slack-sdk/guides/getting-started
- https://api.slack.com/samples
- https://slack.com/intl/ja-jp/help/articles/13345326945043-Slack-%E3%81%AE%E9%96%8B%E7%99%BA%E8%80%85%E7%94%A8%E3%83%84%E3%83%BC%E3%83%AB%E3%81%A7%E3%82%A2%E3%83%97%E3%83%AA%E3%82%92%E6%A7%8B%E7%AF%89%E3%81%99%E3%82%8B
- https://api.slack.com/docs/apps/ai


## やろうとしていたこと

🚀 開始ステップ（Slack上で完結型）
	1.	Slack Appの作成
	•	Botトークンスコープ: files:read, chat:write, commands など
	•	Event Subscriptions: file_shared, message.file_share
	2.	サーバーを立てる
	•	Vercel + Edge Functions や Cloud Run
	•	Slackイベントの受け取り → OpenAI Whisper API呼び出し
	3.	Whisper APIで音声文字起こし
    ```
    curl -X POST https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F file="@audio.mp3" \
  -F model="whisper-1"
  ```
	
    4.	要約生成（ChatGPT）

  ```
  {
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "あなたは文字起こしされた議事録を要約するアシスタントです。"},
    {"role": "user", "content": "（文字起こしテキスト）"}
  ]
}
```

	5.	Slackに結果を返信