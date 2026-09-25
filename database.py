import pymysql
import hashlib
import streamlit as st
import os
from dotenv import load_dotenv

# โหลดตัวแปรจากไฟล์ .env (มีผลเฉพาะตอนรันในเครื่องตัวเอง)
load_dotenv()

def get_db_connection():
    # 💡 ท่านี้จะรองรับทั้งการรันในเครื่อง (.env) และรันบนคลาวด์ (st.secrets)
    db_host = os.getenv("DB_HOST") or st.secrets.get("DB_HOST")
    db_port = int(os.getenv("DB_PORT") or st.secrets.get("DB_PORT", 4000))
    db_user = os.getenv("DB_USER") or st.secrets.get("DB_USER")
    db_pass = os.getenv("DB_PASSWORD") or st.secrets.get("DB_PASSWORD")
    db_name = os.getenv("DB_NAME") or st.secrets.get("DB_NAME")

    conn = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_pass,
        database=db_name,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )   

    # 2. 🌟 บังคับตั้งค่าโซนเวลา UTC+7 ทันทีหลังเชื่อมต่อเสร็จ 🌟
    with conn.cursor() as cur:
        cur.execute("SET time_zone = '+07:00';")
        
    # 3. คืนค่าการเชื่อมต่อที่สมบูรณ์ออกไปใช้งาน
    return conn

# 🔒 ฟังก์ชันเข้ารหัสรหัสผ่าน
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()    

def log_activity(user_id, username, action_type, module_name, details):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = """INSERT INTO activity_logs (user_id, username, action_type, module_name, details, created_at) 
                     VALUES (%s, %s, %s, %s, %s, NOW())"""
            cur.execute(sql, (user_id, username, action_type, module_name, details))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการบันทึก Activity Log: {e}")