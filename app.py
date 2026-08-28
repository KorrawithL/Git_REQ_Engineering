import streamlit as st
import streamlit.components.v1 as components
import time
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

@st.dialog("🔑 เปลี่ยนรหัสผ่าน")
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
# 🎯 4. หน้าจอหลักของระบบ (Main Layout & UI)
# -----------------------------------------------------------------------------
else:
    st.markdown("""<style>
    .main .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; max-width: 100% !important; }
    
    /* 🎯 ซ่อน Sidebar และปุ่มเปิด Sidebar ทั้งหมด */
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }
    
    /* 🎯 แต่งกล่อง Top Bar */
    .topbar-box {
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding-top: 2px;
    }
    .tb-lbl { font-size: 12px; color: #64748B; font-weight: 600; margin-bottom: 2px; }
    .tb-val { font-size: 15px; color: #0F172A; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .tb-sub { font-size: 12.5px; font-weight: 700; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .text-green { color: #10B981; }
    .text-blue { color: #3B82F6; }

    /* 🎯 1. สไตล์สำหรับเมนูหลัก (แนวตั้ง สีแดง) */
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[data-testid="stRadio"] {
        background-color: #FFFFFF;
        border: 1px solid #EAEAEA;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    /* ส่วนหัวของเมนู (Header) สีแดงโดดเด่น */
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[data-testid="stRadio"] > label {
        background-color: #E4222C !important;
        color: #FFFFFF !important;
        padding: 15px 20px !important;
        font-weight: 700 !important;
        font-size: 17px !important;
        display: block !important;
        margin-bottom: 0 !important;
        border-bottom: none !important;
    }
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[data-testid="stRadio"] > label p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 17px !important;
    }

    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 0 !important;
        padding: 0 !important;
    }
    
    /* กล่องปุ่มเมนูย่อย */
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[role="radiogroup"] > label {
        background-color: #FFFFFF !important;
        border: none !important;
        border-bottom: 1px solid #F0F0F0 !important;
        border-radius: 0 !important;
        padding: 15px 20px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        box-shadow: none !important;
        margin: 0 !important;
    }
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[role="radiogroup"] > label:last-child {
        border-bottom: none !important;
    }
    
    /* เอฟเฟกต์เมื่อเอาเมาส์ชี้ (Hover) */
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[role="radiogroup"] > label:hover {
        background-color: #FAFAFA !important;
    }
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[role="radiogroup"] > label > div:first-child {
        display: none !important; /* ซ่อนจุดวงกลมของ Radio ทิ้ง */
    }
    
    /* สีของตัวอักษรตอนปกติ (สีเทาเข้ม) */
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p {
        font-size: 14.5px !important;
        font-weight: 600 !important;
        color: #555555 !important;
        margin: 0 !important;
        transition: color 0.2s ease !important;
    }
    
    /* สถานะ Active (ปุ่มที่ถูกเลือกอยู่ - สีแดงและมีแถบด้านซ้าย) */
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[role="radiogroup"] > label:has(input:checked) {
        background: #FAFAFA !important;
        border-left: 5px solid #E4222C !important;
        padding-left: 15px !important;
    }
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[role="radiogroup"] > label:has(input:checked) div[data-testid="stMarkdownContainer"] p {
        color: #E4222C !important;
        font-weight: 700 !important;
    }
    
    /* ตัวหนังสือสีแดงเมื่อ Hover */
    div[data-testid="stElementContainer"]:has(.main-menu-marker) + div[data-testid="stElementContainer"] div[role="radiogroup"] > label:hover div[data-testid="stMarkdownContainer"] p {
        color: #E4222C !important;
    }

    /* 🎯 2. สไตล์สำหรับ Tabs (แท็บย่อยในหน้ารายงาน) ให้เป็นปุ่ม Pills สวยงาม */
    div[data-baseweb="tab-list"] {
        gap: 12px;
        padding-bottom: 10px;
        border-bottom: none !important;
    }
    div[data-baseweb="tab-highlight"] {
        display: none !important;
    }
    button[data-baseweb="tab"] {
        background-color: #FFFFFF !important;
        border: 2px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 10px 20px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
        margin: 0 !important;
    }
    button[data-baseweb="tab"] > div {
        font-size: 15px !important;
        font-weight: 600 !important;
        color: #475569 !important;
    }
    button[data-baseweb="tab"]:hover {
        border-color: #3B82F6 !important;
        background-color: #F8FAFC !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.12) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%) !important;
        border-color: transparent !important;
        box-shadow: 0 6px 15px rgba(37, 99, 235, 0.35) !important;
        transform: translateY(-2px) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] > div {
        color: #FFFFFF !important;
    }
    </style>""", unsafe_allow_html=True)
    
    st.session_state['last_activity'] = time.time()
    st.query_params["auth_user"] = st.session_state['username']
    st.query_params["auth_time"] = str(st.session_state['last_activity'])

    current_role = st.session_state.get('role_tab')

    # 🎯 สร้างพื้นที่ว่างด้านบนสุดจองไว้ (Placeholder) สำหรับนำแถบโปรไฟล์(สีน้ำเงิน)มาโชว์ในภายหลัง
    top_bar_placeholder = st.empty()
    st.write("") 

    # =========================================================================
    # 🎯 แยกระบบจัดหน้า Layout ใหม่ออกเป็น 2 คอลัมน์ (เมนูซ้าย - เนื้อหาขวา) (ประมวลผลก่อน)
    # =========================================================================
    if current_role == 'admin':
        col_menu, col_content = st.columns([2.5, 9.5], gap="large")
        with col_menu:
            st.markdown('<div class="main-menu-marker"></div>', unsafe_allow_html=True)
            admin_menu = st.radio("หมวดหมู่เมนูหลัก", ["⚙️ ระบบจัดการผู้ใช้และสิทธิ์", "📝 หน้าจอบันทึกข้อมูลประจำวัน", "📑 รายงานรวมทุกระบบ (All Report)", "🛠️ จัดการข้อมูลอุปกรณ์ในระบบ"])
        with col_content:
            if admin_menu == "⚙️ ระบบจัดการผู้ใช้และสิทธิ์": render_admin_user_management()
            elif admin_menu == "📝 หน้าจอบันทึกข้อมูลประจำวัน": render_engineering_system_tabs(st.session_state.get('branch_name'))
            elif admin_menu == "📑 รายงานรวมทุกระบบ (All Report)": render_all_reports_module(st.session_state.get('branch_name'))
            elif admin_menu == "🛠️ จัดการข้อมูลอุปกรณ์ในระบบ": render_add_new_equipment()
    
    elif current_role == 'reporter':
        col_menu, col_content = st.columns([2.5, 9.5], gap="large")
        with col_menu:
            st.markdown('<div class="main-menu-marker"></div>', unsafe_allow_html=True)
            reporter_menu = st.radio("หมวดหมู่เมนูหลัก", ["📑 รายงานรวมทุกระบบ (All Report)"])
        with col_content:
            if reporter_menu == "📑 รายงานรวมทุกระบบ (All Report)": render_all_reports_module(st.session_state.get('branch_name'))
    
    else:
        report_names_map = {"1": "⚙️ รายงานสรุปเครื่องจักร & เบรกดาวน์", "2": "🚚 รายงานสรุปการใช้เชื้อเพลิงรถ", "3": "💨 รายงานสรุปแรงดันไอน้ำ บอยเลอร์", "4": "🔥 รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์"}
        allowed_tabs_list = st.session_state.get('allowed_tabs', [])
        user_tab_keys = [k for k in allowed_tabs_list if k in report_names_map]

        if current_role == 'manager': 
            report_menu_label = "📑 รายงานสรุปประจำสาขา"
            menu_choices = ["📝 หน้าจอบันทึกข้อมูลประจำวัน", report_menu_label, "🛠️ จัดการข้อมูลอุปกรณ์ในระบบ"]
        else: 
            if len(user_tab_keys) == 1: report_menu_label = report_names_map[user_tab_keys[0]]
            else: report_menu_label = "📑 รายงานสรุปประจำบัญชี"
            menu_choices = ["📝 หน้าจอบันทึกข้อมูลประจำวัน", report_menu_label]

        col_menu, col_content = st.columns([2.5, 9.5], gap="large")
        with col_menu:
            st.markdown('<div class="main-menu-marker"></div>', unsafe_allow_html=True)
            user_menu = st.radio("หมวดหมู่เมนูหลัก", menu_choices)
        with col_content:
            if user_menu == "📝 หน้าจอบันทึกข้อมูลประจำวัน": render_engineering_system_tabs(st.session_state.get('branch_name'))
            elif user_menu == report_menu_label: render_all_reports_module(st.session_state.get('branch_name'))
            elif user_menu == "🛠️ จัดการข้อมูลอุปกรณ์ในระบบ": render_add_new_equipment()

    # =========================================================================
    # 🎯 แถบ Top Bar แนวนอนด้านบนสุด (ถูกนำไปแสดงใน Placeholder ด้านบนที่จองไว้)
    # =========================================================================
    disp_name = st.session_state.get('full_name') or st.session_state.get('username')
    disp_pos = st.session_state.get('position') or "-"
    
    with top_bar_placeholder.container(border=True):
        tc1, tc2, tc3, tc4, tc5, tc6 = st.columns([1.5, 1.5, 1.2, 2.5, 1.2, 1.2])
        
        with tc1: 
            st.markdown(f"<div class='topbar-box'><div class='tb-lbl'>👤 ผู้ใช้งาน</div><div class='tb-val'>{disp_name}</div></div>", unsafe_allow_html=True)
        with tc2: 
            st.markdown(f"<div class='topbar-box'><div class='tb-lbl'>💼 ตำแหน่ง</div><div class='tb-val'>{disp_pos}</div></div>", unsafe_allow_html=True)
        with tc3: 
            st.markdown(f"<div class='topbar-box'><div class='tb-lbl'>🏢 สังกัดปัจจุบัน</div><div class='tb-val'>{st.session_state.get('branch_name')}</div></div>", unsafe_allow_html=True)
        with tc4:
            if current_role == 'admin':
                st.markdown(f"<div class='topbar-box'><div class='tb-lbl'>👑 ระดับสิทธิ์: {current_role.upper()}</div><div class='tb-sub text-green'>🌟 เข้าถึงได้ทุกสาขา (Full Access)</div></div>", unsafe_allow_html=True)
            else:
                user_all_branches = st.session_state.get('allowed_branches', [])
                if len(user_all_branches) > 1:
                    extra_b_names = [k.split(" ")[1] for k, v in branch_dict.items() if str(v) in user_all_branches]
                    b_str = ", ".join(extra_b_names)
                    st.markdown(f"<div class='topbar-box'><div class='tb-lbl'>👑 ระดับสิทธิ์: {current_role.upper()}</div><div class='tb-sub text-blue'>📍 เข้าถึงได้: {b_str}</div></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='topbar-box'><div class='tb-lbl'>👑 ระดับสิทธิ์</div><div class='tb-val'>{current_role.upper()}</div></div>", unsafe_allow_html=True)
        
        with tc5:
            st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
            if st.button("🔑 เปลี่ยนรหัสผ่าน", use_container_width=True): change_password_dialog()
        with tc6:
            st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
            if st.button("🚪 ออกจากระบบ", use_container_width=True): perform_logout(); st.rerun()