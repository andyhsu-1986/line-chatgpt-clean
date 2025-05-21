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

# 白名單使用者 LINE ID（你可以換成自己的）
ALLOWED_USER_IDS = ["你的LINE使用者ID"]  # TODO: 請更換為你的實際 LINE 使用者 ID

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
    user_id = event.source.user_id
    user_msg = event.message.text
    print(f"👤 使用者傳來：{user_msg}")

    # 白名單驗證
    if user_id not in ALLOWED_USER_IDS:
        print("⛔ 拒絕未授權使用者")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="很抱歉，此機器人僅限授權使用者使用。")
        )
        return

    # 指令處理
    if user_msg.strip().lower() == "/help":
        help_msg = "您好，我是您的 AI 助理，您可以傳送以下內容來獲得協助：\n\n" \
                   "+ 一般提問（如：今天是星期幾？）\n" \
                   "+ 寫作協助（如：幫我寫一段自我介紹）\n" \
                   "+ `/help`：顯示本說明\n"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=help_msg)
        )
        return

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    prompt_prefix = "你是一位友善且說中文的 AI 助理。使用者說："
    payload = {
        "inputs": f"{prompt_prefix}{user_msg}\n助理：",
        "parameters": {"max_new_tokens": 150, "do_sample": True}
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        result = response.json()
        reply = result[0]["generated_text"].split("助理：")[-1].strip()

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
