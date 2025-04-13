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