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
# 🎯 1. ตั้งค่าหน้าเว็บ Streamlit
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Woodwork Engineering Records System",
    page_icon="🪵",
    layout="wide",
    initial_sidebar_state="expanded"
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
        st.markdown("""<style>header {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;} .main .block-container { padding-top: 3.5rem !important; padding-bottom: 2rem !important; max-width: 950px !important; margin: auto; } div[data-testid="stHorizontalBlock"] { border-radius: 28px; box-shadow: 0 20px 45px rgba(0, 0, 0, 0.15); overflow: hidden; } div[data-testid="stHorizontalBlock"] > div:first-child { background: radial-gradient(circle at top right, #1d68d8 0%, #0d47a1 60%, #082d69 100%) !important; border-radius: 28px 0 0 28px !important; padding: 45px 35px 35px 35px !important; color: #FFFFFF !important; display: flex !important; flex-direction: column !important; justify-content: center !important; } div[data-testid="stHorizontalBlock"] > div:last-child { background: #FFFFFF !important; border-radius: 0 28px 28px 0 !important; padding: 50px 35px !important; display: flex !important; flex-direction: column !important; justify-content: center !important; align-items: center !important; text-align: center !important; } div[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; } div[data-testid="stForm"] div[data-baseweb="input"] { background-color: #FFFFFF !important; border-radius: 12px !important; border: 1px solid #CBD5E1 !important; margin-bottom: 6px !important; } div[data-testid="stForm"] div[data-baseweb="input"] input { color: #0F172A !important; } div[data-testid="stForm"] .stButton > button { background: linear-gradient(135deg, #F59E0B 0%, #EA580C 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 12px !important; padding: 10px !important; font-size: 16px !important; font-weight: 700 !important; box-shadow: 0 4px 15px rgba(234, 88, 12, 0.35) !important; margin-top: 10px !important; } div[data-testid="stHorizontalBlock"] > div:last-child .stButton > button { background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 12px !important; padding: 10px 40px !important; font-size: 16px !important; font-weight: 700 !important; box-shadow: 0 4px 15px rgba(30, 64, 175, 0.3) !important; margin-top: 15px !important; } .login-header-title { font-size: 30px; font-weight: 800; color: #FFFFFF; text-align: center; margin-bottom: 4px; } .login-header-subtitle { font-size: 13px; color: #BBDEFB; text-align: center; margin-bottom: 25px; } .newhere-header-title { font-size: 30px; font-weight: 800; color: #1E293B; margin-bottom: 12px; } .newhere-header-desc { font-size: 13.5px; color: #64748B; line-height: 1.6; margin-bottom: 25px; max-width: 280px; } @media (max-width: 768px) { div[data-testid="stHorizontalBlock"] > div:first-child { border-radius: 24px 24px 0 0 !important; } div[data-testid="stHorizontalBlock"] > div:last-child { border-radius: 0 0 24px 24px !important; } }</style>""", unsafe_allow_html=True)
        col_left, col_right = st.columns([1.15, 0.95], gap="small")
        with col_left:
            st.markdown('<div class="login-header-title">Welcome Back</div><div class="login-header-subtitle">Woodwork Engineering Records System</div>', unsafe_allow_html=True)
            with st.form("login_form", clear_on_submit=False):
                username_input = st.text_input("User Name", placeholder="👤 User Name", label_visibility="collapsed")
                password_input = st.text_input("Password", type="password", placeholder="🔒 Password", label_visibility="collapsed")
                if st.form_submit_button("Login", use_container_width=True):
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
# 🎯 4. หน้าจอหลักของระบบ
# -----------------------------------------------------------------------------
else:
    st.markdown("<style>.main .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }</style>", unsafe_allow_html=True)
    st.session_state['last_activity'] = time.time()
    st.query_params["auth_user"] = st.session_state['username']
    st.query_params["auth_time"] = str(st.session_state['last_activity'])

    with st.sidebar:
        disp_name = st.session_state.get('full_name') or st.session_state.get('username')
        disp_pos = st.session_state.get('position') or "-"
        
        st.success(f"👤 ผู้ใช้งาน: **{disp_name}**")
        st.info(f"💼 ตำแหน่ง: **{disp_pos}**")
        st.info(f"🏢 สังกัดปัจจุบัน: **{st.session_state.get('branch_name')}**")
        st.warning(f"👑 ระดับสิทธิ์: **{st.session_state.get('role_tab').upper()}**")
        
        user_all_branches = st.session_state.get('allowed_branches', [])
        if len(user_all_branches) > 1:
            extra_b_names = [k for k, v in branch_dict.items() if str(v) in user_all_branches]
            st.markdown(f"<div style='font-size:12px; color:#64748B;'>สาขาที่สามารถเข้าถึงได้:<br>• " + "<br>• ".join(extra_b_names) + "</div>", unsafe_allow_html=True)

        st.write("---")
        if st.button("🔑 เปลี่ยนรหัสผ่าน", use_container_width=True):
            change_password_dialog()
            
        if st.button("🚪 ออกจากระบบ (Logout)", use_container_width=True):
            perform_logout()
            st.rerun()

    current_role = st.session_state.get('role_tab')
    
    if current_role == 'admin':
        admin_menu = st.radio("เลือกเมนูหลัก (Admin Console):", ["⚙️ ระบบจัดการผู้ใช้และสิทธิ์", "📝 หน้าจอบันทึกข้อมูลประจำวัน (Data Entry)", "📑 รายงานรวมทุกระบบ (All Report)", "🛠️ จัดการข้อมูลอุปกรณ์ในระบบ"], horizontal=True)
        st.write("---")
        if admin_menu == "⚙️ ระบบจัดการผู้ใช้และสิทธิ์": render_admin_user_management()
        elif admin_menu == "📝 หน้าจอบันทึกข้อมูลประจำวัน (Data Entry)": render_engineering_system_tabs(st.session_state.get('branch_name'))
        elif admin_menu == "📑 รายงานรวมทุกระบบ (All Report)": render_all_reports_module(st.session_state.get('branch_name'))
        elif admin_menu == "🛠️ จัดการข้อมูลอุปกรณ์ในระบบ": render_add_new_equipment()
    
    elif current_role == 'reporter':
        reporter_menu = st.radio("เลือกเมนูหลัก:", ["📑 รายงานรวมทุกระบบ (All Report)"], horizontal=True)
        st.write("---")
        if reporter_menu == "📑 รายงานรวมทุกระบบ (All Report)": render_all_reports_module(st.session_state.get('branch_name'))
    
    else:
        report_names_map = {"1": "⚙️ รายงานสรุปเครื่องจักร & เบรกดาวน์", "2": "🚚 รายงานสรุปการใช้เชื้อเพลิงรถ", "3": "💨 รายงานสรุปแรงดันไอน้ำ บอยเลอร์", "4": "🔥 รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)"}
        allowed_tabs_list = st.session_state.get('allowed_tabs', [])
        user_tab_keys = [k for k in allowed_tabs_list if k in report_names_map]

        if current_role == 'manager': 
            report_menu_label = "📑 รายงานสรุปประจำสาขา"
            menu_choices = ["📝 บันทึกข้อมูลประจำวัน (Data Entry)", report_menu_label, "🛠️ จัดการข้อมูลอุปกรณ์ในระบบ"]
        else: 
            if len(user_tab_keys) == 1: report_menu_label = report_names_map[user_tab_keys[0]]
            else: report_menu_label = "📑 รายงานสรุปประจำบัญชี"
            menu_choices = ["📝 บันทึกข้อมูลประจำวัน (Data Entry)", report_menu_label]

        user_menu = st.radio("เลือกเมนูหลัก:", menu_choices, horizontal=True)
        st.write("---")
        if user_menu == "📝 บันทึกข้อมูลประจำวัน (Data Entry)": render_engineering_system_tabs(st.session_state.get('branch_name'))
        elif user_menu == report_menu_label: render_all_reports_module(st.session_state.get('branch_name'))
        elif user_menu == "🛠️ จัดการข้อมูลอุปกรณ์ในระบบ": render_add_new_equipment()