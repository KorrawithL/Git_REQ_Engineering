import streamlit as st
import pandas as pd
import time
from database import get_db_connection, hash_password, log_activity

# =============================================================================
# 🏢 ฟังก์ชันดึงข้อมูลสาขาจาก Database แบบ Real-time
# =============================================================================
def get_db_branches():
    b_dict = {}
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, CONVERT(branch_name USING utf8mb4) AS b_name 
                FROM branches 
                WHERE is_active = 1 
                ORDER BY id ASC
            """)
            for r in cur.fetchall():
                if r['b_name']:
                    b_dict[r['b_name'].strip()] = r['id']
    except Exception as e:
        print(f"Error fetching branches: {e}")
    finally:
        if conn:
            conn.close()
    return b_dict

# =============================================================================
# 🚨 ฟังก์ชัน Popup ยืนยันการลบบัญชีผู้ใช้งาน (เพิ่ม Safety Check ประวัติงาน)
# =============================================================================
@st.dialog("⚠️ ยืนยันการจัดการบัญชีผู้ใช้งาน")
def confirm_delete_user_dialog(user_id, username):
    st.error(f"คุณกำลังเลือกจัดการบัญชีผู้ใช้งาน: **'{username}'** (User ID: {user_id})")
    
    # 🌟 ตรวจสอบว่าผู้ใช้คนนี้เคยมีประวัติการบันทึกงานในระบบหรือไม่
    total_records = 0
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM machine_trans WHERE created_by = %s) +
                    (SELECT COUNT(*) FROM fuel_records WHERE created_by = %s) +
                    (SELECT COUNT(*) FROM boiler_pressure_records WHERE created_by = %s) +
                    (SELECT COUNT(*) FROM boiler_fuel_records WHERE created_by = %s) +
                    (SELECT COUNT(*) FROM daily_wood_oven_records WHERE created_by = %s) AS total_count
            """, (user_id, user_id, user_id, user_id, user_id))
            res = cur.fetchone()
            if res and res['total_count']:
                total_records = int(res['total_count'])
    except Exception:
        pass
    finally:
        if conn: conn.close()

    if total_records > 0:
        st.warning(f"⚠️ **ตรวจพบประวัติงาน:** บัญชีนี้เคยลงบันทึกข้อมูลในระบบไปแล้วทั้งหมด **{total_records}** รายการ")
        st.markdown("<span style='color:#475569; font-size:14px;'>* ข้อแนะนำ: หากลบบัญชีถาวร ประวัติงานเดิมจะขาดข้อมูลผู้บันทึก แนะนำให้เลือก **'ระงับการใช้งาน (Disabled)'** เพื่อไม่ให้เข้าสู่ระบบได้แต่ยังรักษาประวัติเดิมไว้</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span style='color:#EF4444; font-size:14px;'>* คำเตือน: ข้อมูลบัญชีผู้ใช้และสิทธิ์การเข้าถึงทั้งหมดจะถูกลบถาวร ไม่สามารถกู้คืนได้</span>", unsafe_allow_html=True)
    
    st.write("")
    
    col_act1, col_act2, col_act3 = st.columns([1.2, 1.8, 1.4])
    with col_act1:
        if st.button("❌ ยกเลิก", use_container_width=True, key=f"cancel_del_u_{user_id}"):
            st.rerun()
            
    with col_act2:
        # ปุ่มทางเลือกที่ปลอดภัย: ระงับการใช้งานแทน
        if st.button("🚫 ระงับใช้งาน (Disabled)", use_container_width=True, key=f"disable_u_{user_id}"):
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("UPDATE system_users SET status = 'disabled' WHERE user_id = %s", (int(user_id),))
                    conn.commit()
                    log_activity(
                        st.session_state.user_id,
                        st.session_state.username,
                        "UPDATE",
                        "Admin: User Management",
                        f"ระงับการใช้งานบัญชี '{username}' (User ID: {user_id})"
                    )
                st.success(f"ทำการระงับบัญชี '{username}' เรียบร้อยแล้ว (ไม่สามารถล็อกอินได้)")
                time.sleep(1.2)
                st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
            finally:
                if conn: conn.close()

    with col_act3:
        if st.button("🗑️ ยืนยันลบถาวร", type="primary", use_container_width=True, key=f"confirm_del_u_{user_id}"):
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM system_users WHERE user_id = %s", (int(user_id),))
                    cur.execute("DELETE FROM user_branches WHERE user_id = %s", (int(user_id),))
                    conn.commit()
                    log_activity(
                        st.session_state.user_id,
                        st.session_state.username,
                        "DELETE",
                        "Admin: User Management",
                        f"ลบบัญชีผู้ใช้งาน '{username}' (User ID: {user_id}) ออกจากระบบถาวร"
                    )
                st.success(f"ทำการลบบัญชี '{username}' ออกจากฐานข้อมูลเรียบร้อยแล้ว")
                time.sleep(1.2)
                st.rerun()
            except Exception as e:
                st.error(f"ไม่สามารถลบข้อมูลได้: {e}")
            finally:
                if conn: conn.close()

def render_admin_user_management():
    st.markdown("""
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        #header { visibility: hidden !important; }
        #MainMenu { visibility: hidden !important; }
        .block-container { padding-top: 1rem !important; margin-top: -20px !important; }
        </style>
    """, unsafe_allow_html=True)
    st.header("👥 ระบบบริหารสิทธิ์และจัดการผู้ใช้งานระบบ")

    current_branch_dict = get_db_branches()

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

    # =========================================================================
    # ➕ เพิ่มบัญชีผู้ใช้งานใหม่เข้าระบบ
    # =========================================================================
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
            new_branch_label = st.selectbox("เลือกสาขาประจำตัว (หลัก) *", options=list(current_branch_dict.keys()), key="adm_add_br")
            new_role = st.selectbox("กำหนดระดับสิทธิ์ (Role_tab) *", options=["user", "reporter", "manager", "admin"])
            
            st.write("")
            if st.form_submit_button("➕ เพิ่มข้อมูลผู้ใช้ระบบ"):
                if not new_user or not new_pass or not new_fullname or new_pos == "-- กรุณาเลือกตำแหน่ง --": 
                    st.error("⚠️ กรุณากรอกข้อมูลที่มีเครื่องหมาย * ให้ครบถ้วน และเลือกตำแหน่งให้ถูกต้อง")
                else:
                    # 🌟 ข้อ 5: กำหนดค่า Default allowed_tabs ตาม Role โดยอัตโนมัติ
                    if new_role == "admin":
                        default_tabs = "1,2,3,4,6"
                    elif new_role == "manager":
                        default_tabs = "1,2,3,4,5,6"
                    else:
                        default_tabs = "1,2,3,4"

                    conn = None
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT user_id FROM system_users WHERE CONVERT(username USING utf8mb4) = CONVERT(%s USING utf8mb4)", (new_user,))
                            if cursor.fetchone(): 
                                st.error("❌ ชื่อ Username นี้มีอยู่ในระบบแล้ว")
                            else:
                                sql = """INSERT INTO system_users (username, password_hash, full_name, position, email, phone_number, branch_id, Role_tab, allowed_tabs, status) 
                                         VALUES (CONVERT(%s USING utf8mb4), %s, CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), %s, %s, %s, 'active')"""
                                cursor.execute(sql, (new_user, hash_password(new_pass), new_fullname, new_pos, new_email, new_phone, current_branch_dict[new_branch_label], new_role, default_tabs))
                                conn.commit()
                                log_activity(
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    "INSERT",
                                    "Admin: User Management",
                                    f"สร้างบัญชีใหม่: {new_user} (สิทธิ์: {new_role}, สาขาหลัก: {new_branch_label}, แท็บ: {default_tabs})"
                                )
                                st.success(f"เพิ่มผู้ใช้งาน {new_user} สำเร็จ! (กำหนดสิทธิ์เริ่มต้นเรียบร้อย)")
                                time.sleep(1)
                                st.rerun()
                    except Exception as err: 
                        st.error(f"เกิดข้อผิดพลาด: {err}")
                    finally:
                        if conn: conn.close()

    # =========================================================================
    # 🗂️ รายชื่อผู้ใช้งานและแผงค้นหา (Search & Filter)
    # =========================================================================
    st.write("### 🗂️ รายชื่อผู้ใช้งานทั้งหมดในระบบ")
    if all_users:
        reverse_branch_dict = {str(v): k for k, v in current_branch_dict.items()}
        def get_extra_branches_display(ids_str):
            if not ids_str: return ""
            return ", ".join([reverse_branch_dict.get(str(i).strip(), str(i).strip()) for i in str(ids_str).split(',') if i.strip()])

        raw_user_list = []
        for u in all_users:
            raw_user_list.append({
                'ID': u['user_id'], 
                'Username': u['username'],
                'ชื่อ-นามสกุล': u.get('full_name') or '-',
                'ตำแหน่ง': u.get('position') or '-',
                'E-mail': u.get('email') or '-',
                'เบอร์โทร': u.get('phone_number') or '-',
                'สาขาประจำตัว': u.get('branch_name') or '-',
                'ระดับสิทธิ์': u['Role_tab'],
                'หน้ารายการที่เข้าถึงได้': u.get('allowed_tabs') or '-',
                'สาขาเสริมที่มีสิทธิ์': get_extra_branches_display(u['additional_branches']),
                'สถานะบัญชี': u['status']
            })
        
        df_all_users = pd.DataFrame(raw_user_list)

        with st.expander("🔍 แผงค้นหาและตัวกรองรายชื่อผู้ใช้ (Filter Panel)", expanded=True):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1:
                search_kw = st.text_input("🔍 ค้นหา (ชื่อ/User/เบอร์):", placeholder="พิมพ์เพื่อค้นหา...")
            with f_col2:
                filter_branch = st.selectbox("🏢 สาขาประจำตัว:", options=["ทั้งหมด"] + list(current_branch_dict.keys()))
            with f_col3:
                filter_role = st.selectbox("👑 ระดับสิทธิ์:", options=["ทั้งหมด", "admin", "manager", "reporter", "user"])
            with f_col4:
                filter_status = st.selectbox("📍 สถานะบัญชี:", options=["ทั้งหมด", "active", "disabled"])

        filtered_df = df_all_users.copy()
        if search_kw:
            kw = search_kw.strip().lower()
            filtered_df = filtered_df[
                filtered_df['Username'].astype(str).str.lower().str.contains(kw) |
                filtered_df['ชื่อ-นามสกุล'].astype(str).str.lower().str.contains(kw) |
                filtered_df['เบอร์โทร'].astype(str).str.contains(kw)
            ]
        if filter_branch != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df['สาขาประจำตัว'] == filter_branch]
        if filter_role != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df['ระดับสิทธิ์'] == filter_role]
        if filter_status != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df['สถานะบัญชี'] == filter_status]

        st.caption(f"แสดงผล **{len(filtered_df)}** รายการ (จากทั้งหมด {len(df_all_users)} บัญชี)")
        display_user_cols = ['ID', 'Username', 'ชื่อ-นามสกุล', 'ตำแหน่ง', 'E-mail', 'เบอร์โทร', 'สาขาประจำตัว', 'ระดับสิทธิ์', 'หน้ารายการที่เข้าถึงได้', 'สาขาเสริมที่มีสิทธิ์', 'สถานะบัญชี']
        st.dataframe(filtered_df[display_user_cols], use_container_width=True, height=280)
        
        st.write("---")
        st.write("#### 🛠️ เครื่องมืออนุมัติและปรับเปลี่ยนข้อมูลรายบัญชี")

        if not filtered_df.empty:
            user_options = {
                f"[{r['สถานะบัญชี']}] {r['Username']} — {r['ชื่อ-นามสกุล']} ({r['สาขาประจำตัว']})": r['ID']
                for _, r in filtered_df.iterrows()
            }
            selected_label = st.selectbox("เลือกบัญชีผู้ใช้งานที่ต้องการปรับปรุง:", options=list(user_options.keys()))
            target_id = user_options[selected_label]
            selected_target_user = [r['Username'] for _, r in filtered_df.iterrows() if r['ID'] == target_id][0]
        else:
            st.warning("⚠️ ไม่พบบัญชีผู้ใช้งานที่ตรงกับเงื่อนไขการค้นหา")
            return
        
        # ค้นหาข้อมูลเต็มของแถวที่เลือก
        current_user_row = [r for r in all_users if r['user_id'] == target_id][0]
        current_user_tabs = [x.strip() for x in str(current_user_row.get('allowed_tabs', '') or '').split(',') if x.strip()]

        sa_key = "sa_edit"
        t1_key = "t1_edit"
        t2_key = "t2_edit"
        t3_key = "t3_edit"
        t4_key = "t4_edit"
        t5_key = "t5_edit"
        t6_key = "t6_edit"

        # 🌟 ป้องกัน KeyError: ตั้งค่าเริ่มต้นให้ทุกคีย์
        for k in [sa_key, t1_key, t2_key, t3_key, t4_key, t5_key, t6_key]:
            if k not in st.session_state:
                st.session_state[k] = False

        if st.session_state.get('loaded_edit_user') != target_id:
            st.session_state['loaded_edit_user'] = target_id
            st.session_state[sa_key] = (len(current_user_tabs) >= 4)
            st.session_state[t1_key] = ("1" in current_user_tabs)
            st.session_state[t2_key] = ("2" in current_user_tabs)
            st.session_state[t3_key] = ("3" in current_user_tabs)
            st.session_state[t4_key] = ("4" in current_user_tabs)
            st.session_state[t5_key] = ("5" in current_user_tabs)
            st.session_state[t6_key] = ("6" in current_user_tabs)

        def on_select_all():
            val = st.session_state.get(sa_key, False)
            st.session_state[t1_key] = val
            st.session_state[t2_key] = val
            st.session_state[t3_key] = val
            st.session_state[t4_key] = val
            st.session_state[t5_key] = val
            st.session_state[t6_key] = val

        def on_tab_change():
            # 🌟 ดึงค่าแบบปลอดภัยด้วย .get()
            t1 = st.session_state.get(t1_key, False)
            t2 = st.session_state.get(t2_key, False)
            t3 = st.session_state.get(t3_key, False)
            t4 = st.session_state.get(t4_key, False)
            st.session_state[sa_key] = (t1 and t2 and t3 and t4)

        role_list = ["user", "reporter", "manager", "admin"]
        curr_role_idx = role_list.index(current_user_row['Role_tab']) if current_user_row['Role_tab'] in role_list else 0
        status_list = ["active", "disabled"]
        curr_status_idx = status_list.index(current_user_row['status']) if current_user_row['status'] in status_list else 0

        raw_allowed_branches = str(current_user_row.get('additional_branches', '')) or ''
        extra_b_ids = [int(x.strip()) for x in raw_allowed_branches.split(',') if x.strip().isdigit()]
        all_allowed_ids = set([current_user_row['branch_id']] + extra_b_ids)
        current_allowed_branch_names = [k for k, v in current_branch_dict.items() if v in all_allowed_ids]

        with st.container(border=True): 
            # 🔑 รีเซ็ตรหัสผ่านใหม่โดย Admin
            with st.expander("🔑 รีเซ็ตรหัสผ่านใหม่ให้บัญชีนี้ (Admin Reset Password)", expanded=False):
                st.caption(f"กำหนดรหัสผ่านใหม่ให้กับคุณ **{selected_target_user}** (กรณีพนักงานลืมรหัสผ่าน)")
                r_c1, r_c2 = st.columns([2.5, 1.5])
                with r_c1:
                    new_reset_pass = st.text_input("ระบุรหัสผ่านใหม่:", type="password", key=f"rst_pwd_{target_id}", placeholder="กรอกรหัสผ่านใหม่ที่ต้องการ...")
                with r_c2:
                    st.write("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    btn_reset = st.button("🔑 ยืนยันเปลี่ยนรหัส", key=f"btn_rst_{target_id}", type="primary", use_container_width=True)
                
                if btn_reset:
                    if not new_reset_pass:
                        st.error("⚠️ กรุณาระบุรหัสผ่านใหม่ก่อนกดบันทึก")
                    elif len(new_reset_pass) < 4:
                        st.warning("⚠️ รหัสผ่านควรมีความยาวอย่างน้อย 4 ตัวอักษร")
                    else:
                        conn_rst = None
                        try:
                            conn_rst = get_db_connection()
                            with conn_rst.cursor() as cur:
                                cur.execute("UPDATE system_users SET password_hash = %s WHERE user_id = %s", 
                                            (hash_password(new_reset_pass), int(target_id)))
                                conn_rst.commit()
                                
                                log_activity(
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    "UPDATE",
                                    "Admin: Password Reset",
                                    f"แอดมินรีเซ็ตรหัสผ่านใหม่ให้กับ '{selected_target_user}' (User ID: {target_id})"
                                )
                            st.success(f"✅ ทำการรีเซ็ตรหัสผ่านของ '{selected_target_user}' สำเร็จเรียบร้อย!")
                            time.sleep(1.2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาดในการเปลี่ยนรหัสผ่าน: {e}")
                        finally:
                            if conn_rst: conn_rst.close()

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
            st.markdown("**🔐 ปรับเปลี่ยนสิทธิ์การเข้าถึงและสังกัด**")
            
            branch_names_list = list(current_branch_dict.keys())
            curr_b_name = next((k for k, v in current_branch_dict.items() if v == current_user_row['branch_id']), branch_names_list[0] if branch_names_list else "")
            curr_b_idx = branch_names_list.index(curr_b_name) if curr_b_name in branch_names_list else 0

            c_edit0, c_edit1, c_edit2 = st.columns(3)
            with c_edit0: 
                edit_primary_branch = st.selectbox("🏢 สาขาประจำตัว (หลัก) *", options=branch_names_list, index=curr_b_idx, key=f"pbr_{target_id}")
            with c_edit1: 
                edit_role = st.selectbox("ระดับสิทธิ์ (Role_tab):", options=role_list, index=curr_role_idx, key=f"ro_{target_id}")
            with c_edit2: 
                edit_status = st.selectbox("สถานะบัญชี:", options=status_list, index=curr_status_idx, key=f"st_{target_id}")
            
            st.markdown("<p style='font-size: 14.5px; font-weight: 600; margin-bottom: 0px;'>🏷️ เลือกจัดสรรแท็บงานประจำบัญชี:</p>", unsafe_allow_html=True)
            st.caption("☑️ ติ๊กเลือกแท็บที่ต้องการให้บัญชีนี้เข้าถึงได้ (หากไม่เลือกเลย ระบบจะทำการ 'ล็อกสิทธิ์' อัตโนมัติ)")
            
            st.markdown("<div style='background-color: #F8FAFC; padding: 5px 15px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 10px;'>", unsafe_allow_html=True)
            st.checkbox("☑️ **Select all (เลือกทั้งหมด)**", key=sa_key, on_change=on_select_all)
            st.markdown("</div>", unsafe_allow_html=True)
            
            cb_col1, cb_col2 = st.columns(2)
            with cb_col1:
                st.checkbox("⚙️ TAB 1: รายงานสรุปเครื่องจักร & เบรกดาวน์", key=t1_key, on_change=on_tab_change)
                st.checkbox("🚚 TAB 2: รายงานสรุปการใช้เชื้อเพลิงรถ", key=t2_key, on_change=on_tab_change)
                if edit_role == "manager":
                    st.checkbox("🛠️ หน้า 5: จัดการข้อมูลอุปกรณ์", key=t5_key)
            with cb_col2:
                st.checkbox("💨 TAB 3: รายงานสรุปแรงดันไอน้ำ บอยเลอร์", key=t3_key, on_change=on_tab_change)
                st.checkbox("🔥 TAB 4: รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)", key=t4_key, on_change=on_tab_change)
                if edit_role in ["manager", "admin"]:
                    st.checkbox("⚙️ หน้า 6: กำหนดเกณฑ์มาตรฐาน (STD Settings)", key=t6_key)
            st.write("")
            
            if edit_role == "admin":
                st.markdown("<p style='font-size: 14.5px; font-weight: 600; margin-bottom: 5px;'>📍 กำหนดสาขาที่มีสิทธิ์:</p>", unsafe_allow_html=True)
                st.success("🌟 **Full Access** (สิทธิ์ระดับ Admin สามารถเข้าถึงและจัดการข้อมูลได้ทุกสาขาอัตโนมัติ)")
                edit_allowed_branches = []
            else:
                edit_allowed_branches = st.multiselect(
                    "📍 กำหนดสาขาที่มีสิทธิ์ (รวมสาขาหลักของ User คนนี้แล้ว):", 
                    options=list(current_branch_dict.keys()), 
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
                if edit_role == "manager" and st.session_state.get(t5_key): allowed_tabs_list.append("5")
                if edit_role in ["manager", "admin"] and st.session_state.get(t6_key): allowed_tabs_list.append("6")

                allowed_tabs_str = ",".join(allowed_tabs_list)
                final_edit_pos = edit_pos if edit_pos != "-- กรุณาเลือกตำแหน่ง --" else ""

                conn = None
                try:
                    conn = get_db_connection()
                    new_primary_b_id = current_branch_dict[edit_primary_branch]
                    
                    with conn.cursor() as cur:
                        cur.execute("""UPDATE system_users 
                                       SET branch_id=%s, full_name=CONVERT(%s USING utf8mb4), position=CONVERT(%s USING utf8mb4), 
                                           email=CONVERT(%s USING utf8mb4), phone_number=CONVERT(%s USING utf8mb4), 
                                           Role_tab=%s, allowed_tabs=%s, status=%s 
                                       WHERE user_id=%s""", 
                                    (new_primary_b_id, edit_fullname, final_edit_pos, edit_email, edit_phone, edit_role, allowed_tabs_str, edit_status, int(target_id)))
                        
                        cur.execute("DELETE FROM user_branches WHERE user_id=%s", (int(target_id),))
                        for b_name in edit_allowed_branches:
                            b_id = current_branch_dict.get(b_name)
                            if b_id and b_id != new_primary_b_id:
                                cur.execute("INSERT INTO user_branches (user_id, branch_id) VALUES (%s, %s)", (int(target_id), b_id))
                        
                        conn.commit()
                        log_activity(
                            st.session_state.user_id,
                            st.session_state.username,
                            "UPDATE",
                            "Admin: User Management",
                            f"แก้ไขข้อมูล/สิทธิ์ของ '{selected_target_user}' (สาขาหลัก: {edit_primary_branch}, Role: {edit_role}, สถานะ: {edit_status}, แท็บ: {allowed_tabs_str})"
                        )
                    st.session_state['loaded_edit_user'] = None 
                    st.success(f"อัปเดตสิทธิ์การใช้งานของ '{selected_target_user}' สำเร็จเรียบร้อย!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: 
                    st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
                finally:
                    if conn: conn.close()
                
        st.write("<br>", unsafe_allow_html=True)
        with st.expander("🚨 โซนอันตราย: จัดการ / ลบบัญชีผู้ใช้นี้ออกจากระบบ"):
            st.warning(f"การจัดการบัญชี **{selected_target_user}** กรุณาตรวจสอบให้แน่ใจก่อนดำเนินการ")
            
            is_self = (int(target_id) == int(st.session_state.user_id))
            if is_self:
                st.info("ℹ️ คุณไม่สามารถลบหรือระงับบัญชีของตัวเองในขณะที่กำลังเข้าสู่ระบบอยู่ได้")

            if st.button(f"🗑️ ขอลบบัญชี {selected_target_user}", key="btn_del_usr", type="primary", use_container_width=True, disabled=is_self):
                confirm_delete_user_dialog(target_id, selected_target_user)               
    else:
        st.info("ยังไม่มีข้อมูลบัญชีผู้ใช้ระบบคนอื่นนอกจากตัวคุณ")