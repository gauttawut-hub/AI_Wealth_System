import os
import json
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
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
    try:
        handler.handle(body, request.headers.get('X-Line-Signature', ''))
    except Exception:
        try:
            data = json.loads(body)
            for event in data.get('events', []):
                if event['type'] == 'message':
                    class DummyEvent:
                        def __init__(self, e):
                            self.reply_token = e['replyToken']
                            self.message = type('obj', (object,), {'text': e['message']['text']})
                    handle_message(DummyEvent(event))
        except Exception:
            pass
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text.strip().upper()
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            stock = yf.Ticker(user_text)
            hist = stock.history(period="7d")
            
            if hist.empty:
                reply_text = f"คุณ Auttawut ครับ ผมหาหุ้น '{user_text}' ไม่เจอ ลองเช็กชื่อย่ออีกครั้งนะครับ"
            else:
                current_price = hist['Close'].iloc[-1]
                asset_info = f"{user_text}: ${current_price:.2f}"
                prompt = (f"ในฐานะที่ปรึกษาการลงทุน ช่วยวิเคราะห์หุ้น {asset_info} "
                         f"สำหรับพอร์ตเน้นเงินปันผล (Cycle 1) ของนักลงทุนอายุ 46 ปี "
                         f"ที่มีพื้นฐานวิศวกรรมและต้องการอิสรภาพทางการเงินครับ")

                # --- 🤖 ระบบเรียก Gemini แบบ Hybrid (แก้ปัญหา 404) ---
                try:
                    # ลองแบบที่ 1: ใส่ models/ นำหน้า
                    response = client.models.generate_content(model="models/gemini-1.5-flash", contents=prompt)
                except Exception:
                    # ลองแบบที่ 2: ใส่แค่ชื่อรุ่น
                    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
                
                reply_text = f"[📊 AI Analysis]\n{asset_info}\n\n{response.text}"
                
        except Exception as e:
            reply_text = f"ขออภัยครับคุณ Auttawut ระบบ Gemini แจ้ง Error: {str(e)[:100]}"

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)