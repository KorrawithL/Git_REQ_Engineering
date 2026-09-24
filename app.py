import streamlit as st
import streamlit.components.v1 as components
import time
import os
import pandas as pd
import numpy as np
import altair as alt

# 📦 นำเข้าฟังก์ชันจากไฟล์แยกที่ทำการ Refactoring ไว้
from streamlit_cookies_controller import CookieController
from home import render_dashboard
from database import get_db_connection, hash_password
from tab_views import render_engineering_system_tabs
from admin import render_admin_user_management
from all_reports import render_all_reports_module
from addMachines import render_add_new_equipment

# =============================================================================
# 🚀 1. ฟังก์ชันดึงข้อมูลสาขาจาก Database (เพิ่ม show_spinner=False ซ่อนข้อความโหลด)
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False) 
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
        if (!window.parent.document.getElementById('pwa-manifest')) {
            const manifest = {
                "name": "Woodwork Engineering Records System",
                "short_name": "Work Wood",
                "theme_color": "#D97706",
                "background_color": "#F2EFEA",
                "display": "standalone", 
                "orientation": "portrait", 
                "scope": "/",
                "start_url": "/",
                "icons": [
                    {
                        "src": "https://cdn-icons-png.flaticon.com/512/3206/3206016.png", 
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
            const manifestString = JSON.stringify(manifest);
            const manifestUrl = 'data:application/manifest+json;charset=utf-8,' + encodeURIComponent(manifestString);
            
            const link = window.parent.document.createElement('link');
            link.id = 'pwa-manifest';
            link.rel = 'manifest';
            link.href = manifestUrl;
            window.parent.document.head.appendChild(link);
            
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

            const appleIcon = window.parent.document.createElement('link');
            appleIcon.rel = "apple-touch-icon";
            appleIcon.href = "https://cdn-icons-png.flaticon.com/512/3206/3206016.png";
            window.parent.document.head.appendChild(appleIcon);
        }
    </script>
    """
    components.html(pwa_script, height=0, width=0)

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

# 🚀 🌟 วาง CSS หลักสำหรับแต่งหน้าจอ ไว้บนสุดเพื่อแก้ปัญหาหน้าจอสีขาว 🌟 🚀
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0');

.stAppDeployButton { display: none !important; }
[data-testid="stHeaderActionElements"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }

@media (min-width: 769px) {
    html body header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
    html body [data-testid="stSidebarCollapseButton"] { display: none !important; }       
    html body [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stSidebar"] { min-width: 275px !important; max-width: 275px !important; }
    .main .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }
    div[data-testid="stMainBlockContainer"] { padding-top: 1.5rem !important; }
    .dash-title { font-size: 38px !important; margin-top: 0px !important; }
    .welcome-title { font-size: 26px !important; }
    .welcome-desc { font-size: 18px !important; }
    .welcome-details { font-size: 16px !important; }
}

@media (max-width: 768px) {
    html body header[data-testid="stHeader"] { display: block !important; visibility: visible !important; background: transparent !important; box-shadow: none !important; }
    html body [data-testid="stSidebarCollapseButton"], html body [data-testid="collapsedControl"], html body button[kind="header"] { display: inline-flex !important; visibility: visible !important; z-index: 99999 !important; }
    .main .block-container { padding-top: 3.5rem !important; padding-bottom: 2rem !important; }
    div[data-testid="stMainBlockContainer"] { padding-top: 3.5rem !important; }
    .dash-title { font-size: 28px !important; margin-top: 10px !important; }
    .welcome-title { font-size: 20px !important; }
    .welcome-desc { font-size: 15px !important; }
    .welcome-details { font-size: 14px !important; }
}

.stApp { background-color: #F2EFEA !important; color: #333333 !important; }
[data-testid="stSidebar"] { background-color: #E8E3DD !important; border-right: 1px solid #D6D3D1 !important; }

html, body, h1, h2, h3, h4, h5, h6, p, label, input, div.stMarkdown, div.stMetric { font-family: 'TH Sarabun PSK', 'Sarabun', Tahoma, sans-serif !important; color: #333333 !important; }

span.material-symbols-rounded, span.material-icons, .material-symbols-rounded, .material-icons, [data-testid="stIconMaterial"], [data-testid="stTooltipIcon"], html body [data-testid="stSidebarCollapseButton"] *, html body [data-testid="collapsedControl"] *, html body header[data-testid="stHeader"] * { font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important; color: #333333 !important; }

div[data-baseweb="tab"][aria-selected="false"] p, div[data-baseweb="tab"][aria-selected="false"] span { color: #666666 !important; }

div[data-testid="stVerticalBlockBorderWrapper"]:has(.data-entry-marker) { background-color: #FCFBF8 !important; border: 2px solid #D97706 !important; border-radius: 12px !important; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.08) !important; padding: 5px !important; }

div[data-testid="stForm"] { background-color: transparent !important; border: 1px solid #D6D3D1 !important; border-radius: 10px !important; padding: 20px !important; }
div[data-testid="stExpander"] details { background-color: #FCFBF8 !important; border: 1px solid #D6D3D1 !important; border-radius: 10px !important; overflow: hidden !important; }
div[data-testid="stExpander"] details summary { background-color: #FCFBF8 !important; padding: 10px !important; }
div[data-testid="stExpander"] details summary:hover { background-color: #F5F5F5 !important; }

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

[data-testid="stSidebar"] div.stButton > button { background-color: #FFFFFF !important; border: 1px solid #D6D3D1 !important; color: #333333 !important; border-radius: 8px !important; padding: 10px 14px !important; font-family: 'TH Sarabun PSK', 'Sarabun', Tahoma, sans-serif !important; font-size: 18px !important; font-weight: 700 !important; width: 100% !important; margin-bottom: 2px !important; transition: all 0.2s ease !important; }
[data-testid="stSidebar"] div.stButton > button:hover { border-color: #D97706 !important; color: #D97706 !important; }
[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] { background-color: #D97706 !important; color: #FFFFFF !important; border: 1px solid #D97706 !important; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.25) !important; }

[data-testid="stSidebar"] div[data-testid="stRadio"] { border-left: 2px solid #D6D3D1 !important; margin-left: 20px !important; padding-left: 5px !important; margin-bottom: 15px !important; }
[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] input[type="radio"], [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] input[type="radio"] + div { display: none !important; }
[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label { background-color: transparent !important; padding: 8px 10px !important; margin: 0 !important; border-radius: 8px !important; cursor: pointer !important; }
[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label p { color: #666666 !important; font-size: 16px !important; font-weight: 500 !important; margin: 0 !important; line-height: 1.5 !important; }
[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:hover { background-color: #F5F5F5 !important; }
[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) { background-color: #FCFBF8 !important; border: 1px solid #D6D3D1 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.03) !important; }
[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p { color: #D97706 !important; font-weight: 700 !important; }

div[data-testid="stMetric"] { background-color: #FCFBF8 !important; padding: 10px !important; border-radius: 8px !important; }
[data-testid="stDataFrame"], [data-testid="stDataFrame"] * { font-family: 'TH Sarabun PSK', 'Sarabun', Tahoma, sans-serif !important; font-size: 14px !important; }

/* 🌟 บังคับให้ปุ่มใน Sidebar ตัดคำขึ้นบรรทัดใหม่ได้ 🌟 */
[data-testid="stSidebar"] div.stButton > button {
    height: auto !important; /* ปล่อยให้ปุ่มยืดความสูงตามข้อความ */
    min-height: 45px !important;
    padding: 8px 2px !important; /* ลดขอบซ้ายขวาลงนิดนึง */
}
[data-testid="stSidebar"] div.stButton > button div,
[data-testid="stSidebar"] div.stButton > button p {
    white-space: normal !important; /* 👈 คำสั่งหัวใจหลักที่สั่งให้ขึ้นบรรทัดใหม่ */
    word-wrap: break-word !important;
    line-height: 1.2 !important;
    text-align: center !important;
    font-size: 16px !important;
}

/* 🌟 1. บังคับตัวหนังสือบนปุ่ม (Primary) ให้เป็นสีขาว "เฉพาะในหน้าต่าง Popup" เท่านั้น */
    div[role="dialog"] div.stButton button[data-testid="baseButton-primary"] p,
    div[role="dialog"] div.stButton button[data-testid="baseButton-primary"] span,
    div[role="dialog"] div.stButton button[kind="primary"] p,
    div[role="dialog"] div.stButton button[kind="primary"] span {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    /* 🌟 2. คืนชีพปุ่มเมนูแถบซ้าย (Sidebar) ที่กำลังใช้งานอยู่ ให้พื้นหลังเป็นสีส้ม และตัวหนังสือสีขาวเด่นๆ */
    [data-testid="stSidebar"] div.stButton button[data-testid="baseButton-primary"],
    [data-testid="stSidebar"] div.stButton button[kind="primary"] { 
        background-color: #D97706 !important; 
        border: 1px solid #D97706 !important; 
        box-shadow: 0 4px 12px rgba(217, 119, 6, 0.25) !important; 
    }
    [data-testid="stSidebar"] div.stButton button[data-testid="baseButton-primary"] p,
    [data-testid="stSidebar"] div.stButton button[data-testid="baseButton-primary"] span,
    [data-testid="stSidebar"] div.stButton button[kind="primary"] p,
    [data-testid="stSidebar"] div.stButton button[kind="primary"] span {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-weight: 700 !important;
    } /* 👈👈 เติมปีกกาปิดที่หายไปตรงนี้ครับ !!! */

    /* 🌟 แก้ไขปุ่มในหน้าจอหลัก & ปุ่ม Download ไม่ให้ตัดคำเป็นจุดไข่ปลา (วงสีแดง) 🌟 */
    div[data-testid="stDownloadButton"] button,
    div[data-testid="stDownloadButton"] button p,
    div[data-testid="stDownloadButton"] button span,
    div[data-testid="stMain"] div.stButton > button,
    div[data-testid="stMain"] div.stDownloadButton > button {
        white-space: normal !important;
        word-wrap: break-word !important;
        height: auto !important;
        
        line-height: 1.3 !important;
        width: 100% !important;
    }

    /* 🌟 แก้ไขเมนูตัวเลือก (Radio) ใน Sidebar ให้ขึ้นบรรทัดใหม่ได้ (วงสีน้ำเงิน) 🌟 */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label {
        height: auto !important;
        min-height: 45px !important;
        align-items: flex-start !important; /* ดันปุ่มวงกลมให้อยู่บรรทัดบนสุดเสมอเวลาข้อความยาว */
        padding-top: 8px !important;
        padding-bottom: 8px !important;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label p,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label span {
        white-space: normal !important;
        word-wrap: break-word !important;
        line-height: 1.4 !important;
        width: 100% !important;
        overflow: visible !important;
        text-overflow: clip !important;
        display: inline-block !important;
    }

</style>
""", unsafe_allow_html=True)

# =========================================================================
# 🍪 เกราะป้องกันระบบคุกกี้ (Cookie Safe Methods) 🍪
# ดักจับ Error ทุกชนิด ป้องกันโค้ดหยุดทำงานกลางคัน
# =========================================================================
controller = CookieController()
SESSION_TIMEOUT_SECONDS = 1800  

def safe_set_cookie(name, value, max_age):
    try:
        # บังคับสร้าง Dictionary จำลองถ้าเบราว์เซอร์ยังโหลดไม่เสร็จ
        if getattr(controller, '_CookieController__cookies', None) is None:
            controller._CookieController__cookies = {}
        controller.set(name, value, max_age=max_age)
    except Exception:
        pass

def safe_remove_cookie(name):
    try:
        if getattr(controller, '_CookieController__cookies', None) is None:
            controller._CookieController__cookies = {}
        controller.remove(name)
    except Exception:
        pass

def safe_get_cookie(name):
    try:
        return controller.get(name)
    except Exception:
        return None

# =========================================================================
# 🌟 ท่าไม้ตาย: ดักการกด F5 เพื่อรอรับคุกกี้ ป้องกันหน้า Login กระพริบ 🌟
# =========================================================================
if 'app_init' not in st.session_state:
    st.session_state['app_init'] = True
    st.markdown("""
        <div style='text-align:center; padding-top:25vh; font-family:"Sarabun", sans-serif;'>
            <h1 style='color:#D97706; font-weight:800; font-size:45px;'> WORK WOOD</h1>
            <p style='color:#64748B; font-size:18px;'>กำลังเชื่อมต่อและตรวจสอบข้อมูลการเข้าสู่ระบบ...</p>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(2.5) # สั่งหยุดรอ 2.5 วินาที
    st.rerun() 
# =========================================================================

def perform_logout(message=None):
    # 🌟 1. ล้างข้อมูลในหน่วยความจำทั้งหมดให้สะอาดกริ๊บ
    st.session_state.clear()
    
    # 🌟 2. ปักธงป้องกัน "คุกกี้ผีหลอก"
    st.session_state['just_logged_out'] = True
    
    # 🌟 3. สั่งทำลายคุกกี้
    safe_remove_cookie("auth_user")
    
    if message:
        st.warning(message)
        
    # 🌟 4. หน่วงเวลาให้เบราว์เซอร์ลบคุกกี้ให้เสร็จจริงๆ (ครึ่งวินาที)
    time.sleep(0.5)

def restore_session_from_cookie():
    # 🌟 ดักจับคุกกี้ผีหลอก: ถ้าเพิ่งกดออกจากระบบ ให้ข้ามการอ่านคุกกี้ไปเลย!
    if st.session_state.get('just_logged_out'):
        st.session_state['just_logged_out'] = False # ปลดธงทิ้ง
        return

    if not st.session_state.get('logged_in'):
        saved_user = safe_get_cookie("auth_user") # ดึงคุกกี้อย่างปลอดภัย
        if saved_user:
            try:
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

# 🍪 เรียกใช้งานการดึงคุกกี้เมื่อเปิดหน้าเว็บ
restore_session_from_cookie()
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
            
    # 🔥 1. หน้าจอคั่นเวลาหลังจากกด Login ถูกต้อง (แยกออกมา ไม่ทำให้จอบัคขาว) 🔥
    elif st.session_state.get('show_login_success'):
        st.markdown("""
            <div style='text-align:center; padding-top:25vh; font-family:"Sarabun", sans-serif;'>
                <h1 style='color:#1D4ED8; font-weight:800; font-size:45px;'>✅ เข้าสู่ระบบสำเร็จ!</h1>
                <p style='color:#64748B; font-size:18px;'>กำลังจัดเตรียมหน้าแดชบอร์ดของคุณ...</p>
            </div>
        """, unsafe_allow_html=True)
        
        # ปรับสถานะเป็นเข้าสู่ระบบจริง แล้วสั่งวาร์ปไป Dashboard
        st.session_state['logged_in'] = True
        del st.session_state['show_login_success']
        time.sleep(0.7)
        st.rerun()

    else:
        # 🌟 2. หน้า Login ปกติ (ไม่ต้องใช้ Placeholder ครอบแล้ว) 🌟
        st.markdown("""<style>
        /* ล็อคเป้าหมายให้กล่องสีน้ำเงิน-ขาว ทำงานเฉพาะในพื้นที่จอหลัก (stMain) */
        section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] { border-radius: 28px; box-shadow: 0 20px 45px rgba(0, 0, 0, 0.15); overflow: hidden; } 
        section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] > div:first-child { background: radial-gradient(circle at top right, #1d68d8 0%, #0d47a1 60%, #082d69 100%) !important; border-radius: 28px 0 0 28px !important; padding: 45px 35px 35px 35px !important; color: #FFFFFF !important; display: flex !important; flex-direction: column !important; justify-content: center !important; } 
        section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] > div:last-child { background: #FFFFFF !important; border-radius: 0 28px 28px 0 !important; padding: 50px 35px !important; display: flex !important; flex-direction: column !important; justify-content: center !important; align-items: center !important; text-align: center !important; } 
        
        div[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; } 
        div[data-testid="stForm"] div[data-baseweb="input"] { background-color: #CCCCCC !important; border-radius: 12px !important; border: 1px solid #CBD5E1 !important; margin-bottom: 6px !important; } 
        div[data-testid="stForm"] div[data-baseweb="input"] input { color: #0F172A !important; } 
        div[data-testid="stFormSubmitButton"] > button, div[data-testid="stForm"] .stButton > button { background: linear-gradient(135deg, #F59E0B 0%, #EA580C 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 12px !important; padding: 10px !important; font-size: 16px !important; font-weight: 700 !important; box-shadow: 0 4px 15px rgba(234, 88, 12, 0.35) !important; margin-top: 10px !important; } 
        section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] > div:last-child .stButton > button { background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 12px !important; padding: 10px 40px !important; font-size: 16px !important; font-weight: 700 !important; box-shadow: 0 4px 15px rgba(30, 64, 175, 0.3) !important; margin-top: 15px !important; } 
        
        .login-header-title { font-size: 30px; font-weight: 800; color: #FFFFFF; text-align: center; margin-bottom: 4px; } 
        .login-header-subtitle { font-size: 13px; color: #BBDEFB; text-align: center; margin-bottom: 25px; } 
        .newhere-header-title { font-size: 30px; font-weight: 800; color: #1E293B; margin-bottom: 12px; } 
        .newhere-header-desc { font-size: 15px; color: #64748B; line-height: 1.6; margin-bottom: 25px; max-width: 280px; } 
        @media (max-width: 768px) { section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] > div:first-child { border-radius: 24px 24px 0 0 !important; } section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] > div:last-child { border-radius: 0 0 24px 24px !important; } }
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
                                    safe_set_cookie("auth_user", user['username'], SESSION_TIMEOUT_SECONDS)
                                    
                                    now_time = time.time()
                                    for k in ['user_id', 'username', 'full_name', 'position', 'branch_id', 'branch_name']: 
                                        st.session_state[k] = user[k]
                                    st.session_state['role_tab'] = str(user['Role_tab']).strip().lower()
                                    
                                    raw_tabs = user.get('allowed_tabs', '') or ''
                                    st.session_state['allowed_tabs'] = [x.strip() for x in str(raw_tabs).split(',') if x.strip()]
                                    
                                    allowed_b_list = [str(user['branch_id'])] + [str(b['branch_id']) for b in extra_branches]
                                    st.session_state['allowed_branches'] = list(set(allowed_b_list)) 
                                    st.session_state['last_activity'] = now_time
                                    
                                    # 🔥 3. เซ็ตสถานะให้ข้ามไปโชว์หน้า Loading แทน แล้วรีรันทันที 🔥
                                    st.session_state['show_login_success'] = True
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

    # 🌟 ท่าไม้ตายป้องกัน F5 เด้งหลุด: ย้ำการฝังคุกกี้เข้าเบราว์เซอร์อย่างเด็ดขาด!
    if st.session_state.get('username'):
        safe_set_cookie("auth_user", st.session_state.get('username'), SESSION_TIMEOUT_SECONDS)

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

    # =========================================================================
    # 🌟 เตรียมรายการเมนูหลัก 
    # =========================================================================
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

    # =========================================================================
    # 🌟 ฟื้นความจำ: ดึงชื่อ Tab ล่าสุดจากคุกกี้ ป้องกันการเด้งกลับหน้า Dashboard
    # =========================================================================
    saved_main_tab = safe_get_cookie("last_main_tab")
    
    if 'sidebar_main' not in st.session_state:
        if saved_main_tab and saved_main_tab in main_choices:
            st.session_state['sidebar_main'] = saved_main_tab
        else:
            st.session_state['sidebar_main'] = main_choices[0] # ค่าเริ่มต้น
            # 🌟 ย้ำการฝังคุกกี้หน้าแรกด้วย เผื่อกรณีเพิ่งเข้าสู่ระบบครั้งแรก
            safe_set_cookie("last_main_tab", main_choices[0], SESSION_TIMEOUT_SECONDS) 
            
    if 'sidebar_sub_entry' not in st.session_state:
        st.session_state['sidebar_sub_entry'] = sub_opts[0] if sub_opts else "⚙️ 1. ระบบเครื่องจักร / เบรกดาวน์"
    if 'sidebar_sub_report' not in st.session_state:
        st.session_state['sidebar_sub_report'] = rep_opts[0] if rep_opts else "⚙️ 1. รายงานสรุปเครื่องจักร / เบรกดาวน์"
    with st.sidebar:
        st.markdown(f"<h3 style='color: #333333; margin-top: 5px; margin-bottom: 25px; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;'>WORK WOOD</h3>", unsafe_allow_html=True)

        for choice in main_choices:
            is_main_active = (st.session_state['sidebar_main'] == choice)
            btn_type = "primary" if is_main_active else "secondary"
            
            if st.button(choice, key=f"sb_main_{choice}", use_container_width=True, type=btn_type):
                st.session_state['sidebar_main'] = choice
                # 🌟 ท่าไม้ตาย: สั่งจำชื่อหน้าเว็บนี้ฝังลงในเบราว์เซอร์ทันที!
                safe_set_cookie("last_main_tab", choice, SESSION_TIMEOUT_SECONDS)
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
    # 🌟 ท่าไม้ตายล้างกราฟค้าง (Force UI Flush) 🌟
    # =========================================================================
    ui_flusher = st.empty()
    with ui_flusher:
        st.markdown("<div style='height: 1px;'></div>", unsafe_allow_html=True)
    time.sleep(0.01) 
    ui_flusher.empty() 
    # =========================================================================

    # 🌟 สร้าง Key เพื่อเช็คว่า "เพิ่งมีการเปลี่ยนหน้า Tab" หรือไม่
    current_view_state = f"{selected_main}_{sub_menu_entry}_{sub_menu_report}"

    # =========================================================================
    # 🌟 พื้นที่แสดงผลหลัก (พร้อมระบบล้างจอก่อนโหลด)
    # =========================================================================
    main_view = st.empty()

    # 🎯 1. เช็คว่าเพิ่งเปลี่ยนหน้ามาใหม่ใช่ไหม? 
    if st.session_state.get('last_view_state') != current_view_state:
        
        # 🔥 สั่งเคลียร์พื้นที่ทั้งหมดทิ้งทันที! (ลบกราฟและตารางเก่าทิ้งไม่ให้หลงเหลือ)
        main_view.empty()
        
        # วาดหน้า Loading Screen
        with main_view.container():
            st.markdown("""
                <div style='text-align:center; padding-top:25vh; font-family:"Sarabun", sans-serif; height: 100vh;'>
                    <h1 style='color:#D97706; font-weight:800; font-size:35px;'>กำลังเตรียมข้อมูล...</h1>
                    <p style='color:#64748B; font-size:18px;'>กรุณารอสักครู่ ระบบกำลังดึงข้อมูลสำหรับหน้านี้</p>
                    <div style="margin: 20px auto; width: 45px; height: 45px; border: 5px solid #E8E3DD; border-top: 5px solid #D97706; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                    <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
                </div>
            """, unsafe_allow_html=True)
            
        # 🪄 ย้ายท่าไม้ตายล้างกราฟค้าง มาแอบทำงานตอนกำลังโหลด
        ui_flusher = st.empty()
        with ui_flusher:
            st.markdown("<div style='height: 1px;'></div>", unsafe_allow_html=True)
        time.sleep(0.05) 
        ui_flusher.empty()

        # หน่วงเวลาอีก 1.45 วินาที (รวมกับ 0.05 ด้านบนจะเป็น 1.5 วินาทีพอดี)
        time.sleep(1.45)  
        
        # บันทึกว่าโหลดเสร็จแล้ว และสั่งรีเฟรช 1 รอบ
        st.session_state['last_view_state'] = current_view_state
        st.rerun()

    # 🎯 2. ถ้าโหลดเสร็จแล้ว (รอจนครบ 1.5 วิ) ให้แสดงเนื้อหาจริง
    else:
        with main_view.container():
            if selected_main == "📊 แดชบอร์ดภาพรวม (Dashboard)":
                user_position = st.session_state.get('position', '-')
                render_dashboard(
                    current_branch_id, disp_name, role_th, current_branch, 
                    user_position, current_access, access_color, access_desc
                )

            elif selected_main == "📝 บันทึกข้อมูลประจำวัน": 
                st.markdown('<div class="data-entry-marker" style="display:none;"></div>', unsafe_allow_html=True)
                render_engineering_system_tabs(st.session_state.get('branch_name'), sub_menu_entry)
                
            elif selected_main == "⚙️ จัดการผู้ใช้และสิทธิ์": 
                render_admin_user_management()
                
            elif selected_main == report_menu_label: 
                render_all_reports_module(st.session_state.get('branch_name'), sub_menu_report)
                
            elif selected_main == "🛠️ จัดการข้อมูลอุปกรณ์": 
                render_add_new_equipment()