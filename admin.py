import streamlit as st
import pandas as pd
import time
from database import get_db_connection, hash_password
from config import branch_dict

def render_admin_user_management():
    # 🎯 เพิ่ม CSS ชุดนี้เพื่อบังคับซ่อนแถบ Header ด้านบน (พื้นที่สีแดง)
    st.markdown("""
        <style>
        /* ซ่อนแถบ Header หลักของ Streamlit */
        header[data-testid="stHeader"] { display: none !important; }
        header { visibility: hidden !important; }
        #MainMenu { visibility: hidden !important; }
        
        /* ขยับคอนเทนต์ (พื้นที่สีน้ำเงิน) ขึ้นไปชิดขอบบนสุดแทน */
        .block-container { padding-top: 1rem !important; margin-top: -20px !important; }
        </style>
    """, unsafe_allow_html=True)
    st.header("👥 ระบบบริหารสิทธิ์และจัดการผู้ใช้งานระบบ")
    
    # 🎯 1. ดึงข้อมูลตำแหน่งจากตาราง departments เพื่อนำมาสร้างตัวเลือก Dropdown
    position_list = ["-- กรุณาเลือกตำแหน่ง --"]
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT CONVERT(position USING utf8mb4) AS pos FROM departments WHERE position IS NOT NULL AND position != '' ORDER BY pos ASC")
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
        reverse_branch_dict = {str(v): k for k, v in branch_dict.items()}
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
                'ระดับสิทธิ์ (Role_tab)': u['Role_tab'],
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
        
        current_user_tabs = [x.strip() for x in str(current_user_row.get('allowed_tabs', '') or '').split(',') if x.strip()]

        sa_key = "sa_edit"
        t1_key = "t1_edit"
        t2_key = "t2_edit"
        t3_key = "t3_edit"
        t4_key = "t4_edit"

        if st.session_state.get('loaded_edit_user') != target_id:
            st.session_state['loaded_edit_user'] = target_id
            st.session_state[sa_key] = (len(current_user_tabs) == 4)
            st.session_state[t1_key] = ("1" in current_user_tabs)
            st.session_state[t2_key] = ("2" in current_user_tabs)
            st.session_state[t3_key] = ("3" in current_user_tabs)
            st.session_state[t4_key] = ("4" in current_user_tabs)

        def on_select_all():
            val = st.session_state[sa_key]
            st.session_state[t1_key] = val
            st.session_state[t2_key] = val
            st.session_state[t3_key] = val
            st.session_state[t4_key] = val

        def on_tab_change():
            if st.session_state[t1_key] and st.session_state[t2_key] and st.session_state[t3_key] and st.session_state[t4_key]:
                st.session_state[sa_key] = True
            else:
                st.session_state[sa_key] = False

        role_list = ["user", "reporter", "manager", "admin"]
        curr_role_idx = role_list.index(current_user_row['Role_tab']) if current_user_row['Role_tab'] in role_list else 0
        status_list = ["active", "disabled"]
        curr_status_idx = status_list.index(current_user_row['status']) if current_user_row['status'] in status_list else 0

        raw_allowed_branches = str(current_user_row.get('additional_branches', '')) or ''
        extra_b_ids = [int(x.strip()) for x in raw_allowed_branches.split(',') if x.strip().isdigit()]
        all_allowed_ids = set([current_user_row['branch_id']] + extra_b_ids)
        current_allowed_branch_names = [k for k, v in branch_dict.items() if v in all_allowed_ids]

        with st.container(border=True): 
            st.markdown("**📋 แก้ไขข้อมูลส่วนตัว**")
            c_info1, c_info2 = st.columns(2)
            with c_info1: edit_fullname = st.text_input("ชื่อ-สกุล:", value=current_user_row.get('full_name') or '', key=f"fn_{target_id}")
            
            raw_pos = str(current_user_row.get('position') or '').strip()
            if not raw_pos or raw_pos == "-" or raw_pos.lower() == "none":
                curr_pos = "-- กรุณาเลือกตำแหน่ง --"
            else:
                curr_pos = raw_pos
                
            edit_pos_list = position_list.copy() 
            if curr_pos not in edit_pos_list:
                edit_pos_list.insert(1, curr_pos) 
            
            pos_idx = edit_pos_list.index(curr_pos)
            
            with c_info2: edit_pos = st.selectbox("ตำแหน่ง:", options=edit_pos_list, index=pos_idx, key=f"pos_{target_id}")
            
            c_info3, c_info4 = st.columns(2)
            with c_info3: edit_email = st.text_input("E-mail:", value=current_user_row.get('email') or '', key=f"em_{target_id}")
            with c_info4: edit_phone = st.text_input("เบอร์โทรศัพท์:", value=current_user_row.get('phone_number') or '', key=f"ph_{target_id}")
            
            st.markdown("---")
            st.markdown("**🔐 ปรับเปลี่ยนสิทธิ์การเข้าถึง**")
            
            c_edit1, c_edit2 = st.columns(2)
            with c_edit1: edit_role = st.selectbox("ระดับสิทธิ์ (Role_tab):", options=role_list, index=curr_role_idx, key=f"ro_{target_id}")
            with c_edit2: edit_status = st.selectbox("สถานะบัญชี:", options=status_list, index=curr_status_idx, key=f"st_{target_id}")
            
            st.markdown("<p style='font-size: 14.5px; font-weight: 600; margin-bottom: 0px;'>🏷️ เลือกจัดสรรแท็บงานประจำบัญชี:</p>", unsafe_allow_html=True)
            st.caption("☑️ ติ๊กเลือกแท็บที่ต้องการให้บัญชีนี้เข้าถึงได้ (หากไม่เลือกเลย ระบบจะทำการ 'ล็อกสิทธิ์' อัตโนมัติ)")
            
            st.markdown("<div style='background-color: #F8FAFC; padding: 5px 15px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 10px;'>", unsafe_allow_html=True)
            st.checkbox("☑️ **Select all (เลือกทั้งหมด)**", key=sa_key, on_change=on_select_all)
            st.markdown("</div>", unsafe_allow_html=True)
            
            cb_col1, cb_col2 = st.columns(2)
            with cb_col1:
                st.checkbox("⚙️ TAB 1: รายงานสรุปเครื่องจักร & เบรกดาวน์", key=t1_key, on_change=on_tab_change)
                st.checkbox("🚚 TAB 2: รายงานสรุปการใช้เชื้อเพลิงรถ", key=t2_key, on_change=on_tab_change)
            with cb_col2:
                st.checkbox("💨 TAB 3: รายงานสรุปแรงดันไอน้ำ บอยเลอร์", key=t3_key, on_change=on_tab_change)
                st.checkbox("🔥 TAB 4: รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)", key=t4_key, on_change=on_tab_change)
            
            st.write("")
            
            # 🎯 ตรวจสอบสิทธิ์แบบ Real-time ถ้าเป็น Admin ให้ซ่อนและโชว์ Full Access
            if edit_role == "admin":
                st.markdown("<p style='font-size: 14.5px; font-weight: 600; margin-bottom: 5px;'>📍 กำหนดสาขาที่มีสิทธิ์:</p>", unsafe_allow_html=True)
                st.success("🌟 **Full Access** (สิทธิ์ระดับ Admin สามารถเข้าถึงและจัดการข้อมูลได้ทุกสาขาอัตโนมัติ)")
                edit_allowed_branches = [] # เคลียร์ค่าออกไปเลย เพราะ Admin ดูได้หมดอยู่แล้ว
            else:
                edit_allowed_branches = st.multiselect(
                    "📍 กำหนดสาขาที่มีสิทธิ์ (รวมสาขาหลักของ User คนนี้แล้ว):", 
                    options=list(branch_dict.keys()), 
                    default=current_allowed_branch_names,
                    key=f"br_{target_id}",
                    help="ผู้ใช้งานจะสามารถดูและจัดการข้อมูลของสาขาที่ถูกเลือกได้เหมือนกับเป็นสาขาของตนเอง"
                )

            if st.button("💾 บันทึกและอนุมัติสิทธิ์การเข้าถึง", type="primary", use_container_width=True):
                allowed_tabs_list = []
                if st.session_state[t1_key]: allowed_tabs_list.append("1")
                if st.session_state[t2_key]: allowed_tabs_list.append("2")
                if st.session_state[t3_key]: allowed_tabs_list.append("3")
                if st.session_state[t4_key]: allowed_tabs_list.append("4")
                
                allowed_tabs_str = ",".join(allowed_tabs_list)
                
                final_edit_pos = edit_pos if edit_pos != "-- กรุณาเลือกตำแหน่ง --" else ""

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        cur.execute("""UPDATE system_users SET full_name=CONVERT(%s USING utf8mb4), position=CONVERT(%s USING utf8mb4), email=CONVERT(%s USING utf8mb4), phone_number=CONVERT(%s USING utf8mb4), Role_tab=%s, allowed_tabs=%s, status=%s WHERE user_id=%s""", 
                                    (edit_fullname, final_edit_pos, edit_email, edit_phone, edit_role, allowed_tabs_str, edit_status, int(target_id)))
                        
                        cur.execute("DELETE FROM user_branches WHERE user_id=%s", (int(target_id),))
                        for b_name in edit_allowed_branches:
                            b_id = branch_dict[b_name]
                            if b_id != current_user_row['branch_id']:
                                cur.execute("INSERT INTO user_branches (user_id, branch_id) VALUES (%s, %s)", (int(target_id), b_id))
                        
                        conn.commit()
                    conn.close()
                    st.session_state['loaded_edit_user'] = None 
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