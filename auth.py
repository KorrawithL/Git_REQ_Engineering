import time
import streamlit as st
from database import get_db_connection, hash_password, log_activity

# =============================================================================
# 🎨 1. ค่าคงที่และสไตล์ CSS สำหรับหน้าลงทะเบียน
# =============================================================================
DEFAULT_POS_LABEL = "-- กรุณาเลือกตำแหน่ง --"
EMPTY_BRANCH_LABEL = "-- ไม่พบข้อมูลสาขา --"

REGISTER_CSS = """
<style>
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #D97706 0%, #B45309 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    box-shadow: 0 4px 10px rgba(217, 119, 6, 0.3) !important;
    transition: all 0.3s ease !important;
    width: 100% !important;
}
div[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(217, 119, 6, 0.4) !important;
}

.back-btn-container div.stButton > button {
    background-color: #F1F5F9 !important;
    color: #475569 !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    padding: 10px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    width: 100% !important;
}
.back-btn-container div.stButton > button:hover {
    background-color: #E2E8F0 !important;
    color: #1E293B !important;
    border-color: #94A3B8 !important;
}
</style>
"""


# =============================================================================
# 🚀 2. ฟังก์ชันจัดการข้อมูลและเชื่อมต่อ Database (Data Access Helpers)
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_register_master_data():
    """ดึงรายการตำแหน่งงานและสาขาที่เปิดใช้งานสำหรับหน้าสมัครสมาชิก"""
    position_list = [DEFAULT_POS_LABEL]
    active_branches = {}
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT CONVERT(`position` USING utf8mb4) AS pos 
                FROM departments 
                WHERE `position` IS NOT NULL AND TRIM(`position`) != '' 
                ORDER BY pos ASC
            """)
            for r in cur.fetchall():
                val = r.get("pos")
                if val and val.strip():
                    position_list.append(val.strip())

            cur.execute("""
                SELECT id, CONVERT(branch_name USING utf8mb4) AS branch_name 
                FROM branches 
                WHERE is_active = 1 
                ORDER BY id ASC
            """)
            for r in cur.fetchall():
                if r.get("branch_name"):
                    active_branches[r["branch_name"]] = r["id"]
    except Exception as e:
        st.error(f"🚨 ระบบไม่สามารถเชื่อมต่อฐานข้อมูลได้: {e}")
    finally:
        if conn:
            conn.close()

    if not active_branches:
        active_branches[EMPTY_BRANCH_LABEL] = None

    return position_list, active_branches


def authenticate_user(username, password):
    """ตรวจสอบข้อมูลการเข้าสู่ระบบและดึงสิทธิ์สาขาเพิ่มเติม"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT u.*, b.branch_name 
                FROM system_users u 
                LEFT JOIN branches b ON u.branch_id = b.id
                WHERE CONVERT(u.username USING utf8mb4) = CONVERT(%s USING utf8mb4) 
                  AND u.password_hash = %s 
                  AND u.status = 'active'
            """
            cursor.execute(sql, (username.strip(), hash_password(password)))
            user_data = cursor.fetchone()

            if not user_data:
                return None, []

            cursor.execute("SELECT branch_id FROM user_branches WHERE user_id = %s", (user_data["user_id"],))
            extra_branches = cursor.fetchall()
            return user_data, extra_branches
    finally:
        if conn:
            conn.close()


def register_new_user(username, password, fullname, position, email, phone, branch_id):
    """บันทึกบัญชีผู้ใช้งานใหม่ลงฐานข้อมูล (คืนค่า (success: bool, result_or_msg))"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM system_users WHERE CONVERT(username USING utf8mb4) = CONVERT(%s USING utf8mb4)",
                (username,)
            )
            if cursor.fetchone():
                return False, "❌ User ID นี้มีผู้ใช้งานในระบบแล้ว"

            sql = """
                INSERT INTO system_users 
                (username, password_hash, full_name, position, email, phone_number, branch_id, Role_tab, allowed_tabs, status) 
                VALUES (CONVERT(%s USING utf8mb4), %s, CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), 
                        CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), %s, 'user', '', 'active')
            """
            cursor.execute(sql, (
                username, hash_password(password), fullname,
                position, email, phone, branch_id
            ))
            conn.commit()
            return True, (cursor.lastrowid or 0)
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการลงทะเบียน: {e}"
    finally:
        if conn:
            conn.close()


# =============================================================================
# 🔐 3. ฟังก์ชันแสดงผลหน้าเข้าสู่ระบบและหน้าลงทะเบียน (UI Views)
# =============================================================================
def render_login_page():
    st.title("🔐 Woodwork System - เข้าสู่ระบบ")
    st.write("---")

    with st.form("login_form"):
        log_user = st.text_input("User ID (Username)")
        log_pass = st.text_input("Password", type="password")
        btn_log = st.form_submit_button("🔓 ล็อกอินเข้าสู่ระบบ")

        if btn_log:
            try:
                user_data, extra_branches = authenticate_user(log_user, log_pass)
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_data["user_id"]
                    st.session_state.username = user_data["username"]
                    st.session_state.full_name = user_data.get("full_name") or user_data["username"]
                    st.session_state.position = user_data.get("position") or "-"
                    st.session_state.branch_id = user_data["branch_id"]
                    st.session_state.branch_name = user_data["branch_name"]
                    st.session_state.role_tab = str(user_data.get("Role_tab", "user")).strip().lower()

                    raw_tabs = user_data.get("allowed_tabs", "")
                    st.session_state.allowed_tabs = [t.strip() for t in raw_tabs.split(",") if t.strip()] if raw_tabs else []

                    allowed_b_list = [str(user_data["branch_id"])] + [str(b["branch_id"]) for b in extra_branches]
                    st.session_state.allowed_branches = list(set(allowed_b_list))

                    log_activity(user_data["user_id"], user_data["username"], "LOGIN", "Auth: System", "เข้าสู่ระบบสำเร็จ")
                    st.success("ล็อกอินสำเร็จ! กำลังนำเข้าสู่ระบบ...")
                    st.rerun()
                else:
                    st.error("User ID หรือ Password ไม่ถูกต้อง โปรดตรวจสอบอีกครั้ง")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

    st.write("ยังไม่มีบัญชีผู้ใช้งานใช่หรือไม่?")
    if st.button("📝 สมัครสมาชิกใหม่ (Register) ที่นี่"):
        st.session_state.page = "register"
        st.rerun()


def render_register_page():
    position_list, active_branches = get_register_master_data()

    st.markdown(REGISTER_CSS, unsafe_allow_html=True)
    st.markdown("<h1 style='margin: 0; margin-top: -5px; color: #333333; font-weight: 800;'>WOODWORK</h1>", unsafe_allow_html=True)
    st.caption("ระบบลงทะเบียนบัญชีผู้ใช้งานใหม่ (Woodwork Engineering Records System)")
    st.info(
        "💡 **คำแนะนำสำหรับผู้สมัครใหม่:** กรุณากรอกข้อมูลที่มีเครื่องหมาย `*` ให้ครบถ้วน "
        "หลังจากลงทะเบียนสำเร็จ กรุณาแจ้ง **ผู้ดูแลระบบ (Admin)** เพื่อเปิดสิทธิ์การเข้าถึงแท็บงานประจำตำแหน่งของคุณ"
    )

    with st.form("register_form", clear_on_submit=True):
        st.markdown("#### 👤 ข้อมูลบัญชีผู้ใช้งาน")
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            reg_user = st.text_input(
                "กำหนด User ID (Username) *",
                placeholder="เช่น somchai_wg",
                help="ชื่อบัญชีสำหรับใช้ล็อกอินเข้าสู่ระบบ (แนะนำให้ใช้ภาษาอังกฤษหรือตัวเลขโดยไม่เว้นวรรค)"
            )
        with col_u2:
            reg_pass = st.text_input(
                "กำหนด Password *",
                type="password",
                placeholder="ตั้งรหัสผ่าน...",
                help="รหัสผ่านสำหรับเข้าสู่ระบบ (ควรมีความยาวอย่างน้อย 4 ตัวอักษร)"
            )

        st.markdown("#### 📋 ข้อมูลส่วนตัว")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            reg_fullname = st.text_input("ชื่อ-นามสกุล *", placeholder="ระบุชื่อและนามสกุลจริง...")
        with col_p2:
            reg_position = st.selectbox("ตำแหน่งงาน (Position) *", options=position_list)

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            reg_email = st.text_input("E-mail (ถ้ามี)")
        with col_c2:
            reg_phone = st.text_input("เบอร์โทรศัพท์ (ถ้ามี)")

        st.markdown("#### 🏢 ข้อมูลสังกัด")
        reg_branch_label = st.selectbox(
            "เลือกสาขาประจำตัวของคุณ *",
            options=list(active_branches.keys()),
            help="เลือกสาขาหลักที่คุณปฏิบัติงานประจำ"
        )
        reg_branch_id = active_branches.get(reg_branch_label)

        st.write("")
        _, col_btn_reg2, _ = st.columns([1, 2, 1])
        with col_btn_reg2:
            btn_reg = st.form_submit_button("💥 ยืนยันและลงทะเบียนบัญชี", use_container_width=True)

        if btn_reg:
            clean_user = reg_user.strip()
            clean_fullname = reg_fullname.strip()

            if not clean_user or not reg_pass or not clean_fullname or reg_position == DEFAULT_POS_LABEL or reg_branch_id is None:
                st.error("⚠️ กรุณากรอกข้อมูลที่มีเครื่องหมาย * ให้ครบถ้วน และเลือกตำแหน่ง/สาขาให้ถูกต้อง")
            else:
                ok, res = register_new_user(
                    clean_user, reg_pass, clean_fullname,
                    reg_position, reg_email.strip(), reg_phone.strip(), reg_branch_id
                )
                if not ok:
                    st.error(res)
                else:
                    log_activity(
                        res, clean_user, "INSERT", "Auth: Register",
                        f"ผู้ใช้งานลงทะเบียนบัญชีใหม่: {clean_user} (ตำแหน่ง: {reg_position}, สาขา: {reg_branch_label})"
                    )
                    st.success("🎉 ลงทะเบียนสำเร็จ! กำลังพากลับไปหน้าเข้าสู่ระบบ...")
                    st.toast("สมัครสมาชิกสำเร็จ!", icon="🎉")

                    st.session_state.page = "login"
                    time.sleep(1.5)
                    st.rerun()

    st.write("")
    st.markdown('<div class="back-btn-container"></div>', unsafe_allow_html=True)
    _, col_btn_log2, _ = st.columns([1, 2, 1])
    with col_btn_log2:
        if st.button("⬅️ กลับไปหน้าเข้าสู่ระบบ (Login)", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()