#!/bin/sh

# スクリプトが管理者権限で実行されているか確認
if [ "$(id -u)" -ne 0 ]; then
  echo "このスクリプトは管理者権限で実行する必要があります。"
  echo "sudo ./install-node.sh を実行してください。"
  exit 1
fi

echo "Node.jsとnpmをインストールしています..."

# Alpine Linuxの場合
if [ -f /etc/alpine-release ]; then
  # 必要な依存関係をインストール
  apk update
  apk add --no-cache nodejs npm curl

  # バージョン確認
  echo "インストールされたバージョン:"
  node --version
  npm --version

  # npm自体を最新版にアップデート
  echo "npmを最新版にアップデートしています..."
  npm install -g npm@latest

# Debian/Ubuntu系の場合
else
  # 必要な依存関係をインストール
  apt-get update
  apt-get -y install curl ca-certificates

  # Node.jsのバージョン設定
  NODE_VERSION="20.12.2"

  # Node.jsのインストール
  echo "Node.js v${NODE_VERSION}をインストールしています..."
  curl -fsSL https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.gz | tar -xzC /usr/local --strip-components=1

  # バージョン確認
  echo "インストールされたバージョン:"
  node --version
  npm --version

  # npm自体を最新版にアップデート
  echo "npmを最新版にアップデートしています..."
  npm install -g npm@latest
fi

echo "セットアップが完了しました！"
echo "automation-appディレクトリで 'npm run test' を実行できるようになりました。"
