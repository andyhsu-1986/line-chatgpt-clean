from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import os

app = Flask(__name__)

# 環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

def ask_openrouter(message):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://linebot.ai",  # 可隨意填寫
        "X-Title": "LINE Claude Gemini"
    }

    payload = {
        "model": "anthropic/claude-3-haiku",
        "messages": [{"role": "user", "content": message}],
        "temperature": 0.7,
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content']
            return reply.strip() + "\n\n（模型：Claude 3）"
    except Exception:
        pass

    # fallback: Gemini
    payload["model"] = "google/gemini-pro"
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content']
            return reply.strip() + "\n\n（模型：Gemini Pro）"
    except Exception:
        return "⚠️ 目前 AI 模型暫時無法回應，請稍後再試。"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text
    reply = ask_openrouter(user_input)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run()
