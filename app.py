from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os
import requests
import google.generativeai as genai

app = Flask(__name__)

# LINE 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# 驗證 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET
if not LINE_CHANNEL_ACCESS_TOKEN:
    print("錯誤：LINE_CHANNEL_ACCESS_TOKEN 未設定。")
    exit(1)
if not LINE_CHANNEL_SECRET:
    print("錯誤：LINE_CHANNEL_SECRET 未設定。")
    exit(1)

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Claude Proxy 設定（修正為穩定網址）
CLAUDE_API_URL = os.getenv("CLAUDE_API_URL")

# Gemini 設定（強制使用 v1 版本）
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("錯誤：GOOGLE_API_KEY 未設定。")
    genai_available = False
else:
    genai.configure(api_key=GOOGLE_API_KEY, transport="rest", api_version="v1")
    genai_available = True

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("InvalidSignatureError：請檢查你的 LINE_CHANNEL_SECRET。")
        abort(400)
    except Exception as e:
        print(f"處理 webhook 時發生意外錯誤：{e}")
        abort(500)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text
    user_id = event.source.user_id
    print(f"🟢 收到 LINE 的 webhook 請求")
    print(f"📌 使用者 ID：{user_id}")
    print(f"👤 使用者傳來：{user_input}")

    reply = ""
    error_message = "⚠️ 抱歉，目前系統暫時無法回應，請稍後再試。"

    # Claude 優先
    if CLAUDE_API_URL:
        try:
            response = requests.post(CLAUDE_API_URL, json={"prompt": user_input}, timeout=15)
            if response.status_code == 200:
                reply = response.json().get("reply", "").strip()
                if not reply:
                    print("Claude 回傳了空的回覆。")
            else:
                print(f"Claude 失敗：HTTP 狀態碼 {response.status_code}，回覆：{response.text}")
        except requests.exceptions.Timeout:
            print("Claude 失敗：請求超時。")
        except requests.exceptions.RequestException as e:
            print(f"Claude 失敗：網路請求錯誤 - {e}")
        except Exception as e:
            print(f"Claude 失敗：未知錯誤 - {e}")
    else:
        print("CLAUDE_API_URL 未設定。跳過 Claude。")

    # fallback 到 Gemini
    if not reply and genai_available:
        try:
            model = genai.GenerativeModel('gemini-pro')
            chat = model.start_chat()
            response = chat.send_message(user_input)
            reply = response.text.strip()
            if not reply:
                print("Gemini 回傳了空的回覆。")
        except Exception as e:
            print(f"Gemini 失敗：{e}")

    if not reply:
        reply = error_message

    print("🤖 回覆：", reply)
    try:
        line_bot_api.reply_message(event.reply_token, TextSendMess
