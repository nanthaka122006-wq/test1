import os
import re
import fitz  # PyMuPDF
import google.generativeai as genai
import streamlit as st
import dotenv
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# 1. พยายามโหลด prompt ถ้าไม่มีให้สร้าง dummy ไว้ก่อนกัน Error
try:
    from prompt import PROMPT_WORKAW
except ImportError:
    PROMPT_WORKAW = "คุณคือผู้เชี่ยวชาญด้านกราฟิก ตอบคำถามจากเนื้อหาที่ให้มาเท่านั้น"

# โหลด Environment Variables
dotenv.load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    st.error("❌ ไม่พบ GOOGLE_API_KEY ในไฟล์ .env")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# --- Configuration ---
generation_config = {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_output_tokens": 2048,
}

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
}

# --- CSS ธีมทะเลพาสเทล (ปรับปรุงให้รันง่ายขึ้น) ---
st.set_page_config(page_title="Graphic Bot Under the Sea", layout="centered")

page_style = """
<style>
    /* พื้นหลังไล่เฉดสีฟ้าเขียวพาสเทล */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #A2D2FF 0%, #BDE0FE 40%, #E0F7FA 100%);
        background-attachment: fixed;
    }
    
    /* กล่องแชท */
    [data-testid="stChatMessage"] {
        background-color: rgba(255, 255, 255, 0.8) !important;
        border-radius: 15px;
        margin-bottom: 10px;
        border: 1px solid #B2EBF2;
    }

    /* แอเรียลที่มุมขวา */
    .ariel-overlay {
        position: fixed;
        bottom: 10px;
        right: 10px;
        width: 150px;
        z-index: 100;
        pointer-events: none;
        opacity: 0.9;
    }
</style>
<img src="https://www.pngplay.com/wp-content/uploads/12/The-Little-Mermaid-Ariel-Transparent-File.png" class="ariel-overlay">
"""
st.markdown(page_style, unsafe_allow_html=True)

# --- ฟังก์ชันโหลด PDF ---
@st.cache_resource
def load_pdf(file_path):
    if not os.path.exists(file_path):
        return None, None
    
    text_content = ""
    images_map = {}
    try:
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            p_num = i + 1
            text_content += f"\n[--- Page {p_num} START ---]\n{page.get_text()}\n[--- Page {p_num} END ---]\n"
            # เก็บภาพหน้าเต็มแบบประหยัด Memory
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            images_map[p_num] = [pix.tobytes("png")]
        return text_content, images_map
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
        return None, None

pdf_text, pdf_images = load_pdf("Graphic.pdf")

if not pdf_text:
    st.warning("⚠️ ไม่พบไฟล์ Graphic.pdf กรุณาตรวจสอบชื่อไฟล์")
    st.stop()

# --- ตั้งค่า AI Model ---
system_instruction = f"{PROMPT_WORKAW}\n\nCONTEXT:\n{pdf_text}\n\nคำสั่งพิเศษ: ต้องระบุเลขหน้าในรูปแบบ [PAGE: X] เสมอ"
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction,
    generation_config=generation_config,
    safety_settings=SAFETY_SETTINGS
)

# --- UI ส่วนแสดงผล ---
st.title("🧜‍♀️ Graphic Bot (Sea Edition)")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "model", "content": "สวัสดีค่ะ มีอะไรให้ช่วยเกี่ยวกับกราฟิกไหมคะ? 🌊"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧜‍♀️" if msg["role"]=="model" else "🐚"):
        st.write(msg["content"])
        if "imgs" in msg and msg["imgs"]:
            for img in msg["imgs"]:
                st.image(img)

# --- ส่วนรับข้อความ ---
if prompt := st.chat_input("พิมพ์คำถามที่นี่..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🐚"):
        st.write(prompt)

    try:
        chat = model.start_chat(history=[{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]])
        response = chat.send_message(prompt)
        res_text = response.text
        
        # ค้นหาเลขหน้า
        match = re.search(r"\[PAGE:\s*(\d+)\]", res_text)
        found_imgs = []
        page_num = None
        if match:
            page_num = int(match.group(1))
            found_imgs = pdf_images.get(page_num, [])

        with st.chat_message("model", avatar="🧜‍♀️"):
            st.write(res_text)
            for img in found_imgs:
                st.image(img, caption=f"อ้างอิงจากหน้า {page_num}")

        st.session_state.messages.append({"role": "model", "content": res_text, "imgs": found_imgs})
    except Exception as e:
        st.error(f"AI Error: {e}")