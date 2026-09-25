import pymysql
import hashlib
import streamlit as st
import os
from dotenv import load_dotenv

# 🪄 โหลดตัวแปรจากไฟล์ .env (มีผลเฉพาะตอนรันในเครื่องตัวเอง)
load_dotenv()

def get_db_connection():
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 4000)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
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