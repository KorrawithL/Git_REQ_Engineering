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
    # 💡 ระบบหลักดึงข้อมูลจาก .env หรือ st.secrets เพื่อความปลอดภัย
    db_host = os.getenv("DB_HOST") or st.secrets.get("DB_HOST")
    db_port = int(os.getenv("DB_PORT") or st.secrets.get("DB_PORT", 4000))
    db_user = os.getenv("DB_USER") or st.secrets.get("DB_USER")
    db_pass = os.getenv("DB_PASSWORD") or st.secrets.get("DB_PASSWORD")
    db_name = os.getenv("DB_NAME") or st.secrets.get("DB_NAME")

    # URL Format: mysql+pymysql://user:pass@host:port/dbname
    db_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
    
    # ปล่อยให้ SQLAlchemy เช็คระบบพื้นฐานได้ปกติ (เอา connect_args ออกเพื่อแก้บัค Error 0)
    engine = create_engine(
        db_url, 
        pool_size=10, 
        max_overflow=20, 
        pool_recycle=3600
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
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = """INSERT INTO activity_logs (user_id, username, action_type, module_name, details, created_at) 
                     VALUES (%s, %s, %s, %s, %s, NOW())"""
            cur.execute(sql, (user_id, username, action_type, module_name, details))
            conn.commit()
        conn.close() # โยนท่อกลับลงสระ
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการบันทึก Activity Log: {e}")