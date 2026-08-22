import streamlit as st
import pandas as pd
import time
from database import get_db_connection, hash_password
from config import branch_dict

def render_admin_user_management():
    st.header("👥 ระบบบริหารสิทธิ์และจัดการผู้ใช้งานระบบ")
    
    # 🎯 1. ดึงข้อมูลตำแหน่งจากตาราง departments เพื่อนำมาสร้างตัวเลือก Dropdown
    position_list = ["-- กรุณาเลือกตำแหน่ง --"]
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT CONVERT(position USING utf8mb4) AS pos FROM departments WHERE position IS NOT NULL AND position != '' ORDER BY position ASC")
            for r in cur.fetchall():
                if r['pos']: position_list.append(r['pos'].strip())
        conn.close()
    except Exception as e:
        st.warning(f"ไม่สามารถดึงข้อมูลตำแหน่งได้: {e}")

    try:
        conn = get_db_connection()
        with conn.cursor() as user_cursor:
            user_cursor.execute("""
                SELECT u.user_id, u.username, u.full_name, u.position, u.email, u.phone_number, u.branch_id, b.branch_name, u.Role_tab, u.allowed_tabs, u.status,
                       GROUP_CONCAT(ub.branch_id) as additional_branches
                FROM system_users u
                LEFT JOIN branches b ON u.branch_id = b.id
                LEFT JOIN user_branches ub ON u.user_id = ub.user_id
                GROUP BY u.user_id, u.username, u.full_name, u.position, u.email, u.phone_number, u.branch_id, b.branch_name, u.Role_tab, u.allowed_tabs, u.status
                ORDER BY u.user_id ASC
            """)
            all_users = user_cursor.fetchall()
        conn.close()
    except Exception as e:
        st.error(f"ไม่สามารถดึงตารางรายชื่อผู้ใช้งานได้: {e}")
        all_users = []

    with st.expander("➕ เพิ่มบัญชีผู้ใช้งานใหม่เข้าระบบโดยแอดมิน"):
        with st.form("admin_add_user_form", clear_on_submit=True):
            st.markdown("#### 👤 ข้อมูลบัญชีผู้ใช้งาน")
            col_u1, col_u2 = st.columns(2)
            with col_u1: new_user = st.text_input("Username (User ID) *")
            with col_u2: new_pass = st.text_input("Password *", type="password")
            
            st.markdown("#### 📋 ข้อมูลส่วนตัว")
            col_p1, col_p2 = st.columns(2)
            with col_p1: new_fullname = st.text_input("ชื่อ-นามสกุล *")
            
            # 🎯 2. เปลี่ยนช่อง Text เป็น Selectbox ดึงจากฐานข้อมูล
            with col_p2: new_pos = st.selectbox("ตำแหน่ง *", options=position_list)
            
            col_c1, col_c2 = st.columns(2)
            with col_c1: new_email = st.text_input("E-mail")
            with col_c2: new_phone = st.text_input("เบอร์โทรศัพท์")
            
            st.markdown("#### 🏢 ข้อมูลสิทธิ์และสังกัด")
            new_branch_label = st.selectbox("เลือกสาขาประจำตัว (หลัก) *", options=list(branch_dict.keys()), key="adm_add_br")
            new_role = st.selectbox("กำหนดระดับสิทธิ์ (Role_tab) *", options=["user", "reporter", "manager", "admin"])
            
            st.write("")
            if st.form_submit_button("➕ เพิ่มข้อมูลผู้ใช้ระบบ"):
                if not new_user or not new_pass or not new_fullname or new_pos == "-- กรุณาเลือกตำแหน่ง --": 
                    st.error("⚠️ กรุณากรอกข้อมูลที่มีเครื่องหมาย * ให้ครบถ้วน และเลือกตำแหน่งให้ถูกต้อง")
                else:
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT user_id FROM system_users WHERE CONVERT(username USING utf8mb4) = CONVERT(%s USING utf8mb4)", (new_user,))
                            if cursor.fetchone(): st.error("❌ ชื่อ Username นี้มีอยู่ในระบบแล้ว")
                            else:
                                sql = """INSERT INTO system_users (username, password_hash, full_name, position, email, phone_number, branch_id, Role_tab, allowed_tabs, status) 
                                         VALUES (CONVERT(%s USING utf8mb4), %s, CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), %s, %s, '', 'active')"""
                                cursor.execute(sql, (new_user, hash_password(new_pass), new_fullname, new_pos, new_email, new_phone, branch_dict[new_branch_label], new_role))
                                conn.commit()
                                st.success(f"เพิ่มผู้ใช้งาน {new_user} สำเร็จ!")
                                time.sleep(1)
                                st.rerun()
                        conn.close()
                    except Exception as err: st.error(f"เกิดข้อผิดพลาด: {err}")

    st.write("### 🗂️ รายชื่อผู้ใช้งานทั้งหมดในระบบ")
    if all_users:
        reverse_branch_dict = {str(v): k.split(" ")[1] for k, v in branch_dict.items()}
        def get_extra_branches_display(ids_str):
            if not ids_str: return ""
            return ", ".join([reverse_branch_dict.get(str(i).strip(), str(i).strip()) for i in str(ids_str).split(',') if i.strip()])

        df_display = []
        for u in all_users:
            df_display.append({
                'ID': u['user_id'], 
                'Username': u['username'],
                'ชื่อ-นามสกุล': u.get('full_name') or '-',
                'ตำแหน่ง': u.get('position') or '-',
                'E-mail': u.get('email') or '-',
                'เบอร์โทร': u.get('phone_number') or '-',
                'ชื่อสาขา (หลัก)': u['branch_name'], 
                'ระดับสิทธิ์': u['Role_tab'],
                'แท็บที่เข้าถึงได้': u['allowed_tabs'],
                'สาขาที่มีสิทธิ์ (เพิ่มเติม)': get_extra_branches_display(u['additional_branches']),
                'สถานะบัญชี': u['status']
            })
            
        st.dataframe(pd.DataFrame(df_display), use_container_width=True)
        
        st.write("---")
        st.write("#### 🛠️ เครื่องมืออนุมัติและปรับเปลี่ยนข้อมูลรายบัญชี")
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
        status_list = ["active", "disabled"]
        curr_status_idx = status_list.index(current_user_row['status']) if current_user_row['status'] in status_list else 0

        raw_allowed_branches = str(current_user_row.get('additional_branches', '')) or ''
        extra_b_ids = [int(x.strip()) for x in raw_allowed_branches.split(',') if x.strip().isdigit()]
        all_allowed_ids = set([current_user_row['branch_id']] + extra_b_ids)
        current_allowed_branch_names = [k for k, v in branch_dict.items() if v in all_allowed_ids]

        with st.form(f"admin_edit_form_{target_id}"):
            st.markdown("**📋 แก้ไขข้อมูลส่วนตัว**")
            c_info1, c_info2 = st.columns(2)
            with c_info1: edit_fullname = st.text_input("ชื่อ-สกุล:", value=current_user_row.get('full_name') or '')
            
            # 🎯 3. โหลดตำแหน่งเดิมขึ้นมาเป็นค่าเริ่มต้นตอนแก้ข้อมูล
            curr_pos = current_user_row.get('position') or ''
            edit_pos_list = [p for p in position_list if p != "-- กรุณาเลือกตำแหน่ง --"]
            if curr_pos and curr_pos not in edit_pos_list:
                edit_pos_list.insert(0, curr_pos) # เผื่อกรณีตำแหน่งเดิมโดนลบออกจากตารางไปแล้ว จะได้ไม่ Error
            pos_idx = edit_pos_list.index(curr_pos) if curr_pos in edit_pos_list else 0
            
            with c_info2: edit_pos = st.selectbox("ตำแหน่ง:", options=edit_pos_list, index=pos_idx)
            
            c_info3, c_info4 = st.columns(2)
            with c_info3: edit_email = st.text_input("E-mail:", value=current_user_row.get('email') or '')
            with c_info4: edit_phone = st.text_input("เบอร์โทรศัพท์:", value=current_user_row.get('phone_number') or '')
            
            st.markdown("---")
            st.markdown("**🔐 ปรับเปลี่ยนสิทธิ์การเข้าถึง**")
            c_edit1, c_edit2, c_edit3 = st.columns(3)
            with c_edit1: edit_role = st.selectbox("ระดับสิทธิ์ (Role_tab):", options=role_list, index=curr_role_idx)
            with c_edit2: selected_tab_label = st.selectbox("เลือกจัดสรรแท็บงานประจำบัญชี:", options=tab_keys, index=default_idx)
            with c_edit3: edit_status = st.selectbox("สถานะบัญชี:", options=status_list, index=curr_status_idx)
            
            edit_allowed_branches = st.multiselect(
                "📍 กำหนดสาขาที่มีสิทธิ์ (รวมสาขาหลักของ User คนนี้แล้ว):", 
                options=list(branch_dict.keys()), 
                default=current_allowed_branch_names,
                help="ผู้ใช้งานจะสามารถดูและจัดการข้อมูลของสาขาที่ถูกเลือกได้เหมือนกับเป็นสาขาของตนเอง"
            )

            selected_allowed_tabs = tab_assign_options[selected_tab_label]

            if st.form_submit_button("💾 บันทึกและอนุมัติสิทธิ์การเข้าถึง", use_container_width=True):
                try:
                    allowed_tabs_str = ",".join(selected_allowed_tabs)
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        cur.execute("""UPDATE system_users SET full_name=CONVERT(%s USING utf8mb4), position=CONVERT(%s USING utf8mb4), email=CONVERT(%s USING utf8mb4), phone_number=CONVERT(%s USING utf8mb4), Role_tab=%s, allowed_tabs=%s, status=%s WHERE user_id=%s""", 
                                    (edit_fullname, edit_pos, edit_email, edit_phone, edit_role, allowed_tabs_str, edit_status, int(target_id)))
                        
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
                        cur.execute("DELETE FROM user_branches WHERE user_id = %s", (int(target_id),))
                        conn.commit()
                    conn.close()
                    st.success(f"ทำการลบบัญชี {selected_target_user} ออกจากฐานข้อมูลเสร็จสิ้น")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"ไม่สามารถลบข้อมูลได้: {e}")
    else:
        st.info("ยังไม่มีข้อมูลบัญชีผู้ใช้ระบบคนอื่นนอกจากตัวคุณ")