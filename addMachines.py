import streamlit as st
import pandas as pd
import time
from datetime import datetime
from database import get_db_connection, log_activity

# =============================================================================
# 🚀 ฟังก์ชันดึงข้อมูลสาขาจาก Database
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

def render_add_new_equipment():
    st.markdown("""
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        header { visibility: hidden !important; }
        #MainMenu { visibility: hidden !important; }
        .block-container { padding-top: 1rem !important; margin-top: -20px !important; }
        </style>
    """, unsafe_allow_html=True)
    
    # 🎯 ดึงข้อมูลสาขาจาก Database แทน config.py
    branch_dict = get_branch_dict_from_db()

    current_role = st.session_state.get('role_tab', 'user')
    user_allowed_branches = st.session_state.get('allowed_branches', [str(st.session_state.get('branch_id'))])

    if current_role == 'admin':
        available_branches_dict = branch_dict
    else:
        available_branches_dict = {k: v for k, v in branch_dict.items() if str(v) in user_allowed_branches}
        
    branch_options = list(available_branches_dict.keys())

    st.header("🛠️ จัดการข้อมูลอุปกรณ์ในระบบ")
    st.caption("หน้าจอเพิ่ม แก้ไข และระงับการใช้งานอุปกรณ์ (เพื่อรักษาประวัติข้อมูลเดิม ระบบจะใช้การเปลี่ยนสถานะแทนการลบข้อมูลจริง)")

    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE machines_set SET is_active = 0 WHERE expiration_date IS NOT NULL AND expiration_date < CURDATE() AND is_active = 1")
            conn.commit()
    except Exception as e:
        pass
    finally:
        if conn:
            conn.close()
    """

    with st.expander("➕ เพิ่มอุปกรณ์ใหม่เข้าสู่ระบบ", expanded=False):
    
        equip_options = ["-- กรุณาเลือกประเภทอุปกรณ์ --", "⚙️ เครื่องจักร (Machine)", "🚚 รถยนต์ / รถยก (Vehicle)"]
        equip_type_add = st.selectbox("เลือกประเภทอุปกรณ์ที่ต้องการเพิ่ม:", options=equip_options)
        
        is_not_selected = (equip_type_add == "-- กรุณาเลือกประเภทอุปกรณ์ --")
        is_machine_add = (equip_type_add == "⚙️ เครื่องจักร (Machine)")
        
        engine_type_dict = {}
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT id, CONVERT(type_name USING utf8mb4) AS type_name FROM engine_types ORDER BY id ASC")
                for r in cur.fetchall():
                    engine_type_dict[r['type_name']] = r['id']
        except Exception: 
            pass
        finally:
            if conn:
                conn.close()
                
        type_options = list(engine_type_dict.keys()) if engine_type_dict else ["-- ไม่มีข้อมูลประเภทรถ --"]

        with st.form("add_equipment_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
        
            with col1:
                lbl_name = "รหัสงาน / ทะเบียนรถใหม่ *"
                if is_not_selected: lbl_name = "ชื่อ/รหัสอุปกรณ์ *"
                elif is_machine_add: lbl_name = "ชื่อเครื่องจักร / รหัสทะเบียนรถ *"
                
                new_name_code = st.text_input(lbl_name, placeholder="ระบุชื่อหรือรหัสอุปกรณ์...", disabled=is_not_selected)
                new_exp_date = st.date_input("วันหมดอายุการใช้งาน", value=None, disabled=is_not_selected)
            
            with col2:
                new_engine_type = st.selectbox("ชนิดของรถรถยนต์ *", options=type_options, disabled=(is_not_selected or is_machine_add))
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

            col7 = st.columns(1)[0] 
            with col7:
                new_remark = st.text_input("หมายเหตุ", placeholder="ระบุหมายเหตุเพิ่มเติม (ถ้ามี)", disabled=is_not_selected)
                
            submit_add = st.form_submit_button("➕ บันทึกข้อมูลเข้าสู่ระบบ (สถานะ Active)", disabled=is_not_selected, use_container_width=True)
            
            if submit_add:
                if is_not_selected:
                    st.error("⚠️ กรุณาเลือกประเภทอุปกรณ์ก่อนทำการบันทึก")
                elif not new_name_code:
                    st.error("⚠️ กรุณาระบุชื่อ/รหัสอุปกรณ์ให้ชัดเจน")
                elif not is_machine_add and new_engine_type == "-- ไม่มีข้อมูลประเภทรถ --":
                    st.error("⚠️ กรุณาเลือกชนิดของรถให้ครบถ้วน")
                else:
                    conn = None
                    try:
                        b_id = available_branches_dict[new_branch]
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            if is_machine_add:
                                sql_add = "INSERT INTO machines_set (machine_name, branch_id, machine_type, created_at, expiration_date, remark, is_active, machine_value, vendor, purchase_date, usage_start_date) VALUES (%s, %s, 'machine', NOW(), %s, %s, 1, %s, %s, %s, %s)"
                                cur.execute(sql_add, (new_name_code, b_id, new_exp_date, new_remark, new_value, new_vendor, new_purchase_date, new_usage_date))
                                log_msg = f"เพิ่มเครื่องจักรใหม่: {new_name_code}"
                            else:
                                t_id = engine_type_dict[new_engine_type]
                                sql_add = "INSERT INTO machines_set (machine_name, engine_type_id, branch_id, machine_type, created_at, expiration_date, remark, is_active, machine_value, vendor, purchase_date, usage_start_date) VALUES (%s, %s, %s, 'engine', NOW(), %s, %s, 1, %s, %s, %s, %s)"
                                cur.execute(sql_add, (new_name_code, t_id, b_id, new_exp_date, new_remark, new_value, new_vendor, new_purchase_date, new_usage_date))
                                log_msg = f"เพิ่มรถใหม่: {new_name_code}"
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

    st.subheader("📋 รายการอุปกรณ์ทั้งหมดในระบบ")
    
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
            
            if current_role == 'admin':
                cur.execute(base_query + "ORDER BY m.id DESC")
            else:
                placeholders = ', '.join(['%s'] * len(user_allowed_branches))
                cur.execute(base_query + f"WHERE m.branch_id IN ({placeholders}) ORDER BY m.id DESC", tuple(user_allowed_branches))
            
            for r in cur.fetchall():
                status_label = "▶️ ใช้งาน" if r.get('is_active') == 1 else "🔴 ระงับ"
                is_mach = (r.get('machine_type') == 'machine')
                
                cat_label = "⚙️ เครื่องจักร" if is_mach else "🚚 รถยนต์/รถยก"
                t_name = "-" if is_mach else (r.get('type_name') or "ไม่ระบุ")
                
                combined_data.append({
                    "หมวดหมู่": cat_label, 
                    "ID": r['id'], 
                    "ชื่อ/รหัส": r['name_code'], 
                    "ชนิดรถ": t_name,
                    "branch_id": r['branch_id'], 
                    "สาขา": r['branch_name'], 
                    "วันที่ซื้อ": r.get('purchase_date'),
                    "วันที่เริ่มใช้งาน": r.get('usage_start_date'), 
                    "วันหมดอายุ": r['expiration_date'],
                    "หมายเหตุ": r['remark'],
                    "มูลค่าของอุปกรณ์ (บาท)": r.get('machine_value'),
                    "ผู้ขาย/vendor": r.get('vendor') or'-',
                    "สถานะ": status_label, 
                    "is_active": r.get('is_active', 1), 
                    "type_id": r.get('engine_type_id')
                })
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลได้: {e}")
    finally:
        if conn:
            conn.close()

    if combined_data:
        df = pd.DataFrame(combined_data)
        df['วันหมดอายุ_date'] = pd.to_datetime(df['วันหมดอายุ']).dt.date
        
        with st.expander("🔍 แผงกรองข้อมูล (Filter Panel)", expanded=True):
            f_c1, f_c2, f_c3 = st.columns(3)
            with f_c1:
                search_q = st.text_input("🔍 ค้นหาชื่อ/รหัส:", placeholder="พิมพ์เพื่อค้นหา...")
                f_status = st.selectbox("📍 สถานะการใช้งาน:", ["ทั้งหมด", "▶️ ใช้งาน", "🔴 ระงับ"])
            with f_c2:
                branch_list = ["ทั้งหมด"] + sorted(df['สาขา'].dropna().unique().tolist())
                f_branch = st.selectbox("🏢 สาขา:", options=branch_list)
                type_list = ["ทั้งหมด"] + sorted(df[df['หมวดหมู่']=="🚚 รถยนต์/รถยก"]['ชนิดรถ'].dropna().unique().tolist())
                f_type = st.selectbox("🚜 ชนิดรถ (เฉพาะรถ):", options=type_list)
            with f_c3:
                f_cat = st.selectbox("📌 หมวดหมู่:", ["ทั้งหมด", "⚙️ เครื่องจักร", "🚚 รถยนต์/รถยก"])
                f_exp = st.date_input("⏳ วันหมดอายุ (ช่วงเวลา):", value=[])
                
        filtered_df = df.copy()
        if search_q:
            filtered_df = filtered_df[filtered_df['ชื่อ/รหัส'].astype(str).str.contains(search_q, case=False, na=False)]
        if f_cat != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df['หมวดหมู่'] == f_cat]
        if f_branch != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df['สาขา'] == f_branch]
        if f_type != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df['ชนิดรถ'] == f_type]
        if f_status != "ทั้งหมด":
            filtered_df = filtered_df[filtered_df['สถานะ'] == f_status]
        if len(f_exp) == 2:
            filtered_df = filtered_df[filtered_df['วันหมดอายุ_date'].notna() & filtered_df['วันหมดอายุ_date'].between(f_exp[0], f_exp[1])]

        st.write(f"แสดงผล **{len(filtered_df)}** รายการ จากทั้งหมด {len(df)} รายการ")
        display_cols = ['สถานะ', 'หมวดหมู่', 'ID', 'ชื่อ/รหัส', 'ชนิดรถ', 'สาขา', 'วันที่ซื้อ', 'วันที่เริ่มใช้งาน', 'มูลค่าของอุปกรณ์ (บาท)', 'ผู้ขาย/vendor', 'วันหมดอายุ', 'หมายเหตุ']
        st.dataframe(filtered_df[display_cols], use_container_width=True, height=350)

        with st.expander("✏️ / 🚫 แก้ไขข้อมูล หรือ ระงับการใช้งานอุปกรณ์", expanded=False):
            item_options = {f"[{r['สถานะ']}] {r['หมวดหมู่'].split(' ')[1]} ID:{r['ID']} - {r['ชื่อ/รหัส']} ({r['สาขา']})": r for r in combined_data}
            selected_label = st.selectbox("เลือกอุปกรณ์ที่ต้องการจัดการ:", options=list(item_options.keys()))
            sel_data = item_options[selected_label]
            is_machine_edit = sel_data['หมวดหมู่'] == "⚙️ เครื่องจักร"

            with st.form("edit_equipment_form"):
                e_c1, e_c2, e_c3 = st.columns(3)
                with e_c1:
                    edit_name = st.text_input("แก้ไข ชื่อ/รหัส", value=sel_data['ชื่อ/รหัส'])
                    status_opts = ["🟢 ใช้งานปกติ (Active)", "🔴 ระงับการใช้งาน (Disabled)"]
                    default_status = 0 if sel_data['is_active'] == 1 else 1
                    edit_status = st.selectbox("สถานะการใช้งาน", options=status_opts, index=default_status)

                with e_c2:
                    t_idx = 0
                    if not is_machine_edit:
                        for i, (k, v) in enumerate(engine_type_dict.items()):
                            if v == sel_data['type_id']:
                                t_idx = i; break
                    edit_type = st.selectbox("แก้ไข ชนิดของรถ", options=type_options, index=t_idx, disabled=is_machine_edit)
                    exp_val = pd.to_datetime(sel_data['วันหมดอายุ']) if pd.notna(sel_data.get('วันหมดอายุ')) else None
                    edit_exp = st.date_input("แก้ไข วันหมดอายุการใช้งาน", value=exp_val)
    
                with e_c3:
                    b_idx = 0
                    for i, b_name in enumerate(branch_options):
                        if available_branches_dict[b_name] == sel_data['branch_id']:
                            b_idx = i; break
                    edit_branch = st.selectbox("แก้ไข สาขา", options=branch_options, index=b_idx)
                    edit_remark = st.text_input("แก้ไข หมายเหตุ", value=sel_data.get('หมายเหตุ') or "")

                e_c4, e_c5 = st.columns(2)
                with e_c4:
                    edit_value = st.number_input("มูลค่าของอุปกรณ์ (บาท)", value=float(sel_data.get('มูลค่าของอุปกรณ์ (บาท)') or 0.0), step=100000.0)

                with e_c5:
                    old_vendor = sel_data.get('ผู้ขาย/vendor')
                    edit_vendor = st.text_input("แก้ไข ผู้ขาย/vendor", value=old_vendor if old_vendor != '-' else "")

                e_c6, e_c7 = st.columns(2)    
                with e_c6:
                    pur_val = pd.to_datetime(sel_data['วันที่ซื้อ']) if pd.notna(sel_data.get('วันที่ซื้อ')) else None
                    edit_purchase_date = st.date_input("แก้ไข วันที่ซื้อ", value=pur_val)

                with e_c7:
                    use_val = pd.to_datetime(sel_data['วันที่เริ่มใช้งาน']) if pd.notna(sel_data.get('วันที่เริ่มใช้งาน')) else None
                    edit_usage_date = st.date_input("แก้ไข วันที่เริ่มใช้งาน", value=use_val)

                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                
                a_c1, a_c2 = st.columns(2)
                with a_c1:
                    if st.form_submit_button("💾 อัปเดตข้อมูล (Update)", use_container_width=True):
                        conn = None
                        try:
                            new_is_active = 1 if "🟢" in edit_status else 0
                            conn = get_db_connection()
                            with conn.cursor() as cur:
                                if is_machine_edit:
                                    cur.execute("UPDATE machines_set SET machine_name=%s, branch_id=%s, expiration_date=%s, remark=%s, is_active=%s , machine_value=%s, vendor=%s, purchase_date=%s, usage_start_date=%s WHERE id=%s", 
                                                (edit_name, available_branches_dict[edit_branch], edit_exp, edit_remark, new_is_active, edit_value, edit_vendor, edit_purchase_date, edit_usage_date, sel_data['ID']))
                                else:
                                    cur.execute("UPDATE machines_set SET machine_name=%s, engine_type_id=%s, branch_id=%s, expiration_date=%s, remark=%s, is_active=%s , machine_value=%s, vendor=%s, purchase_date=%s, usage_start_date=%s WHERE id=%s", 
                                                (edit_name, engine_type_dict[edit_type], available_branches_dict[edit_branch], edit_exp, edit_remark, new_is_active, edit_value, edit_vendor, edit_purchase_date, edit_usage_date, sel_data['ID']))
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
    else:
        st.info("ยังไม่มีข้อมูลอุปกรณ์ในระบบ")