import streamlit as st
from database import get_db_connection

@st.cache_data(ttl=300) # แคชข้อมูลไว้ 5 นาทีเพื่อไม่ให้ดึง Database ซ้ำซ้อน
def get_branch_dict():
    b_dict = {}
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # ดึงเฉพาะสาขาที่กำลังเปิดใช้งานอยู่ (is_active = 1)
            cur.execute("SELECT id, CONVERT(branch_name USING utf8mb4) AS branch_name FROM branches WHERE is_active = 1 ORDER BY id ASC")
            for r in cur.fetchall():
                b_dict[r['branch_name']] = r['id']
    except Exception as e:
        print(f"Error fetching branches in config: {e}")
    finally:
        if conn:
            conn.close()
    return b_dict

# สร้างตัวแปร branch_dict จากฐานข้อมูล เพื่อให้ไฟล์อื่นๆ (tab_views, all_reports ฯลฯ) import ไปใช้ได้เหมือนเดิมเป๊ะ
branch_dict = get_branch_dict()