import os
import json
from flask import Flask, request
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import yfinance as yf
from google import genai

app = Flask(__name__)

# --- 🔑 Environment Variables ---
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

configuration = Configuration(access_token=LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = genai.Client(api_key=GEMINI_API_KEY)

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_data(as_text=True)
    # Bypass Signature เพื่อความไว
    data = json.loads(body)
    for event in data.get('events', []):
        if event['type'] == 'message':
            class DummyEvent:
                def __init__(self, e):
                    self.reply_token = e['replyToken']
                    self.message = type('obj', (object,), {'text': e['message']['text']})
            handle_message(DummyEvent(event))
    return 'OK'

def handle_message(event):
    user_text = event.message.text.strip().upper()
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            # 📊 ดึงราคาปัจจุบันเท่านั้น (ลดภาระ API)
            stock = yf.Ticker(user_text)
            price = stock.fast_info['last_price']
            asset_info = f"{user_text}: ${price:.2f}"
            
            # 🤖 ส่งวิเคราะห์ (ลดความยาว Prompt)
            prompt = f"วิเคราะห์หุ้น {asset_info} สำหรับพอร์ตปันผล Cycle 1 ของวิศวกรวัย 46 ปี แบบสรุปสั้นได้ใจความ"
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            reply_text = f"[📊 AI Analysis]\n{asset_info}\n\n{response.text}"
            
        except Exception:
            reply_text = f"คุณ Auttawut ครับ ระบบกำลัง Reset โควตา รบกวนลองใหม่อีกครั้งใน 1 นาทีนะครับ"

        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)])
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)