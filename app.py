import streamlit as st
import streamlit.components.v1 as components
import time
import os
import pandas as pd
import numpy as np
import altair as alt
from database import get_db_connection, hash_password
from tab_views import render_engineering_system_tabs
from admin import render_admin_user_management
from all_reports import render_all_reports_module
from addMachines import render_add_new_equipment

# =============================================================================
# 🚀 1. ฟังก์ชันดึงข้อมูลสาขาจาก Database
# =============================================================================
@st.cache_data(ttl=300) 
def get_branch_dict_from_db():
    b_dict = {}
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, CONVERT(branch_name USING utf8mb4) AS branch_name FROM branches WHERE is_active = 1 ORDER BY id ASC")
            for r in cur.fetchall():
                b_dict[r['branch_name']] = r['id']
    except Exception as e:
        print(f"Error fetching branches: {e}")
    finally:
        if conn:
            conn.close()
    return b_dict

# =============================================================================
# 🚀 ฟังก์ชันเสก PWA (Progressive Web App) ให้ติดตั้งลงมือถือได้
# =============================================================================
def setup_pwa():
    pwa_script = """
    <script>
        // ป้องกันการแอดโค้ดซ้ำ
        if (!window.parent.document.getElementById('pwa-manifest')) {
            // 1. สร้าง Manifest ปลอมขึ้นมา (บอกชื่อแอป สี และไอคอน)
            const manifest = {
                "name": "Woodwork Engineering Records System",
                "short_name": "Work Wood",
                "theme_color": "#D97706",
                "background_color": "#F2EFEA",
                "display": "standalone", // คำสั่งบังคับให้เปิดแบบเต็มจอ (ซ่อนแถบ URL)
                "orientation": "portrait", // ล็อคหน้าจอแนวตั้ง
                "scope": "/",
                "start_url": "/",
                "icons": [
                    {
                        "src": "https://cdn-icons-png.flaticon.com/512/3206/3206016.png", // ลิงก์รูปไอคอนแอป (เปลี่ยนได้)
                        "sizes": "192x192",
                        "type": "image/png"
                    },
                    {
                        "src": "https://cdn-icons-png.flaticon.com/512/3206/3206016.png",
                        "sizes": "512x512",
                        "type": "image/png"
                    }
                ]
            };
            
            // แปลง Manifest ให้เป็น Data URL แล้วฝังใน Header
            const manifestString = JSON.stringify(manifest);
            const manifestUrl = 'data:application/manifest+json;charset=utf-8,' + encodeURIComponent(manifestString);
            
            const link = window.parent.document.createElement('link');
            link.id = 'pwa-manifest';
            link.rel = 'manifest';
            link.href = manifestUrl;
            window.parent.document.head.appendChild(link);
            
            // 2. ตั้งค่า Meta Tags บังคับให้ iOS (iPhone/iPad) มองว่าเป็น App
            const metaTags = [
                {name: "apple-mobile-web-app-capable", content: "yes"},
                {name: "apple-mobile-web-app-status-bar-style", content: "black-translucent"},
                {name: "apple-mobile-web-app-title", content: "Work Wood"},
                {name: "theme-color", content: "#D97706"}
            ];
            
            metaTags.forEach(tag => {
                const meta = window.parent.document.createElement('meta');
                meta.name = tag.name;
                meta.content = tag.content;
                window.parent.document.head.appendChild(meta);
            });

            // 3. กำหนดไอคอนสำหรับ iOS
            const appleIcon = window.parent.document.createElement('link');
            appleIcon.rel = "apple-touch-icon";
            appleIcon.href = "https://cdn-icons-png.flaticon.com/512/3206/3206016.png";
            window.parent.document.head.appendChild(appleIcon);
        }
    </script>
    """
    # ซ่อนกล่อง html ไม่ให้แสดงบนหน้าจอ
    components.html(pwa_script, height=0, width=0)

# =============================================================================
# 🚀 2. ฟังก์ชันดึงข้อมูลจริงทำหน้า Dashboard
# =============================================================================
def get_dashboard_data(user_branch_id):
    data = {
        "active_machines": 0,
        "breakdown_count": 0,
        "fuel_usage": 0.0,
        "boiler_drop": 0,
        "fuel_chart_df": pd.DataFrame(),
        "pressure_chart_df": pd.DataFrame()
    }
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            
            cur.execute("""
                SELECT COUNT(id) AS count 
                FROM machine_trans 
                WHERE record_date = CURDATE() 
                AND branch_id = %s 
                AND status = 'active'
            """, (user_branch_id,))
            res = cur.fetchone()
            if res and res['count']: data["active_machines"] = res['count']

            cur.execute("""
                SELECT COUNT(id) AS count 
                FROM machine_trans 
                WHERE record_date = CURDATE() 
                AND breakdown_hours > 0 
                AND branch_id = %s 
                AND status = 'active'
            """, (user_branch_id,))
            res = cur.fetchone()
            if res and res['count']: data["breakdown_count"] = res['count']

            cur.execute("""
                SELECT SUM(fuel_liters) AS total 
                FROM fuel_records  
                WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
                AND record_date <= CURDATE()
                AND branch_id = %s 
            """, (user_branch_id,))
            res = cur.fetchone()
            if res and res['total']: data["fuel_usage"] = round(float(res['total']), 2)

            cur.execute("""
                SELECT SUM(total_drop) AS drops 
                FROM boiler_pressure_records  
                WHERE record_date = CURDATE()
                AND branch_id = %s 
            """, (user_branch_id,))
            res = cur.fetchone()
            if res and res['drops']: data["boiler_drop"] = int(res['drops'])

            cur.execute("""
                SELECT DATE(record_date) AS log_date, SUM(fuel_liters) AS total_liters
                FROM fuel_records  
                WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
                AND record_date <= CURDATE()
                AND branch_id = %s 
                GROUP BY DATE(record_date)
                ORDER BY DATE(record_date) ASC
            """, (user_branch_id,))
            fuel_rows = cur.fetchall()
            if fuel_rows:
                df_fuel = pd.DataFrame(fuel_rows)
                df_fuel['วันที่'] = pd.to_datetime(df_fuel['log_date']).dt.strftime('%d/%m/%Y')
                df_fuel['ปริมาณเชื้อเพลิง (ลิตร)'] = df_fuel['total_liters'].astype(float)
                df_fuel = df_fuel[['วันที่', 'ปริมาณเชื้อเพลิง (ลิตร)']].set_index('วันที่')
                data["fuel_chart_df"] = df_fuel

            cur.execute("""
                SELECT DATE(record_date) AS log_date, SUM(total_drop) AS total_drops
                FROM boiler_pressure_records 
                WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
                AND record_date <= CURDATE()
                AND branch_id = %s 
                GROUP BY DATE(record_date)
                ORDER BY DATE(record_date) ASC
            """, (user_branch_id,))
            pres_rows = cur.fetchall()
            if pres_rows:
                df_pres = pd.DataFrame(pres_rows)
                df_pres['วันที่'] = pd.to_datetime(df_pres['log_date']).dt.strftime('%d/%m/%Y')
                df_pres['จำนวนครั้งที่ตก'] = df_pres['total_drops'].astype(float) 
                df_pres = df_pres[['วันที่', 'จำนวนครั้งที่ตก']].set_index('วันที่')
                data["pressure_chart_df"] = df_pres

    except Exception as e:
        st.error(f"⚠️ พบข้อผิดพลาดในการดึงข้อมูลแสดงกราฟ: {e}")
    finally:
        if conn: conn.close()
    return data

# -----------------------------------------------------------------------------
# 🎯 3. ตั้งค่าหน้าเว็บ Streamlit
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Woodwork Engineering Records System",
    page_icon="🪵",
    layout="wide",
    initial_sidebar_state="expanded" 
)

setup_pwa()

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
# 🔐 หน้าจอ Authentication
# -----------------------------------------------------------------------------
if not st.session_state.get('logged_in'):
    if st.session_state.get('page') == 'register':
        
        position_list = ["-- กรุณาเลือกตำแหน่ง --"]
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # เปลี่ยน ORDER BY position ASC เป็น ORDER BY pos ASC
                cur.execute("SELECT DISTINCT CONVERT(position USING utf8mb4) AS pos FROM departments WHERE position IS NOT NULL AND position != '' ORDER BY pos ASC")
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
            branch_dict = get_branch_dict_from_db()
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
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/icon?family=Material+Icons');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0');
        
        header {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;} 
        .main .block-container { padding-top: 3.5rem !important; padding-bottom: 2rem !important; max-width: 950px !important; margin: auto; } 
        div[data-testid="stHorizontalBlock"] { border-radius: 28px; box-shadow: 0 20px 45px rgba(0, 0, 0, 0.15); overflow: hidden; } 
        div[data-testid="stHorizontalBlock"] > div:first-child { background: radial-gradient(circle at top right, #1d68d8 0%, #0d47a1 60%, #082d69 100%) !important; border-radius: 28px 0 0 28px !important; padding: 45px 35px 35px 35px !important; color: #FFFFFF !important; display: flex !important; flex-direction: column !important; justify-content: center !important; } 
        div[data-testid="stHorizontalBlock"] > div:last-child { background: #FFFFFF !important; border-radius: 0 28px 28px 0 !important; padding: 50px 35px !important; display: flex !important; flex-direction: column !important; justify-content: center !important; align-items: center !important; text-align: center !important; } 
        div[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; } 
        div[data-testid="stForm"] div[data-baseweb="input"] { background-color: #CCCCCC !important; border-radius: 12px !important; border: 1px solid #CBD5E1 !important; margin-bottom: 6px !important; } 
        div[data-testid="stForm"] div[data-baseweb="input"] input { color: #0F172A !important; } 
        div[data-testid="stFormSubmitButton"] > button, div[data-testid="stForm"] .stButton > button { background: linear-gradient(135deg, #F59E0B 0%, #EA580C 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 12px !important; padding: 10px !important; font-size: 16px !important; font-weight: 700 !important; box-shadow: 0 4px 15px rgba(234, 88, 12, 0.35) !important; margin-top: 10px !important; } 
        div[data-testid="stHorizontalBlock"] > div:last-child .stButton > button { background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 12px !important; padding: 10px 40px !important; font-size: 16px !important; font-weight: 700 !important; box-shadow: 0 4px 15px rgba(30, 64, 175, 0.3) !important; margin-top: 15px !important; } 
        
        [data-testid="stSidebarCollapseButton"] { display: none !important; }       
        [data-testid="collapsedControl"] { display: none !important; }

        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, span, div, label, button, input {
            font-family: 'TH Sarabun PSK', 'Sarabun', Tahoma, sans-serif !important;
        }

        /* 🌟 ป้องกันฟอนต์ไอคอนพังในหน้าล็อกอิน */
        span.material-symbols-rounded, span.material-icons, .material-symbols-rounded, .material-icons, [data-testid="stIconMaterial"], [data-testid="stTooltipIcon"] {
            font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        }

        .login-header-title { font-size: 30px; font-weight: 800; color: #FFFFFF; text-align: center; margin-bottom: 4px; } 
        .login-header-subtitle { font-size: 13px; color: #BBDEFB; text-align: center; margin-bottom: 25px; } 
        .newhere-header-title { font-size: 30px; font-weight: 800; color: #1E293B; margin-bottom: 12px; } 
        .newhere-header-desc { font-size: 15px; color: #64748B; line-height: 1.6; margin-bottom: 25px; max-width: 280px; } 
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
# 🎯 4. หน้าจอหลักของระบบ (Main Layout) 
# -----------------------------------------------------------------------------
else:
    st.session_state['last_activity'] = time.time()
    st.query_params["auth_user"] = st.session_state['username']
    st.query_params["auth_time"] = str(st.session_state['last_activity'])

    disp_name = st.session_state.get('full_name') or st.session_state.get('username')
    current_role = str(st.session_state.get('role_tab', 'user')).strip().lower()
    current_branch = st.session_state.get('branch_name', '-')
    current_branch_id = st.session_state.get('branch_id', None) 
    
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
        st.session_state['sidebar_main'] = "📊 แดชบอร์ดภาพรวม (Dashboard)"
    if 'sidebar_sub_entry' not in st.session_state:
        st.session_state['sidebar_sub_entry'] = sub_opts[0] if sub_opts else "⚙️ 1. ระบบเครื่องจักร / เบรกดาวน์"
    if 'sidebar_sub_report' not in st.session_state:
        st.session_state['sidebar_sub_report'] = rep_opts[0] if rep_opts else "⚙️ 1. รายงานสรุปเครื่องจักร / เบรกดาวน์"

    with st.sidebar:
        st.markdown(f"<h3 style='color: #333333; margin-top: 5px; margin-bottom: 25px; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;'>WORK WOOD</h3>", unsafe_allow_html=True)

        report_menu_label = "📑 รายงานรวม (All Report)"
        if current_role == 'admin':
            main_choices = ["📊 แดชบอร์ดภาพรวม (Dashboard)", "⚙️ จัดการผู้ใช้และสิทธิ์", "📝 บันทึกข้อมูลประจำวัน", report_menu_label, "🛠️ จัดการข้อมูลอุปกรณ์"]
        elif current_role == 'reporter':
            main_choices = ["📊 แดชบอร์ดภาพรวม (Dashboard)", report_menu_label]
        else:
            report_menu_label = "📑 รายงานประจำสาขา" if current_role == 'manager' else "📑 รายงานประจำบัญชี"
            main_choices = ["📊 แดชบอร์ดภาพรวม (Dashboard)", "📝 บันทึกข้อมูลประจำวัน", report_menu_label]
            if current_role == 'manager':
                main_choices.append("🛠️ จัดการข้อมูลอุปกรณ์")

        for choice in main_choices:
            is_main_active = (st.session_state['sidebar_main'] == choice)
            btn_type = "primary" if is_main_active else "secondary"
            
            if st.button(choice, key=f"sb_main_{choice}", use_container_width=True, type=btn_type):
                st.session_state['sidebar_main'] = choice
                st.rerun()
                
            if choice == "📝 บันทึกข้อมูลประจำวัน" and is_main_active and sub_opts:
                default_idx = sub_opts.index(st.session_state['sidebar_sub_entry']) if st.session_state['sidebar_sub_entry'] in sub_opts else 0
                st.radio("เมนูย่อย", sub_opts, index=default_idx, key="sidebar_sub_entry", label_visibility="collapsed")
                
            if choice == report_menu_label and is_main_active and rep_opts:
                default_idx_rep = rep_opts.index(st.session_state['sidebar_sub_report']) if st.session_state['sidebar_sub_report'] in rep_opts else 0
                st.radio("เมนูย่อยรายงาน", rep_opts, index=default_idx_rep, key="sidebar_sub_report", label_visibility="collapsed")

        st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
        st.markdown(f"<hr style='border-color: #D6D3D1; margin: 10px 0;'>", unsafe_allow_html=True)
        
        col_sb_pw, col_sb_out = st.columns(2, gap="small")
        with col_sb_pw:
            if st.button("🔑 เปลี่ยนรหัส", use_container_width=True, key="sb_btn_pw"): 
                change_password_dialog()
        with col_sb_out:
            if st.button("🚪 ออกจากระบบ", use_container_width=True, key="sb_btn_out"):
                perform_logout()
                st.rerun()

    selected_main = st.session_state['sidebar_main']
    sub_menu_entry = st.session_state.get('sidebar_sub_entry')
    sub_menu_report = st.session_state.get('sidebar_sub_report')

    # =========================================================================
    # 🌟 Dashboard View
    # =========================================================================
    if selected_main == "📊 แดชบอร์ดภาพรวม (Dashboard)":
        
        db_data = get_dashboard_data(current_branch_id)
        
        st.markdown(f"<h1 class='dash-title' style='color: #333333; font-weight: 800;'>หน้าหลัก (Dashboard)</h1>", unsafe_allow_html=True)
        
        user_position = st.session_state.get('position', '-')
        welcome_html = f"""
        <div style="background-color: #FCFBF8; border-radius: 12px; padding: 20px; margin-bottom: 25px; border: 1px solid #D6D3D1; border-left: 6px solid #D97706; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.08);">
            <h3 class='welcome-title' style="color: #D97706; margin-top: 0; font-weight: 800; margin-bottom: 8px;">😊 ยินดีต้อนรับเข้าสู่ระบบ</h3>
            <p class='welcome-desc' style="color: #666666; margin-bottom: 15px;">สวัสดีคุณ <strong style="color: #333333;">{disp_name}</strong> — เลือกงานจากเมนูด้านซ้ายหรือดูสรุปข้อมูลด้านล่างได้เลยครับ</p>
            <div class='welcome-details' style="color: #333333; line-height: 1.8;">
                <div><span style="font-weight: 600; color: #64748B;">👤 กลุ่มสิทธิ์:</span> {role_th}</div>
                <div><span style="font-weight: 600; color: #64748B;">🏢 สาขา:</span> {current_branch}</div>
                <div><span style="font-weight: 600; color: #64748B;">💼 ตำแหน่ง:</span> {user_position}</div>
                <div style="margin-top: 4px;"><span style="font-weight: 600; color: #64748B;">👑 ระดับสิทธิ์:</span> {current_access} — <strong style="color: {access_color};">{access_desc}</strong></div>
            </div>
        </div>
        """
        st.markdown(welcome_html, unsafe_allow_html=True)
        
        fuel_display = f"{db_data['fuel_usage']:,.1f}" if db_data['fuel_usage'] > 0 else "0.0"

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            with st.container(border=True):
                st.metric("⚙️ เครื่องจักรทำงาน (วันนี้)", f"{db_data['active_machines']} เครื่อง")
        with col2:
            with st.container(border=True):
                st.metric("⚠️ แจ้งซ่อม (ค้างซ่อม)", f"{db_data['breakdown_count']} รายการ")
        with col3:
            with st.container(border=True):
                st.metric("🚚 เชื้อเพลิง 7 วัน (ลิตร)", fuel_display)
        with col4:
            with st.container(border=True):
                st.metric("💨 แรงดันตก (วันนี้)", f"{db_data['boiler_drop']} ครั้ง")

        st.markdown("<br>", unsafe_allow_html=True)

        c_chart1, c_chart2 = st.columns(2)
        
        with c_chart1:
            st.markdown(f"<h4 style='color: #333333; font-size: 20px; font-weight:bold; margin-bottom: 10px;'>📉 Performance Trend: ปริมาณเชื้อเพลิง (7 วัน)</h4>", unsafe_allow_html=True)
            with st.container(border=True):
                if not db_data["fuel_chart_df"].empty:
                    df_f = db_data["fuel_chart_df"].reset_index()
                    
                    area_f = alt.Chart(df_f).mark_area(
                        interpolate='monotone', color='#6366F1', opacity=0.15
                    ).encode(
                        x=alt.X('วันที่:O', axis=alt.Axis(labelAngle=-45, grid=False, title=None)),
                        y=alt.Y('ปริมาณเชื้อเพลิง (ลิตร):Q', axis=alt.Axis(grid=True, gridColor='#E8E3DD', title=None))
                    )
                    
                    line_f = alt.Chart(df_f).mark_line(
                        interpolate='monotone', color='#6366F1', strokeWidth=3
                    ).encode(
                        x='วันที่:O', y='ปริมาณเชื้อเพลิง (ลิตร):Q'
                    )
                    
                    points_f = alt.Chart(df_f).mark_circle(
                        size=80, color='#FCFBF8', stroke='#6366F1', strokeWidth=2
                    ).encode(
                        x='วันที่:O', y='ปริมาณเชื้อเพลิง (ลิตร):Q',
                        tooltip=[alt.Tooltip('วันที่', title='วันที่'), alt.Tooltip('ปริมาณเชื้อเพลิง (ลิตร)', title='ลิตร')]
                    )
                    
                    chart_f = (area_f + line_f + points_f).configure(
                        font='"TH Sarabun PSK", Sarabun, sans-serif'
                    ).configure_view(strokeWidth=0).configure_axis(
                        domain=False, tickColor='transparent', labelColor='#666666', labelFontSize=14
                    )
                    st.altair_chart(chart_f, use_container_width=True)
                else:
                    st.info("📊 ยังไม่มีข้อมูลปริมาณเชื้อเพลิงใน 7 วันล่าสุด")
                
        with c_chart2:
            st.markdown(f"<h4 style='color: #333333; font-size: 20px; font-weight:bold; margin-bottom: 10px;'>🚀 Traffic Trend: แรงดันไอน้ำตกสะสม (7 วัน)</h4>", unsafe_allow_html=True)
            with st.container(border=True):
                if not db_data["pressure_chart_df"].empty:
                    df_p = db_data["pressure_chart_df"].reset_index()
                    
                    area_p = alt.Chart(df_p).mark_area(
                        interpolate='monotone', color='#F59E0B', opacity=0.15
                    ).encode(
                        x=alt.X('วันที่:O', axis=alt.Axis(labelAngle=-45, grid=False, title=None)),
                        y=alt.Y('จำนวนครั้งที่ตก:Q', axis=alt.Axis(grid=True, gridColor='#E8E3DD', title=None))
                    )
                    
                    line_p = alt.Chart(df_p).mark_line(
                        interpolate='monotone', color='#F59E0B', strokeWidth=3
                    ).encode(
                        x='วันที่:O', y='จำนวนครั้งที่ตก:Q'
                    )
                    
                    points_p = alt.Chart(df_p).mark_circle(
                        size=80, color='#FCFBF8', stroke='#F59E0B', strokeWidth=2
                    ).encode(
                        x='วันที่:O', y='จำนวนครั้งที่ตก:Q',
                        tooltip=[alt.Tooltip('วันที่', title='วันที่'), alt.Tooltip('จำนวนครั้งที่ตก', title='ครั้ง')]
                    )
                    
                    chart_p = (area_p + line_p + points_p).configure(
                        font='"TH Sarabun PSK", Sarabun, sans-serif'
                    ).configure_view(strokeWidth=0).configure_axis(
                        domain=False, tickColor='transparent', labelColor='#666666', labelFontSize=14
                    )
                    st.altair_chart(chart_p, use_container_width=True)
                else:
                    st.info("🔥 ยังไม่มีการบันทึกแรงดันไอน้ำตกใน 7 วันล่าสุด")

    # =========================================================================
    # 🌟 หน้าอื่นๆ
    # =========================================================================
    elif selected_main == "📝 บันทึกข้อมูลประจำวัน": 
        st.markdown('<div class="data-entry-marker" style="display:none;"></div>', unsafe_allow_html=True)
        render_engineering_system_tabs(st.session_state.get('branch_name'), sub_menu_entry)
        
    elif selected_main == "⚙️ จัดการผู้ใช้และสิทธิ์": 
        render_admin_user_management()
        
    elif selected_main == report_menu_label: 
        render_all_reports_module(st.session_state.get('branch_name'), sub_menu_report)
        
    elif selected_main == "🛠️ จัดการข้อมูลอุปกรณ์": 
        render_add_new_equipment()


    # =========================================================================
    # 🚀 🌟 CSS ท่าไม้ตาย: ย้ายมาไว้ก้นสุดของไฟล์ (ล้างโค้ดงัดตารางเก่าทิ้งแล้ว) 🌟 🚀
    # =========================================================================
    st.markdown("""
    <style>
    /* โหลดฟอนต์ตัวหนังสือ และฟอนต์ไอคอนให้ครบ */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0');

    .stAppDeployButton { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    
    /* 🌟 ระบบ Responsive สำหรับหน้าจอคอม (PC) */
    @media (min-width: 769px) {
        html body header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
        html body [data-testid="stSidebarCollapseButton"] { display: none !important; }       
        html body [data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stSidebar"] { min-width: 250px !important; max-width: 250px !important; }
        .main .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }
        div[data-testid="stMainBlockContainer"] { padding-top: 1.5rem !important; }
        .dash-title { font-size: 38px !important; margin-top: 0px !important; }
        .welcome-title { font-size: 26px !important; }
        .welcome-desc { font-size: 18px !important; }
        .welcome-details { font-size: 16px !important; }
    }

    /* 🌟 ระบบ Responsive สำหรับหน้าจอมือถือ (Mobile) - บังคับเปิดปุ่มเมนูให้ทำงานทุกหน้า Tab! */
    @media (max-width: 768px) {
        html body header[data-testid="stHeader"] { 
            display: block !important; 
            visibility: visible !important;
            background: transparent !important; 
            box-shadow: none !important; 
        }
        html body [data-testid="stSidebarCollapseButton"], 
        html body [data-testid="collapsedControl"],
        html body button[kind="header"] { 
            display: inline-flex !important; 
            visibility: visible !important;
            z-index: 99999 !important;
        }
        
        .main .block-container { padding-top: 3.5rem !important; padding-bottom: 2rem !important; }
        div[data-testid="stMainBlockContainer"] { padding-top: 3.5rem !important; }
        
        .dash-title { font-size: 28px !important; margin-top: 10px !important; }
        .welcome-title { font-size: 20px !important; }
        .welcome-desc { font-size: 15px !important; }
        .welcome-details { font-size: 14px !important; }
    }
    
    .stApp { background-color: #F2EFEA !important; color: #333333 !important; }
    [data-testid="stSidebar"] { background-color: #E8E3DD !important; border-right: 1px solid #D6D3D1 !important; }
    
    /* 🌟 บังคับฟอนต์ TH Sarabun ให้เฉพาะพวก Text ทั่วไป (หลีกเลี่ยงการโดนปุ่มเมนู) */
    html, body, h1, h2, h3, h4, h5, h6, p, label, input, div.stMarkdown, div.stMetric {
        font-family: 'TH Sarabun PSK', 'Sarabun', Tahoma, sans-serif !important;
        color: #333333 !important; 
    }
    
    /* 🌟 กฎเหล็ก: คืนชีพรูปลูกศรและไอคอน (ห้ามฟอนต์ Sarabun ไปทับไอคอนเด็ดขาด) */
    span.material-symbols-rounded, 
    span.material-icons, 
    .material-symbols-rounded, 
    .material-icons, 
    [data-testid="stIconMaterial"], 
    [data-testid="stTooltipIcon"],
    html body [data-testid="stSidebarCollapseButton"] *, 
    html body [data-testid="collapsedControl"] *, 
    html body header[data-testid="stHeader"] * {
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        color: #333333 !important;
    }
    
    div[data-baseweb="tab"][aria-selected="false"] p, div[data-baseweb="tab"][aria-selected="false"] span {
        color: #666666 !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.data-entry-marker) {
        background-color: #FCFBF8 !important;
        border: 2px solid #D97706 !important;  
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(217, 119, 6, 0.08) !important;
        padding: 5px !important;
    }

    div[data-testid="stForm"] {
        background-color: transparent !important;
        border: 1px solid #D6D3D1 !important; 
        border-radius: 10px !important;
        padding: 20px !important;
    }

    div[data-testid="stExpander"] details {
        background-color: #FCFBF8 !important;
        border: 1px solid #D6D3D1 !important; 
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    div[data-testid="stExpander"] details summary {
        background-color: #FCFBF8 !important;
        padding: 10px !important;
    }
    div[data-testid="stExpander"] details summary:hover {
        background-color: #F5F5F5 !important;
    }

    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea { background-color: #FFFFFF !important; color: #000000 !important; border-color: #D6D3D1 !important; }
    table th, table td { color: #333333 !important; border-color: #D6D3D1 !important; background-color: #F2EFEA !important; }
    div[data-baseweb="select"] > div, div[data-baseweb="select"] > div:hover { background-color: #FFFFFF !important; color: #000000 !important; border-color: #D6D3D1 !important; }
    div[data-baseweb="select"] span { color: #000000 !important; }
    div[data-baseweb="select"] svg, div[data-testid="stDateInput"] svg, div[data-testid="stTimeInput"] svg { fill: #0F172A !important; color: #0F172A !important; }
    
    div[role="dialog"], [data-testid="stDialog"], div[data-testid="stModal"] > div { background-color: #FFFFFF !important; }
    div[role="dialog"] p, div[role="dialog"] span, div[role="dialog"] label, div[role="dialog"] h1, div[role="dialog"] h2, div[role="dialog"] h3, div[role="dialog"] h4, div[role="dialog"] h5, div[role="dialog"] h6 { color: #0F172A !important; -webkit-text-fill-color: #0F172A !important; }
    div[role="dialog"] button[data-testid="baseButton-primary"] * { color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }
    div[role="dialog"] div[data-testid="stForm"] { background-color: #F8FAFC !important; border: 1px solid #CBD5E1 !important; }
    div[role="dialog"] input, div[role="dialog"] textarea, div[role="dialog"] div[data-baseweb="select"] span { background-color: transparent !important; color: #0F172A !important; }
    
    div[data-testid="stNumberInput"] button { background-color: #F8FAFC !important; border: none !important; }
    div[data-testid="stNumberInput"] button svg { fill: #0F172A !important; }
    
    [data-testid="stSidebar"] div.stButton > button { 
        background-color: #FFFFFF !important; 
        border: 1px solid #D6D3D1 !important; 
        color: #333333 !important; 
        border-radius: 8px !important; 
        padding: 10px 14px !important; 
        font-family: 'TH Sarabun PSK', 'Sarabun', Tahoma, sans-serif !important;
        font-size: 18px !important; 
        font-weight: 700 !important; 
        width: 100% !important; 
        margin-bottom: 2px !important; 
        transition: all 0.2s ease !important; 
    }
    [data-testid="stSidebar"] div.stButton > button:hover { border-color: #D97706 !important; color: #D97706 !important; }
    [data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] { 
        background-color: #D97706 !important; 
        color: #FFFFFF !important; 
        border: 1px solid #D97706 !important; 
        box-shadow: 0 4px 12px rgba(217, 119, 6, 0.25) !important; 
    }
    
    [data-testid="stSidebar"] div[data-testid="stRadio"] { border-left: 2px solid #D6D3D1 !important; margin-left: 20px !important; padding-left: 5px !important; margin-bottom: 15px !important; }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] input[type="radio"], [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] input[type="radio"] + div { display: none !important; }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label { background-color: transparent !important; padding: 8px 10px !important; margin: 0 !important; border-radius: 8px !important; cursor: pointer !important; }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label p { color: #666666 !important; font-size: 16px !important; font-weight: 500 !important; margin: 0 !important; line-height: 1.5 !important; }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:hover { background-color: #F5F5F5 !important; }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) { background-color: #FCFBF8 !important; border: 1px solid #D6D3D1 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.03) !important; }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p { color: #D97706 !important; font-weight: 700 !important; }
    
    div[data-testid="stMetric"] {
        background-color: #FCFBF8 !important;
        padding: 10px !important;
        border-radius: 8px !important;
    }
    
    /* 🌟 บังคับฟอนต์ให้ตาราง DataFrame สวยงามเข้ากับเว็บ */
    [data-testid="stDataFrame"], [data-testid="stDataFrame"] * {
        font-family: 'TH Sarabun PSK', 'Sarabun', Tahoma, sans-serif !important;
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)