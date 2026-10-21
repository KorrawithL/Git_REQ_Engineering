import streamlit as st
import time
from database import get_db_connection, log_activity

# =============================================================================
# 🏢 ฟังก์ชันดึงข้อมูลสาขาที่มีในระบบ
# =============================================================================
def get_branch_list():
    branches = {}
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, CONVERT(branch_name USING utf8mb4) AS b_name FROM branches WHERE is_active = 1 ORDER BY id ASC")
            for r in cur.fetchall():
                if r['b_name']:
                    branches[r['b_name'].strip()] = r['id']
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลสาขา: {e}")
    finally:
        if conn:
            conn.close()
    return branches

# =============================================================================
# 📥 ฟังก์ชันดึงค่า STD Settings ของสาขาที่เลือก
# =============================================================================
def get_std_by_branch(branch_id):
    default_vals = {
        'std_fuel_price_per_cubft': 12.0,
        'std_steam_per_hr': 12.0,
        'std_fuel_price_per_steam_ton': 240.0,
        'std_avg_pressure': 3.0,
        'std_fuel_kg_per_cubft': 15.0,
        'std_steam_multiplier': 0.1875,
        'std_fuel_kg_per_ton_b1': 280.0,
        'std_fuel_kg_per_ton_b2': 280.0,
        'std_fuel_kg_per_ton_b1_2': 300.0
    }
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM std_settings WHERE branch_id = %s LIMIT 1", (branch_id,))
            res = cur.fetchone()
            if res:
                for k in default_vals.keys():
                    if k in res and res[k] is not None:
                        default_vals[k] = float(res[k])
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงค่ามาตรฐาน: {e}")
    finally:
        if conn:
            conn.close()
    return default_vals

# =============================================================================
# 🎯 ฟังก์ชันหลักสำหรับ Render หน้าจอ STD Settings
# =============================================================================
def render_std_settings_module():
    st.markdown("""
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        .block-container { padding-top: 1rem !important; }
        </style>
    """, unsafe_allow_html=True)

    st.header("⚙️ ระบบกำหนดเกณฑ์มาตรฐาน (STD Settings)")
    st.caption("กำหนดค่าเกณฑ์มาตรฐานการใช้เชื้อเพลิงและไอน้ำของบอยเลอร์แยกตามรายสาขา")

    branch_dict = get_branch_list()
    if not branch_dict:
        st.warning("ไม่พบข้อมูลสาขาในระบบ")
        return

    raw_role = st.session_state.get('role_tab') or st.session_state.get('role') or 'user'
    current_role = str(raw_role).strip().lower()
    user_allowed_branches = st.session_state.get('allowed_branches', [str(st.session_state.get('branch_id'))])

    # กรองตัวเลือกสาขาตามสิทธิ์ผู้ใช้งาน
    if current_role == "admin":
        available_branch_names = list(branch_dict.keys())
    else:
        available_branch_names = [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]
        if not available_branch_names:
            available_branch_names = list(branch_dict.keys())

    selected_branch_name = st.selectbox(
        "🏢 เลือกสาขาที่ต้องการตั้งค่าเกณฑ์มาตรฐาน:", 
        options=available_branch_names,
        key="std_sel_branch"
    )
    selected_branch_id = branch_dict[selected_branch_name]

    # ดึงค่าปัจจุบันของสาขานั้น
    current_std = get_std_by_branch(selected_branch_id)

    with st.form("std_settings_form"):
        st.markdown(f"### 📋 เกณฑ์มาตรฐานประจำ: **{selected_branch_name}**")
        
        st.markdown("#### 1. เกณฑ์ด้านราคาและต้นทุนเชื้อเพลิง")
        c1, c2 = st.columns(2)
        with c1:
            inp_price_cubft = st.number_input("💰 ค่าเชื้อเพลิงมาตรฐาน (บาท/ลบ.ฟ.):", value=float(current_std['std_fuel_price_per_cubft']), step=0.5, format="%.2f", key=f"std_p_cubft_{selected_branch_id}")
        with c2:
            inp_price_steam_ton = st.number_input("💸 ค่าเชื้อเพลิงมาตรฐาน (บาท/ตันไอน้ำ):", value=float(current_std['std_fuel_price_per_steam_ton']), step=10.0, format="%.2f", key=f"std_p_ton_{selected_branch_id}")

        st.markdown("#### 2. เกณฑ์ด้านการผลิตไอน้ำและแรงดัน")
        c3, c4, c5 = st.columns(3)
        with c3:
            inp_steam_hr = st.number_input("💨 ผลิตไอน้ำมาตรฐาน (ตัน/ชม.):", value=float(current_std['std_steam_per_hr']), step=0.5, format="%.2f", key=f"std_stm_hr_{selected_branch_id}")
        with c4:
            inp_steam_mul = st.number_input("✖️ ตัวคูณผลิตไอน้ำ (Ton/Hr per Oven):", value=float(current_std['std_steam_multiplier']), step=0.0001, format="%.4f", key=f"std_stm_mul_{selected_branch_id}")
        with c5:
            inp_avg_press = st.number_input("⏲️ แรงดันปลายทางเฉลี่ยมาตรฐาน (Bar):", value=float(current_std['std_avg_pressure']), step=0.5, format="%.2f", key=f"std_avg_p_{selected_branch_id}")

        st.markdown("#### 3. เกณฑ์ประสิทธิภาพการใช้เชื้อเพลิง (กก./หน่วย)")
        c6, c7 = st.columns(2)
        with c6:
            inp_kg_cubft = st.number_input("🔥 เชื้อเพลิงใช้มาตรฐาน (กก./ลบ.ฟ.):", value=float(current_std['std_fuel_kg_per_cubft']), step=1.0, format="%.2f", key=f"std_kg_cubft_{selected_branch_id}")
        with c7:
            inp_kg_ton_b1_2 = st.number_input("🔥 เชื้อเพลิงมาตรฐาน บอยเลอร์ 1+2 (กก./ตันไอน้ำ):", value=float(current_std['std_fuel_kg_per_ton_b1_2']), step=5.0, format="%.2f", key=f"std_kg_b1_2_{selected_branch_id}")

        c8, c9 = st.columns(2)
        with c8:
            inp_kg_ton_b1 = st.number_input("🔥 เชื้อเพลิงมาตรฐาน บอยเลอร์ 1 (กก./ตันไอน้ำ):", value=float(current_std['std_fuel_kg_per_ton_b1']), step=5.0, format="%.2f", key=f"std_kg_b1_{selected_branch_id}")
        with c9:
            inp_kg_ton_b2 = st.number_input("🔥 เชื้อเพลิงมาตรฐาน บอยเลอร์ 2 (กก./ตันไอน้ำ):", value=float(current_std['std_fuel_kg_per_ton_b2']), step=5.0, format="%.2f", key=f"std_kg_b2_{selected_branch_id}")

        st.write("")
        submit_btn = st.form_submit_button("💾 บันทึกเกณฑ์มาตรฐานสาขานี้", type="primary", use_container_width=True)

    if submit_btn:
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # ตรวจสอบว่ามีข้อมูลของสาขานี้อยู่แล้วหรือไม่
                cur.execute("SELECT id FROM std_settings WHERE branch_id = %s", (selected_branch_id,))
                row = cur.fetchone()

                if row:
                    sql = """
                        UPDATE std_settings SET
                            std_fuel_price_per_cubft = %s,
                            std_steam_per_hr = %s,
                            std_fuel_price_per_steam_ton = %s,
                            std_avg_pressure = %s,
                            std_fuel_kg_per_cubft = %s,
                            std_steam_multiplier = %s,
                            std_fuel_kg_per_ton_b1 = %s,
                            std_fuel_kg_per_ton_b2 = %s,
                            std_fuel_kg_per_ton_b1_2 = %s
                        WHERE branch_id = %s
                    """
                    cur.execute(sql, (
                        inp_price_cubft, inp_steam_hr, inp_price_steam_ton, inp_avg_press,
                        inp_kg_cubft, inp_steam_mul, inp_kg_ton_b1, inp_kg_ton_b2, inp_kg_ton_b1_2,
                        selected_branch_id
                    ))
                else:
                    sql = """
                        INSERT INTO std_settings (
                            branch_id, std_fuel_price_per_cubft, std_steam_per_hr,
                            std_fuel_price_per_steam_ton, std_avg_pressure, std_fuel_kg_per_cubft,
                            std_steam_multiplier, std_fuel_kg_per_ton_b1, std_fuel_kg_per_ton_b2,
                            std_fuel_kg_per_ton_b1_2
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cur.execute(sql, (
                        selected_branch_id, inp_price_cubft, inp_steam_hr, inp_price_steam_ton,
                        inp_avg_press, inp_kg_cubft, inp_steam_mul, inp_kg_ton_b1, inp_kg_ton_b2,
                        inp_kg_ton_b1_2
                    ))

                conn.commit()

                # บันทึกกิจกรรมลง Audit Log
                log_activity(
                    st.session_state.user_id,
                    st.session_state.username,
                    "UPDATE",
                    "STD Settings",
                    f"ปรับเกณฑ์มาตรฐานสาขา '{selected_branch_name}' (ID: {selected_branch_id})"
                )

            conn.close()
            st.cache_data.clear() # เคลียร์แคชเพื่อให้รายงานคำนวณใหม่ทันที
            st.success(f"✅ บันทึกเกณฑ์มาตรฐานของสาขา {selected_branch_name} เรียบร้อยแล้ว!")
            time.sleep(1.2)
            st.rerun()
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการบันทึก: {e}")