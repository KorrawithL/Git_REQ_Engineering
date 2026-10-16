import pymysql
import hashlib
import streamlit as st
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

# 🌟 1. สร้าง Connection Pool ด้วย SQLAlchemy
@st.cache_resource
def get_db_engine():
    db_user = 'root'
    db_pass = ''
    db_host = '127.0.0.1'
    db_port = 3306
    db_name = 'woodwork_engineering_records_system'
    
    db_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
    
    # ถอดคำสั่งบังคับ DictCursor ออกจากตรงนี้ ปล่อยให้ SQLAlchemy เช็คระบบพื้นฐานได้ปกติ
    engine = create_engine(
        db_url, 
        pool_size=10, 
        max_overflow=20, 
        pool_recycle=1800,        # ลดเวลาแอบรีเซ็ตท่อเหลือ 30 นาที (1800 วินาที)
        pool_pre_ping=True        # 🌟 พระเอกของงานนี้: เคาะเทสสายก่อนใช้งาน ถ้าสายหลุดให้ต่อใหม่ทันที!
    )
    return engine

# 🌟 2. สร้างปลอกสวม (Wrapper) เพื่อเปลี่ยนให้คืนค่าเป็น Dictionary เฉพาะในแอปของเรา
# 🌟 2. สร้างปลอกสวม (Wrapper) เพื่อเปลี่ยนให้คืนค่าเป็น Dictionary เฉพาะในแอปของเรา
class DictConnectionWrapper:
    def __init__(self, raw_conn):
        self.raw_conn = raw_conn
        
    def cursor(self):
        # บังคับแปลงเป็น Dict ทันทีเมื่อแอปเราเรียกใช้
        return self.raw_conn.cursor(pymysql.cursors.DictCursor)
        
    def __getattr__(self, name):
        # 🌟 เพิ่มคำสั่งนี้: ถ้าไฟล์อื่นเรียกใช้คำสั่งที่ไม่ได้เขียนไว้ตรงนี้ (เช่น .open, .commit, .close)
        # ให้มันฉลาดพอที่จะส่งผ่าน (Forward) ไปให้ตัวการเชื่อมต่อจริงทำงานแทนอัตโนมัติ!
        return getattr(self.raw_conn, name)

def get_db_connection():
    # ดึงท่อการเชื่อมต่อจากสระน้ำ (Pool)
    engine = get_db_engine()
    raw_conn = engine.raw_connection() 
    
    # สวมปลอก Dict ให้ Connection ก่อนส่งไปใช้งาน
    wrapped_conn = DictConnectionWrapper(raw_conn)
    
    with wrapped_conn.cursor() as cur:
        cur.execute("SET time_zone = '+07:00';")
        
    return wrapped_conn

# 🔒 ฟังก์ชันเข้ารหัสรหัสผ่าน
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()    

def log_activity(user_id, username, action_type, module_name, details):
    # 🌟 ดึง IP Address ของผู้ใช้งานผ่าน Request Headers (รองรับ Nginx Reverse Proxy)
    client_ip = "127.0.0.1"
    try:
        headers = st.context.headers
        client_ip = headers.get("X-Forwarded-For", headers.get("X-Real-IP", "127.0.0.1"))
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
    except Exception:
        pass

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = """INSERT INTO activity_logs (user_id, ip_address, username, action_type, module_name, details, created_at) 
                     VALUES (%s, %s, %s, %s, %s, %s, NOW())"""
            cur.execute(sql, (user_id, client_ip, username, action_type, module_name, details))
            conn.commit()
        conn.close() # โยนท่อกลับลงสระ
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการบันทึก Activity Log: {e}")