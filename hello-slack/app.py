import os
import logging
from slack_bolt import App
from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler


print("--- app.py script started ---")
logging.basicConfig(level=logging.INFO)
load_dotenv()

# Initializes your app with your bot token and signing secret
bot_token = os.getenv("SLACK_BOT_TOKEN")
app_token = os.getenv("SLACK_APP_TOKEN")
print(f"SLACK_BOT_TOKEN loaded: {'Yes' if bot_token else 'No'}")

app = App(
    token=bot_token,
)

@app.event("app_mention")
def handle_app_mention(event, say):
    logging.info("app_mention event received")
    user = event["user"]
    say(f"<@{user}> メンションありがとう！")

# Listens to incoming messages that contain "hello"
# To learn available listener arguments,
# visit https://tools.slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html
@app.message("hello")
def message_hello(message, say):
    logging.info("hello message received")
    # say() sends a message to the channel where the event was triggered
    say(f"Hey there <@{message['user']}>!")

# Start your app
if __name__ == "__main__":
    print("--- Starting Bolt app in Socket Mode ---")
    try:
        SocketModeHandler(app, app_token).start()
        # app.start(port=int(os.environ.get("PORT", 3000)))
    except Exception as e:
        logging.exception(f"Error starting Bolt app: {e}")
        print(f"Error starting Bolt app: {e}")
