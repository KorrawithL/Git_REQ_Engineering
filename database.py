import pymysql
import hashlib
import streamlit as st

# 🔌 ฟังก์ชันเชื่อมต่อฐานข้อมูล
def get_db_connection():
    # 1. สร้างตัวแปร conn มารับค่าการเชื่อมต่อ (เอาคำว่า return ออกไปก่อน)
    conn = pymysql.connect(
        host='gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
        port=4000,
        user='2mbHs86f3hLpHFz.root',
        password='cJaPr62UlEdMdvs6',
        database='Woodwork_Engineering_Records_System',
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