import streamlit as st
import pandas as pd
import time
from database import get_db_connection, hash_password
from config import branch_dict

def render_admin_user_management():
    st.header("👥 ระบบบริหารสิทธิ์และจัดการผู้ใช้งานระบบ")
    
    try:
        connection = get_db_connection()
        with connection.cursor() as user_cursor:
            user_cursor.execute("""
                SELECT u.user_id, u.username, u.branch_id, b.branch_name, u.Role_tab, u.allowed_tabs, u.status 
                FROM system_users u LEFT JOIN branches b ON u.branch_id = b.id ORDER BY u.user_id ASC
            """)
            all_users = user_cursor.fetchall()
        connection.close()
    except Exception as e:
        st.error(f"ไม่สามารถดึงตารางรายชื่อผู้ใช้งานได้: {e}")
        all_users = []

    with st.expander("➕ เพิ่มบัญชีผู้ใช้งานใหม่เข้าระบบโดยแอดมิน"):
        with st.form("admin_add_user_form", clear_on_submit=True):
            new_user = st.text_input("Username (User ID)")
            new_pass = st.text_input("Password", type="password")
            new_branch_label = st.selectbox("เลือกสาขาประจำตัว", options=list(branch_dict.keys()), key="adm_add_br")
            
            # 🎯 เพิ่ม Role Reporter
            new_role = st.selectbox("กำหนดระดับสิทธิ์ (Role_tab)", options=["user", "reporter", "manager", "admin"])
            
            if st.form_submit_button("➕ เพิ่มข้อมูลผู้ใช้ระบบ"):
                if new_user == "" or new_pass == "":
                    st.error("กรุณากรอก Username และ Password ให้ครบถ้วน")
                else:
                    try:
                        connection = get_db_connection()
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT user_id FROM system_users WHERE username = %s", (new_user,))
                            if cursor.fetchone(): st.error("ชื่อ Username นี้มีอยู่ในระบบแล้ว")
                            else:
                                sql = """INSERT INTO system_users (username, password_hash, branch_id, Role_tab, allowed_tabs, status) 
                                         VALUES (%s, %s, %s, %s, '', 'active')"""
                                cursor.execute(sql, (new_user, hash_password(new_pass), branch_dict[new_branch_label], new_role))
                                connection.commit()
                                st.success(f"เพิ่มผู้ใช้งาน {new_user} สำเร็จ!")
                                time.sleep(1)
                                st.rerun()
                        connection.close()
                    except Exception as err: st.error(f"เกิดข้อผิดพลาด: {err}")

    st.write("### 🗂️ รายชื่อผู้ใช้งานทั้งหมดในระบบ")
    if all_users:
        df_users = pd.DataFrame(all_users)
        df_users.columns = ['ID', 'Username', 'รหัสสาขา', 'ชื่อสาขา', 'ระดับสิทธิ์ (Role_tab)', 'แท็บที่เข้าถึงได้', 'สถานะบัญชี']
        st.dataframe(df_users[['ID', 'Username', 'ชื่อสาขา', 'ระดับสิทธิ์ (Role_tab)', 'แท็บที่เข้าถึงได้', 'สถานะบัญชี']], use_container_width=True)
        
        st.write("---")
        st.write("#### 🛠️ เครื่องมืออนุมัติและปรับเปลี่ยนสิทธิ์รายบัญชี")
        user_options = {row['username']: row['user_id'] for row in all_users}
        selected_target_user = st.selectbox("เลือกชื่อบัญชีผู้ใช้งานที่ต้องการปรับปรุง:", options=list(user_options.keys()))
        target_id = user_options[selected_target_user]
        
        current_user_row = [r for r in all_users if r['user_id'] == target_id][0]
        
        tab_assign_options = {
            "🔒 ล็อกสิทธิ์เข้าใช้งานทุกแท็บ (รออนุมัติ)": [],
            "🌐 เข้าถึงได้ทุกแท็บงาน (1, 2, 3, 4)": ["1", "2", "3", "4"],
            "⚙️ 1. ระบบเครื่องจักร / เบรกดาวน์": ["1"],
            "🚚 2. ระบบเชื้อเพลิง (รถยก/เครื่องยนต์)": ["2"],
            "💨 3. แรงดันไอน้ำปลายทาง บอยเลอร์": ["3"],
            "🔥 4. การใช้เชื้อเพลิง บอยเลอร์": ["4"]
        }

        raw_tabs = current_user_row.get('allowed_tabs', '') or ''
        current_user_tabs = [x.strip() for x in str(raw_tabs).split(',') if x.strip()]

        default_idx = 0
        set_tabs = set(current_user_tabs)
        if set_tabs == {"1", "2", "3", "4"}: default_idx = 1
        elif "1" in set_tabs: default_idx = 2
        elif "2" in set_tabs: default_idx = 3
        elif "3" in set_tabs: default_idx = 4
        elif "4" in set_tabs: default_idx = 5

        # 🎯 เพิ่ม Reporter สำหรับแก้ไข
        role_list = ["user", "reporter", "manager", "admin"]
        curr_role_idx = role_list.index(current_user_row['Role_tab']) if current_user_row['Role_tab'] in role_list else 0
        status_list = ["active", "pending", "disabled"]
        curr_status_idx = status_list.index(current_user_row['status']) if current_user_row['status'] in status_list else 0

        c_edit1, c_edit2, c_edit3 = st.columns(3)
        with c_edit1: edit_role = st.selectbox("ระดับสิทธิ์ (Role_tab):", options=role_list, index=curr_role_idx)
        with c_edit2: selected_tab_label = st.selectbox("เลือกจัดสรรแท็บงานประจำบัญชี:", options=list(tab_assign_options.keys()), index=default_idx)
        with c_edit3: edit_status = st.selectbox("สถานะบัญชี:", options=status_list, index=curr_status_idx)

        selected_allowed_tabs = tab_assign_options[selected_tab_label]

        if st.button("💾 บันทึกและอนุมัติสิทธิ์การเข้าถึงแท็บ", use_container_width=True):
            try:
                allowed_tabs_str = ",".join(selected_allowed_tabs)
                conn = get_db_connection()
                with conn.cursor() as cur:
                    sql_update = """UPDATE system_users SET Role_tab=%s, allowed_tabs=%s, status=%s WHERE user_id=%s"""
                    cur.execute(sql_update, (edit_role, allowed_tabs_str, edit_status, int(target_id)))
                    conn.commit()
                conn.close()
                st.success(f"อัปเดตสิทธิ์การใช้งานของ '{selected_target_user}' สำเร็จเรียบร้อย!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
                
        st.write("<br>", unsafe_allow_html=True)
        with st.expander("🚨 โซนอันตราย: ลบบัญชีผู้ใช้นี้ออกจากระบบ"):
            st.warning(f"คุณแน่ใจหรือไม่ที่จะทำการลบบัญชีผู้ใช้งานที่ชื่อว่า **{selected_target_user}**?")
            if st.button(f"🗑️ ยืนยันการลบตัวตน {selected_target_user}", key="btn_del_usr", type="primary", use_container_width=True):
                try:
                    connection = get_db_connection()
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM system_users WHERE user_id = %s", (int(target_id),))
                        connection.commit()
                    connection.close()
                    st.success(f"ทำการลบบัญชี {selected_target_user} ออกจากฐานข้อมูลเสร็จสิ้น")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"ไม่สามารถลบข้อมูลได้: {e}")