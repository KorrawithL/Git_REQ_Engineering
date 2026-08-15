import streamlit as st
import streamlit.components.v1 as components
import time
from database import get_db_connection, hash_password
from config import branch_dict
from tab_views import render_engineering_system_tabs
from admin import render_admin_user_management
from all_reports import render_all_reports_module

# -----------------------------------------------------------------------------
# 🎯 1. ตั้งค่าหน้าเว็บ Streamlit
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Woodwork Engineering Records System",
    page_icon="🪵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 🎨 2. ฟังก์ชัน Responsive Web Design (RWD CSS)
# -----------------------------------------------------------------------------
def apply_responsive_css():
    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }

        @media (max-width: 768px) {
            h1 { font-size: 1.6rem !important; }
            h2 { font-size: 1.3rem !important; }
            h3 { font-size: 1.1rem !important; }
            
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
                margin-bottom: 0.5rem !important;
            }

            .stButton > button {
                width: 100% !important;
                font-size: 1rem !important;
                padding: 0.6rem 1rem !important;
            }

            [data-testid="stDataFrame"] {
                width: 100% !important;
                overflow-x: auto !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)

apply_responsive_css()

# -----------------------------------------------------------------------------
# ⏱️ 3. ตั้งค่า Session Timeout (30 นาที = 1,800 วินาที)
# -----------------------------------------------------------------------------
SESSION_TIMEOUT_SECONDS = 1800  

def perform_logout(message=None):
    for key in ['logged_in', 'user_id', 'username', 'branch_id', 'branch_name', 'role_tab', 'allowed_tabs', 'last_activity', 'page']:
        if key in st.session_state:
            del st.session_state[key]
    st.query_params.clear()
    if message:
        st.warning(message)

def restore_session_from_url():
    saved_user = st.query_params.get("auth_user")
    saved_time = st.query_params.get("auth_time")

    if saved_user and saved_time and not st.session_state.get('logged_in'):
        try:
            last_time = float(saved_time)
            elapsed = time.time() - last_time

            if elapsed > SESSION_TIMEOUT_SECONDS:
                perform_logout("⏱️ หมดเวลาการใช้งาน (ทิ้งหน้าจอนิ่งเกิน 30 นาที) ระบบได้ออกจากระบบอัตโนมัติเพื่อความปลอดภัย")
                return

            conn = get_db_connection()
            with conn.cursor() as cur:
                sql = """SELECT u.user_id, u.username, u.branch_id, b.branch_name, u.Role_tab, u.allowed_tabs, u.status 
                         FROM system_users u
                         LEFT JOIN branches b ON u.branch_id = b.id
                         WHERE u.username = %s AND u.status = 'active'"""
                cur.execute(sql, (saved_user,))
                user = cur.fetchone()
            conn.close()

            if user:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user['user_id']
                st.session_state['username'] = user['username']
                st.session_state['branch_id'] = user['branch_id']
                st.session_state['branch_name'] = user['branch_name']
                st.session_state['role_tab'] = str(user['Role_tab']).strip().lower()
                
                raw_tabs = user.get('allowed_tabs', '') or ''
                st.session_state['allowed_tabs'] = [x.strip() for x in str(raw_tabs).split(',') if x.strip()]
                st.session_state['last_activity'] = last_time
        except Exception as e:
            print(f"Error restoring session: {e}")

def check_session_timeout():
    if st.session_state.get('logged_in'):
        current_time = time.time()
        last_activity = st.session_state.get('last_activity', current_time)
        elapsed = current_time - last_activity

        if elapsed > SESSION_TIMEOUT_SECONDS:
            perform_logout("⏱️ หมดเวลาการใช้งาน (ทิ้งหน้าจอนิ่งเกิน 30 นาที) ระบบได้ทำการออกจากระบบอัตโนมัติ")
            st.rerun()
        else:
            remaining_ms = int((SESSION_TIMEOUT_SECONDS - elapsed + 1) * 1000)
            
            components.html(
                f"""
                <script>
                if (window.parent.idleTimer) {{
                    clearTimeout(window.parent.idleTimer);
                }}
                window.parent.idleTimer = setTimeout(function() {{
                    window.parent.location.reload();
                }}, {remaining_ms});
                </script>
                """,
                height=0,
                width=0
            )

restore_session_from_url()
check_session_timeout()

# -----------------------------------------------------------------------------
# 🔐 4. หน้าจอ Authentication (Login & Register)
# -----------------------------------------------------------------------------
if not st.session_state.get('logged_in'):
    if st.session_state.get('page') == 'register':
        # 📝 หน้าลงทะเบียนสมาชิกใหม่
        st.title("📝 ลงทะเบียนสมาชิกใหม่แยกตามสาขา")
        st.write("---")
        
        with st.form("register_form", clear_on_submit=True):
            reg_user = st.text_input("กำหนด User ID (Username)")
            reg_pass = st.text_input("กำหนด Password", type="password")
            reg_branch_label = st.selectbox("เลือกสาขาประจำตัวของคุณ", options=list(branch_dict.keys()))
            reg_branch_id = branch_dict[reg_branch_label]
            
            btn_reg = st.form_submit_button("💥 ลงทะเบียนบัญชี", use_container_width=True)
            
            if btn_reg:
                if reg_user == "" or reg_pass == "":
                    st.error("กรุณากรอกข้อมูล Username และ Password ให้ครบถ้วน")
                else:
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
                                
                                st.success("🎉 ลงทะเบียนสำเร็จ! กำลังพากลับไปหน้าเข้าสู่ระบบ...")
                                st.toast("สมัครสมาชิกสำเร็จ!", icon="🎉")
                                st.session_state.page = "login"
                                time.sleep(1.2)
                                st.rerun()
                        conn.close()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการลงทะเบียน: {e}")
        
        if st.button("⬅️ กลับไปหน้าเข้าสู่ระบบ (Login)", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

    else:
        # 🔐 หน้าเข้าสู่ระบบ
        st.title("🪵 Woodwork Engineering Records System")
        st.subheader("🔐 เข้าสู่ระบบ")

        with st.form("login_form", clear_on_submit=False):
            username_input = st.text_input("ชื่อผู้ใช้งาน (Username)")
            password_input = st.text_input("รหัสผ่าน (Password)", type="password")
            submit_login = st.form_submit_button("🔑 เข้าสู่ระบบ", use_container_width=True)

            if submit_login:
                if not username_input or not password_input:
                    st.error("⚠️ กรุณากรอก Username และ Password ให้ครบถ้วน")
                else:
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            sql = """SELECT u.user_id, u.username, u.password_hash, u.branch_id, b.branch_name, u.Role_tab, u.allowed_tabs, u.status 
                                     FROM system_users u
                                     LEFT JOIN branches b ON u.branch_id = b.id
                                     WHERE u.username = %s"""
                            cur.execute(sql, (username_input,))
                            user = cur.fetchone()
                        conn.close()

                        if user and user['password_hash'] == hash_password(password_input):
                            if user['status'] != 'active':
                                st.error("🚫 บัญชีของคุณถูกระงับการใช้งาน หรือรอการอนุมัติสิทธิ์")
                            else:
                                now_time = time.time()
                                st.session_state['logged_in'] = True
                                st.session_state['user_id'] = user['user_id']
                                st.session_state['username'] = user['username']
                                st.session_state['branch_id'] = user['branch_id']
                                st.session_state['branch_name'] = user['branch_name']
                                st.session_state['role_tab'] = str(user['Role_tab']).strip().lower()
                                
                                raw_tabs = user.get('allowed_tabs', '') or ''
                                st.session_state['allowed_tabs'] = [x.strip() for x in str(raw_tabs).split(',') if x.strip()]
                                st.session_state['last_activity'] = now_time

                                st.query_params["auth_user"] = user['username']
                                st.query_params["auth_time"] = str(now_time)
                                
                                st.success("เข้าสู่ระบบสำเร็จ!")
                                st.rerun()
                        else:
                            st.error("❌ ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล: {e}")

        st.write("---")
        st.write("ยังไม่มีบัญชีผู้ใช้งานใช่หรือไม่?")
        if st.button("📝 สมัครสมาชิกใหม่ (Register) ที่นี่", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()

# -----------------------------------------------------------------------------
# 🎯 5. หน้าจอหลักของระบบ (Main Application)
# -----------------------------------------------------------------------------
else:
    st.session_state['last_activity'] = time.time()
    st.query_params["auth_user"] = st.session_state['username']
    st.query_params["auth_time"] = str(st.session_state['last_activity'])

    with st.sidebar:
        st.success(f"👤 ผู้ใช้งาน: **{st.session_state.get('username')}**")
        st.info(f"🏢 สังกัดปัจจุบัน: **{st.session_state.get('branch_name')}**")
        st.warning(f"👑 ระดับสิทธิ์: **{st.session_state.get('role_tab').upper()}**")
        st.write("---")
        if st.button("🚪 ออกจากระบบ (Logout)", use_container_width=True):
            perform_logout()
            st.rerun()

    current_role = st.session_state.get('role_tab')
    
    # 🎯 หากเป็น ADMIN
    if current_role == 'admin':
        admin_menu = st.radio(
            "เลือกเมนูหลัก (Admin Console):", 
            [
                "⚙️ ระบบจัดการผู้ใช้และสิทธิ์", 
                "📝 หน้าจอบันทึกข้อมูลประจำวัน (Data Entry)", 
                "📑 รายงานรวมทุกระบบ (All Report)"
            ], 
            horizontal=True
        )
        st.write("---")
        
        if admin_menu == "⚙️ ระบบจัดการผู้ใช้และสิทธิ์":
            render_admin_user_management()
        elif admin_menu == "📝 หน้าจอบันทึกข้อมูลประจำวัน (Data Entry)":
            render_engineering_system_tabs(st.session_state.get('branch_name'))
        elif admin_menu == "📑 รายงานรวมทุกระบบ (All Report)":
            render_all_reports_module(st.session_state.get('branch_name'))

    # 🎯 หากเป็น MANAGER หรือ USER ทั่วไป
    else:
        report_names_map = {
            "1": "⚙️ รายงานสรุปเครื่องจักร & เบรกดาวน์",
            "2": "🚚 รายงานสรุปการใช้เชื้อเพลิงรถ",
            "3": "💨 รายงานสรุปแรงดันไอน้ำ บอยเลอร์",
            "4": "🔥 รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)"
        }
        
        allowed_tabs_list = st.session_state.get('allowed_tabs', [])
        user_tab_keys = [k for k in allowed_tabs_list if k in report_names_map]

        if current_role == 'manager':
            report_menu_label = "📑 รายงานรวมทุกระบบ (All Report)"
        elif len(user_tab_keys) == 1:
            report_menu_label = report_names_map[user_tab_keys[0]]
        else:
            report_menu_label = "📑 รายงานสรุปประจำบัญชี"

        user_menu = st.radio(
            "เลือกเมนูหลัก:",
            [
                "📝 บันทึกข้อมูลประจำวัน (Data Entry)", 
                report_menu_label
            ],
            horizontal=True
        )
        st.write("---")
        
        if user_menu == "📝 บันทึกข้อมูลประจำวัน (Data Entry)":
            render_engineering_system_tabs(st.session_state.get('branch_name'))
        elif user_menu == report_menu_label:
            render_all_reports_module(st.session_state.get('branch_name'))