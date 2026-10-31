import time
import streamlit as st
from database import get_db_connection, log_activity

# =============================================================================
# 📌 1. ค่าคงที่และค่าเริ่มต้นของเกณฑ์มาตรฐาน (Constants & Defaults)
# =============================================================================
DEFAULT_STD_VALUES = {
    "std_fuel_price_per_cubft": 12.0,
    "std_steam_per_hr": 12.0,
    "std_fuel_price_per_steam_ton": 240.0,
    "std_avg_pressure": 3.0,
    "std_fuel_kg_per_cubft": 15.0,
    "std_steam_multiplier": 0.1875,
    "std_fuel_kg_per_ton_b1": 280.0,
    "std_fuel_kg_per_ton_b2": 280.0,
    "std_fuel_kg_per_ton_b1_2": 300.0,
}

STD_SETTINGS_CSS = """
<style>
header[data-testid="stHeader"] { display: none !important; }
#header { visibility: hidden !important; }
#MainMenu { visibility: hidden !important; }
.block-container { padding-top: 1rem !important; margin-top: -20px !important; }

div[data-testid="stForm"] div[data-testid="stNumberInput"] label[data-testid="stWidgetLabel"] svg,
div[data-testid="stNumberInput"] label[data-testid="stWidgetLabel"] svg,
label[data-testid="stWidgetLabel"] div[data-testid="stTooltipIcon"] svg,
div[data-testid="stTooltipHoverTarget"] svg,
div[data-testid="stTooltipIcon"] svg {
    fill: none !important;
    stroke: #64748B !important;
    color: #64748B !important;
    background: transparent !important;
}

div[data-testid="stForm"] div[data-testid="stNumberInput"] label[data-testid="stWidgetLabel"] svg *,
div[data-testid="stNumberInput"] label[data-testid="stWidgetLabel"] svg *,
label[data-testid="stWidgetLabel"] div[data-testid="stTooltipIcon"] svg *,
div[data-testid="stTooltipHoverTarget"] svg *,
div[data-testid="stTooltipIcon"] svg * {
    fill: none !important;
    stroke: #64748B !important;
    stroke-width: 2px !important;
}
</style>
"""


# =============================================================================
# 🚀 2. ฟังก์ชันจัดการฐานข้อมูล (Database Helpers)
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_branch_list():
    """ดึงข้อมูลสาขาที่เปิดใช้งานอยู่จากฐานข้อมูล"""
    branches = {}
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, CONVERT(branch_name USING utf8mb4) AS b_name FROM branches WHERE is_active = 1 ORDER BY id ASC")
            for r in cur.fetchall():
                if r.get("b_name"):
                    branches[r["b_name"].strip()] = r["id"]
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลสาขา: {e}")
    finally:
        if conn:
            conn.close()
    return branches


def get_std_by_branch(branch_id):
    """ดึงค่าเกณฑ์มาตรฐาน (STD Settings) ของสาขาที่ระบุ หากไม่มีจะใช้ค่าเริ่มต้น"""
    std_vals = DEFAULT_STD_VALUES.copy()
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM std_settings WHERE branch_id = %s LIMIT 1", (branch_id,))
            res = cur.fetchone()
            if res:
                for k in std_vals:
                    if res.get(k) is not None:
                        std_vals[k] = float(res[k])
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงค่ามาตรฐาน: {e}")
    finally:
        if conn:
            conn.close()
    return std_vals


def save_std_settings(branch_id, branch_name, std_payload):
    """บันทึกหรืออัปเดตค่าเกณฑ์มาตรฐานของสาขาลงฐานข้อมูล"""
    conn = None
    try:
        conn = get_db_connection()
        cols = list(std_payload.keys())
        vals = [std_payload[c] for c in cols]

        with conn.cursor() as cur:
            cur.execute("SELECT id FROM std_settings WHERE branch_id = %s", (branch_id,))
            exists = cur.fetchone()

            if exists:
                set_clause = ", ".join([f"{c} = %s" for c in cols])
                sql = f"UPDATE std_settings SET {set_clause} WHERE branch_id = %s"
                cur.execute(sql, tuple(vals + [branch_id]))
            else:
                col_names = ", ".join(["branch_id"] + cols)
                placeholders = ", ".join(["%s"] * (len(cols) + 1))
                sql = f"INSERT INTO std_settings ({col_names}) VALUES ({placeholders})"
                cur.execute(sql, tuple([branch_id] + vals))

            conn.commit()

        log_activity(
            st.session_state.user_id,
            st.session_state.username,
            "UPDATE",
            "STD Settings",
            f"ปรับเกณฑ์มาตรฐานสาขา '{branch_name}' (ID: {branch_id})"
        )
        st.cache_data.clear()
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        if conn:
            conn.close()


# =============================================================================
# 🎯 3. ฟังก์ชันหลักสำหรับแสดงหน้าจอ STD Settings
# =============================================================================
def render_std_settings_module():
    st.markdown(STD_SETTINGS_CSS, unsafe_allow_html=True)

    st.header(
        "⚙️ ระบบกำหนดเกณฑ์มาตรฐาน (STD Settings)",
        help=(
            "💡 คำแนะนำการใช้งาน: ค่าเกณฑ์มาตรฐานเหล่านี้จะถูกนำไปใช้คำนวณใน รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (Tab 4) "
            "เพื่อเปรียบเทียบผลผลิตจริงกับเป้าหมาย (KPI) และประเมินประสิทธิภาพต้นทุนการเผาไหม้ประจำวัน"
        )
    )
    st.caption("กำหนดค่าเกณฑ์มาตรฐานการใช้เชื้อเพลิงและไอน้ำของบอยเลอร์แยกตามรายสาขา")

    branch_dict = get_branch_list()
    if not branch_dict:
        st.warning("ไม่พบข้อมูลสาขาในระบบ")
        return

    raw_role = st.session_state.get("role_tab") or st.session_state.get("role") or "user"
    current_role = str(raw_role).strip().lower()
    user_allowed_branches = st.session_state.get("allowed_branches", [str(st.session_state.get("branch_id"))])

    if current_role == "admin":
        available_branch_names = list(branch_dict.keys())
    else:
        available_branch_names = [k for k, v in branch_dict.items() if str(v) in user_allowed_branches] or list(branch_dict.keys())

    selected_branch_name = st.selectbox(
        "🏢 เลือกสาขาที่ต้องการตั้งค่าเกณฑ์มาตรฐาน:",
        options=available_branch_names,
        key="std_sel_branch",
        help="เกณฑ์มาตรฐานจะถูกแยกบันทึกตามแต่ละสาขา การปรับค่าจะมีผลต่อการคำนวณเปรียบเทียบในหน้ารายงาน (Tab 4) ทันที"
    )
    selected_branch_id = branch_dict[selected_branch_name]
    current_std = get_std_by_branch(selected_branch_id)

    with st.form("std_settings_form"):
        st.markdown(f"### 📋 เกณฑ์มาตรฐานประจำ: **{selected_branch_name}**")

        st.markdown("#### 1. เกณฑ์ด้านราคาและต้นทุนเชื้อเพลิง")
        c1, c2 = st.columns(2)
        with c1:
            inp_price_cubft = st.number_input(
                "💰 ค่าเชื้อเพลิงมาตรฐาน (บาท/ลบ.ฟ.):",
                value=float(current_std["std_fuel_price_per_cubft"]),
                step=0.5,
                format="%.2f",
                key=f"std_p_cubft_{selected_branch_id}",
                help="เป้าหมายต้นทุนค่าเชื้อเพลิงต่อปริมาตรไม้อบ 1 ลูกบาศก์ฟุต ใช้เปรียบเทียบกับต้นทุนจริงในรายงาน"
            )
        with c2:
            inp_price_steam_ton = st.number_input(
                "💸 ค่าเชื้อเพลิงมาตรฐาน (บาท/ตันไอน้ำ):",
                value=float(current_std["std_fuel_price_per_steam_ton"]),
                step=10.0,
                format="%.2f",
                key=f"std_p_ton_{selected_branch_id}",
                help="เป้าหมายต้นทุนเชื้อเพลิงที่ใช้ในการผลิตไอน้ำ 1 ตัน ใช้ประเมินความคุ้มค่าของการเผาไหม้"
            )

        st.markdown("#### 2. เกณฑ์ด้านการผลิตไอน้ำและแรงดัน")
        c3, c4, c5 = st.columns(3)
        with c3:
            inp_steam_hr = st.number_input(
                "💨 ผลิตไอน้ำมาตรฐาน (ตัน/ชม.):",
                value=float(current_std["std_steam_per_hr"]),
                step=0.5,
                format="%.2f",
                key=f"std_stm_hr_{selected_branch_id}",
                help="เป้าหมายกำลังการผลิตไอน้ำเฉลี่ยต่อชั่วโมงของระบบบอยเลอร์"
            )
        with c4:
            inp_steam_mul = st.number_input(
                "✖️ ตัวคูณผลิตไอน้ำ (Ton/Hr per Oven):",
                value=float(current_std["std_steam_multiplier"]),
                step=0.0001,
                format="%.4f",
                key=f"std_stm_mul_{selected_branch_id}",
                help="ตัวคูณคำนวณไอน้ำมาตรฐานตามจำนวนเตาอบ เช่น 0.1875 ตัน/ชม. ต่อ 1 เตาอบที่เปิดใช้งาน"
            )
        with c5:
            inp_avg_press = st.number_input(
                "⏲️ แรงดันปลายทางเฉลี่ยมาตรฐาน (Bar):",
                value=float(current_std["std_avg_pressure"]),
                step=0.5,
                format="%.2f",
                key=f"std_avg_p_{selected_branch_id}",
                help="ค่าแรงดันไอน้ำปลายทางเป้าหมายที่ต้องจ่ายเข้าเตาอบ (หากต่ำกว่าเกณฑ์นี้จะถูกนับเป็นช่วงแรงดันตก)"
            )

        st.markdown("#### 3. เกณฑ์ประสิทธิภาพการใช้เชื้อเพลิง (กก./หน่วย)")
        c6, c7 = st.columns(2)
        with c6:
            inp_kg_cubft = st.number_input(
                "🔥 เชื้อเพลิงใช้มาตรฐาน (กก./ลบ.ฟ.):",
                value=float(current_std["std_fuel_kg_per_cubft"]),
                step=1.0,
                format="%.2f",
                key=f"std_kg_cubft_{selected_branch_id}",
                help="เกณฑ์น้ำหนักเชื้อเพลิงชีวมวลที่ควรใช้ต่อเนื้อไม้อบ 1 ลูกบาศก์ฟุต"
            )
        with c7:
            inp_kg_ton_b1_2 = st.number_input(
                "🔥 เชื้อเพลิงมาตรฐาน บอยเลอร์ 1+2 (กก./ตันไอน้ำ):",
                value=float(current_std["std_fuel_kg_per_ton_b1_2"]),
                step=5.0,
                format="%.2f",
                key=f"std_kg_b1_2_{selected_branch_id}",
                help="เกณฑ์ปริมาณเชื้อเพลิงต่อการผลิตไอน้ำ 1 ตัน ในกรณีที่เปิดใช้งานบอยเลอร์พร้อมกันทั้ง 2 ตัว"
            )

        c8, c9 = st.columns(2)
        with c8:
            inp_kg_ton_b1 = st.number_input(
                "🔥 เชื้อเพลิงมาตรฐาน บอยเลอร์ 1 (กก./ตันไอน้ำ):",
                value=float(current_std["std_fuel_kg_per_ton_b1"]),
                step=5.0,
                format="%.2f",
                key=f"std_kg_b1_{selected_branch_id}",
                help="เกณฑ์ปริมาณเชื้อเพลิงต่อการผลิตไอน้ำ 1 ตัน ในกรณีที่เดินเครื่องเฉพาะบอยเลอร์ 1 เพียงตัวเดียว"
            )
        with c9:
            inp_kg_ton_b2 = st.number_input(
                "🔥 เชื้อเพลิงมาตรฐาน บอยเลอร์ 2 (กก./ตันไอน้ำ):",
                value=float(current_std["std_fuel_kg_per_ton_b2"]),
                step=5.0,
                format="%.2f",
                key=f"std_kg_b2_{selected_branch_id}",
                help="เกณฑ์ปริมาณเชื้อเพลิงต่อการผลิตไอน้ำ 1 ตัน ในกรณีที่เดินเครื่องเฉพาะบอยเลอร์ 2 เพียงตัวเดียว"
            )

        st.write("")
        submit_btn = st.form_submit_button("💾 บันทึกเกณฑ์มาตรฐานสาขานี้", type="primary", use_container_width=True)

    if submit_btn:
        std_payload = {
            "std_fuel_price_per_cubft": inp_price_cubft,
            "std_steam_per_hr": inp_steam_hr,
            "std_fuel_price_per_steam_ton": inp_price_steam_ton,
            "std_avg_pressure": inp_avg_press,
            "std_fuel_kg_per_cubft": inp_kg_cubft,
            "std_steam_multiplier": inp_steam_mul,
            "std_fuel_kg_per_ton_b1": inp_kg_ton_b1,
            "std_fuel_kg_per_ton_b2": inp_kg_ton_b2,
            "std_fuel_kg_per_ton_b1_2": inp_kg_ton_b1_2,
        }
        ok, err_msg = save_std_settings(selected_branch_id, selected_branch_name, std_payload)
        if ok:
            st.success(f"✅ บันทึกเกณฑ์มาตรฐานของสาขา {selected_branch_name} เรียบร้อยแล้ว!")
            time.sleep(1.2)
            st.rerun()
        else:
            st.error(f"❌ เกิดข้อผิดพลาดในการบันทึก: {err_msg}")