from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os
import google.generativeai as genai

app = Flask(__name__)

# LINE 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    print("錯誤：LINE API 金鑰未正確設定")
    exit(1)

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Gemini 設定
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("錯誤：GOOGLE_API_KEY 未設定")
    exit(1)

genai.configure(api_key=GOOGLE_API_KEY, transport='rest', api_version='v1')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("⚠️ LINE 簽名驗證失敗，請確認 secret 正確")
        abort(400)
    except Exception as e:
        print(f"⚠️ Webhook 錯誤：{e}")
        abort(500)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text
    user_id = event.source.user_id
    print(f"🟢 收到來自 {user_id} 的訊息：{user_input}")

    reply = ""
    error_message = "⚠️ 抱歉，目前無法回應，請稍後再試。"

    try:
        model = genai.GenerativeModel('gemini-pro')
        chat = model.start_chat()
        response = chat.send_message(user_input)
        reply = response.text.strip()
        print(f"🤖 Gemini 回應：{reply}")
    except Exception as e:
        print(f"Gemini 發生錯誤：{e}")
        reply = error_message

    try:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    except Exception as e:
        print(f"LINE 回應錯誤：{e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
