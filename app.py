from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests

# LINE 金鑰
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Hugging Face Token
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"

app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    print("🟢 收到 LINE 的 webhook 請求")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("🔴 webhook 驗證失敗")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text
    print(f"👤 使用者傳來：{user_msg}")

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": f"User: {user_msg}\nAssistant:",
        "parameters": {"max_new_tokens": 100, "do_sample": True}
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        result = response.json()
        reply = result[0]["generated_text"].split("Assistant:")[-1].strip()

        print(f"🤖 HuggingFace 回覆：{reply}")

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
    except Exception as e:
        print(f"⚠️ Hugging Face 發生錯誤：{str(e)}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="抱歉，AI 回覆錯誤")
        )

if __name__ == "__main__":
    app.run(port=5000)
