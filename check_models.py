import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("Error: ไม่พบ API Key ในไฟล์ .env")
else:
    genai.configure(api_key=api_key)
    print("กำลังตรวจสอบรายชื่อโมเดลที่ใช้ได้... (กรุณารอสักครู่)")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")