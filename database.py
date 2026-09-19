import pymysql
import hashlib
import streamlit as st

# 🔌 ฟังก์ชันเชื่อมต่อฐานข้อมูลภายในเครื่อง (Localhost)
def get_db_connection():
    return pymysql.connect(
        host='gateway01.ap-southeast-1.prod.aws.tidbcloud.com',      # หรือใช้ 'localhost' เพื่อชี้มาที่เครื่องตัวเอง
        port=4000,             # Port มาตรฐานของ MySQL/MariaDB บนเครื่อง (ปรับเป็น 3307 ได้หากตั้งค่าไว้)
        user='2mbHs86f3hLpHFz.root',           # User ปกติของเครื่อง Local มักจะเป็น 'root'
        password='BIMEgjBQow3etWIX',           # รหัสผ่าน MySQL บนเครื่องของคุณ (ถ้าไม่มีให้ใส่ '')
        database='Woodwork_Engineering_Records_System', # ชื่อฐานข้อมูลภายในเครื่อง
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

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