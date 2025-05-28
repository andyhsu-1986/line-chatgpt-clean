import os
import json
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

app = Flask(__name__)

# LINE credentials
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Claude Proxy URL
CLAUDE_PROXY_URL = "https://claude.onrenderapi.com/ask"  # 可切換為 Zeabur 私有 URL

# Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-pro")


def ask_claude(prompt):
    try:
        response = requests.post(CLAUDE_PROXY_URL, json={"prompt": prompt}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "reply" in data and data["reply"].strip():
                return f"🤖 Claude 回應：{data['reply']}"
            else:
                raise ValueError("Claude 回傳空內容")
        else:
            raise ValueError(f"Claude 回傳錯誤碼：{response.status_code}")
    except Exception as e:
        print(f"Claude 失敗：{e}")
        return None


def ask_gemini(prompt):
    try:
        response = gemini_model.generate_content(prompt)
        return f"🧠 Gemini 回應：{response.text}"
    except Exception as e:
        print(f"Gemini 失敗：{e}")
        return "⚠️ Claude 與 Gemini 均無法回應，請稍後再試。"


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
    reply_text = ask_claude(user_input)

    if not reply_text:
        reply_text = ask_gemini(user_input)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
