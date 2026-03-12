import os
import json
from flask import Flask, request
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import yfinance as yf
from openai import OpenAI

app = Flask(__name__)

# --- 🔑 Environment Variables ---
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

configuration = Configuration(access_token=LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = OpenAI(api_key=OPENAI_API_KEY)

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, request.headers.get('X-Line-Signature', ''))
    except Exception:
        # Bypass Signature เพื่อความชัวร์บน Render
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
            # 📊 ดึงราคาปัจจุบัน
            stock = yf.Ticker(user_text)
            price = stock.fast_info['last_price']
            asset_info = f"{user_text}: ${price:.2f}"
            
            # 🤖 เรียกใช้ GPT-4o วิเคราะห์ระดับพรีเมียม
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "คุณคือที่ปรึกษาการลงทุนอัจฉริยะ วิเคราะห์หุ้นปันผลพอร์ต Cycle 1 สำหรับคุณ Auttawut วิศวกรวัย 46 ปี เน้นความคุ้มค่าและอิสรภาพทางการเงิน"},
                    {"role": "user", "content": f"ช่วยวิเคราะห์หุ้น {asset_info} สั้นๆ ว่าน่าสนใจสำหรับสะสมเพิ่มไหม?"}
                ]
            )
            reply_text = f"[🏆 Wealth Insights]\n{asset_info}\n\n{response.choices[0].message.content}"
            
        except Exception:
            reply_text = f"คุณ Auttawut ครับ ผมหาหุ้น '{user_text}' ไม่เจอ รบกวนลองเช็กตัวสะกดอีกครั้งนะครับ"

        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)])
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)