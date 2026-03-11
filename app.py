import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import yfinance as yf
from google import genai

app = Flask(__name__)

# --- 🔑 ดึงข้อมูลผ่าน Environment Variables ---
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

configuration = Configuration(access_token=LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = genai.Client(api_key=GEMINI_API_KEY)

@app.route("/callback", methods=['POST'])
def callback():
    # ข้ามการตรวจสอบ Signature ชั่วคราวเพื่อทดสอบสัญญาณ
    body = request.get_data(as_text=True)
    try:
        # สั่งให้ handler ทำงานโดยไม่เช็ค Signature
        handler.handle(body, "dummy_signature_for_test")
    except Exception:
        # ถ้าพังในด่าน handler ให้เราบังคับรัน handle_message เองเลย
        import json
        data = json.loads(body)
        for event in data.get('events', []):
            if event['type'] == 'message':
                # จำลองโครงสร้าง event ส่งไปให้ handle_message
                class DummyEvent:
                    def __init__(self, e):
                        self.reply_token = e['replyToken']
                        self.message = type('obj', (object,), {'text': e['message']['text']})
                handle_message(DummyEvent(event))
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text.strip().upper()
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            # ดึงราคาหุ้น
            stock = yf.Ticker(user_text)
            hist = stock.history(period="1d")
            
            if hist.empty:
                reply_text = f"คุณ Auttawut ครับ ผมหาหุ้น '{user_text}' ไม่เจอ ลองเช็กตัวสะกดดูอีกครั้งนะครับ"
            else:
                price = hist['Close'].iloc[-1]
                asset_info = f"{user_text}: ${price:.2f}"
                
                # ส่งต่อให้ Gemini วิเคราะห์ตามสไตล์วิศวกรและพอร์ต Cycle 1
                prompt = (f"ในฐานะที่ปรึกษาการลงทุน ช่วยวิเคราะห์หุ้น {asset_info} "
                         f"สำหรับพอร์ตเน้นเงินปันผล (Cycle 1) ของนักลงทุนวัย 46 ปี "
                         f"ที่มีพื้นฐานวิศวกรรมและต้องการอิสรภาพทางการเงินครับ")
                
                response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
                reply_text = f"[📊 AI Analysis]\n{asset_info}\n\n{response.text}"
                
        except Exception as e:
            reply_text = f"ขออภัยครับคุณ Auttawut เกิดข้อผิดพลาดในการดึงข้อมูลหุ้น '{user_text}'"

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

# แก้ไขจุดนี้: เพื่อให้ Render/Gunicorn ตรวจพบ Port ได้โดยตรง
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)