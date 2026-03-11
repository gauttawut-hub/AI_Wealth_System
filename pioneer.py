import requests
import yfinance as yf
from google import genai

# --- 🔑 กุญแจส่วนตัวของคุณ ---
GEMINI_API_KEY = "AIzaSyDGiNY4zKNUg9Fw5H9gFlV5gjO_Ji0m_rM"
CHANNEL_ACCESS_TOKEN = "0MAaQKPtnor10euvj8gitpfCVstVo4z34LU8b3K8wpSYk34CP7r7USWZvZwqJy8bc8HHTlFi99Qti+TS0zXH0xNjFht/TmJIpG0LFUs3TIGx2UWWPdkTsjql5A7CwEMArVUTz2noFqXu+6pmtFzldAdB04t89/1O/w1cDnyilFU="
USER_ID = "Ucf88076ccc251f1b94b2dd2ffdb0bfac"

client = genai.Client(api_key=GEMINI_API_KEY)

def send_line(msg):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {CHANNEL_ACCESS_TOKEN}'}
    data = {'to': USER_ID, 'messages': [{'type': 'text', 'text': msg}]}
    return requests.post(url, headers=headers, json=data).status_code

def run_pioneer():
    print("\n--- 🔍 ระบบค้นหาโมเดลที่ใช้งานได้ (v1.4.2) ---")
    
    # ดึงรายชื่อโมเดลด้วย Syntax ใหม่
    available_models = []
    try:
        print("📡 กำลังตรวจสอบรายชื่อโมเดล...")
        # SDK ตัวใหม่จะใช้ m.name และเช็คผ่าน list ปกติ
        for m in client.models.list():
            # เราเน้นเฉพาะตระกูล gemini-1.5-flash หรือ gemini-2.0-flash
            if "gemini" in m.name:
                available_models.append(m.name)
        
        if available_models:
            print(f"✅ พบโมเดลที่ใช้งานได้: {available_models[0]}")
        else:
            print("❌ ไม่พบโมเดลที่รองรับในบัญชีนี้")
            return
    except Exception as e:
        print(f"❌ ระบบขัดข้อง: {e}")
        return

    ticker = input("\nป้อนชื่อหุ้น (เช่น PM): ").strip().upper()
    try:
        # ดึงราคาตลาด
        price = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
        asset_data = f"{ticker}: ${price:.2f}"
        
        # ใช้โมเดลตัวแรกที่พบ
        target_model = available_models[0]
        print(f"🤖 กำลังวิเคราะห์หุ้นปันผลสำหรับคุณ Auttawut...")
        
        response = client.models.generate_content(
            model=target_model, 
            contents=f"หุ้น {asset_data} เหมาะกับพอร์ต Cycle 1 ของนักลงทุนวัย 46 ปีไหม?"
        )
        
        report = f"[📊 รายงานด่วน]\n{asset_data}\n💡 AI วิเคราะห์:\n{response.text}"
        
        if send_line(report) == 200:
            print("✅ สำเร็จ! บทวิเคราะห์ถูกส่งเข้า LINE เรียบร้อยแล้ว")
        else:
            print("❌ ส่ง LINE ไม่สำเร็จ")
            
    except Exception as e:
        print(f"❌ พังที่จุดวิเคราะห์: {e}")

if __name__ == "__main__":
    run_pioneer()