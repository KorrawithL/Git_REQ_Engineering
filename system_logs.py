import streamlit as st
import pandas as pd
import io
from database import get_db_connection

def render_system_logs_module():
    st.subheader("📋 ประวัติกิจกรรมของระบบ (System Activity Logs)")
    st.caption("ระบบตรวจสอบและติดตามกิจกรรมการบันทึก แก้ไข ลบข้อมูล และการเข้าถึงระบบ")

    # ==========================================
    # 🔍 1. ส่วนตัวกรองข้อมูล (Filters)
    # ==========================================
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1.5])
    
    with col1:
        start_date = st.date_input("ตั้งแต่วันที่", value=pd.to_datetime("today").date().replace(day=1), key="log_s_date")
    with col2:
        end_date = st.date_input("ถึงวันที่", value=pd.to_datetime("today").date(), key="log_e_date")
        
    # ดึงรายชื่อ User และ Action Type ทั้งหมดที่มีในระบบมาทำตัวเลือก
    user_list = ["ทั้งหมด"]
    action_list = ["ทั้งหมด", "INSERT", "UPDATE", "DELETE"]
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT username FROM activity_logs ORDER BY username ASC")
            for r in cur.fetchall():
                if r.get('username'):
                    user_list.append(r['username'])
        conn.close()
    except Exception:
        pass

    with col3:
        selected_user = st.selectbox("ผู้ใช้งาน (User):", options=user_list, key="log_sel_user")
    with col4:
        selected_action = st.selectbox("ประเภทกิจกรรม:", options=action_list, key="log_sel_act")

    search_keyword = st.text_input("🔎 ค้นหาข้อความในรายละเอียด หรือชื่อโมดูล:", placeholder="พิมพ์คำค้นหา เช่น บอยเลอร์, ลบข้อมูล, รหัสผ่าน...", key="log_search_kw")

    # ==========================================
    # 🗄️ 2. ดึงข้อมูลจากตาราง activity_logs
    # ==========================================
    logs_data = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = """
                SELECT log_id, user_id, username, action_type, module_name, details, created_at
                FROM activity_logs
                WHERE DATE(created_at) BETWEEN %s AND %s
            """
            params = [str(start_date), str(end_date)]

            if selected_user != "ทั้งหมด":
                sql += " AND username = %s"
                params.append(selected_user)

            if selected_action != "ทั้งหมด":
                sql += " AND action_type = %s"
                params.append(selected_action)

            if search_keyword.strip():
                sql += " AND (details LIKE %s OR module_name LIKE %s)"
                kw = f"%{search_keyword.strip()}%"
                params.extend([kw, kw])

            sql += " ORDER BY created_at DESC"
            cur.execute(sql, tuple(params))
            logs_data = cur.fetchall()
        conn.close()
    except Exception as e:
        st.error(f"⚠️ เกิดข้อผิดพลาดในการดึงข้อมูล Log: {e}")

    # ==========================================
    # 📊 3. แสดงผลตารางข้อมูลและส่งออก Excel
    # ==========================================
    if logs_data:
        df_logs = pd.DataFrame(logs_data)
        
        # จัดรูปแบบวันที่เวลาให้แสดงชัดเจน
        df_logs['created_at'] = pd.to_datetime(df_logs['created_at']).dt.strftime('%d/%m/%Y %H:%M:%S')
        
        # เปลี่ยนชื่อคอลัมน์ให้อ่านง่าย
        df_display = df_logs.rename(columns={
            'log_id': 'รหัส Log',
            'user_id': 'User ID',
            'username': 'ชื่อผู้ใช้',
            'action_type': 'กิจกรรม',
            'module_name': 'เมนู / โมดูล',
            'details': 'รายละเอียดกิจกรรม',
            'created_at': 'วัน-เวลาที่ทำรายการ'
        })

        st.markdown(f"**พบข้อมูลทั้งหมด:** `{len(df_display):,}` รายการ")
        
        # แสดงตารางแบบเต็มความกว้าง
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # เตรียมปุ่มดาวน์โหลดเป็นไฟล์ Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_display.to_excel(writer, index=False, sheet_name='Activity_Logs')
            
        st.download_button(
            label="📗 Export ประวัติ Log เป็น Excel",
            data=excel_buffer.getvalue(),
            file_name=f"System_Activity_Logs_{start_date}_to_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("ℹ️ ไม่พบประวัติกิจกรรมตามเงื่อนไขที่เลือก")