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
                    sql = "SELECT * FROM system_users WHERE username = %s AND password_hash = %s AND status = 'active'"
                    cursor.execute(sql, (log_user, hash_password(log_pass)))
                    user_data = cursor.fetchone()
                    
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_data['user_id']
                        st.session_state.username = user_data['username']
                        st.session_state.branch_id = user_data['branch_id']
                        st.session_state.role_tab = str(user_data.get('Role_tab', 'user')).strip().lower()
                        
                        raw_tabs = user_data.get('allowed_tabs', '')
                        st.session_state.allowed_tabs = [t.strip() for t in raw_tabs.split(',')] if raw_tabs else []
                        
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
    st.title("📝 ลงทะเบียนสมาชิกใหม่แยกตามสาขา")
    st.write("---")
    
    with st.form("register_form", clear_on_submit=True):
        reg_user = st.text_input("กำหนด User ID (Username)")
        reg_pass = st.text_input("กำหนด Password", type="password")
        reg_branch_label = st.selectbox("เลือกสาขาประจำตัวของคุณ", options=list(branch_dict.keys()))
        reg_branch_id = branch_dict[reg_branch_label]
        
        btn_reg = st.form_submit_button("💥 ลงทะเบียนบัญชี")
        
        if btn_reg:
            if reg_user == "" or reg_pass == "":
                st.error("กรุณากรอกข้อมูล Username และ Password ให้ครบถ้วน")
            else:
                conn = None
                try:
                    conn = get_db_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT user_id FROM system_users WHERE username = %s", (reg_user,))
                        if cursor.fetchone():
                            st.error("User ID นี้มีผู้ใช้งานในระบบแล้ว")
                        else:
                            sql = """INSERT INTO system_users (username, password_hash, branch_id, Role_tab, allowed_tabs, status) 
                                     VALUES (%s, %s, %s, 'user', '', 'active')"""
                            cursor.execute(sql, (reg_user, hash_password(reg_pass), reg_branch_id))
                            conn.commit() 
                            
                            st.success("🎉 ลงทะเบียนสำเร็จ! กำลังพากลับไปหน้าเข้าสู่ระบบเพื่อรีเช็คข้อมูล...")
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