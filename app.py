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

# Claude 中繼 API（我方提供）
CLAUDE_PROXY_URL = "https://claude-gateway.onrender.com/ask"

# 白名單（第一次使用者自動加入）
ALLOWED_USER_IDS = []

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
def handle_text(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()
    print(f"📌 使用者 ID：{user_id}")
    print(f"👤 使用者傳來：{user_msg}")

    global ALLOWED_USER_IDS
    if not ALLOWED_USER_IDS:
        ALLOWED_USER_IDS = [user_id]
        print("✅ 已自動設定使用者 ID 為白名單")
    if user_id not in ALLOWED_USER_IDS:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="很抱歉，此機器人僅限授權使用者使用。"))
        return

    if user_msg.lower() == "/help":
        help_msg = (
            "🤖 Claude 模型已啟用，可直接傳文字提問。\n"
            "- 一般提問：輸入任何問題\n"
            "- `/help`：顯示此說明"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_msg))
        return

    # 呼叫 Claude 中繼 API
    try:
        payload = {"prompt": user_msg}
        response = requests.post(CLAUDE_PROXY_URL, json=payload)
        result = response.json()
        reply = result.get("reply", "Claude 沒有回應，請稍後再試。")
        print(f"🤖 Claude 回覆：{reply}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    except Exception as e:
        print(f"⚠️ Claude 呼叫錯誤：{str(e)}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Claude 回覆失敗，請稍後再試。"))

if __name__ == "__main__":
    app.run(port=5000)
