import time
import pandas as pd
import streamlit as st
from database import get_db_connection, log_activity

# =============================================================================
# 📌 1. ฟังก์ชันช่วยเหลือสำหรับจัดรูปแบบข้อมูล (Formatting Helpers)
# =============================================================================
def clean_date_str(val):
    """แปลงวันที่เป็นรูปแบบ DD/MM/YYYY สำหรับแสดงในตาราง"""
    if pd.isna(val) or val is None or str(val).strip().lower() in ["none", "nat", ""]:
        return "-"
    try:
        return pd.to_datetime(val).strftime("%d/%m/%Y")
    except Exception:
        return str(val)

def clean_currency_str(val):
    """แปลงตัวเลขมูลค่าเป็นรูปแบบทศนิยม 2 ตำแหน่งพร้อมลูกน้ำ"""
    if pd.isna(val) or val is None:
        return "-"
    try:
        f_val = float(val)
        return f"{f_val:,.2f}" if f_val > 0 else "-"
    except Exception:
        return str(val)

def clean_text_str(val):
    """จัดการค่าว่างหรือ None ให้แสดงเป็นเครื่องหมาย -"""
    if pd.isna(val) or val is None or not str(val).strip() or str(val).strip().lower() == "none":
        return "-"
    return str(val).strip()

def safe_to_date(val):
    """แปลงค่าวันที่จากฐานข้อมูลให้เป็น date object สำหรับใส่ใน st.date_input"""
    if pd.isna(val) or val is None or str(val).strip().lower() in ["none", "nat", "", "-"]:
        return None
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


# =============================================================================
# 🚀 2. ฟังก์ชันดึงข้อมูล Master Data และรายการอุปกรณ์จาก Database
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
                b_dict[r["branch_name"]] = r["id"]
    except Exception as e:
        print(f"Error fetching branches: {e}")
    finally:
        if conn:
            conn.close()
    return b_dict

@st.cache_data(ttl=300, show_spinner=False)
def get_engine_types_from_db():
    engine_type_dict = {}
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, CONVERT(type_name USING utf8mb4) AS type_name FROM engine_types ORDER BY id ASC")
            for r in cur.fetchall():
                engine_type_dict[r["type_name"]] = r["id"]
    except Exception as e:
        print(f"Error fetching engine types: {e}")
    finally:
        if conn:
            conn.close()
    return engine_type_dict

def fetch_equipment_data(current_role, user_allowed_branches):
    """ดึงรายการเครื่องจักรและรถยนต์ทั้งหมดตามสิทธิ์ของผู้ใช้งาน"""
    combined_data = []
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            base_query = """
                SELECT m.id, CONVERT(m.machine_name USING utf8mb4) AS name_code, 
                       m.engine_type_id, CONVERT(et.type_name USING utf8mb4) AS type_name, 
                       m.branch_id, CONVERT(b.branch_name USING utf8mb4) AS branch_name,
                       m.created_at, m.expiration_date, CONVERT(m.remark USING utf8mb4) AS remark, 
                       m.is_active, m.machine_type,
                       m.machine_value, CONVERT(m.vendor USING utf8mb4) AS vendor,
                       m.purchase_date, m.usage_start_date
                FROM machines_set m 
                LEFT JOIN engine_types et ON m.engine_type_id = et.id 
                LEFT JOIN branches b ON m.branch_id = b.id 
            """
            if current_role == "admin":
                cur.execute(base_query + "ORDER BY m.id DESC")
            else:
                placeholders = ", ".join(["%s"] * len(user_allowed_branches))
                cur.execute(base_query + f"WHERE m.branch_id IN ({placeholders}) ORDER BY m.id DESC", tuple(user_allowed_branches))

            for r in cur.fetchall():
                is_mach = (r.get("machine_type") == "machine")
                combined_data.append({
                    "หมวดหมู่": "⚙️ เครื่องจักร" if is_mach else "🚚 รถยนต์/รถยก",
                    "ID": r["id"],
                    "ชื่อ/รหัส": r["name_code"],
                    "ชนิดรถ": "-" if is_mach else (r.get("type_name") or "ไม่ระบุ"),
                    "branch_id": r["branch_id"],
                    "สาขา": r["branch_name"],
                    "วันที่ซื้อ": r.get("purchase_date"),
                    "วันที่เริ่มใช้งาน": r.get("usage_start_date"),
                    "วันหมดอายุ": r["expiration_date"],
                    "หมายเหตุ": r["remark"],
                    "มูลค่าของอุปกรณ์ (บาท)": r.get("machine_value"),
                    "ผู้ขาย/vendor": r.get("vendor"),
                    "สถานะ": "▶️ ใช้งาน" if r.get("is_active") == 1 else "🔴 ระงับ",
                    "is_active": r.get("is_active", 1),
                    "type_id": r.get("engine_type_id")
                })
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลได้: {e}")
    finally:
        if conn:
            conn.close()
    return combined_data


# =============================================================================
# 🎨 3. ฟังก์ชันแสดงการ์ดสรุปตัวเลขภาพรวม (KPI Card)
# =============================================================================
def render_equipment_kpi_card(df):
    total_items = len(df)
    total_machines = len(df[df["หมวดหมู่"] == "⚙️ เครื่องจักร"])
    total_vehicles = len(df[df["หมวดหมู่"] == "🚚 รถยนต์/รถยก"])
    total_active = len(df[df["is_active"] == 1])
    total_disabled = len(df[df["is_active"] == 0])

    pct_mach = (total_machines / total_items * 100) if total_items > 0 else 0.0
    pct_veh = (total_vehicles / total_items * 100) if total_items > 0 else 0.0

    kpi_html = f"""
<div style="background-color: #FCFBF8; padding: 22px 25px; border-radius: 12px; margin-bottom: 25px; border: 1px solid #D6D3D1; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.05); font-family: 'Sarabun', sans-serif;">
    <div style="color: #0F172A; font-size: 18px; font-weight: bold; margin-bottom: 18px;">⚡ สถานะความพร้อมและหมวดหมู่อุปกรณ์ (ข้อมูลปัจจุบัน)</div>
    <div style="display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between;">
        <div style="flex: 1; min-width: 140px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">📦 อุปกรณ์ทั้งหมด</div>
            <div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{total_items:,} <span style="font-size: 16px; font-weight: normal; color: #666666;">รายการ</span></div>
        </div>
        <div style="flex: 1; min-width: 140px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">⚙️ เครื่องจักร</div>
            <div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{total_machines:,} <span style="font-size: 16px; font-weight: normal; color: #666666;">เครื่อง</span></div>
            <span style="background-color: #F1F5F9; color: #475569; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">{pct_mach:.1f}% ของระบบ</span>
        </div>
        <div style="flex: 1; min-width: 140px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">🚚 รถยนต์ / รถยก</div>
            <div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{total_vehicles:,} <span style="font-size: 16px; font-weight: normal; color: #666666;">คัน</span></div>
            <span style="background-color: #FFFBEB; color: #D97706; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">{pct_veh:.1f}% ของระบบ</span>
        </div>
        <div style="flex: 1; min-width: 140px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">▶️ ใช้งานปกติ (Active)</div>
            <div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{total_active:,} <span style="font-size: 16px; font-weight: normal; color: #666666;">รายการ</span></div>
        </div>
        <div style="flex: 1; min-width: 140px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">🔴 ระงับการใช้งาน</div>
            <div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{total_disabled:,} <span style="font-size: 16px; font-weight: normal; color: #666666;">รายการ</span></div>
        </div>
    </div>
</div>
"""
    st.markdown(kpi_html, unsafe_allow_html=True)


# =============================================================================
# 🛠️ 4. ฟังก์ชันหลักสำหรับแสดงผลหน้าจัดการอุปกรณ์
# =============================================================================
def render_add_new_equipment():
    st.markdown("""
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        #header { visibility: hidden !important; }
        #MainMenu { visibility: hidden !important; }
        .block-container { padding-top: 1rem !important; margin-top: -20px !important; }
        </style>
    """, unsafe_allow_html=True)

    branch_dict = get_branch_dict_from_db()
    engine_type_dict = get_engine_types_from_db()

    current_role = str(st.session_state.get("role_tab", "user")).strip().lower()
    user_allowed_branches = st.session_state.get("allowed_branches", [str(st.session_state.get("branch_id"))])

    available_branches_dict = branch_dict if current_role == "admin" else {k: v for k, v in branch_dict.items() if str(v) in user_allowed_branches}
    branch_options = list(available_branches_dict.keys())
    type_options = list(engine_type_dict.keys()) if engine_type_dict else ["-- ไม่มีข้อมูลประเภทรถ --"]

    st.header("🛠️ จัดการข้อมูลอุปกรณ์ในระบบ")
    st.caption("หน้าจอเพิ่ม แก้ไข และระงับการใช้งานอุปกรณ์ (เพื่อรักษาประวัติข้อมูลเดิม ระบบจะใช้การเปลี่ยนสถานะแทนการลบข้อมูลจริง)")

    # -------------------------------------------------------------------------
    # ➕ ส่วนที่ 1: เพิ่มอุปกรณ์ใหม่เข้าสู่ระบบ
    # -------------------------------------------------------------------------
    with st.expander("➕ เพิ่มอุปกรณ์ใหม่เข้าสู่ระบบ", expanded=False):
        equip_options = ["-- กรุณาเลือกประเภทอุปกรณ์ --", "⚙️ เครื่องจักร (Machine)", "🚚 รถยนต์ / รถยก (Vehicle)"]
        equip_type_add = st.selectbox(
            "เลือกประเภทอุปกรณ์ที่ต้องการเพิ่ม:",
            options=equip_options,
            help="• เครื่องจักร: อุปกรณ์ที่ไม่ต้องระบุชนิดรถ (เช่น โต๊ะเลื่อย (≤ 0.15%), ตาชั่งใหญ่(≤ 0.20%))\n• รถยนต์/รถยก: ต้องระบุยี่ห้อ/ชนิดรถยนต์ร่วมด้วยเสมอ (เช่น TOYOTA, TCK)"
        )

        is_not_selected = (equip_type_add == "-- กรุณาเลือกประเภทอุปกรณ์ --")
        is_machine_add = (equip_type_add == "⚙️ เครื่องจักร (Machine)")

        with st.form("add_equipment_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                lbl_name = "ชื่อ/รหัสอุปกรณ์ *" if is_not_selected else ("ชื่อเครื่องจักร / รหัสทะเบียนรถ *" if is_machine_add else "รหัสงาน / ทะเบียนรถใหม่ *")
                new_name_code = st.text_input(lbl_name, placeholder="ระบุชื่อหรือรหัสอุปกรณ์...", disabled=is_not_selected)
                new_exp_date = st.date_input("วันหมดอายุการใช้งาน", value=None, disabled=is_not_selected)
            with col2:
                new_engine_type = st.selectbox("ชนิดของรถยนต์ *", options=type_options, disabled=(is_not_selected or is_machine_add))
                new_branch = st.selectbox("สาขาประจำการ *", options=branch_options, disabled=is_not_selected)

            col3, col4 = st.columns(2)
            with col3:
                new_value = st.number_input("มูลค่าของอุปกรณ์ (บาท)", min_value=0.0, step=100000.0, value=0.0, disabled=is_not_selected)
            with col4:
                new_vendor = st.text_input("ผู้ขาย / Vendor", placeholder="ระบุชื่อบริษัท หรือผู้จัดจำหน่าย", disabled=is_not_selected)

            col5, col6 = st.columns(2)
            with col5:
                new_purchase_date = st.date_input("วันที่ซื้อ", value=None, disabled=is_not_selected)
            with col6:
                new_usage_date = st.date_input("วันที่เริ่มใช้งาน", value=None, disabled=is_not_selected)

            new_remark = st.text_input("หมายเหตุ", placeholder="ระบุหมายเหตุเพิ่มเติม (ถ้ามี)", disabled=is_not_selected)
            submit_add = st.form_submit_button("➕ บันทึกข้อมูลเข้าสู่ระบบ (สถานะ Active)", disabled=is_not_selected, use_container_width=True)

            if submit_add:
                if is_not_selected:
                    st.error("⚠️ กรุณาเลือกประเภทอุปกรณ์ก่อนทำการบันทึก")
                elif not new_name_code.strip():
                    st.error("⚠️ กรุณาระบุชื่อ/รหัสอุปกรณ์ให้ชัดเจน")
                elif not is_machine_add and new_engine_type == "-- ไม่มีข้อมูลประเภทรถ --":
                    st.error("⚠️ กรุณาเลือกชนิดของรถให้ครบถ้วน")
                else:
                    conn = None
                    try:
                        b_id = available_branches_dict[new_branch]
                        t_id = None if is_machine_add else engine_type_dict[new_engine_type]
                        m_type = "machine" if is_machine_add else "engine"
                        log_msg = f"เพิ่ม{'เครื่องจักร' if is_machine_add else 'รถ'}ใหม่: {new_name_code}"

                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            sql_add = """
                                INSERT INTO machines_set 
                                (machine_name, engine_type_id, branch_id, machine_type, created_at, expiration_date, remark, is_active, machine_value, vendor, purchase_date, usage_start_date) 
                                VALUES (%s, %s, %s, %s, NOW(), %s, %s, 1, %s, %s, %s, %s)
                            """
                            cur.execute(sql_add, (new_name_code.strip(), t_id, b_id, m_type, new_exp_date, new_remark, new_value, new_vendor, new_purchase_date, new_usage_date))
                            conn.commit()

                        log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Master Data Setup", log_msg)
                        st.success(f"✅ เพิ่ม '{new_name_code}' เข้าสู่ระบบสำเร็จ!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
                    finally:
                        if conn:
                            conn.close()

    # -------------------------------------------------------------------------
    # 📋 ส่วนที่ 2: แสดงรายการอุปกรณ์และแผงตัวกรองข้อมูล
    # -------------------------------------------------------------------------
    st.subheader("📋 รายการอุปกรณ์ทั้งหมดในระบบ")
    combined_data = fetch_equipment_data(current_role, user_allowed_branches)

    if not combined_data:
        st.info("ยังไม่มีข้อมูลอุปกรณ์ในระบบ")
        return

    df = pd.DataFrame(combined_data)
    df["วันหมดอายุ_date"] = pd.to_datetime(df["วันหมดอายุ"]).dt.date

    # วาดการ์ดสรุป KPI
    render_equipment_kpi_card(df)

    # แผงกรองข้อมูล (Filter Panel)
    with st.expander("🔍 แผงกรองข้อมูล (Filter Panel)", expanded=False):
        f_c1, f_c2, f_c3 = st.columns(3)
        with f_c1:
            search_q = st.text_input("🔍 ค้นหาชื่อ/รหัส:", placeholder="พิมพ์เพื่อค้นหา...")
            f_status = st.selectbox("📍 สถานะการใช้งาน:", ["ทั้งหมด", "▶️ ใช้งาน", "🔴 ระงับ"])
        with f_c2:
            branch_list = ["ทั้งหมด"] + sorted(df["สาขา"].dropna().unique().tolist())
            f_branch = st.selectbox("🏢 สาขา:", options=branch_list)
            type_list = ["ทั้งหมด"] + sorted(df[df["หมวดหมู่"] == "🚚 รถยนต์/รถยก"]["ชนิดรถ"].dropna().unique().tolist())
            f_type = st.selectbox("🚜 ชนิดรถ (เฉพาะรถ):", options=type_list)
        with f_c3:
            f_cat = st.selectbox("📌 หมวดหมู่:", ["ทั้งหมด", "⚙️ เครื่องจักร", "🚚 รถยนต์/รถยก"])
            f_exp = st.date_input("⏳ วันหมดอายุ (ช่วงเวลา):", value=[])

    filtered_df = df.copy()
    if search_q:
        filtered_df = filtered_df[filtered_df["ชื่อ/รหัส"].astype(str).str.contains(search_q, case=False, na=False)]
    if f_cat != "ทั้งหมด":
        filtered_df = filtered_df[filtered_df["หมวดหมู่"] == f_cat]
    if f_branch != "ทั้งหมด":
        filtered_df = filtered_df[filtered_df["สาขา"] == f_branch]
    if f_type != "ทั้งหมด":
        filtered_df = filtered_df[filtered_df["ชนิดรถ"] == f_type]
    if f_status != "ทั้งหมด":
        filtered_df = filtered_df[filtered_df["สถานะ"] == f_status]
    if len(f_exp) == 2:
        filtered_df = filtered_df[filtered_df["วันหมดอายุ_date"].notna() & filtered_df["วันหมดอายุ_date"].between(f_exp[0], f_exp[1])]

    st.caption(f"แสดงผล **{len(filtered_df)}** รายการ จากทั้งหมด {len(df)} รายการ")

    # จัดฟอร์แมตข้อมูลสำหรับแสดงในตาราง
    df_display = filtered_df.copy()
    for date_col in ["วันที่ซื้อ", "วันที่เริ่มใช้งาน", "วันหมดอายุ"]:
        df_display[date_col] = df_display[date_col].apply(clean_date_str)
    df_display["มูลค่าของอุปกรณ์ (บาท)"] = df_display["มูลค่าของอุปกรณ์ (บาท)"].apply(clean_currency_str)
    df_display["ผู้ขาย/vendor"] = df_display["ผู้ขาย/vendor"].apply(clean_text_str)
    df_display["หมายเหตุ"] = df_display["หมายเหตุ"].apply(clean_text_str)

    display_cols = ["สถานะ", "หมวดหมู่", "ID", "ชื่อ/รหัส", "ชนิดรถ", "สาขา", "วันที่ซื้อ", "วันที่เริ่มใช้งาน", "มูลค่าของอุปกรณ์ (บาท)", "ผู้ขาย/vendor", "วันหมดอายุ", "หมายเหตุ"]
    st.dataframe(df_display[display_cols], use_container_width=True, height=350, hide_index=True)

    # -------------------------------------------------------------------------
    # ✏️ ส่วนที่ 3: แก้ไขข้อมูล หรือ ระงับการใช้งานอุปกรณ์
    # -------------------------------------------------------------------------
    with st.expander("✏️ / 🚫 แก้ไขข้อมูล หรือ ระงับการใช้งานอุปกรณ์", expanded=False):
        if filtered_df.empty:
            st.warning("⚠️ ไม่พบข้อมูลอุปกรณ์ที่ตรงกับเงื่อนไขการค้นหา")
            return

        filtered_ids = set(filtered_df["ID"].tolist())
        target_items = [r for r in combined_data if r["ID"] in filtered_ids]
        item_options = {f"[{r['สถานะ']}] {r['หมวดหมู่'].split(' ')[1]} ID:{r['ID']} - {r['ชื่อ/รหัส']} ({r['สาขา']})": r for r in target_items}

        col_sel1, col_sel2 = st.columns([2.5, 1.5])
        with col_sel1:
            selected_label = st.selectbox(
                "เลือกอุปกรณ์ที่ต้องการจัดการ:",
                options=list(item_options.keys()),
                help="รายชื่อจะปรับเปลี่ยนตามตัวกรองและการค้นหาด้านบนอัตโนมัติ"
            )
        with col_sel2:
            st.markdown("<div style='text-align: right; padding-top: 28px;'><span style='background-color: #E0F2FE; color: #0284C7; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;'>🔗 ซิงค์ตามตัวกรองด้านบน</span></div>", unsafe_allow_html=True)

        sel_data = item_options[selected_label]
        is_machine_edit = (sel_data["หมวดหมู่"] == "⚙️ เครื่องจักร")

        with st.form("edit_equipment_form"):
            e_c1, e_c2, e_c3 = st.columns(3)
            with e_c1:
                edit_name = st.text_input("แก้ไข ชื่อ/รหัส", value=sel_data["ชื่อ/รหัส"])
                status_opts = ["▶️ ใช้งานปกติ (Active)", "🔴 ระงับการใช้งาน (Disabled)"]
                default_status = 0 if sel_data["is_active"] == 1 else 1
                edit_status = st.selectbox(
                    "สถานะการใช้งาน",
                    options=status_opts,
                    index=default_status,
                    help="การเปลี่ยนเป็น 'ระงับการใช้งาน' จะซ่อนอุปกรณ์ออกจากหน้าบันทึกงานใหม่ แต่ยังคงรักษาประวัติงานและชั่วโมงการทำงานเดิมไว้ในระบบ"
                )

            with e_c2:
                t_idx = next((i for i, v in enumerate(engine_type_dict.values()) if v == sel_data["type_id"]), 0) if not is_machine_edit else 0
                edit_type = st.selectbox("แก้ไข ชนิดของรถ", options=type_options, index=t_idx, disabled=is_machine_edit)
                edit_exp = st.date_input("แก้ไข วันหมดอายุการใช้งาน", value=safe_to_date(sel_data.get("วันหมดอายุ")))

            with e_c3:
                b_idx = next((i for i, b_name in enumerate(branch_options) if available_branches_dict[b_name] == sel_data["branch_id"]), 0)
                edit_branch = st.selectbox("แก้ไข สาขา", options=branch_options, index=b_idx)
                old_rem = sel_data.get("หมายเหตุ")
                edit_remark = st.text_input("แก้ไข หมายเหตุ", value="" if clean_text_str(old_rem) == "-" else str(old_rem))

            e_c4, e_c5 = st.columns(2)
            with e_c4:
                edit_value = st.number_input("มูลค่าของอุปกรณ์ (บาท)", value=float(sel_data.get("มูลค่าของอุปกรณ์ (บาท)") or 0.0), step=100000.0)
            with e_c5:
                old_vendor = sel_data.get("ผู้ขาย/vendor")
                edit_vendor = st.text_input("แก้ไข ผู้ขาย/vendor", value="" if clean_text_str(old_vendor) == "-" else str(old_vendor))

            e_c6, e_c7 = st.columns(2)
            with e_c6:
                edit_purchase_date = st.date_input("แก้ไข วันที่ซื้อ", value=safe_to_date(sel_data.get("วันที่ซื้อ")))
            with e_c7:
                edit_usage_date = st.date_input("แก้ไข วันที่เริ่มใช้งาน", value=safe_to_date(sel_data.get("วันที่เริ่มใช้งาน")))

            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

            if st.form_submit_button("💾 อัปเดตข้อมูล (Update)", use_container_width=True):
                conn = None
                try:
                    new_is_active = 1 if "▶️" in edit_status else 0
                    new_type_id = None if is_machine_edit else engine_type_dict[edit_type]
                    new_branch_id = available_branches_dict[edit_branch]

                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        sql_update = """
                            UPDATE machines_set 
                            SET machine_name=%s, engine_type_id=%s, branch_id=%s, expiration_date=%s, 
                                remark=%s, is_active=%s, machine_value=%s, vendor=%s, purchase_date=%s, usage_start_date=%s 
                            WHERE id=%s
                        """
                        cur.execute(sql_update, (
                            edit_name.strip(), new_type_id, new_branch_id, edit_exp,
                            edit_remark, new_is_active, edit_value, edit_vendor,
                            edit_purchase_date, edit_usage_date, sel_data["ID"]
                        ))
                        conn.commit()

                    log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "Master Data Setup", f"อัปเดตอุปกรณ์ ID: {sel_data['ID']} (Active={new_is_active})")
                    st.success("✅ อัปเดตข้อมูลและสถานะสำเร็จ!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการอัปเดต: {e}")
                finally:
                    if conn:
                        conn.close()