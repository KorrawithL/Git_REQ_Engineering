import streamlit as st
import pandas as pd
import time
from database import get_db_connection, hash_password
from config import branch_dict

def render_admin_user_management():
    st.header("👥 ระบบบริหารสิทธิ์และจัดการผู้ใช้งานระบบ")
    
    try:
        conn = get_db_connection()
        with conn.cursor() as user_cursor:
            # 🎯 ใช้ GROUP_CONCAT รวม ID สาขาจากตาราง user_branches
            user_cursor.execute("""
                SELECT u.user_id, u.username, u.branch_id, b.branch_name, u.Role_tab, u.allowed_tabs, u.status,
                       GROUP_CONCAT(ub.branch_id) as additional_branches
                FROM system_users u
                LEFT JOIN branches b ON u.branch_id = b.id
                LEFT JOIN user_branches ub ON u.user_id = ub.user_id
                GROUP BY u.user_id
                ORDER BY u.user_id ASC
            """)
            all_users = user_cursor.fetchall()
        conn.close()
    except Exception as e:
        st.error(f"ไม่สามารถดึงตารางรายชื่อผู้ใช้งานได้: {e}")
        all_users = []

    with st.expander("➕ เพิ่มบัญชีผู้ใช้งานใหม่เข้าระบบโดยแอดมิน"):
        with st.form("admin_add_user_form", clear_on_submit=True):
            new_user = st.text_input("Username (User ID)")
            new_pass = st.text_input("Password", type="password")
            new_branch_label = st.selectbox("เลือกสาขาประจำตัว (หลัก)", options=list(branch_dict.keys()), key="adm_add_br")
            new_role = st.selectbox("กำหนดระดับสิทธิ์ (Role_tab)", options=["user", "reporter", "manager", "admin"])
            
            if st.form_submit_button("➕ เพิ่มข้อมูลผู้ใช้ระบบ"):
                if new_user == "" or new_pass == "": st.error("กรุณากรอก Username และ Password ให้ครบถ้วน")
                else:
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT user_id FROM system_users WHERE username = %s", (new_user,))
                            if cursor.fetchone(): st.error("ชื่อ Username นี้มีอยู่ในระบบแล้ว")
                            else:
                                sql = """INSERT INTO system_users (username, password_hash, branch_id, Role_tab, allowed_tabs, status) 
                                         VALUES (%s, %s, %s, %s, '', 'active')"""
                                cursor.execute(sql, (new_user, hash_password(new_pass), branch_dict[new_branch_label], new_role))
                                conn.commit()
                                st.success(f"เพิ่มผู้ใช้งาน {new_user} สำเร็จ!")
                                time.sleep(1)
                                st.rerun()
                        conn.close()
                    except Exception as err: st.error(f"เกิดข้อผิดพลาด: {err}")

    st.write("### 🗂️ รายชื่อผู้ใช้งานทั้งหมดในระบบ")
    if all_users:
        # 🎯 ฟังก์ชันแสดงชื่อสาขาเพิ่มเติมในตาราง
        reverse_branch_dict = {str(v): k.split(" ")[1] for k, v in branch_dict.items()}
        def get_extra_branches_display(ids_str):
            if not ids_str: return ""
            return ", ".join([reverse_branch_dict.get(str(i).strip(), str(i).strip()) for i in str(ids_str).split(',') if i.strip()])

        df_display = []
        for u in all_users:
            df_display.append({
                'ID': u['user_id'], 'Username': u['username'],
                'ชื่อสาขา (หลัก)': u['branch_name'], 'ระดับสิทธิ์ (Role_tab)': u['Role_tab'],
                'แท็บที่เข้าถึงได้': u['allowed_tabs'],
                'สาขาที่มีสิทธิ์ (เพิ่มเติม)': get_extra_branches_display(u['additional_branches']), # 🎯 คอลัมน์ใหม่
                'สถานะบัญชี': u['status']
            })
            
        st.dataframe(pd.DataFrame(df_display), use_container_width=True)
        
        st.write("---")
        st.write("#### 🛠️ เครื่องมืออนุมัติและปรับเปลี่ยนสิทธิ์รายบัญชี")
        user_options = {row['username']: row['user_id'] for row in all_users}
        selected_target_user = st.selectbox("เลือกชื่อบัญชีผู้ใช้งานที่ต้องการปรับปรุง:", options=list(user_options.keys()))
        target_id = user_options[selected_target_user]
        
        current_user_row = [r for r in all_users if r['user_id'] == target_id][0]
        
        tab_assign_options = {
            "🔒 ล็อกสิทธิ์เข้าใช้งานทุกแท็บ (รออนุมัติ)": [], "🌐 เข้าถึงได้ทุกแท็บงาน (1, 2, 3, 4)": ["1", "2", "3", "4"],
            "⚙️ แท็บ 1 (เครื่องจักร/เบรกดาวน์)": ["1"], "🚚 แท็บ 2 (เชื้อเพลิงรถยนต์)": ["2"],
            "💨 แท็บ 3 (แรงดันไอน้ำ บอยเลอร์)": ["3"], "🔥 แท็บ 4 (เชื้อเพลิง บอยเลอร์)": ["4"],
            "🗂️ แท็บ 1 และ 2": ["1", "2"], "🗂️ แท็บ 1 และ 3": ["1", "3"], "🗂️ แท็บ 1 และ 4": ["1", "4"],
            "🗂️ แท็บ 2 และ 3": ["2", "3"], "🗂️ แท็บ 2 และ 4": ["2", "4"], "🗂️ แท็บ 3 และ 4": ["3", "4"],
            "🗂️ แท็บ 1, 2 และ 3": ["1", "2", "3"], "🗂️ แท็บ 1, 2 และ 4": ["1", "2", "4"],
            "🗂️ แท็บ 1, 3 และ 4": ["1", "3", "4"], "🗂️ แท็บ 2, 3 และ 4": ["2", "3", "4"]
        }

        current_user_tabs = [x.strip() for x in str(current_user_row.get('allowed_tabs', '') or '').split(',') if x.strip()]
        default_idx = 0
        set_tabs = set(current_user_tabs)
        tab_keys = list(tab_assign_options.keys())
        for i, key in enumerate(tab_keys):
            if set(tab_assign_options[key]) == set_tabs:
                default_idx = i; break

        role_list = ["user", "reporter", "manager", "admin"]
        curr_role_idx = role_list.index(current_user_row['Role_tab']) if current_user_row['Role_tab'] in role_list else 0
        status_list = ["active", "pending", "disabled"]
        curr_status_idx = status_list.index(current_user_row['status']) if current_user_row['status'] in status_list else 0

        # 🎯 ดึงรายชื่อสาขาปัจจุบัน (หลัก + เพิ่มเติม) มาแสดงใน Multi-select
        raw_allowed_branches = str(current_user_row.get('additional_branches', '')) or ''
        extra_b_ids = [int(x.strip()) for x in raw_allowed_branches.split(',') if x.strip().isdigit()]
        all_allowed_ids = set([current_user_row['branch_id']] + extra_b_ids)
        current_allowed_branch_names = [k for k, v in branch_dict.items() if v in all_allowed_ids]

        c_edit1, c_edit2, c_edit3 = st.columns(3)
        with c_edit1: edit_role = st.selectbox("ระดับสิทธิ์ (Role_tab):", options=role_list, index=curr_role_idx)
        with c_edit2: selected_tab_label = st.selectbox("เลือกจัดสรรแท็บงานประจำบัญชี:", options=tab_keys, index=default_idx)
        with c_edit3: edit_status = st.selectbox("สถานะบัญชี:", options=status_list, index=curr_status_idx)
        
        # 🎯 Multi-select เพื่อกำหนดสาขา
        edit_allowed_branches = st.multiselect(
            "📍 กำหนดสาขาที่มีสิทธิ์ (รวมสาขาหลักของ User คนนี้แล้ว):", 
            options=list(branch_dict.keys()), 
            default=current_allowed_branch_names,
            help="ผู้ใช้งานจะสามารถดูและจัดการข้อมูลของสาขาที่ถูกเลือกได้เหมือนกับเป็นสาขาของตนเอง"
        )

        selected_allowed_tabs = tab_assign_options[selected_tab_label]

        if st.button("💾 บันทึกและอนุมัติสิทธิ์การเข้าถึง", use_container_width=True):
            try:
                allowed_tabs_str = ",".join(selected_allowed_tabs)
                conn = get_db_connection()
                with conn.cursor() as cur:
                    # อัปเดตข้อมูลผู้ใช้หลัก
                    cur.execute("""UPDATE system_users SET Role_tab=%s, allowed_tabs=%s, status=%s WHERE user_id=%s""", 
                                (edit_role, allowed_tabs_str, edit_status, int(target_id)))
                    
                    # 🎯 อัปเดตตาราง user_branches (ลบของเก่าทิ้ง แล้ว Insert เข้าไปใหม่เฉพาะสาขาที่ไม่ใช่สาขาหลัก)
                    cur.execute("DELETE FROM user_branches WHERE user_id=%s", (int(target_id),))
                    for b_name in edit_allowed_branches:
                        b_id = branch_dict[b_name]
                        if b_id != current_user_row['branch_id']:
                            cur.execute("INSERT INTO user_branches (user_id, branch_id) VALUES (%s, %s)", (int(target_id), b_id))
                    
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
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM system_users WHERE user_id = %s", (int(target_id),))
                        # ไม่ต้องสั่ง DELETE จาก user_branches ถ้า DB ตั้งค่า CASCADE ไว้ (แต่ถ้าไม่ได้ตั้งไว้ ก็สั่งเผื่อได้เลย)
                        cur.execute("DELETE FROM user_branches WHERE user_id = %s", (int(target_id),))
                        conn.commit()
                    conn.close()
                    st.success(f"ทำการลบบัญชี {selected_target_user} ออกจากฐานข้อมูลเสร็จสิ้น")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"ไม่สามารถลบข้อมูลได้: {e}")
    else:
        st.info("ยังไม่มีข้อมูลบัญชีผู้ใช้ระบบคนอื่นนอกจากตัวคุณ")