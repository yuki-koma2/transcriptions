#!/bin/bash

# Gitユーザー設定自動化スクリプト
# このスクリプトは、Gitのユーザー名とメールアドレスを設定します

# 色の定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ロゴ表示
echo -e "${BLUE}"
echo "  _____  _  _                         __ _       "
echo " / ____|(_)| |                       / _(_)      "
echo "| |  __  _ | |_   ___  ___  _ __  __| |_  _  ___ "
echo "| | |_ || || __| / __|/ _ \| '__|/ _\` | || |/ __|"
echo "| |__| || || |_ | (__| (_) | |  | (_| | || |\__ \\"
echo " \_____||_| \__| \___|\___/|_|   \__,_|_||_||___/"
echo -e "${NC}"

echo -e "${YELLOW}Git設定自動化ツール${NC}\n"

# デフォルト値の設定
DEFAULT_EMAIL="user@example.com"
DEFAULT_NAME="Your Name"

# パラメータチェック
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "使用方法: ./setup-git.sh [--global] [メールアドレス] [ユーザー名]"
  echo ""
  echo "オプション:"
  echo "  --global    グローバル設定として適用（デフォルト）"
  echo "  --local     このリポジトリのみに設定を適用"
  echo "  --help, -h  このヘルプメッセージを表示"
  echo ""
  echo "例:"
  echo "  ./setup-git.sh                             # 対話形式でグローバル設定"
  echo "  ./setup-git.sh --local                     # 対話形式でローカル設定"
  echo "  ./setup-git.sh user@example.com \"山田 太郎\" # 指定された値でグローバル設定"
  exit 0
fi

# スコープの設定（デフォルトはグローバル）
SCOPE="--global"
if [ "$1" = "--local" ]; then
  SCOPE=""
  shift
elif [ "$1" = "--global" ]; then
  shift
fi

# メールとユーザー名の取得
if [ -n "$1" ] && [ -n "$2" ]; then
  # コマンドライン引数から取得
  EMAIL="$1"
  NAME="$2"
else
  # 対話形式で入力を促す
  echo -e "${YELLOW}Gitの設定を行います。${NC}"
  
  # 既存の設定があれば表示
  CURRENT_EMAIL=$(git config --get user.email || echo "未設定")
  CURRENT_NAME=$(git config --get user.name || echo "未設定")
  
  echo -e "現在の設定:"
  echo -e "  メールアドレス: ${BLUE}${CURRENT_EMAIL}${NC}"
  echo -e "  ユーザー名　　: ${BLUE}${CURRENT_NAME}${NC}\n"
  
  # メールアドレスの入力
  read -p "メールアドレスを入力してください [$DEFAULT_EMAIL]: " EMAIL
  EMAIL=${EMAIL:-$DEFAULT_EMAIL}
  
  # ユーザー名の入力
  read -p "ユーザー名を入力してください [$DEFAULT_NAME]: " NAME
  NAME=${NAME:-$DEFAULT_NAME}
fi

# Git設定の適用
echo -e "\n${YELLOW}次の設定を適用します:${NC}"
echo -e "  スコープ　　　: ${SCOPE:-"このリポジトリのみ"}"
echo -e "  メールアドレス: ${BLUE}${EMAIL}${NC}"
echo -e "  ユーザー名　　: ${BLUE}${NAME}${NC}"

# 確認
read -p "この設定を適用しますか？ [Y/n]: " CONFIRM
CONFIRM=${CONFIRM:-Y}

if [[ $CONFIRM =~ ^[Yy]$ ]]; then
  git config ${SCOPE} user.email "${EMAIL}"
  git config ${SCOPE} user.name "${NAME}"
  echo -e "\n${GREEN}✓ Git設定が正常に適用されました！${NC}"
  
  # 現在の設定を表示
  echo -e "\n${YELLOW}現在のGit設定:${NC}"
  echo -e "  メールアドレス: ${BLUE}$(git config user.email)${NC}"
  echo -e "  ユーザー名　　: ${BLUE}$(git config user.name)${NC}"
else
  echo -e "\n${YELLOW}操作はキャンセルされました。設定は変更されていません。${NC}"
fi

# 使用方法のヒント
echo -e "\n${YELLOW}ヒント:${NC}"
echo "このスクリプトは以下のコマンドで実行できます:"
echo "  ./setup-git.sh                             # 対話形式でグローバル設定"
echo "  ./setup-git.sh --local                     # 対話形式でローカル設定"
echo "  ./setup-git.sh user@example.com \"山田 太郎\" # 指定された値でグローバル設定"
