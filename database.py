import pymysql
import hashlib
import streamlit as st

# 🔌 ฟังก์ชันเชื่อมต่อฐานข้อมูลบน TiDB Cloud
def get_db_connection():
    db_config = st.secrets["mysql"]
    
    return pymysql.connect(
        host=db_config["host"],
        port=int(db_config["port"]),
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        charset='utf8mb4',
        ssl_verify_cert=True,
        ssl_verify_identity=True,
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