# アプリエージェント & アシスタントテンプレート (Bolt for JavaScript)

このJavaScript用Boltテンプレートは、Slackで[エージェント & アシスタント](https://api.slack.com/docs/apps/ai)を構築する方法を示しています。

## セットアップ

始める前に、アプリをインストールする権限を持つ開発用ワークスペースがあることを確認してください。まだ持っていない場合は、[作成](https://slack.com/create)してください。

### 開発者プログラム

[Slack開発者プログラム](https://api.slack.com/developer-program)に参加して、アプリの構築とテスト用のサンドボックス環境、ツール、リソースへの独占的なアクセスを得ましょう。

## インストール

### Slackアプリの作成

1. [https://api.slack.com/apps/new](https://api.slack.com/apps/new)を開き、
   "From an app manifest"を選択します
2. アプリケーションをインストールしたいワークスペースを選択します
3. [manifest.json](./manifest.json)の内容を`*Paste your manifest code here*`と書かれたテキストボックス（JSONタブ内）にコピーして、_Next_をクリックします
4. 設定を確認して_Create_をクリックします
5. その後、アプリ設定にリダイレクトされます。**Install App**ページを開き、アプリをインストールしてください。

### 環境変数

アプリを実行する前に、いくつかの環境変数を設定する必要があります。

1. `.env.sample`を`.env`にリネームします
2. [このリスト](https://api.slack.com/apps)からアプリの設定ページを開き、左側のメニューから_OAuth & Permissions_をクリックし、_Bot User OAuth Token_を`.env`ファイルの`SLACK_BOT_TOKEN`にコピーします
3. 左側のメニューから_Basic Information_をクリックし、_App-Level Tokens_セクションの手順に従って`connections:write`スコープを持つアプリレベルトークンを作成します。そのトークンを`.env`の`SLACK_APP_TOKEN`にコピーします。

### ローカルプロジェクト

```zsh
# このプロジェクトをマシンにクローンします
git clone https://github.com/slack-samples/bolt-js-assistant-template.git

# このプロジェクトディレクトリに移動します
cd bolt-js-assistant-template

# 依存関係をインストールします
npm install

# Boltサーバーを実行します
npm start
```

### リンティング

```zsh
# コードフォーマットとリンティングを実行します
npm run lint
```

## プロジェクト構造

### `manifest.json`

`manifest.json`はSlackアプリの設定ファイルです。マニフェストを使用することで、事前定義された設定でアプリを作成したり、既存のアプリの設定を調整したりできます。

### `app.js`

`app.js`はアプリケーションのエントリーポイントであり、サーバーを起動するために実行するファイルです。このプロジェクトでは、このファイルをできるだけシンプルに保ち、主に受信リクエストのルーティングに使用します。

## アプリの配布 / OAuth

複数のワークスペースにアプリケーションを配布する予定がある場合にのみ、OAuthを実装してください。関連するOAuth設定を含む別の`app-oauth.js`ファイルが用意されています。

OAuthを使用する場合、Slackはリクエストを送信できる公開URLを必要とします。このテンプレートアプリでは、[`ngrok`](https://ngrok.com/download)を使用しています。セットアップについては[このガイド](https://ngrok.com/docs#getting-started-expose)をご覧ください。

`ngrok`を起動して、外部ネットワークからアプリにアクセスし、OAuth用のリダイレクトURLを作成します。

```
ngrok http 3000
```

この出力には、`http`と`https`の転送アドレスが含まれているはずです（`https`を使用します）。以下のような形式になります：

```
Forwarding   https://3cb89939.ngrok.io -> http://localhost:3000
```

アプリ設定の**OAuth & Permissions**に移動し、**Add a Redirect URL**をクリックします。リダイレクトURLは、`ngrok`転送アドレスに`slack/oauth_redirect`パスを追加したものに設定する必要があります。例：

```
https://3cb89939.ngrok.io/slack/oauth_redirect
```
