from flask import Flask, request, abort, send_file
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage
import os
import requests
import tempfile

# LINE 金鑰
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Hugging Face 語言模型 & 圖像模型
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_TEXT_MODEL = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
HF_IMAGE_CAPTION_MODEL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
HF_IMAGE_GEN_MODEL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"

# 白名單
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

@app.route("/image/<filename>")
def serve_image(filename):
    return send_file(f"generated_images/{filename}", mimetype='image/png')

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    user_msg = event.message.text
    print(f"📌 使用者 ID：{user_id}")
    print(f"👤 使用者傳來：{user_msg}")

    global ALLOWED_USER_IDS
    if not ALLOWED_USER_IDS:
        ALLOWED_USER_IDS = [user_id]
        print("✅ 已自動設定使用者 ID 為白名單")
    if user_id not in ALLOWED_USER_IDS:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="很抱歉，此機器人僅限授權使用者使用。"))
        return

    # 指令：/help
    if user_msg.strip().lower() == "/help":
        help_msg = (
            "🤖 可用指令如下：\n"
            "- 一般提問（如：幫我寫報告開頭）\n"
            "- `/畫 安全巡檢現場`：生成圖片\n"
            "- 傳圖片：會自動辨識內容\n"
            "- `/help`：顯示此說明"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_msg))
        return

    # 指令：/畫 文字
    if user_msg.startswith("/畫"):
        prompt = user_msg.replace("/畫", "").strip()
        headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
        payload = {"inputs": prompt}
        try:
            response = requests.post(HF_IMAGE_GEN_MODEL, headers=headers, json=payload)
            if response.status_code == 200:
                os.makedirs("generated_images", exist_ok=True)
                temp_path = os.path.join("generated_images", f"gen_{user_id}.png")
                with open(temp_path, "wb") as f:
                    f.write(response.content)
                public_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/image/gen_{user_id}.png"
                line_bot_api.reply_message(
                    event.reply_token,
                    ImageSendMessage(
                        original_content_url=public_url,
                        preview_image_url=public_url
                    )
                )
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="圖片生成失敗，請稍後再試。"))
        except Exception as e:
            print(f"⚠️ 圖片生成錯誤：{str(e)}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="圖片生成發生錯誤。"))
        return

    # 一般 GPT 對話
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": user_msg,
        "parameters": {"max_new_tokens": 150, "do_sample": True}
    }
    try:
        response = requests.post(HF_TEXT_MODEL, headers=headers, json=payload)
        result = response.json()
        reply = result[0]["generated_text"].split(user_msg)[-1].strip()
        print(f"🤖 模型回覆：{reply}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    except Exception as e:
        print(f"⚠️ 語言模型錯誤：{str(e)}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="回覆錯誤，請稍後再試。"))

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id
    if user_id not in ALLOWED_USER_IDS:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="很抱歉，此機器人僅限授權使用者使用。"))
        return
    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
        for chunk in message_content.iter_content():
            temp.write(chunk)
        image_path = temp.name
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}"
    }
    files = {"file": open(image_path, "rb")}
    try:
        response = requests.post(HF_IMAGE_CAPTION_MODEL, headers=headers, files=files)
        result = response.json()
        caption = result[0]["generated_text"] if isinstance(result, list) else result.get("error", "無法辨識圖片")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🖼 圖像辨識結果：{caption}"))
    except Exception as e:
        print(f"⚠️ 圖像辨識錯誤：{str(e)}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="圖片辨識錯誤，請稍後再試。"))

if __name__ == "__main__":
    app.run(port=5000)
