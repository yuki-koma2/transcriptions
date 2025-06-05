# プロジェクト概要

このリポジトリは、Slack 上で共有された音声ファイルを文字起こしし、その内容を要約して Slack に投稿することを目的とした実験的なプロジェクトです。主な機能は以下の通りです。

- **my-app**: Slack Bot を実装する Bolt for JavaScript テンプレート。
- **local-transcriber**: OpenAI Whisper API を利用した CLI。Node.js 版と Python 版が含まれ、ローカル環境でも動作します。

## ディレクトリ構成

```
transcriptions/
├─ my-app/            # Slack Bot (Bolt for JS)
├─ local-transcriber/ # ローカルでの文字起こしスクリプト
└─ docs/              # プロジェクトドキュメント
```

### my-app
Slack からのメッセージを受け取り、OpenAI API を呼び出して応答するサンプルです。manifest.json でスコープを定義し、`app.js` でイベント処理を行います。

### local-transcriber
Node.js 製 CLI (`transcribe.js`) と、Python 製スクリプト (`transcription.py`) の2種類を提供しています。音声ファイルのパスを指定すると、Whisper で文字起こしを行い、オプションで要約も生成します。

## セットアップ
1. 必要に応じて `my-app` と `local-transcriber` の README を参照し、依存パッケージをインストールしてください。
2. OpenAI API キーを `.env` ファイルで設定します。

## 今後の展望
Slack CLI を用いたアプリ開発を試みましたが、現時点では制限があるため、まずは音声の文字起こしから着手しています。将来的には Slack Bot と連携し、音声投稿から要約までを自動化することを目指しています。
