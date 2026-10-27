import streamlit as st
import pandas as pd
import io
from database import get_db_connection

def render_system_logs_module():
    # 🎯 ซ่อนแถบ Header ด้านบน, ปรับ Padding Top และแก้ไอคอน Help (?)
    st.markdown("""
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        #header { visibility: hidden !important; }
        #MainMenu { visibility: hidden !important; }
        .block-container { padding-top: 1rem !important; margin-top: -20px !important; }

        div[data-testid="stTooltipHoverTarget"] svg,
        div[data-testid="stTooltipIcon"] svg,
        label[data-testid="stWidgetLabel"] svg {
            fill: none !important;
            stroke: #64748B !important;
            color: #64748B !important;
            background: transparent !important;
        }
        div[data-testid="stTooltipHoverTarget"] svg *,
        div[data-testid="stTooltipIcon"] svg *,
        label[data-testid="stWidgetLabel"] svg * {
            fill: none !important;
            stroke: #64748B !important;
            stroke-width: 2px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.header("📋 ประวัติกิจกรรมของระบบ (System Activity Logs)")
    st.caption("ระบบตรวจสอบและติดตามกิจกรรมการบันทึก แก้ไข ลบข้อมูล และการเข้าถึงระบบ")

    # กล่องคำแนะนำภาพรวมด้านบน
    st.info(
        "💡 **ข้อมูลเพื่อการตรวจสอบ (Audit Trail):** ประวัติทั้งหมดในหน้านี้ถูกบันทึกอัตโนมัติทุกครั้งที่มีการทำรายการ "
        "ไม่สามารถแก้ไขหรือลบออกได้ เพื่อใช้ตรวจสอบย้อนหลังด้านความปลอดภัยและความถูกต้องของข้อมูล"
    )

    # ดึงรายชื่อ User และ Module ทั้งหมดที่มีในระบบมาทำตัวเลือก Dropdown
    user_list = ["ทั้งหมด"]
    module_list = ["ทั้งหมด"]
    action_list = ["ทั้งหมด", "INSERT", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "FAILED_LOGIN"]
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT username FROM activity_logs WHERE username IS NOT NULL AND username != '' ORDER BY username ASC")
            for r in cur.fetchall():
                if r.get('username'):
                    user_list.append(r['username'])
                    
            cur.execute("SELECT DISTINCT CONVERT(module_name USING utf8mb4) AS mod_name FROM activity_logs WHERE module_name IS NOT NULL AND module_name != '' ORDER BY mod_name ASC")
            for r in cur.fetchall():
                if r.get('mod_name'):
                    module_list.append(r['mod_name'])
    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    # ==========================================
    # 🔍 1. ส่วนตัวกรองข้อมูล (แบบพับเก็บ/กางออกได้ + Dropdown โมดูล)
    # ==========================================
    with st.expander("🔍 ตัวกรองค้นหาประวัติกิจกรรม (Filter Panel)", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            start_date = st.date_input(
                "📅 ตั้งแต่วันที่:", 
                value=pd.to_datetime("today").date().replace(day=1), 
                key="log_s_date",
                help="วันเริ่มต้นที่ต้องการดูประวัติ (ค่าเริ่มต้นจะตั้งไว้ที่วันที่ 1 ของเดือนปัจจุบัน)"
            )
        with col2:
            end_date = st.date_input(
                "📅 ถึงวันที่:", 
                value=pd.to_datetime("today").date(), 
                key="log_e_date",
                help="วันสิ้นสุดที่ต้องการดูประวัติ (ค่าเริ่มต้นคือวันปัจจุบัน)"
            )
        with col3:
            selected_user = st.selectbox(
                "👤 ผู้ใช้งาน (User):", 
                options=user_list, 
                key="log_sel_user",
                help="เลือกดูประวัติเฉพาะผู้ใช้งานที่ต้องการ"
            )
        with col4:
            selected_action = st.selectbox(
                "⚡ ประเภทกิจกรรม:", 
                options=action_list, 
                key="log_sel_act",
                help=(
                    "📌 ความหมายของประเภทกิจกรรม:\n"
                    "• INSERT: เพิ่มข้อมูลใหม่ หรือลงบันทึกประจำวัน\n"
                    "• UPDATE: แก้ไขข้อมูล, ปรับสิทธิ์, กู้คืนข้อมูล หรือระงับการใช้งาน\n"
                    "• DELETE: ย้ายข้อมูลลงถังขยะ หรือลบข้อมูลถาวร\n"
                    "• LOGIN / LOGOUT: เข้าสู่ระบบ / ออกจากระบบปกติ\n"
                    "• FAILED_LOGIN: พยายามเข้าสู่ระบบไม่สำเร็จ (เช่น รหัสผ่านผิด)"
                )
            )

        col5, col6 = st.columns([1.5, 2.5])
        with col5:
            selected_module = st.selectbox(
                "📂 เลือกเมนู / โมดูล:",
                options=module_list,
                key="log_sel_mod",
                help="คลิกเลือกหน้าเมนูหรือโมดูลที่ต้องการตรวจสอบจากรายการ Dropdown"
            )
        with col6:
            search_keyword = st.text_input(
                "🔎 ค้นหาคำสำคัญในรายละเอียด:", 
                placeholder="พิมพ์คำค้นหา เช่น ชื่อสาขา, รหัสเครื่องจักร, รหัสผ่าน...", 
                key="log_search_kw",
                help="พิมพ์ Keyword เพื่อค้นหาเจาะจงในคอลัมน์รายละเอียดกิจกรรม"
            )

    # ==========================================
    # 🗄️ 2. ดึงข้อมูลจากตาราง activity_logs
    # ==========================================
    logs_data = []
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = """
                SELECT log_id, user_id, ip_address, username, action_type, module_name, details, created_at
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

            if selected_module != "ทั้งหมด":
                sql += " AND CONVERT(module_name USING utf8mb4) = %s"
                params.append(selected_module)

            if search_keyword.strip():
                sql += " AND (details LIKE %s OR module_name LIKE %s)"
                kw = f"%{search_keyword.strip()}%"
                params.extend([kw, kw])

            sql += " ORDER BY created_at DESC"
            cur.execute(sql, tuple(params))
            logs_data = cur.fetchall()
    except Exception as e:
        st.error(f"⚠️ เกิดข้อผิดพลาดในการดึงข้อมูล Log: {e}")
    finally:
        if conn:
            conn.close()

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
            'ip_address': 'IP Address',
            'username': 'ชื่อผู้ใช้',
            'action_type': 'กิจกรรม',
            'module_name': 'เมนู / โมดูล',
            'details': 'รายละเอียดกิจกรรม',
            'created_at': 'วัน-เวลาที่ทำรายการ'
        })

        # แสดงจำนวนที่พบ พร้อมป้ายบอกลำดับการเรียงข้อมูลชิดขวา
        col_res1, col_res2 = st.columns([2, 2])
        with col_res1:
            st.markdown(f"**พบข้อมูลทั้งหมด:** `{len(df_display):,}` รายการ")
        with col_res2:
            st.markdown(
                "<div style='text-align: right;'><span style='background-color: #F1F5F9; color: #475569; "
                "padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;'>"
                "🕒 เรียงจากรายการล่าสุดไปเก่าสุด</span></div>", 
                unsafe_allow_html=True
            )
        
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
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="ดาวน์โหลดรายการประวัติกิจกรรมที่แสดงอยู่ในตารางด้านบนออกมาเป็นไฟล์ Excel (.xlsx)"
        )
    else:
        st.info("ℹ️ ไม่พบประวัติกิจกรรมตามเงื่อนไขที่เลือก (ลองขยายช่วงวันที่ หรือเปลี่ยนตัวกรองใหม่)")