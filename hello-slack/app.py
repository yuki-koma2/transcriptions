import os
import logging
import re
from slack_bolt import App
from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler
from openai import OpenAI # OpenAIライブラリをインポート


print("--- app.py script started ---")
logging.basicConfig(level=logging.INFO)
load_dotenv()

# Initializes your app with your bot token and signing secret
bot_token = os.getenv("SLACK_BOT_TOKEN")
app_token = os.getenv("SLACK_APP_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY") # OpenAI APIキーを読み込む
print(f"SLACK_BOT_TOKEN loaded: {'Yes' if bot_token else 'No'}")
print(f"OPENAI_API_KEY loaded: {'Yes' if openai_api_key else 'No'}")


app = App(
    token=bot_token,
)

# OpenAIクライアントを初期化
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
else:
    client = None
    logging.warning("OPENAI_API_KEY is not set. ChatGPT integration will be disabled.")


@app.event("app_mention")
def handle_app_mention(event, say, context):
    logging.info("app_mention event received")
    user = event["user"]
    text = event["text"]
    channel_id = event["channel"]
    thread_ts = event.get("thread_ts") # スレッドのタイムスタンプを取得 (存在しない場合はNone)
    ts = event["ts"] # 現在のメッセージのタイムスタンプ

    # ボットへのメンション部分を除去して、ユーザーの質問内容を取得
    try:
        bot_user_id = context['bot_user_id']
        if text.startswith(f"<@{bot_user_id}>"):
             prompt = text.split(f"<@{bot_user_id}>", 1)[1].strip()
        else:
             prompt = re.sub(r'^<@.*?>\s*', '', text).strip()

        if not prompt:
            # スレッド内のメンションでプロンプトがない場合も応答しないようにする
            if thread_ts is None or thread_ts == ts:
                 say(f"<@{user}> メンションありがとうございます！何か質問があればどうぞ！", thread_ts=thread_ts) # スレッド内で返信
            return

        if not client:
            say(f"<@{user}> すみません、現在ChatGPT連携が無効になっています。", thread_ts=thread_ts) # スレッド内で返信
            logging.warning("ChatGPT client is not initialized.")
            return

        messages = [
            {"role": "system", "content": "You are a helpful assistant responding in Slack. You analyze the conversation history in the thread if provided."}
        ]

        # スレッド情報を取得してコンテキストに追加
        if thread_ts:
            try:
                logging.info(f"Fetching replies for thread: {thread_ts} in channel: {channel_id}")
                # conversations.replies APIを呼び出す (app.clientを使用)
                replies_response = app.client.conversations_replies(
                    channel=channel_id,
                    ts=thread_ts
                )
                replies = replies_response.get("messages", [])
                logging.info(f"Fetched {len(replies)} messages from the thread.")

                # メッセージ履歴を整形 (最新のものをいくつか含めるなど、調整可能)
                # 元のメッセージも含める (repliesの最初の要素)
                # 現在のメッセージ (prompt) は最後に追加するので、履歴からは除外する
                for msg in replies:
                    # 現在処理中のメッセージは履歴に含めない
                    if msg['ts'] == ts:
                        continue
                    msg_text = msg.get("text", "")
                    # ボットからの返信かユーザーからのメッセージかを判定
                    # 簡単な判定: bot_idがあればボット、なければユーザーとする
                    # より正確には event['bot_id'] や context['bot_user_id'] と比較
                    if msg.get("bot_id") == context.get('bot_id') or msg.get("user") == bot_user_id :
                         # ボットの過去の返信からメンション部分を取り除く (任意)
                         cleaned_text = re.sub(r'^<@.*?>\s*', '', msg_text).strip()
                         if cleaned_text: # 空でなければ追加
                            messages.append({"role": "assistant", "content": cleaned_text})
                    elif msg.get("user"): # ユーザーからのメッセージ
                         # ユーザーメッセージからメンション部分を取り除く (任意)
                         cleaned_text = re.sub(r'^<@.*?>\s*', '', msg_text).strip()
                         if cleaned_text: # 空でなければ追加
                             messages.append({"role": "user", "content": cleaned_text})

                # トークン数制限のため、メッセージ履歴を適切な長さに制限することを検討
                messages = messages[-10:] # 直近10件（system含む）

            except Exception as e:
                logging.error(f"Error fetching thread replies: {e}")
                # スレッド取得に失敗しても、現在のプロンプトだけで応答を試みる
                pass # エラーメッセージを出す場合はここに追加

        # 現在のユーザーのプロンプトを追加
        messages.append({"role": "user", "content": prompt})

        logging.info(f"Sending messages to ChatGPT (including thread context if any): {messages}")

        # ChatGPT APIを呼び出す
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            chatgpt_response = response.choices[0].message.content
            logging.info(f"Received response from ChatGPT: {chatgpt_response}")
            # スレッド内で返信するために thread_ts を指定
            say(f"<@{user}> {chatgpt_response}", thread_ts=thread_ts)
        except Exception as e:
            logging.error(f"Error calling OpenAI API: {e}")
            say(f"<@{user}> すみません、ChatGPTからの応答の取得中にエラーが発生しました。", thread_ts=thread_ts) # スレッド内で返信

    except Exception as e:
        logging.error(f"Error processing app_mention: {e}")
        say(f"<@{user}> 処理中にエラーが発生しました。", thread_ts=thread_ts) # スレッド内で返信


# Listens to incoming messages that contain "hello"
# To learn available listener arguments,
# visit https://tools.slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html
# @app.message("hello")
# def message_hello(message, say):
#     logging.info("hello message received")
#     # say() sends a message to the channel where the event was triggered
#     say(f"Hey there <@{message['user']}>!")

# Start your app
if __name__ == "__main__":
    print("--- Starting Bolt app in Socket Mode ---")
    try:
        SocketModeHandler(app, app_token).start()
        # app.start(port=int(os.environ.get("PORT", 3000)))
    except Exception as e:
        logging.exception(f"Error starting Bolt app: {e}")
        print(f"Error starting Bolt app: {e}")
