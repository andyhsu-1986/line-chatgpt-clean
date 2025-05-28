from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import os
import google.generativeai as genai

app = Flask(__name__)

# LINE credentials
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Claude Proxy URL
CLAUDE_API_URL = os.getenv("CLAUDE_API_URL", "https://claude-proxy.zeabur.app/claude")

# Gemini config
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# 使用新版 Gemini 模型（v1）
gemini_model = genai.GenerativeModel(model_name="models/gemini-pro")

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id
    print(f"🟢 收到 LINE 的 webhook 請求\n📌 使用者 ID：{user_id}\n👤 使用者傳來：{user_message}")

    reply = ""
    # Claude 優先
    try:
        response = requests.post(CLAUDE_API_URL, json={"prompt": user_message}, timeout=15)
        response.raise_for_status()
        result = response.json()
        answer = result.get("completion", "").strip()
        if not answer:
            raise ValueError("Claude 回應為空")
        print(f"🤖 Claude 回應：{answer}")
        reply = f"🤖 Claude 回應：{answer}"

    except Exception as e:
        print(f"Claude 失敗：{e}")

        # Gemini 備援
        try:
            result = gemini_model.generate_content(user_message)
            answer = result.text.strip()
            print(f"🧠 Gemini 回應：{answer}")
            reply = f"🧠 Gemini 回應：{answer}"
        except Exception as ge:
            print(f"Gemini 失敗：{ge}")
            reply = "⚠️ Claude 和 Gemini 都無法回應，請稍後再試。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run()
