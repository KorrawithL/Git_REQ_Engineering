import streamlit as st
import streamlit.components.v1 as components
import time
import os
from database import get_db_connection, hash_password
from config import branch_dict
from tab_views import render_engineering_system_tabs
from admin import render_admin_user_management
from all_reports import render_all_reports_module
from addMachines import render_add_new_equipment

# -----------------------------------------------------------------------------
# 🎯 1. ตั้งค่าหน้าเว็บ Streamlit (ปิด Sidebar ทิ้งตั้งแต่เริ่มต้น)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Woodwork Engineering Records System",
    page_icon="🪵",
    layout="wide",
    initial_sidebar_state="collapsed" 
)

SESSION_TIMEOUT_SECONDS = 1800  

def perform_logout(message=None):
    for key in ['logged_in', 'user_id', 'username', 'full_name', 'position', 'branch_id', 'branch_name', 'role_tab', 'allowed_tabs', 'allowed_branches', 'last_activity', 'page']:
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
            if time.time() - last_time > SESSION_TIMEOUT_SECONDS:
                perform_logout("⏱️ หมดเวลาการใช้งาน ระบบได้ออกจากระบบอัตโนมัติเพื่อความปลอดภัย")
                return

            conn = get_db_connection()
            with conn.cursor() as cur:
                sql = """SELECT u.user_id, u.username, u.full_name, u.position, u.branch_id, b.branch_name, u.Role_tab, u.allowed_tabs, u.status 
                         FROM system_users u LEFT JOIN branches b ON u.branch_id = b.id
                         WHERE CONVERT(u.username USING utf8mb4) = CONVERT(%s USING utf8mb4) AND u.status = 'active'"""
                cur.execute(sql, (saved_user,))
                user = cur.fetchone()
                
                if user:
                    cur.execute("SELECT branch_id FROM user_branches WHERE user_id = %s", (user['user_id'],))
                    extra_branches = cur.fetchall()
            conn.close()

            if user:
                st.session_state['logged_in'] = True
                for k in ['user_id', 'username', 'full_name', 'position', 'branch_id', 'branch_name']:
                    st.session_state[k] = user[k]
                st.session_state['role_tab'] = str(user['Role_tab']).strip().lower()
                
                raw_tabs = user.get('allowed_tabs', '') or ''
                st.session_state['allowed_tabs'] = [x.strip() for x in str(raw_tabs).split(',') if x.strip()]
                
                allowed_b_list = [str(user['branch_id'])] + [str(b['branch_id']) for b in extra_branches]
                st.session_state['allowed_branches'] = list(set(allowed_b_list)) 
                
                st.session_state['last_activity'] = last_time
        except Exception as e: print(f"Error: {e}")

def check_session_timeout():
    if st.session_state.get('logged_in'):
        elapsed = time.time() - st.session_state.get('last_activity', time.time())
        if elapsed > SESSION_TIMEOUT_SECONDS:
            perform_logout("⏱️ หมดเวลาการใช้งาน ระบบได้ทำการออกจากระบบอัตโนมัติ")
            st.rerun()
        else:
            components.html(f"<script>if(window.parent.idleTimer) clearTimeout(window.parent.idleTimer); window.parent.idleTimer = setTimeout(function(){{ window.parent.location.reload(); }}, {int((SESSION_TIMEOUT_SECONDS - elapsed + 1) * 1000)});</script>", height=0, width=0)

@st.dialog("🔑 เปลี่ยนรหัสผ่าน Password")
def change_password_dialog():
    st.write("กรุณากรอกรหัสผ่านปัจจุบันและรหัสผ่านใหม่ของคุณ")
    with st.form("change_pwd_form"):
        old_pwd = st.text_input("รหัสผ่านปัจจุบัน *", type="password")
        new_pwd = st.text_input("รหัสผ่านใหม่ *", type="password")
        confirm_pwd = st.text_input("ยืนยันรหัสผ่านใหม่ *", type="password")
        
        if st.form_submit_button("💾 บันทึกรหัสผ่านใหม่", use_container_width=True):
            if not old_pwd or not new_pwd or not confirm_pwd:
                st.error("⚠️ กรุณากรอกข้อมูลให้ครบทุกช่อง")
            elif new_pwd != confirm_pwd:
                st.error("⚠️ รหัสผ่านใหม่และการยืนยันไม่ตรงกัน")
            else:
                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        cur.execute("SELECT password_hash FROM system_users WHERE user_id = %s", (st.session_state.user_id,))
                        user_record = cur.fetchone()
                        if not user_record or user_record['password_hash'] != hash_password(old_pwd):
                            st.error("❌ รหัสผ่านปัจจุบันไม่ถูกต้อง")
                        else:
                            cur.execute("UPDATE system_users SET password_hash = %s WHERE user_id = %s", (hash_password(new_pwd), st.session_state.user_id))
                            conn.commit()
                            st.success("✅ เปลี่ยนรหัสผ่านสำเร็จ! ระบบกำลังนำคุณออกเพื่อเข้าสู่ระบบใหม่...")
                            time.sleep(1.5)
                            perform_logout()
                            st.rerun()
                    conn.close()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

restore_session_from_url()
check_session_timeout()

# -----------------------------------------------------------------------------
# 🔐 3. หน้าจอ Authentication
# -----------------------------------------------------------------------------
if not st.session_state.get('logged_in'):
    if st.session_state.get('page') == 'register':
        
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
            with col_p2: reg_position = st.selectbox("ตำแหน่ง *", options=position_list) 
            
            col_c1, col_c2 = st.columns(2)
            with col_c1: reg_email = st.text_input("E-mail")
            with col_c2: reg_phone = st.text_input("เบอร์โทรศัพท์")
            
            st.markdown("#### 🏢 ข้อมูลสังกัด")
            reg_branch_label = st.selectbox("เลือกสาขาประจำตัวของคุณ *", options=list(branch_dict.keys()))
            reg_branch_id = branch_dict[reg_branch_label]
            
            st.write("")
            if st.form_submit_button("💥 ลงทะเบียนบัญชี", use_container_width=True):
                if not reg_user or not reg_pass or not reg_fullname or reg_position == "-- กรุณาเลือกตำแหน่ง --": 
                    st.error("⚠️ กรุณากรอกข้อมูลที่มีเครื่องหมาย * ให้ครบถ้วน และเลือกตำแหน่ง")
                else:
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT user_id FROM system_users WHERE CONVERT(username USING utf8mb4) = CONVERT(%s USING utf8mb4)", (reg_user,))
                            if cursor.fetchone(): st.error("❌ User ID นี้มีผู้ใช้งานในระบบแล้ว")
                            else:
                                sql = """INSERT INTO system_users (username, password_hash, full_name, position, email, phone_number, branch_id, Role_tab, allowed_tabs, status) 
                                         VALUES (CONVERT(%s USING utf8mb4), %s, CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), %s, 'user', '', 'active')"""
                                cursor.execute(sql, (reg_user, hash_password(reg_pass), reg_fullname, reg_position, reg_email, reg_phone, reg_branch_id))
                                conn.commit()
                                st.success("🎉 ลงทะเบียนสำเร็จ! กำลังพากลับไปหน้าเข้าสู่ระบบ...")
                                st.session_state.page = "login"
                                time.sleep(1.2)
                                st.rerun()
                        conn.close()
                    except Exception as e: st.error(f"เกิดข้อผิดพลาดในการลงทะเบียน: {e}")
                    
        if st.button("⬅️ กลับไปหน้าเข้าสู่ระบบ (Login)", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
    else:
        st.markdown("""<style>
        header {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;} 
        .main .block-container { padding-top: 3.5rem !important; padding-bottom: 2rem !important; max-width: 950px !important; margin: auto; } 
        div[data-testid="stHorizontalBlock"] { border-radius: 28px; box-shadow: 0 20px 45px rgba(0, 0, 0, 0.15); overflow: hidden; } 
        div[data-testid="stHorizontalBlock"] > div:first-child { background: radial-gradient(circle at top right, #1d68d8 0%, #0d47a1 60%, #082d69 100%) !important; border-radius: 28px 0 0 28px !important; padding: 45px 35px 35px 35px !important; color: #FFFFFF !important; display: flex !important; flex-direction: column !important; justify-content: center !important; } 
        div[data-testid="stHorizontalBlock"] > div:last-child { background: #FFFFFF !important; border-radius: 0 28px 28px 0 !important; padding: 50px 35px !important; display: flex !important; flex-direction: column !important; justify-content: center !important; align-items: center !important; text-align: center !important; } 
        div[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; } 
        div[data-testid="stForm"] div[data-baseweb="input"] { background-color: #FFFFFF !important; border-radius: 12px !important; border: 1px solid #CBD5E1 !important; margin-bottom: 6px !important; } 
        div[data-testid="stForm"] div[data-baseweb="input"] input { color: #0F172A !important; } 
        div[data-testid="stFormSubmitButton"] > button, div[data-testid="stForm"] .stButton > button { background: linear-gradient(135deg, #F59E0B 0%, #EA580C 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 12px !important; padding: 10px !important; font-size: 16px !important; font-weight: 700 !important; box-shadow: 0 4px 15px rgba(234, 88, 12, 0.35) !important; margin-top: 10px !important; } 
        div[data-testid="stHorizontalBlock"] > div:last-child .stButton > button { background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 12px !important; padding: 10px 40px !important; font-size: 16px !important; font-weight: 700 !important; box-shadow: 0 4px 15px rgba(30, 64, 175, 0.3) !important; margin-top: 15px !important; } 
        .login-header-title { font-size: 30px; font-weight: 800; color: #FFFFFF; text-align: center; margin-bottom: 4px; } 
        .login-header-subtitle { font-size: 13px; color: #BBDEFB; text-align: center; margin-bottom: 25px; } 
        .newhere-header-title { font-size: 30px; font-weight: 800; color: #1E293B; margin-bottom: 12px; } 
        .newhere-header-desc { font-size: 13.5px; color: #64748B; line-height: 1.6; margin-bottom: 25px; max-width: 280px; } 
        @media (max-width: 768px) { div[data-testid="stHorizontalBlock"] > div:first-child { border-radius: 24px 24px 0 0 !important; } div[data-testid="stHorizontalBlock"] > div:last-child { border-radius: 0 0 24px 24px !important; } }
        </style>""", unsafe_allow_html=True)
        col_left, col_right = st.columns([1.15, 0.95], gap="small")
        with col_left:
            st.markdown('<div class="login-header-title">Welcome Back</div><div class="login-header-subtitle">Woodwork Engineering Records System</div>', unsafe_allow_html=True)
            with st.form("login_form", clear_on_submit=False):
                username_input = st.text_input("User Name", placeholder="👤 User Name", label_visibility="collapsed")
                password_input = st.text_input("Password", type="password", placeholder="🔒 Password", label_visibility="collapsed")
                if st.form_submit_button("Login", type="primary", use_container_width=True):
                    if not username_input or not password_input: st.error("⚠️ กรุณากรอก Username และ Password ให้ครบถ้วน")
                    else:
                        try:
                            conn = get_db_connection()
                            with conn.cursor() as cur:
                                sql = """SELECT u.user_id, u.username, u.full_name, u.position, u.password_hash, u.branch_id, b.branch_name, u.Role_tab, u.allowed_tabs, u.status 
                                         FROM system_users u LEFT JOIN branches b ON u.branch_id = b.id 
                                         WHERE CONVERT(u.username USING utf8mb4) = CONVERT(%s USING utf8mb4)"""
                                cur.execute(sql, (username_input,))
                                user = cur.fetchone()
                                
                                if user:
                                    cur.execute("SELECT branch_id FROM user_branches WHERE user_id = %s", (user['user_id'],))
                                    extra_branches = cur.fetchall()
                            conn.close()

                            if user and user['password_hash'] == hash_password(password_input):
                                if user['status'] != 'active': st.error("🚫 บัญชีของคุณถูกระงับการใช้งาน หรือรอการอนุมัติสิทธิ์")
                                else:
                                    now_time = time.time()
                                    st.session_state['logged_in'] = True
                                    for k in ['user_id', 'username', 'full_name', 'position', 'branch_id', 'branch_name']: 
                                        st.session_state[k] = user[k]
                                    st.session_state['role_tab'] = str(user['Role_tab']).strip().lower()
                                    
                                    raw_tabs = user.get('allowed_tabs', '') or ''
                                    st.session_state['allowed_tabs'] = [x.strip() for x in str(raw_tabs).split(',') if x.strip()]
                                    
                                    allowed_b_list = [str(user['branch_id'])] + [str(b['branch_id']) for b in extra_branches]
                                    st.session_state['allowed_branches'] = list(set(allowed_b_list)) 
                                    
                                    st.session_state['last_activity'] = now_time
                                    st.query_params["auth_user"] = user['username']
                                    st.query_params["auth_time"] = str(now_time)
                                    st.success("เข้าสู่ระบบสำเร็จ!")
                                    st.rerun()
                            else: st.error("❌ ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
                        except Exception as e: st.error(f"เกิดข้อผิดพลาด: {e}")
        with col_right:
            st.markdown('<div class="newhere-header-title">New Here?</div><div class="newhere-header-desc">Dear all, the team has completed the development of the machine usage logging system...</div>', unsafe_allow_html=True)
            if st.button("Sign Up", use_container_width=True):
                st.session_state.page = "register"
                st.rerun()

# -----------------------------------------------------------------------------
# 🎯 4. หน้าจอหลักของระบบ (Main Layout & UI - Nested Hierarchy Fixed Text)
# -----------------------------------------------------------------------------
else:
    st.markdown("""<style>
    /* 🎯 ซ่อน Header และตัวควบคุมมาตรฐานของ Streamlit */
    header[data-testid="stHeader"] { display: none !important; }
    header { visibility: hidden !important; }
    #MainMenu { visibility: hidden !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    
    /* 🎯 พื้นหลังหลักของแอปเป็นสีขาวนวล */
    .stApp {
        background-color: #FDFBF7 !important;
        color: #2C2A29 !important;
    }
    
    /* 🎯 Sidebar เป็นสีครีมละมุน */
    [data-testid="stSidebar"] {
        display: block !important;
        width: 290px !important;
        background-color: #F4EFEA !important;
        border-right: 1px solid #E6DFD5 !important;
    }
    
    .main .block-container { 
        padding-top: 1.5rem !important; 
        padding-left: 2rem !important; 
        padding-right: 2rem !important; 
        max-width: 100% !important; 
        background-color: #FDFBF7 !important;
    }
    
    div[data-testid="stHorizontalBlock"]:first-of-type button {
        background-color: #FFFFFF !important; border: 1px solid #E6DFD5 !important; border-radius: 8px !important; padding: 2px 0px !important; font-size: 14px !important; transition: all 0.2s ease !important; color: #2C2A29 !important; box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
    }
    div[data-testid="stHorizontalBlock"]:first-of-type button:hover { transform: translateY(-1px) !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important; }

    /* =========================================================
       🌟 1. ทำให้เมนูหลักโดดเด่น (Prominent Main Menu)
       ========================================================= */
    [data-testid="stSidebar"] div.stButton > button {
        background-color: #FFFFFF !important;
        border: 1px solid #E6DFD5 !important;
        color: #1C1917 !important;
        padding: 12px 14px !important;
        border-radius: 10px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
        text-align: left !important;
        justify-content: flex-start !important;
        width: 100% !important;
        margin-bottom: 2px !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #FAFAFA !important;
        border-color: #D97706 !important;
        color: #D97706 !important;
    }
    
    /* เมนูหลักที่กำลังเลือก (Active) */
    [data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
        background-color: #D97706 !important; 
        color: #FFFFFF !important;
        border: 1px solid #D97706 !important;
        box-shadow: 0 4px 12px rgba(217, 119, 6, 0.25) !important;
    }

    /* =========================================================
       🌟 2. จัดระเบียบเมนูย่อย (Sub-menu) ให้ตัวหนังสือกลับมา!
       ========================================================= */
    /* จัดการกรอบและเส้นสายตาของเมนูย่อย */
    [data-testid="stSidebar"] div[data-testid="stRadio"] {
        border-left: 2px solid #D1D5DB !important; /* เส้นสีเทานำสายตาด้านซ้าย */
        margin-left: 20px !important; /* เยื้องเข้าไปอยู่ใต้เมนูหลัก */
        padding-left: 5px !important;
        margin-top: 5px !important;
        margin-bottom: 15px !important;
    }
    
    /* 🌟 ซ่อนวงกลม Radio อย่างปลอดภัย (ไม่กระทบข้อความ) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] input[type="radio"] {
        display: none !important;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] input[type="radio"] + div {
        display: none !important;
    }
    
    /* ระยะห่างระหว่างหัวข้อย่อย */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 2px !important;
    }
    
    /* พื้นหลังเมนูย่อย (แบบใส) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        padding: 8px 10px !important;
        margin: 0 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        display: block !important;
        width: 100% !important;
        cursor: pointer !important;
    }
    
    /* บังคับให้กล่องข้อความแสดงผลแน่นอน */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] {
        display: block !important;
        width: 100% !important;
    }
    
    /* จัดข้อความเมนูย่อยให้สวยงาม */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label p {
        color: #57534E !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        margin: 0 !important;
        line-height: 1.5 !important;
        white-space: normal !important;
        /* เทคนิคดันไอคอน: ย่อหน้าลบแล้วดันกลับ */
        text-indent: -22px !important;
        padding-left: 22px !important;
    }
    
    /* เอฟเฟกต์ตอนชี้เมาส์ (Hover) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
        background-color: #EFECE6 !important;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:hover p {
        color: #1C1917 !important;
    }
    
    /* เอฟเฟกต์ตอนถูกเลือก (Active) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
        background-color: #FFFFFF !important;
        border-color: #E6DFD5 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03) !important;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
        color: #D97706 !important;
        font-weight: 700 !important;
    }
    </style>""", unsafe_allow_html=True)
    
    st.session_state['last_activity'] = time.time()
    st.query_params["auth_user"] = st.session_state['username']
    st.query_params["auth_time"] = str(st.session_state['last_activity'])

    # =========================================================================
    # 🎯 แถบ Top Bar แนวนอนด้านบนสุด (Global Navbar)
    # =========================================================================
    disp_name = st.session_state.get('full_name') or st.session_state.get('username')
    current_role = str(st.session_state.get('role_tab', 'user')).strip().lower()
    current_branch = st.session_state.get('branch_name', '-')
    
    role_th = "พนักงานทั่วไป"
    if current_role == "admin":
        role_th = "ผู้ดูแลระบบ"
        current_access = "ADMIN"
        access_desc = "🌟 เข้าถึงได้ทุกสาขา (Full Access)"
        access_color = "#10B981"
    elif current_role in ["manager", "reporter"]:
        role_th = "ผู้จัดการ / รีพอร์ตเตอร์"
        current_access = current_role.upper()
        access_desc = "✨ เข้าถึงได้หลายสาขา"
        access_color = "#3B82F6"
    else:
        current_access = "USER"
        access_desc = "📍 เข้าถึงได้เฉพาะสาขา"
        access_color = "#64748B"

    with st.container(border=True):
        c_logo, c_user, c_role, c_branch, c_access, c_pw, c_out = st.columns([1.2, 2.2, 2.0, 1.2, 2.8, 1.5, 1.2], gap="small", vertical_alignment="center")
        
        with c_logo:
            if os.path.exists("Logo.png"): st.image("Logo.png", use_container_width=True)
            elif os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
            else: st.markdown("<div style='color:#E4222C; font-weight:bold; text-align:center; padding-top:10px;'>[WOODWORK LOGO]</div>", unsafe_allow_html=True)
            
        with c_user: st.markdown(f"<div style='font-size:12px; color:#78716C; margin-bottom:2px;'>👤 ผู้ใช้งาน</div><div style='font-size:14px; font-weight:700; color:#1C1917;'>{disp_name}</div>", unsafe_allow_html=True)
        with c_role: st.markdown(f"<div style='font-size:12px; color:#78716C; margin-bottom:2px;'>💼 ตำแหน่ง</div><div style='font-size:14px; font-weight:700; color:#1C1917;'>{role_th}</div>", unsafe_allow_html=True)
        with c_branch: st.markdown(f"<div style='font-size:12px; color:#78716C; margin-bottom:2px;'>🏢 สังกัดปัจจุบัน</div><div style='font-size:14px; font-weight:700; color:#1C1917;'>{current_branch}</div>", unsafe_allow_html=True)
        with c_access: st.markdown(f"<div style='font-size:12px; color:#78716C; margin-bottom:2px;'>👑 ระดับสิทธิ์: {current_access}</div><div style='font-size:13px; font-weight:700; color:{access_color};'>{access_desc}</div>", unsafe_allow_html=True)
        
        with c_pw:
            st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)
            if st.button("🔑 เปลี่ยนรหัสผ่าน", use_container_width=True, key="app_btn_pw"): change_password_dialog()
                
        with c_out:
            st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)
            if st.button("🚪 ออกจากระบบ", use_container_width=True, key="app_btn_out"):
                perform_logout()
                st.rerun()

    st.write("") 

    # =========================================================================
    # 🎯 โครงสร้าง Sidebar (Nested Accordion สำหรับบันทึกข้อมูล และ รายงาน)
    # =========================================================================
    all_tabs_config = {
        "1": "⚙️ 1. ระบบเครื่องจักร / เบรกดาวน์", 
        "2": "🚚 2. ระบบเชื้อเพลิง (รถยก/เครื่องยนต์)",
        "3": "💨 3. แรงดันไอน้ำปลายทาง บอยเลอร์", 
        "4": "🔥 4. การใช้เชื้อเพลิง บอยเลอร์"
    }
    
    report_names_map = {
        "1": "⚙️ 1. รายงานสรุปเครื่องจักร / เบรกดาวน์", 
        "2": "🚚 2. รายงานสรุปการใช้เชื้อเพลิงรถ", 
        "3": "💨 3. รายงานสรุปแรงดันไอน้ำ บอยเลอร์", 
        "4": "🔥 4. รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์"
    }
    
    def get_sub_menu_options(role, allowed_tabs):
        if role == "admin": return [all_tabs_config[k] for k in ["1", "2", "3", "4"]]
        else: return [all_tabs_config[k] for k in allowed_tabs if k in all_tabs_config]

    def get_report_sub_options(role, allowed_tabs):
        if role in ["admin", "reporter"]: return [report_names_map[k] for k in ["1", "2", "3", "4"]]
        else: return [report_names_map[k] for k in allowed_tabs if k in report_names_map]

    sub_opts = get_sub_menu_options(current_role, st.session_state.get('allowed_tabs', []))
    rep_opts = get_report_sub_options(current_role, st.session_state.get('allowed_tabs', []))

    if 'sidebar_main' not in st.session_state:
        st.session_state['sidebar_main'] = "📝 บันทึกข้อมูลประจำวัน"
    if 'sidebar_sub_entry' not in st.session_state:
        st.session_state['sidebar_sub_entry'] = sub_opts[0] if sub_opts else "⚙️ 1. ระบบเครื่องจักร / เบรกดาวน์"
    if 'sidebar_sub_report' not in st.session_state:
        st.session_state['sidebar_sub_report'] = rep_opts[0] if rep_opts else "⚙️ 1. รายงานสรุปเครื่องจักร / เบรกดาวน์"

    with st.sidebar:
        st.markdown("<h3 style='color: #1C1917; margin-bottom: 20px; font-size: 18px; font-weight: 800; letter-spacing: 0.5px;'>🧭 ScaleApp.</h3>", unsafe_allow_html=True)
        
        # กำหนดชื่อเมนูหลักของรายงานตามสิทธิ์
        report_menu_label = "📑 รายงานรวม (All Report)"
        if current_role == 'admin':
            main_choices = ["⚙️ จัดการผู้ใช้และสิทธิ์", "📝 บันทึกข้อมูลประจำวัน", report_menu_label, "🛠️ จัดการข้อมูลอุปกรณ์"]
        elif current_role == 'reporter':
            main_choices = [report_menu_label]
        else:
            report_menu_label = "📑 รายงานประจำสาขา" if current_role == 'manager' else "📑 รายงานประจำบัญชี"
            main_choices = ["📝 บันทึกข้อมูลประจำวัน", report_menu_label]
            if current_role == 'manager':
                main_choices.append("🛠️ จัดการข้อมูลอุปกรณ์")

        # วนลูปสร้างปุ่มเมนูหลักและแทรกเมนูย่อย
        for choice in main_choices:
            is_main_active = (st.session_state['sidebar_main'] == choice)
            btn_type = "primary" if is_main_active else "secondary"
            
            if st.button(choice, key=f"sb_main_{choice}", use_container_width=True, type=btn_type):
                st.session_state['sidebar_main'] = choice
                st.rerun()
                
            # 🎯 แสดงเมนูย่อย สำหรับ "บันทึกข้อมูลประจำวัน"
            if choice == "📝 บันทึกข้อมูลประจำวัน" and is_main_active and sub_opts:
                default_idx = sub_opts.index(st.session_state['sidebar_sub_entry']) if st.session_state['sidebar_sub_entry'] in sub_opts else 0
                st.radio("เมนูย่อย", sub_opts, index=default_idx, key="sidebar_sub_entry", label_visibility="collapsed")
                
            # 🎯 แสดงเมนูย่อย สำหรับ "รายงาน"
            if choice == report_menu_label and is_main_active and rep_opts:
                default_idx_rep = rep_opts.index(st.session_state['sidebar_sub_report']) if st.session_state['sidebar_sub_report'] in rep_opts else 0
                st.radio("เมนูย่อยรายงาน", rep_opts, index=default_idx_rep, key="sidebar_sub_report", label_visibility="collapsed")

    # =========================================================================
    # 🎯 เรนเดอร์หน้าจอตามเมนูหลักและเมนูย่อยที่ถูกเลือก
    # =========================================================================
    selected_main = st.session_state['sidebar_main']
    sub_menu_entry = st.session_state['sidebar_sub_entry'] if selected_main == "📝 บันทึกข้อมูลประจำวัน" else None
    sub_menu_report = st.session_state['sidebar_sub_report'] if selected_main == report_menu_label else None

    if current_role == 'admin':
        if selected_main == "⚙️ จัดการผู้ใช้และสิทธิ์": render_admin_user_management()
        elif selected_main == "📝 บันทึกข้อมูลประจำวัน": render_engineering_system_tabs(st.session_state.get('branch_name'), sub_menu_entry)
        elif selected_main == report_menu_label: render_all_reports_module(st.session_state.get('branch_name'), sub_menu_report)
        elif selected_main == "🛠️ จัดการข้อมูลอุปกรณ์": render_add_new_equipment()

    elif current_role == 'reporter':
        if selected_main == report_menu_label: render_all_reports_module(st.session_state.get('branch_name'), sub_menu_report)

    else:
        if selected_main == "📝 บันทึกข้อมูลประจำวัน": render_engineering_system_tabs(st.session_state.get('branch_name'), sub_menu_entry)
        elif selected_main == report_menu_label: render_all_reports_module(st.session_state.get('branch_name'), sub_menu_report)
        elif selected_main == "🛠️ จัดการข้อมูลอุปกรณ์": render_add_new_equipment()