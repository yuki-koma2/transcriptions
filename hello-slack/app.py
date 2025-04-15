import os
import logging
import re
from slack_bolt import App
from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler
from openai import OpenAI
import requests
import tempfile
import time
import sys

# local-transcriber モジュールからのインポート
# パスが通っているか確認が必要。実行ディレクトリからの相対パスで考える。
# もし hello-slack/ と local-transcriber/ が同じ階層にあるなら...
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
local_transcriber_path = os.path.join(parent_dir, 'local-transcriber')
if local_transcriber_path not in sys.path:
    sys.path.append(local_transcriber_path)


try:
    from transcription import convert_mp3_to_wav, transcribe_with_openai, diarize_with_resemblyzer
except ImportError as e:
    logging.error(f"Failed to import from local-transcriber: {e}. Ensure the module exists at {local_transcriber_path} and path is correct.")
    # モジュールが見つからない場合、関連機能を無効化するなどの処理が必要かもしれない
    # ここでは、起動時にエラーログを出すだけにする
    convert_mp3_to_wav = None
    transcribe_with_openai = None
    diarize_with_resemblyzer = None

# pydub を使うためにインポートを追加
try:
    from pydub import AudioSegment
except ImportError:
    logging.error("pydub is not installed. Please install it: pip install pydub")
    AudioSegment = None # エラーハンドリング用


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
def handle_app_mention(event, say, context, client): # client を引数に追加 (files_infoのため)
    logging.info("app_mention event received")
    user = event["user"]
    text = event["text"]
    channel_id = event["channel"]
    # thread_ts が存在しない場合は、元のメッセージの ts をスレッドとして扱う
    thread_ts = event.get("thread_ts", event["ts"])
    ts = event["ts"] # 現在のメッセージのタイムスタンプ
    files = event.get("files", []) # 添付ファイル情報を取得

    bot_user_id = context['bot_user_id']

    # 1. 音声ファイルが添付されているかチェック
    audio_file_info = None
    if files:
        for f in files:
            # より堅牢なチェック (例: audio/mpeg, audio/ogg, audio/wav, audio/webm, audio/mp4, audio/x-m4a など Whisperが対応する形式)
            # SlackのMIMEタイプを確認する必要がある
            mime_type = f.get("mimetype", "")
            if mime_type.startswith("audio/") or mime_type in ["video/mp4", "application/octet-stream"]: # Slackが正確なMIMEを返さない場合も考慮
                 # 最初に見つかった音声ファイルを使用
                 audio_file_info = f
                 logging.info(f"Detected potential audio/video file: name='{f.get('name')}', mime_type='{mime_type}', id='{f.get('id')}'")
                 break # 最初のファイルを処理

    # --- 分岐: 音声ファイル処理 or テキストプロンプト処理 ---
    if audio_file_info:
        # --- 音声ファイル処理 ---
        logging.info(f"Processing audio file: {audio_file_info.get('name')}")
        file_id = audio_file_info["id"]
        file_name = audio_file_info.get("name", "downloaded_audio")
        # url_private_download がない場合があるため、files_infoを使う方が確実かもしれない
        file_info_response = client.files_info(file=file_id)
        if not file_info_response.get("ok"):
             logging.error(f"Failed to get file info for {file_id}: {file_info_response.get('error')}")
             say(f"<@{user}> ファイル情報の取得に失敗しました。", thread_ts=thread_ts)
             return

        file_url = file_info_response.get("file", {}).get("url_private_download")

        if not file_url:
            say(f"<@{user}> 音声ファイルのダウンロードURLが見つかりませんでした。", thread_ts=thread_ts)
            return

        # モジュールがロードされているか再確認
        if AudioSegment is None:
            say(f"<@{user}> エラー: 音声処理に必要なライブラリ(pydub)がインストールされていません。", thread_ts=thread_ts)
            return
        if convert_mp3_to_wav is None or transcribe_with_openai is None or diarize_with_resemblyzer is None:
             say(f"<@{user}> エラー: 文字起こしまたは話者分離モジュールの読み込みに失敗しました。", thread_ts=thread_ts)
             return


        temp_dir = None # finally で削除するため、tryの外で宣言
        original_file_path = None
        wav_file_path = None

        try:
            # 1. 一時ディレクトリを作成
            temp_dir = tempfile.mkdtemp()
            logging.info(f"Created temporary directory: {temp_dir}")

            # 2. ファイルダウンロード
            original_file_extension = os.path.splitext(file_name)[1] if '.' in file_name else '.mp3' # 拡張子がない場合のデフォルト
            original_file_path = os.path.join(temp_dir, f"original_audio{original_file_extension}")
            logging.info(f"Downloading audio file to {original_file_path}...")
            headers = {"Authorization": f"Bearer {bot_token}"}
            response = requests.get(file_url, headers=headers, stream=True, timeout=300) # タイムアウト設定
            response.raise_for_status() # エラーチェック
            with open(original_file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info("Audio file downloaded successfully.")

            # 処理中メッセージ
            say(f"<@{user}> 音声ファイルを受け付けました。文字起こしと話者分離を開始します...", thread_ts=thread_ts)

            # 3. WAVファイルへの変換 (Resemblyzer用)
            wav_file_path = os.path.join(temp_dir, "temp_audio_for_diarization.wav")
            logging.info(f"Converting to WAV: {original_file_path} -> {wav_file_path}")
            try:
                 audio = AudioSegment.from_file(original_file_path) # pydub で読み込み
                 audio = audio.set_frame_rate(16000).set_channels(1)
                 audio.export(wav_file_path, format="wav")
                 logging.info("Conversion to WAV successful.")
            except Exception as e:
                 # ffmpeg がない場合 pydub は失敗することがある
                 logging.error(f"Failed to convert audio to WAV: {e}. Check if ffmpeg is installed and in PATH.")
                 say(f"<@{user}> 音声ファイルの変換に失敗しました。必要なライブラリ(ffmpeg等)が不足している可能性があります。", thread_ts=thread_ts)
                 return

            # 4. 文字起こし (OpenAI Whisper API)
            logging.info("Starting transcription with OpenAI...")
            # transcribe_with_openai は MP3パスを取る。元のファイルを渡す。
            segments = transcribe_with_openai(original_file_path)

            if segments is None:
                logging.error("Transcription failed (returned None).")
                say(f"<@{user}> OpenAI APIによる文字起こしに失敗しました。", thread_ts=thread_ts)
                return
            elif not segments:
                logging.info("Transcription returned empty segments.")
                say(f"<@{user}> 音声から文字を検出できませんでした。", thread_ts=thread_ts)
                # この場合も話者分離はスキップ
                return
            else:
                 logging.info(f"Transcription successful, {len(segments)} segments found.")
                 # 最初の返信: 文字起こし全文
                 full_transcription = " ".join([seg.get('text', '') for seg in segments]).strip()
                 if full_transcription:
                     # Slackのメッセージ長制限は約4000文字なので、余裕をもって分割
                     max_length = 3800
                     if len(full_transcription) > max_length:
                         parts = [full_transcription[i:i+max_length] for i in range(0, len(full_transcription), max_length)]
                         for i, part in enumerate(parts):
                             say(f"<@{user}> 文字起こし結果({i+1}/{len(parts)}):\n```\n{part}\n```", thread_ts=thread_ts)
                         logging.warning("Transcription result was too long, split into multiple messages.")
                     else:
                          say(f"<@{user}> 文字起こし結果:\n```\n{full_transcription}\n```", thread_ts=thread_ts)
                 else:
                     say(f"<@{user}> 文字起こし結果は空でした。", thread_ts=thread_ts)
                     # この場合も話者分離は不要
                     return


            # 5. 話者分離 (Local Resemblyzer)
            logging.info("Starting speaker diarization...")
            # diarize_with_resemblyzer はセグメントとWAVパスを取る
            formatted_transcription = diarize_with_resemblyzer(segments, wav_file_path)

            if formatted_transcription:
                 logging.info("Speaker diarization successful.")
                 # 2番目の返信: 話者分離結果
                 max_length = 3800 # 再度定義（スコープのため）
                 if len(formatted_transcription) > max_length :
                      parts = [formatted_transcription[i:i+max_length] for i in range(0, len(formatted_transcription), max_length)]
                      for i, part in enumerate(parts):
                           say(f"<@{user}> 話者分離結果({i+1}/{len(parts)}):\n{part}", thread_ts=thread_ts) # コードブロックは不要かも
                      logging.warning("Diarization result was too long, split into multiple messages.")
                 else:
                      say(f"<@{user}> 話者分離結果:\n{formatted_transcription}", thread_ts=thread_ts)
            else:
                 logging.error("Speaker diarization failed or returned empty.")
                 say(f"<@{user}> 話者分離に失敗しました。", thread_ts=thread_ts)


        except requests.exceptions.RequestException as e:
            logging.error(f"Error downloading file: {e}")
            say(f"<@{user}> 音声ファイルのダウンロードに失敗しました: {e}", thread_ts=thread_ts)
        except Exception as e:
            logging.exception(f"Error processing audio file: {e}") # スタックトレースもログに出力
            say(f"<@{user}> 音声ファイルの処理中に予期せぬエラーが発生しました。", thread_ts=thread_ts)
        finally:
            # 一時ディレクトリとファイルを削除
            if temp_dir and os.path.exists(temp_dir):
                logging.info(f"Removing temporary directory: {temp_dir}")
                import shutil # shutil を使う方が安全
                try:
                    shutil.rmtree(temp_dir)
                    logging.info("Temporary directory removed successfully.")
                except Exception as e:
                    logging.error(f"Error removing temporary directory {temp_dir}: {e}")

    # --- テキストプロンプト処理 (ファイルがない場合) ---
    else:
        logging.info("No audio file detected, processing as text mention.")
        # ボットへのメンション部分を除去して、ユーザーの質問内容を取得
        try:
            if text.startswith(f"<@{bot_user_id}>"):
                 prompt = text.split(f"<@{bot_user_id}>", 1)[1].strip()
            else:
                 # スレッド内の普通のメッセージかもしれないので、これもメンション除去を試みる
                 prompt = re.sub(r'^<@.*?>\s*', '', text).strip()

            # プロンプトが空の場合の応答 (ファイル処理がなかった場合のみ)
            if not prompt:
                # トップレベルのメンション、またはスレッド内の最初のメッセージへのメンションで、
                # かつファイル添付がなかった場合にデフォルト応答
                is_thread_start = thread_ts == event.get("ts") # 自分自身のtsと同じならスレッドの起点
                if is_thread_start:
                    say(f"<@{user}> メンションありがとうございます！何か質問があればどうぞ！", thread_ts=thread_ts)
                else:
                     # スレッドの途中での空メンションは無視する
                     logging.info("Ignoring empty mention in the middle of a thread.")
                return

            if not client:
                say(f"<@{user}> すみません、現在ChatGPT連携が無効になっています。", thread_ts=thread_ts) # スレッド内で返信
                logging.warning("ChatGPT client is not initialized.")
                return

            messages = [
                {"role": "system", "content": "You are a helpful assistant responding in Slack. You analyze the conversation history in the thread if provided."}
            ]

            # スレッド情報を取得してコンテキストに追加 (thread_ts が event["ts"] と異なる場合 = スレッド内の返信)
            is_reply_in_thread = thread_ts != event.get("ts")
            if is_reply_in_thread:
                try:
                    logging.info(f"Fetching replies for thread: {thread_ts} in channel: {channel_id}")
                    replies_response = app.client.conversations_replies(
                        channel=channel_id,
                        ts=thread_ts,
                        limit=20 # 取得件数を増やす (APIデフォルトは少ない可能性)
                    )
                    replies = replies_response.get("messages", [])
                    logging.info(f"Fetched {len(replies)} messages from the thread.")

                    processed_texts = set() # 同じテキストを重複して追加しないように

                    # スレッドのメッセージを古い順に追加 (repliesは通常古い順)
                    for msg in replies:
                        # 現在処理中のメッセージ(今回のメンション)は履歴に含めない
                        if msg['ts'] == ts:
                            continue
                        msg_text = msg.get("text", "")
                        # メンション除去は丁寧に行う (複数メンション対応)
                        cleaned_text = re.sub(r'<@U[A-Z0-9]+>\s*', '', msg_text).strip()


                        if cleaned_text and cleaned_text not in processed_texts:
                            # タイムスタンプもキーにして一意性を担保
                            msg_key = f"{msg['ts']}_{cleaned_text}"
                            if msg_key not in processed_texts:
                                processed_texts.add(msg_key)
                                # ボットからの返信かユーザーからのメッセージかを判定
                                if msg.get("bot_id") == context.get('bot_id') or msg.get("user") == bot_user_id :
                                    messages.append({"role": "assistant", "content": cleaned_text})
                                elif msg.get("user"): # ユーザーからのメッセージ
                                    messages.append({"role": "user", "content": cleaned_text})

                    # トークン数制限のため、メッセージ履歴を適切な長さに制限 (最新10件程度)
                    # system メッセージは維持し、user/assistantメッセージを制限
                    system_message = messages[0]
                    user_assistant_messages = messages[1:]
                    messages = [system_message] + user_assistant_messages[-10:]

                except Exception as e:
                    logging.error(f"Error fetching thread replies: {e}")
                    # スレッド取得に失敗しても、現在のプロンプトだけで応答を試みる
                    messages = [messages[0]] # system メッセージのみ残す
                    pass # エラーメッセージを出す場合はここに追加

            # 現在のユーザーのプロンプトを追加 (空でない場合)
            if prompt:
                 messages.append({"role": "user", "content": prompt})
            else:
                # プロンプトが空ならChatGPTには送らない (ここには到達しないはずだが念のため)
                logging.info("Prompt is empty after removing mention, skipping ChatGPT call.")
                return


            logging.info(f"Sending {len(messages)} messages to ChatGPT (including thread context if any): {messages}")

            # ChatGPT APIを呼び出す
            try:
                response = client.chat.completions.create(
                    # model="gpt-4o-mini-2024-07-18",
                    model="gpt-4o-mini",
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
            logging.exception(f"Error processing app_mention (text): {e}") # スタックトレースもログに
            # ファイル処理が成功していれば、ここでのエラーはテキスト処理部分のみ
            if not audio_file_info: # ファイル処理がなかった場合のみエラー通知
                 say(f"<@{user}> テキストメッセージの処理中にエラーが発生しました。", thread_ts=thread_ts)

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
    print("Checking necessary modules and configurations...")
    # local-transcriber モジュールがインポートできなかった場合のチェック
    transcription_enabled = True
    if AudioSegment is None:
        print("❌ Error: pydub library is not installed or failed to import. Audio conversion will fail.")
        print("  Please install it: pip install pydub")
        transcription_enabled = False
    if convert_mp3_to_wav is None or transcribe_with_openai is None or diarize_with_resemblyzer is None:
         print(f"❌ Error: Failed to import functions from local-transcriber module.")
         print(f"  Attempted path: {local_transcriber_path}")
         print(f"  Please ensure 'local-transcriber/transcription.py' exists and is importable.")
         transcription_enabled = False

    if not transcription_enabled:
         print("⚠️ Warning: Transcription/Diarization functionality will be disabled due to errors.")

    if client is None:
        print("⚠️ Warning: OpenAI client is not initialized. ChatGPT features (text and transcription) will be disabled.")
        print("  Please set the OPENAI_API_KEY environment variable.")

    if not bot_token or not app_token:
        print("❌ Error: SLACK_BOT_TOKEN or SLACK_APP_TOKEN is not set in environment variables.")
        sys.exit(1)

    print("--- Starting Bolt app in Socket Mode ---")
    try:
        SocketModeHandler(app, app_token).start()
    except Exception as e:
        logging.exception(f"Error starting Bolt app: {e}")
        print(f"❌ Error starting Bolt app: {e}")
        sys.exit(1)
