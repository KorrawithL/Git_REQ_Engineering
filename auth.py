import streamlit as st
import time
from database import get_db_connection, hash_password
from config import branch_dict

def render_login_page():
    st.title("🔐 Woodwork System - เข้าสู่ระบบ")
    st.write("---")
    
    with st.form("login_form"):
        log_user = st.text_input("User ID (Username)")
        log_pass = st.text_input("Password", type="password")
        btn_log = st.form_submit_button("🔓 ล็อกอินเข้าสู่ระบบ")
        
        if btn_log:
            try:
                conn = get_db_connection()
                with conn.cursor() as cursor:
                    sql = """SELECT u.*, b.branch_name 
                             FROM system_users u 
                             LEFT JOIN branches b ON u.branch_id = b.id
                             WHERE CONVERT(u.username USING utf8mb4) = CONVERT(%s USING utf8mb4) 
                             AND u.password_hash = %s AND u.status = 'active'"""
                    cursor.execute(sql, (log_user, hash_password(log_pass)))
                    user_data = cursor.fetchone()
                    
                    if user_data:
                        cursor.execute("SELECT branch_id FROM user_branches WHERE user_id = %s", (user_data['user_id'],))
                        extra_branches = cursor.fetchall()
                        
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_data['user_id']
                        st.session_state.username = user_data['username']
                        st.session_state.full_name = user_data.get('full_name') or user_data['username']
                        st.session_state.position = user_data.get('position') or '-'
                        st.session_state.branch_id = user_data['branch_id']
                        st.session_state.branch_name = user_data['branch_name']
                        st.session_state.role_tab = str(user_data.get('Role_tab', 'user')).strip().lower()
                        
                        raw_tabs = user_data.get('allowed_tabs', '')
                        st.session_state.allowed_tabs = [t.strip() for t in raw_tabs.split(',')] if raw_tabs else []
                        
                        allowed_b_list = [str(user_data['branch_id'])] + [str(b['branch_id']) for b in extra_branches]
                        st.session_state.allowed_branches = list(set(allowed_b_list))
                        
                        st.success("ล็อกอินสำเร็จ! กำลังนำเข้าสู่ระบบ...")
                        st.rerun()
                    else:
                        st.error("User ID หรือ Password ไม่ถูกต้อง โปรดตรวจสอบอีกครั้ง")
                conn.close()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
    
    st.write("ยังไม่มีบัญชีผู้ใช้งานใช่หรือไม่?")
    if st.button("📝 สมัครสมาชิกใหม่ (Register) ที่นี่"):
        st.session_state.page = "register"
        st.rerun()

def render_register_page():
    # 🎯 โหลดรายการตำแหน่งเตรียมไว้
    position_list = ["-- กรุณาเลือกตำแหน่ง --"]
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT CONVERT(position USING utf8mb4) AS pos FROM departments WHERE position IS NOT NULL AND position != '' ORDER BY position ASC")
            for r in cur.fetchall():
                if r['pos']: position_list.append(r['pos'].strip())
        conn.close()
    except Exception: pass

    st.title("📝 ลงทะเบียนสมาชิกใหม่แยกตามสาขา")
    st.write("---")
    
    with st.form("register_form", clear_on_submit=True):
        st.markdown("#### 👤 ข้อมูลบัญชีผู้ใช้งาน")
        col_u1, col_u2 = st.columns(2)
        with col_u1: reg_user = st.text_input("กำหนด User ID (Username) *")
        with col_u2: reg_pass = st.text_input("กำหนด Password *", type="password")
        
        st.markdown("#### 📋 ข้อมูลส่วนตัว")
        col_p1, col_p2 = st.columns(2)
        with col_p1: reg_fullname = st.text_input("ชื่อ-นามสกุล *")
        with col_p2: reg_position = st.selectbox("ตำแหน่ง *", options=position_list) # 🎯 เปลี่ยนเป็น Dropdown
        
        col_c1, col_c2 = st.columns(2)
        with col_c1: reg_email = st.text_input("E-mail")
        with col_c2: reg_phone = st.text_input("เบอร์โทรศัพท์")
        
        st.markdown("#### 🏢 ข้อมูลสังกัด")
        reg_branch_label = st.selectbox("เลือกสาขาประจำตัวของคุณ *", options=list(branch_dict.keys()))
        reg_branch_id = branch_dict[reg_branch_label]
        
        btn_reg = st.form_submit_button("💥 ลงทะเบียนบัญชี")
        
        if btn_reg:
            if not reg_user or not reg_pass or not reg_fullname or reg_position == "-- กรุณาเลือกตำแหน่ง --":
                st.error("⚠️ กรุณากรอกข้อมูลที่มีเครื่องหมาย * ให้ครบถ้วน และเลือกตำแหน่ง")
            else:
                conn = None
                try:
                    conn = get_db_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT user_id FROM system_users WHERE CONVERT(username USING utf8mb4) = CONVERT(%s USING utf8mb4)", (reg_user,))
                        if cursor.fetchone():
                            st.error("❌ User ID นี้มีผู้ใช้งานในระบบแล้ว")
                        else:
                            sql = """INSERT INTO system_users (username, password_hash, full_name, position, email, phone_number, branch_id, Role_tab, allowed_tabs, status) 
                                     VALUES (CONVERT(%s USING utf8mb4), %s, CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), %s, 'user', '', 'active')"""
                            cursor.execute(sql, (reg_user, hash_password(reg_pass), reg_fullname, reg_position, reg_email, reg_phone, reg_branch_id))
                            conn.commit() 
                            
                            st.success("🎉 ลงทะเบียนสำเร็จ! กำลังพากลับไปหน้าเข้าสู่ระบบ...")
                            st.toast("สมัครสมาชิกสำเร็จ!", icon="🎉")
                            
                            st.session_state.page = "login"
                            time.sleep(1.5)
                            st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการลงทะเบียน: {e}")
                finally:
                    if conn and conn.open:
                        conn.close()
    
    if st.button("⬅️ กลับไปหน้าเข้าสู่ระบบ (Login)"):
        st.session_state.page = "login"
        st.rerun()