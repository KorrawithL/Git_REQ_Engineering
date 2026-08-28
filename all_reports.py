import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import io
import time
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from database import get_db_connection, log_activity
from config import branch_dict

# ==========================================================
# 🛑 1. ฟังก์ชัน Popup ยืนยันการลบข้อมูล (Delete Dialogs)
# ==========================================================
@st.dialog("⚠️ ยืนยันการลบข้อมูล (Tab 1)")
def delete_record_dialog_t1(row_data, pk_col):
    rec_id = row_data[pk_col]
    st.error(f"คุณแน่ใจหรือไม่ว่าต้องการลบข้อมูล ID: {rec_id} ?")
    st.write(f"**วันที่:** {row_data.get('record_date')} | **สาขา:** {row_data.get('branch_name')}")
    st.write(f"**เครื่องจักร:** {row_data.get('machine_name')}")
    st.markdown("<span style='color:#EF4444; font-size:14px;'>* การกระทำนี้ไม่สามารถกู้คืนข้อมูลได้</span>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("❌ ยกเลิก", use_container_width=True, key=f"cancel_d1_{rec_id}"): st.rerun()
    with c2:
        if st.button("🗑️ ยืนยันการลบ", type="primary", use_container_width=True, key=f"confirm_d1_{rec_id}"):
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM machine_trans WHERE {pk_col}=%s", (rec_id,))
                    conn.commit()
                conn.close()
                st.cache_data.clear()
                log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 1", f"ลบข้อมูล ID: {rec_id}")
                st.success("🗑️ ลบข้อมูลเรียบร้อยแล้ว!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

@st.dialog("⚠️ ยืนยันการลบข้อมูล (Tab 2)")
def delete_record_dialog_t2(row_data, pk_col):
    rec_id = row_data[pk_col]
    st.error(f"คุณแน่ใจหรือไม่ว่าต้องการลบข้อมูล ID: {rec_id} ?")
    st.write(f"**วันที่:** {row_data.get('record_date')} | **สาขา:** {row_data.get('branch_name')}")
    st.write(f"**ทะเบียนรถ:** {row_data.get('engine_code')} ({row_data.get('type_name')})")
    st.markdown("<span style='color:#EF4444; font-size:14px;'>* การกระทำนี้ไม่สามารถกู้คืนข้อมูลได้</span>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("❌ ยกเลิก", use_container_width=True, key=f"cancel_d2_{rec_id}"): st.rerun()
    with c2:
        if st.button("🗑️ ยืนยันการลบ", type="primary", use_container_width=True, key=f"confirm_d2_{rec_id}"):
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM fuel_records WHERE {pk_col}=%s", (rec_id,))
                    conn.commit()
                conn.close()
                st.cache_data.clear()
                log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 2", f"ลบข้อมูล ID: {rec_id}")
                st.success("🗑️ ลบข้อมูลเรียบร้อยแล้ว!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

@st.dialog("⚠️ ยืนยันการลบข้อมูล (Tab 3)")
def delete_record_dialog_t3(row_data, pk_col):
    rec_id = row_data[pk_col]
    st.error(f"คุณแน่ใจหรือไม่ว่าต้องการลบข้อมูล ID: {rec_id} ?")
    st.write(f"**วันที่:** {row_data.get('record_date')} | **สาขา:** {row_data.get('branch_name')}")
    st.write(f"**จำนวนตรวจเช็คทั้งหมด:** {row_data.get('total_count')} ครั้ง | **ตก:** {row_data.get('total_drop')} ครั้ง")
    st.markdown("<span style='color:#EF4444; font-size:14px;'>* การกระทำนี้ไม่สามารถกู้คืนข้อมูลได้</span>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("❌ ยกเลิก", use_container_width=True, key=f"cancel_d3_{rec_id}"): st.rerun()
    with c2:
        if st.button("🗑️ ยืนยันการลบ", type="primary", use_container_width=True, key=f"confirm_d3_{rec_id}"):
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM boiler_pressure_records WHERE {pk_col}=%s", (rec_id,))
                    conn.commit()
                conn.close()
                st.cache_data.clear()
                log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 3", f"ลบข้อมูล ID: {rec_id}")
                st.success("🗑️ ลบข้อมูลเรียบร้อยแล้ว!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

@st.dialog("⚠️ ยืนยันการลบข้อมูล (Tab 4)")
def delete_record_dialog_t4(row_data, pk_col):
    rec_id = row_data[pk_col]
    st.error(f"คุณแน่ใจหรือไม่ว่าต้องการลบข้อมูล ID: {rec_id} ?")
    st.write(f"**วันที่:** {row_data.get('record_date')} | **สาขา:** {row_data.get('branch_name')}")
    st.write(f"**ผลิตไอน้ำ:** {row_data.get('steam_production')} ตัน | **ชม.ทำงาน:** {row_data.get('working_hours')} ชม.")
    st.markdown("<span style='color:#EF4444; font-size:14px;'>* การกระทำนี้ไม่สามารถกู้คืนข้อมูลได้</span>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("❌ ยกเลิก", use_container_width=True, key=f"cancel_d4_{rec_id}"): st.rerun()
    with c2:
        if st.button("🗑️ ยืนยันการลบ", type="primary", use_container_width=True, key=f"confirm_d4_{rec_id}"):
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM boiler_fuel_records WHERE {pk_col}=%s", (rec_id,))
                    conn.commit()
                conn.close()
                st.cache_data.clear()
                log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 4", f"ลบข้อมูล ID: {rec_id}")
                st.success("🗑️ ลบข้อมูลเรียบร้อยแล้ว!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")


# ==========================================================
# 🛠️ 2. ฟังก์ชัน Popup สำหรับแก้ไขข้อมูล (Update Dialogs)
# ==========================================================
@st.dialog("🛠️ แก้ไขข้อมูล (Tab 1)", width="large")
def update_record_dialog_t1(row_data, pk_col):
    rec_id = row_data[pk_col]
    st.info(f"ID: {rec_id} | วันที่: {row_data.get('record_date')} | เครื่อง: {row_data.get('machine_name')} ({row_data.get('branch_name')})")
    with st.form(f"u_form1_{rec_id}", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            e_date = st.date_input("แก้ไข วันที่", value=pd.to_datetime(row_data.get('record_date')))
            e_qty = st.number_input("แก้ไข จำนวนเครื่องจักร", value=int(row_data.get('machine_qty') or 1), min_value=1)
        with col2:
            e_work = st.number_input("แก้ไข ชม.ทำงาน", value=float(row_data.get('working_hours') or 0.0), format="%.2f")
            e_break = st.number_input("แก้ไข ชม.เบรกดาวน์", value=float(row_data.get('breakdown_hours') or 0.0), format="%.2f")
        e_rem = st.text_area("แก้ไข หมายเหตุ", value=str(row_data.get('remarks') or ''))
        
        if st.form_submit_button("💾 บันทึกการแก้ไข", use_container_width=True):
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"UPDATE machine_trans SET record_date=%s, machine_qty=%s, working_hours=%s, breakdown_hours=%s, remarks=%s, updated_at=NOW() WHERE {pk_col}=%s",
                                (e_date, e_qty, e_work, e_break, e_rem, rec_id))
                    conn.commit()
                conn.close()
                st.cache_data.clear()
                log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 1", f"แก้ไข ID: {rec_id}")
                st.success("✅ อัปเดตข้อมูลสำเร็จ!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

@st.dialog("🛠️ แก้ไขข้อมูล (Tab 2)", width="large")
def update_record_dialog_t2(row_data, pk_col, engine_lbl_list, engine_details_t2):
    rec_id = row_data[pk_col]
    st.info(f"ID: {rec_id} | วันที่: {row_data.get('record_date')} | ทะเบียน: {row_data.get('engine_code')} ({row_data.get('branch_name')})")
    
    curr_code = str(row_data.get('engine_code') or '')
    curr_type = str(row_data.get('type_name') or '')
    def_idx = 0
    for idx, lbl in enumerate(engine_lbl_list):
        if engine_details_t2[lbl]['code'] == curr_code and engine_details_t2[lbl]['type'] == curr_type:
            def_idx = idx; break

    with st.form(f"u_form2_{rec_id}", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            e_date = st.date_input("แก้ไข วันที่", value=pd.to_datetime(row_data.get('record_date')))
            e_eng_lbl = st.selectbox("แก้ไข ทะเบียนรถ:", options=engine_lbl_list if engine_lbl_list else ["-- ไม่พบข้อมูล --"], index=def_idx)
        with col2:
            e_liters = st.number_input("แก้ไข น้ำมัน (ลิตร)", min_value=0.0, value=float(row_data.get('fuel_liters') or 0.0))
            e_work = st.number_input("แก้ไข ชม.ทำงาน", min_value=0.0, step=0.5, value=float(row_data.get('working_hours') or 0.0))
        e_rem = st.text_area("แก้ไข หมายเหตุ", value=str(row_data.get('remark') or ''))

        if st.form_submit_button("💾 บันทึกการแก้ไข", use_container_width=True):
            try:
                e_info = engine_details_t2.get(e_eng_lbl, {'code': curr_code, 'type': curr_type})
                u_liter_hr = round(e_liters / e_work, 2) if e_work > 0 else 0.00
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"""UPDATE fuel_records SET record_date=%s, engine_code=CONVERT(%s USING utf8mb4), type_name=CONVERT(%s USING utf8mb4), 
                                   fuel_liters=%s, working_hours=%s, liter_hr=%s, remark=CONVERT(%s USING utf8mb4) WHERE {pk_col}=%s""",
                                (e_date, e_info['code'], e_info['type'], e_liters, e_work, u_liter_hr, e_rem, rec_id))
                    conn.commit()
                conn.close()
                st.cache_data.clear()
                log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 2", f"แก้ไข ID: {rec_id}")
                st.success("✅ อัปเดตข้อมูลสำเร็จ!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

@st.dialog("🛠️ แก้ไขข้อมูล (Tab 3)", width="large")
def update_record_dialog_t3(row_data, pk_col):
    rec_id = row_data[pk_col]
    st.info(f"ID: {rec_id} | วันที่: {row_data.get('record_date')} | สาขา: {row_data.get('branch_name')}")
    with st.form(f"u_form3_{rec_id}", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            e_date = st.date_input("แก้ไข วันที่", value=pd.to_datetime(row_data.get('record_date')))
            e_tot = st.number_input("แก้ไข จำนวนครั้งทั้งหมด", min_value=0, value=int(row_data.get('total_count') or 0))
        with col2:
            e_pm = st.number_input("แก้ไข ตกตาม PM", min_value=0, value=int(row_data.get('pm_drop') or 0))
            e_npm = st.number_input("แก้ไข ตกนอกเหนือ PM", min_value=0, value=int(row_data.get('non_pm_drop') or 0))
        e_rem = st.text_input("แก้ไข หมายเหตุ", value=str(row_data.get('remark') or ''))

        if st.form_submit_button("💾 บันทึกการแก้ไข", use_container_width=True):
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"UPDATE boiler_pressure_records SET record_date=%s, total_count=%s, total_drop=%s, pm_drop=%s, non_pm_drop=%s, remark=%s WHERE {pk_col}=%s",
                                (e_date, e_tot, (e_pm + e_npm), e_pm, e_npm, e_rem, rec_id))
                    conn.commit()
                conn.close()
                st.cache_data.clear()
                log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 3", f"แก้ไข ID: {rec_id}")
                st.success("✅ อัปเดตข้อมูลสำเร็จ!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

@st.dialog("🛠️ แก้ไขข้อมูล (Tab 4)", width="large")
def update_record_dialog_t4(row_data, pk_col):
    rec_id = row_data[pk_col]
    st.info(f"ID: {rec_id} | วันที่: {row_data.get('record_date')} | สาขา: {row_data.get('branch_name')}")
    with st.form(f"u_form4_{rec_id}", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_date = st.date_input("แก้ไข วันที่", value=pd.to_datetime(row_data.get('record_date')))
            e_saw_w = st.number_input("ขี้เลื่อย (ตัน)", min_value=0.0, value=float(row_data.get('sawdust_weight') or 0.0))
            e_wood_w = st.number_input("ปีกไม้ (ตัน)", min_value=0.0, value=float(row_data.get('wood_weight') or 0.0))
            e_waste_w = st.number_input("เศษไม้เสีย (ตัน)", min_value=0.0, value=float(row_data.get('waste_wood_weight') or 0.0))
        with c2:
            st.write(" ")
            e_saw_p = st.number_input("ราคาขี้เลื่อย", min_value=0.0, value=float(row_data.get('sawdust_price') or 0.0))
            e_wood_p = st.number_input("ราคาปีกไม้", min_value=0.0, value=float(row_data.get('wood_price') or 0.0))
            e_waste_p = st.number_input("ราคาเศษไม้เสีย", min_value=0.0, value=float(row_data.get('waste_wood_price') or 0.0))
        with c3:
            st.write(" ")
            e_prod = st.number_input("ผลิตไอน้ำ (ตัน)", min_value=0.1, value=float(row_data.get('steam_production') or 1.0))
            e_hrs = st.number_input("ชม.ทำงาน", min_value=0.1, value=float(row_data.get('working_hours') or 1.0))

        if st.form_submit_button("💾 บันทึกการแก้ไข", use_container_width=True):
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"""UPDATE boiler_fuel_records SET record_date=%s, sawdust_weight=%s, wood_weight=%s, waste_wood_weight=%s, 
                                   sawdust_price=%s, wood_price=%s, waste_wood_price=%s, steam_production=%s, working_hours=%s WHERE {pk_col}=%s""",
                                (e_date, e_saw_w, e_wood_w, e_waste_w, e_saw_p, e_wood_p, e_waste_p, e_prod, e_hrs, rec_id))
                    conn.commit()
                conn.close()
                st.cache_data.clear()
                log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 4", f"แก้ไข ID: {rec_id}")
                st.success("✅ อัปเดตข้อมูลสำเร็จ!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

@st.dialog("📊 หน้าต่างดูสรุปรายงาน", width="large")
def show_summary_report_dialog(html_content):
    components.html(html_content, height=650, scrolling=True)


# ==========================================================
# 🚀 3. ฟังก์ชัน CACHE ประมวลผลข้อมูล
# ==========================================================
@st.cache_data(show_spinner=False)
def process_t1(b_id_t1, start_date_str, end_date_str, allowed_tuple, selected_branch_display):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if b_id_t1 == "ทั้งหมด":
                sql = "SELECT t.*, b.branch_name, m.machine_name FROM machine_trans t LEFT JOIN branches b ON t.branch_id = b.id LEFT JOIN machines_set m ON t.machine_id = m.id WHERE t.record_date BETWEEN %s AND %s ORDER BY t.record_date ASC"
                cur.execute(sql, (start_date_str, end_date_str))
            elif b_id_t1 == "รวมเฉพาะที่มีสิทธิ์":
                placeholders = ', '.join(['%s'] * len(allowed_tuple))
                sql = f"SELECT t.*, b.branch_name, m.machine_name FROM machine_trans t LEFT JOIN branches b ON t.branch_id = b.id LEFT JOIN machines_set m ON t.machine_id = m.id WHERE t.branch_id IN ({placeholders}) AND t.record_date BETWEEN %s AND %s ORDER BY t.record_date ASC"
                cur.execute(sql, allowed_tuple + (start_date_str, end_date_str))
            else:
                sql = "SELECT t.*, b.branch_name, m.machine_name FROM machine_trans t LEFT JOIN branches b ON t.branch_id = b.id LEFT JOIN machines_set m ON t.machine_id = m.id WHERE t.branch_id = %s AND t.record_date BETWEEN %s AND %s ORDER BY t.record_date ASC"
                cur.execute(sql, (b_id_t1, start_date_str, end_date_str))
            raw_data = cur.fetchall()
        conn.close()
    except Exception: return [], None, None

    if not raw_data: return [], None, None

    unique_m_names = set()
    for r in raw_data:
        nm = str(r.get('machine_name') or '').strip()
        if nm: unique_m_names.add(nm)
        
    legacy_mapping = {
        "โต๊ะเลื่อย": {"suffix": " (≤ 0.15%)", "hex": "E2EFDA"},
        "พัดลม": {"suffix": " (≤ 0.15%)", "hex": "F2F2F2"},
        "ตาชั่งใหญ่": {"suffix": " (≤ 0.20%)", "hex": "EDEDED"},
        "ตาชั่งเล็ก": {"suffix": " (≤ 0.20%)", "hex": "F2F2F2"},
        "รถยก": {"suffix": " (≤ 0.20%)", "hex": "FCE4D6"},
        "รถคีบ": {"suffix": " (≤16 ชม.)", "hex": "FFF2CC"},
        "อัดน้ำยา": {"suffix": " (≤ 0.20%)", "hex": "E2EFDA"},
        "เตาอบปกติ": {"suffix": " (≤ 0.20%)", "hex": "D9E1F2"},
        "cdk": {"suffix": " (≤ 0.20%)", "hex": "D9E1F2"},
        "บอยเลอร์": {"suffix": " (≤ 0.15%)", "hex": "FCE4D6"},
        "ชิปเปอร์": {"suffix": " (≤ 0.15%)", "hex": "FFF2CC"}
    }
    
    color_palette = ["D9E1F2", "E2EFDA", "FFF2CC", "FCE4D6", "F2F2F2", "EDEDED"]
    new_color_idx = 0
    
    machines_config = []
    display_name_map = {} 
    
    for m_name in sorted(list(unique_m_names)):
        disp_name = m_name
        assigned_hex = None
        for k, v in legacy_mapping.items():
            if k.lower() in m_name.lower():
                disp_name = f"{m_name}{v['suffix']}"
                assigned_hex = v["hex"]
                break
        
        if not assigned_hex:
            assigned_hex = color_palette[new_color_idx % len(color_palette)]
            new_color_idx += 1
            
        machines_config.append({"name": disp_name, "hex": assigned_hex})
        display_name_map[m_name] = disp_name
        
    if not machines_config:
        return [], None, None

    matrix_data = {d: {m['name']: {'qty': 0, 'work': 0.0, 'break': 0.0, 'has_data': False} for m in machines_config} for d in range(1, 32)}
    
    for row_m in raw_data:
        d_num = pd.to_datetime(row_m['record_date']).day
        m_db_name = str(row_m.get('machine_name') or '').strip()
        if not m_db_name: continue
        
        mapped_name = display_name_map[m_db_name]
        
        w_hr = float(row_m.get('working_hours') or 0.0)
        b_hr = float(row_m.get('breakdown_hours') or 0.0)
        qty = int(row_m.get('machine_qty') or 0)
        
        matrix_data[d_num][mapped_name]['qty'] += qty
        matrix_data[d_num][mapped_name]['work'] += w_hr
        matrix_data[d_num][mapped_name]['break'] += b_hr
        matrix_data[d_num][mapped_name]['has_data'] = True

    active_machines_config = [m for m in machines_config if any([matrix_data[d][m['name']]['has_data'] for d in range(1, 32)])]
    if not active_machines_config: active_machines_config = machines_config
        
    totals_work = {m['name']: sum([matrix_data[d][m['name']]['work'] for d in range(1, 32)]) for m in active_machines_config}
    totals_break = {m['name']: sum([matrix_data[d][m['name']]['break'] for d in range(1, 32)]) for m in active_machines_config}
    percentages = {m['name']: f"{(totals_break[m['name']] / totals_work[m['name']] * 100):.2f}%" if totals_work[m['name']] > 0 else "0.00%" for m in active_machines_config}
    
    start_dt = pd.to_datetime(start_date_str)
    month_str = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][start_dt.month - 1]
    year_buddhist = start_dt.year + 543

    wb = Workbook()
    ws = wb.active
    ws.title = "Summary Machine Report"
    ws.views.sheetView[0].showGridLines = True
    font_title, font_banner, font_header, font_body, font_total, font_pct = Font(name="Sarabun", size=14, bold=True), Font(name="Sarabun", size=12, bold=True), Font(name="Sarabun", size=9, bold=True), Font(name="Sarabun", size=9), Font(name="Sarabun", size=9, bold=True), Font(name="Sarabun", size=10, bold=True, color="FF0000")
    align_center, align_right = Alignment(horizontal="center", vertical="center", wrap_text=True), Alignment(horizontal="right", vertical="center")
    thin_border = Border(left=Side(style="thin", color="000000"), right=Side(style="thin", color="000000"), top=Side(style="thin", color="000000"), bottom=Side(style="thin", color="000000"))
    fill_banner, fill_green = PatternFill(start_color="F8CBAD", end_color="F8CBAD", fill_type="solid"), PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    
    last_col_letter = get_column_letter(1 + len(active_machines_config) * 3)

    ws.merge_cells(f"A1:{last_col_letter}1"); ws["A1"] = f"บริษัท วู้ดเวิร์ค จำกัด สาขา {selected_branch_display}"; ws["A1"].font, ws["A1"].alignment = font_title, align_center
    ws.merge_cells(f"A2:{last_col_letter}2"); ws["A2"] = f"สรุปชั่วโมงการทำงานของเครื่องจักร/เบรกดาวน์ ประจำเดือน....{month_str}................... {year_buddhist}"; ws["A2"].font, ws["A2"].alignment, ws["A2"].fill = font_banner, align_center, fill_banner
    ws.row_dimensions[2].height = 25
    ws.merge_cells("A3:A4"); ws["A3"] = "วันที่"; ws["A3"].font, ws["A3"].alignment, ws["A3"].fill, ws["A3"].border = font_header, align_center, fill_green, thin_border
    ws["A4"].border = thin_border

    col_idx = 2
    for m in active_machines_config:
        start_c, end_c = get_column_letter(col_idx), get_column_letter(col_idx + 2)
        ws.merge_cells(f"{start_c}3:{end_c}3")
        ws[f"{start_c}3"] = m["name"]; ws[f"{start_c}3"].font, ws[f"{start_c}3"].alignment = font_header, align_center; ws[f"{start_c}3"].fill = PatternFill(start_color=m["hex"], end_color=m["hex"], fill_type="solid")
        for c in range(col_idx, col_idx + 3): ws[f"{get_column_letter(c)}3"].border = thin_border
        for i, sh in enumerate(["เครื่องจักร\nใช้งาน\n(เครื่อง)", "ชั่วโมง\nทำงาน\n(ชม.)", "ชั่วโมง\nเบรกดาวน์\n(ชม.)"]):
            cell_ref = f"{get_column_letter(col_idx + i)}4"; ws[cell_ref] = sh; ws[cell_ref].font, ws[cell_ref].alignment, ws[cell_ref].border = Font(name="Sarabun", size=8, bold=True), align_center, thin_border
        col_idx += 3

    ws.row_dimensions[3].height, ws.row_dimensions[4].height = 20, 35
    current_row = 5
    for day in range(1, 32):
        ws[f"A{current_row}"] = day; ws[f"A{current_row}"].font, ws[f"A{current_row}"].alignment, ws[f"A{current_row}"].border = font_header, align_center, thin_border
        c_idx = 2
        for m in active_machines_config:
            item = matrix_data[day][m['name']]
            cell_q, cell_w, cell_b = ws[f"{get_column_letter(c_idx)}{current_row}"], ws[f"{get_column_letter(c_idx+1)}{current_row}"], ws[f"{get_column_letter(c_idx+2)}{current_row}"]
            cell_q.value = (item['qty'] if item['qty'] > 0 else "-") if item['has_data'] else ""
            cell_w.value = (item['work'] if item['work'] > 0 else "-") if item['has_data'] else ""
            cell_b.value = (item['break'] if item['break'] > 0 else "-") if item['has_data'] else ""
            for cell, al in [(cell_q, align_center), (cell_w, align_right if isinstance(cell_w.value, (int, float)) else align_center), (cell_b, align_right if isinstance(cell_b.value, (int, float)) else align_center)]:
                cell.font, cell.alignment, cell.border = font_body, al, thin_border
                if isinstance(cell.value, (int, float)): cell.number_format = '#,##0.00'
            c_idx += 3
        current_row += 1

    ws[f"A{current_row}"] = "รวม"; ws[f"A{current_row}"].font, ws[f"A{current_row}"].alignment, ws[f"A{current_row}"].fill, ws[f"A{current_row}"].border = font_total, align_center, fill_green, thin_border
    c_idx = 2
    for m in active_machines_config:
        m_n = m['name']
        cell_q, cell_w, cell_b = ws[f"{get_column_letter(c_idx)}{current_row}"], ws[f"{get_column_letter(c_idx+1)}{current_row}"], ws[f"{get_column_letter(c_idx+2)}{current_row}"]
        cell_q.value = "-"
        cell_w.value = totals_work[m_n] if totals_work[m_n] > 0 else "-"
        cell_b.value = totals_break[m_n] if totals_break[m_n] > 0 else "-"
        for cell, al in [(cell_q, align_center), (cell_w, align_right if totals_work[m_n] > 0 else align_center), (cell_b, align_right if totals_break[m_n] > 0 else align_center)]:
            cell.font, cell.alignment, cell.fill, cell.border = font_total, al, fill_green, thin_border
            if isinstance(cell.value, (int, float)): cell.number_format = '#,##0.00'
        c_idx += 3

    current_row += 1
    ws[f"A{current_row}"] = "คิดเป็น%"; ws[f"A{current_row}"].font, ws[f"A{current_row}"].alignment, ws[f"A{current_row}"].border = font_pct, align_center, thin_border
    c_idx = 2
    for m in active_machines_config:
        start_c, end_c = get_column_letter(c_idx), get_column_letter(c_idx + 2)
        ws.merge_cells(f"{start_c}{current_row}:{end_c}{current_row}")
        ws[f"{start_c}{current_row}"].value = percentages[m['name']]; ws[f"{start_c}{current_row}"].font, ws[f"{start_c}{current_row}"].alignment = font_pct, align_center
        for c in range(c_idx, c_idx + 3): ws[f"{get_column_letter(c)}{current_row}"].border = thin_border
        c_idx += 3

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_data = excel_buffer.getvalue()

    header_row1 = "".join([f'<th colspan="3" style="background-color:#{m["hex"]};border:1px solid #000;padding:3px;font-size:10px;text-align:center;">{m["name"]}</th>' for m in active_machines_config])
    header_row2 = "".join(['<th style="border:1px solid #000;padding:2px;font-size:8px;width:28px;">เครื่องจักร<br>ใช้งาน</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:32px;">ชั่วโมง<br>ทำงาน</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:32px;">ชั่วโมง<br>เบรกดาวน์</th>' for _ in active_machines_config])

    body_rows = ""
    for day in range(1, 32):
        body_rows += f'<tr><td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;font-weight:bold;">{day}</td>'
        for m in active_machines_config:
            item = matrix_data[day][m['name']]
            if item['has_data']:
                q_val, w_val, b_val = str(item['qty']) if item['qty'] > 0 else "-", f"{item['work']:,.2f}" if item['work'] > 0 else "-", f"{item['break']:,.2f}" if item['break'] > 0 else "-"
            else:
                q_val, w_val, b_val = "", "", ""
            body_rows += f'<td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;">{q_val}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{w_val}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{b_val}</td>'
        body_rows += '</tr>'

    total_row_html = '<tr><td style="border:1px solid #000;padding:3px;text-align:center;font-size:10px;font-weight:bold;background-color:#E2EFDA;">รวม</td>'
    for m in active_machines_config:
        m_n = m['name']
        tw_s, tb_s = f"{totals_work[m_n]:,.2f}" if totals_work[m_n] > 0 else '-', f"{totals_break[m_n]:,.2f}" if totals_break[m_n] > 0 else '-'
        total_row_html += f'<td style="border:1px solid #000;padding:3px;text-align:center;font-size:9px;font-weight:bold;background-color:#E2EFDA;">-</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;background-color:#E2EFDA;">{tw_s}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;background-color:#E2EFDA;">{tb_s}</td>'
    total_row_html += '</tr>'
    
    pct_row_html = '<tr><td style="border:1px solid #000;padding:3px;text-align:center;font-size:10px;font-weight:bold;color:red;">คิดเป็น%</td>'
    for m in active_machines_config:
        pct_row_html += f'<td colspan="3" style="border:1px solid #000;padding:3px;text-align:center;font-size:10px;font-weight:bold;color:red;">{percentages[m["name"]]}</td>'
    pct_row_html += '</tr>'

    table_full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Print</title><style>@page {{ size: A4 landscape; margin: 4mm; }} body {{ font-family: 'Sarabun', Tahoma, sans-serif; margin: 0; padding: 5px; background-color: #FFFFFF; color: #000000; }} .header-title {{ text-align: center; font-size: 16px; font-weight: bold; margin-bottom: 4px; }} .banner {{ background-color: #F8CBAD; text-align: center; font-size: 14px; font-weight: bold; padding: 5px; border: 1px solid #000; margin-bottom: 4px; }} table {{ width: 100%; border-collapse: collapse; }} th, td {{ font-family: 'Sarabun', Tahoma, sans-serif; color: #000000 !important; }}</style></head><body><div class="header-title">บริษัท วู้ดเวิร์ค จำกัด สาขา {selected_branch_display}</div><div class="banner">สรุปชั่วโมงการทำงานของเครื่องจักร/เบรกดาวน์ ประจำเดือน....{month_str}................... {year_buddhist}</div><table><thead><tr><th rowspan="2" style="background-color:#E2EFDA;border:1px solid #000;padding:3px;font-size:10px;width:35px;color:#000000 !important;">วันที่</th>{header_row1}</tr><tr>{header_row2}</tr></thead><tbody>{body_rows}{total_row_html}{pct_row_html}</tbody></table></body></html>"""
    
    return raw_data, excel_data, json.dumps(table_full_html)

@st.cache_data(show_spinner=False)
def process_t2(b_id_t2, start_date_str, end_date_str, allowed_tuple, selected_branch_display):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if b_id_t2 == "ทั้งหมด":
                sql_eng = "SELECT e.id AS engine_pk_id, CONVERT(e.machine_name USING utf8mb4) AS engine_code, CONVERT(et.type_name USING utf8mb4) AS type_name, CONVERT(b.branch_name USING utf8mb4) AS branch_name, e.branch_id FROM machines_set e LEFT JOIN engine_types et ON e.engine_type_id = et.id LEFT JOIN branches b ON e.branch_id = b.id WHERE e.machine_type = 'engine' AND e.is_active = 1 ORDER BY b.id ASC, e.machine_name ASC"
                cur.execute(sql_eng)
                engines_list = cur.fetchall()

                sql_trans = "SELECT r.*, b.branch_name FROM fuel_records r LEFT JOIN branches b ON r.branch_id = b.id WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date ASC"
                cur.execute(sql_trans, (start_date_str, end_date_str))
                raw_data = cur.fetchall()
            elif b_id_t2 == "รวมเฉพาะที่มีสิทธิ์":
                placeholders = ', '.join(['%s'] * len(allowed_tuple))
                sql_eng = f"SELECT e.id AS engine_pk_id, CONVERT(e.machine_name USING utf8mb4) AS engine_code, CONVERT(et.type_name USING utf8mb4) AS type_name, CONVERT(b.branch_name USING utf8mb4) AS branch_name, e.branch_id FROM machines_set e LEFT JOIN engine_types et ON e.engine_type_id = et.id LEFT JOIN branches b ON e.branch_id = b.id WHERE e.branch_id IN ({placeholders}) AND e.machine_type = 'engine' AND e.is_active = 1 ORDER BY e.machine_name ASC"
                cur.execute(sql_eng, allowed_tuple)
                engines_list = cur.fetchall()

                sql_trans = f"SELECT r.*, b.branch_name FROM fuel_records r LEFT JOIN branches b ON r.branch_id = b.id WHERE r.branch_id IN ({placeholders}) AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date ASC"
                cur.execute(sql_trans, allowed_tuple + (start_date_str, end_date_str))
                raw_data = cur.fetchall()
            else:
                sql_eng = "SELECT e.id AS engine_pk_id, CONVERT(e.machine_name USING utf8mb4) AS engine_code, CONVERT(et.type_name USING utf8mb4) AS type_name, CONVERT(b.branch_name USING utf8mb4) AS branch_name, e.branch_id FROM machines_set e LEFT JOIN engine_types et ON e.engine_type_id = et.id LEFT JOIN branches b ON e.branch_id = b.id WHERE e.branch_id = %s AND e.machine_type = 'engine' AND e.is_active = 1 ORDER BY e.id ASC"
                cur.execute(sql_eng, (b_id_t2,))
                engines_list = cur.fetchall()

                sql_trans = "SELECT r.*, b.branch_name FROM fuel_records r LEFT JOIN branches b ON r.branch_id = b.id WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date ASC"
                cur.execute(sql_trans, (b_id_t2, start_date_str, end_date_str))
                raw_data = cur.fetchall()
        conn.close()
    except Exception:
        return [], None, None, [], {}

    engine_options_t2, engine_details_t2 = {}, {}
    if engines_list:
        for eng in engines_list:
            code = str(eng.get('engine_code') or '').strip()
            t_name = str(eng.get('type_name') or 'ไม่ระบุประเภท').strip()
            b_name = str(eng.get('branch_name') or '').strip()
            try: branch_code = b_name.split("สาขา ")[1].split()[0]
            except: branch_code = b_name or "N/A"
            lbl = f"{code} (ประเภท: {t_name}) [{branch_code}]"
            engine_options_t2[lbl] = eng['engine_pk_id']
            engine_details_t2[lbl] = {'code': code, 'type': t_name}
    engine_lbl_list = list(engine_options_t2.keys())

    if not raw_data:
        return [], None, None, engine_lbl_list, engine_details_t2

    real_type_map = {}
    for r in raw_data:
        code, b_name, t_name = str(r.get('engine_code') or '').strip(), str(r.get('branch_name') or '').strip(), str(r.get('type_name') or '').strip()
        if b_id_t2 in ["ทั้งหมด", "รวมเฉพาะที่มีสิทธิ์"] and b_name:
            try: b_short = b_name.split("สาขา ")[1].split()[0]
            except: b_short = b_name
            k = f"{code}_{b_short}".lower()
        else:
            k = code.lower()
        if t_name: real_type_map[k] = t_name

    seen_keys, all_engines_config = set(), []
    if engines_list:
        for eng in engines_list:
            code, b_name = str(eng.get('engine_code') or '').strip(), str(eng.get('branch_name') or '').strip()
            if b_id_t2 in ["ทั้งหมด", "รวมเฉพาะที่มีสิทธิ์"] and b_name:
                try: b_short = b_name.split("สาขา ")[1].split()[0]
                except: b_short = b_name
                eng_key, title_name = f"{code}_{b_short}", f"{code} [{b_short}]"
            else:
                eng_key, title_name = code, code

            if not code or eng_key.lower() in seen_keys: continue
            seen_keys.add(eng_key.lower())
            type_nm = real_type_map.get(eng_key.lower()) or str(eng.get('type_name') or 'TOYOTA')
            hex_color = "FFC000" if "tck" in type_nm.lower() else "FF0000"
            all_engines_config.append({"key": eng_key, "code": code, "title": title_name, "brand": type_nm, "branch": b_name, "hex": hex_color})

    matrix_data = {d: {e['key']: {'liters': 0.0, 'hours': 0.0, 'has_data': False} for e in all_engines_config} for d in range(1, 32)}
    for r in raw_data:
        d_num = pd.to_datetime(r['record_date']).day
        e_code, b_name = str(r.get('engine_code') or '').strip(), str(r.get('branch_name') or '').strip()
        
        if b_id_t2 in ["ทั้งหมด", "รวมเฉพาะที่มีสิทธิ์"] and b_name:
            try: b_short = b_name.split("สาขา ")[1].split()[0]
            except: b_short = b_name
            match_key = f"{e_code}_{b_short}"
        else:
            match_key = e_code
        
        for e in all_engines_config:
            if e['key'].lower() == match_key.lower():
                matrix_data[d_num][e['key']]['liters'] += float(r.get('fuel_liters') or 0.0)
                matrix_data[d_num][e['key']]['hours'] += float(r.get('working_hours') or 0.0)
                matrix_data[d_num][e['key']]['has_data'] = True
                break

    engines_config = [e for e in all_engines_config if any([matrix_data[d][e['key']]['has_data'] for d in range(1, 32)])]
    if not engines_config: engines_config = all_engines_config

    start_dt = pd.to_datetime(start_date_str)
    days_in_current_month = pd.Period(start_dt, freq='M').days_in_month
    toyo_keys = [e['key'] for e in engines_config if "tck" not in e['brand'].lower()]
    tck_keys = [e['key'] for e in engines_config if "tck" in e['brand'].lower()]

    totals_hours, totals_liters, avg_l_hr, std_target_hours = {}, {}, {}, {}
    for e in engines_config:
        c_key = e['key']
        tot_h = sum([matrix_data[d][c_key]['hours'] for d in range(1, 32)])
        tot_l = sum([matrix_data[d][c_key]['liters'] for d in range(1, 32)])
        totals_hours[c_key], totals_liters[c_key] = tot_h, tot_l
        avg_l_hr[c_key] = f"{(tot_l / tot_h):.2f}" if tot_h > 0 else "0.00"
        is_backup_car = "สำรอง" in e['title'] or "สำรอง" in e['code'] or "สำรอง" in e.get('brand', '')
        std_target_hours[c_key] = (4 if is_backup_car else 20) * days_in_current_month

    summary_matrix = {}
    for d in range(1, 32):
        summary_matrix[d] = {
            'toyo': {'hours': sum([matrix_data[d][k]['hours'] for k in toyo_keys]), 'liters': sum([matrix_data[d][k]['liters'] for k in toyo_keys])},
            'tck': {'hours': sum([matrix_data[d][k]['hours'] for k in tck_keys]), 'liters': sum([matrix_data[d][k]['liters'] for k in tck_keys])}
        }

    tot_toyo_hours = sum([summary_matrix[d]['toyo']['hours'] for d in range(1, 32)])
    tot_toyo_liters = sum([summary_matrix[d]['toyo']['liters'] for d in range(1, 32)])
    avg_toyo_rate = f"{(tot_toyo_liters / tot_toyo_hours):.2f}" if tot_toyo_hours > 0 else "0.00"

    tot_tck_hours = sum([summary_matrix[d]['tck']['hours'] for d in range(1, 32)])
    tot_tck_liters = sum([summary_matrix[d]['tck']['liters'] for d in range(1, 32)])
    avg_tck_rate = f"{(tot_tck_liters / tot_tck_hours):.2f}" if tot_tck_hours > 0 else "0.00"

    tot_target_toyo = sum([std_target_hours[k] for k in toyo_keys])
    tot_target_tck = sum([std_target_hours[k] for k in tck_keys])

    month_str = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][start_dt.month - 1]
    year_buddhist = start_dt.year + 543

    wb = Workbook()
    ws = wb.active
    ws.title = "Fuel Report Matrix"
    ws.views.sheetView[0].showGridLines = True
    font_title, font_header, font_header_white, font_body, font_total, font_red = Font(name="Sarabun", size=14, bold=True), Font(name="Sarabun", size=9, bold=True), Font(name="Sarabun", size=9, bold=True, color="FFFFFF"), Font(name="Sarabun", size=9), Font(name="Sarabun", size=9, bold=True), Font(name="Sarabun", size=9, bold=True, color="FF0000")
    align_center, align_right = Alignment(horizontal="center", vertical="center", wrap_text=True), Alignment(horizontal="right", vertical="center")
    thin_border = Border(left=Side(style="thin", color="000000"), right=Side(style="thin", color="000000"), top=Side(style="thin", color="000000"), bottom=Side(style="thin", color="000000"))
    fill_magenta, fill_green_sum, fill_blue_sum, fill_pink_sum = PatternFill(start_color="D90082", end_color="D90082", fill_type="solid"), PatternFill(start_color="A9D08E", end_color="A9D08E", fill_type="solid"), PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid"), PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

    last_col_idx = 1 + (len(engines_config) * 3) + 6
    last_col_letter = get_column_letter(last_col_idx)

    ws.merge_cells(f"A1:{last_col_letter}1"); ws["A1"] = f"บริษัท วู้ดเวิร์ค จำกัด สาขา {selected_branch_display}"; ws["A1"].font, ws["A1"].alignment = font_title, align_center
    ws.merge_cells(f"A2:{last_col_letter}2"); ws["A2"] = f"รายงานการใช้เชื้อเพลิงของรถ ประจำเดือน {month_str} {year_buddhist}"; ws["A2"].font, ws["A2"].alignment = font_title, align_center
    ws.merge_cells("A3:A5"); ws["A3"] = "วันที่"; ws["A3"].font, ws["A3"].alignment, ws["A3"].border = font_header, align_center, thin_border
    ws["A4"].border, ws["A5"].border = thin_border, thin_border

    col_idx = 2
    for e in engines_config:
        start_c, end_c = get_column_letter(col_idx), get_column_letter(col_idx + 2)
        ws.merge_cells(f"{start_c}3:{end_c}3"); ws[f"{start_c}3"] = e["title"]; ws[f"{start_c}3"].font, ws[f"{start_c}3"].alignment = font_header, align_center
        ws.merge_cells(f"{start_c}4:{end_c}4"); ws[f"{start_c}4"] = e["brand"]; ws[f"{start_c}4"].font = font_header_white if e["hex"] == "FF0000" else font_header; ws[f"{start_c}4"].alignment = align_center
        fill_color = PatternFill(start_color=e["hex"], end_color=e["hex"], fill_type="solid"); ws[f"{start_c}4"].fill = fill_color
        for c in range(col_idx, col_idx + 3): ws[f"{get_column_letter(c)}3"].border = thin_border; ws[f"{get_column_letter(c)}4"].border = thin_border; ws[f"{get_column_letter(c)}4"].fill = fill_color
        for i, sh in enumerate(["ชม.", "ลิตร", "ล/ชม."]): cell_ref = f"{get_column_letter(col_idx + i)}5"; ws[cell_ref] = sh; ws[cell_ref].font, ws[cell_ref].alignment, ws[cell_ref].border = font_header, align_center, thin_border
        col_idx += 3

    for grp_title, grp_bg, is_white in [("toyo", "FF0000", True), ("TCK", "FFC000", False)]:
        start_c, end_c = get_column_letter(col_idx), get_column_letter(col_idx + 2)
        ws.merge_cells(f"{start_c}3:{end_c}4"); ws[f"{start_c}3"] = grp_title; ws[f"{start_c}3"].font = font_header_white if is_white else font_header; ws[f"{start_c}3"].alignment = align_center; ws[f"{start_c}3"].fill = PatternFill(start_color=grp_bg, end_color=grp_bg, fill_type="solid")
        for c in range(col_idx, col_idx + 3):
            for r_h in [3, 4]: ws[f"{get_column_letter(c)}{r_h}"].border = thin_border; ws[f"{get_column_letter(c)}{r_h}"].fill = PatternFill(start_color=grp_bg, end_color=grp_bg, fill_type="solid")
        for i, sh in enumerate(["ชม.", "ลิตร", "ล/ชม."]): cell_ref = f"{get_column_letter(col_idx + i)}5"; ws[cell_ref] = sh; ws[cell_ref].font, ws[cell_ref].alignment, ws[cell_ref].border = font_header, align_center, thin_border
        col_idx += 3

    ws.row_dimensions[3].height, ws.row_dimensions[4].height, ws.row_dimensions[5].height = 22, 22, 20

    current_row = 6
    for day in range(1, 32):
        ws[f"A{current_row}"] = day; ws[f"A{current_row}"].font, ws[f"A{current_row}"].alignment, ws[f"A{current_row}"].border = font_header, align_center, thin_border
        c_idx = 2
        for e in engines_config:
            item = matrix_data[day][e['key']]
            cell_h, cell_l, cell_r = ws[f"{get_column_letter(c_idx)}{current_row}"], ws[f"{get_column_letter(c_idx+1)}{current_row}"], ws[f"{get_column_letter(c_idx+2)}{current_row}"]
            cell_h.value = (item['hours'] if item['hours'] > 0 else "-") if item['has_data'] else ""
            cell_l.value = (item['liters'] if item['liters'] > 0 else "-") if item['has_data'] else ""
            cell_r.value = (round(item['liters'] / item['hours'], 2) if item['hours'] > 0 else "-") if item['has_data'] else ""
            for cell in [cell_h, cell_l, cell_r]:
                cell.font, cell.alignment, cell.border = font_body, (align_right if isinstance(cell.value, (int, float)) else align_center), thin_border
                if isinstance(cell.value, (int, float)): cell.number_format = '#,##0.00'
            c_idx += 3

        for grp_k in ['toyo', 'tck']:
            grp_item = summary_matrix[day][grp_k]
            ws[f"{get_column_letter(c_idx)}{current_row}"] = grp_item['hours'] if grp_item['hours'] > 0 else "-"
            ws[f"{get_column_letter(c_idx+1)}{current_row}"] = grp_item['liters'] if grp_item['liters'] > 0 else "-"
            ws[f"{get_column_letter(c_idx+2)}{current_row}"] = round(grp_item['liters']/grp_item['hours'], 2) if grp_item['hours'] > 0 else "-"
            for offset in range(3):
                cell = ws[f"{get_column_letter(c_idx+offset)}{current_row}"]
                cell.font, cell.alignment, cell.border = font_body, (align_right if isinstance(cell.value, (int, float)) else align_center), thin_border
                if isinstance(cell.value, (int, float)): cell.number_format = '#,##0.00'
            c_idx += 3
        current_row += 1

    def add_summary_row(row_label, target_data, toyo_data, tck_data, bg_color=None, font_style=font_total, align_style=align_center):
        nonlocal current_row
        ws[f"A{current_row}"] = row_label
        ws[f"A{current_row}"].font, ws[f"A{current_row}"].alignment, ws[f"A{current_row}"].border = font_total, align_center, thin_border
        if bg_color: ws[f"A{current_row}"].fill = bg_color
        
        c_i = 2
        for e in engines_config:
            val = target_data.get(e['key'], "-")
            ws[f"{get_column_letter(c_i)}{current_row}"] = val
            cell = ws[f"{get_column_letter(c_i)}{current_row}"]
            cell.font, cell.alignment, cell.border = (font_header_white if font_style == font_header_white else font_style), align_style, thin_border
            if bg_color: cell.fill = bg_color
            if isinstance(val, (int, float)) and font_style != font_header_white: cell.number_format = '#,##0.00'
            
            if bg_color and font_style != font_total:
                ws.merge_cells(f"{get_column_letter(c_i)}{current_row}:{get_column_letter(c_i+2)}{current_row}")
                for off in [1, 2]:
                    cell_off = ws[f"{get_column_letter(c_i+off)}{current_row}"]
                    cell_off.border = thin_border
                    cell_off.fill = bg_color
            else:
                ws[f"{get_column_letter(c_i+1)}{current_row}"] = val if isinstance(val, str) else ""
                ws[f"{get_column_letter(c_i+2)}{current_row}"] = val if isinstance(val, str) else ""
                for off in [1, 2]: ws[f"{get_column_letter(c_i+off)}{current_row}"].border = thin_border
            c_i += 3
            
        for sum_val in [toyo_data, tck_data]:
            ws[f"{get_column_letter(c_i)}{current_row}"] = sum_val
            cell = ws[f"{get_column_letter(c_i)}{current_row}"]
            cell.font, cell.alignment, cell.border = (font_header_white if font_style == font_header_white else font_style), align_style, thin_border
            if bg_color: cell.fill = bg_color
            
            if bg_color and font_style != font_total:
                ws.merge_cells(f"{get_column_letter(c_i)}{current_row}:{get_column_letter(c_i+2)}{current_row}")
                for off in [1, 2]:
                    cell_off = ws[f"{get_column_letter(c_i+off)}{current_row}"]
                    cell_off.border = thin_border
                    cell_off.fill = bg_color
            else:
                ws[f"{get_column_letter(c_i+1)}{current_row}"] = ""
                ws[f"{get_column_letter(c_i+2)}{current_row}"] = ""
                for off in [1, 2]: ws[f"{get_column_letter(c_i+off)}{current_row}"].border = thin_border
            c_i += 3
        current_row += 1

    add_summary_row(f"ชม.รวม1-{days_in_current_month}", std_target_hours, tot_target_toyo, tot_target_tck, fill_magenta, font_header_white)
    
    ws[f"A{current_row}"] = f"ชม.ใช้จริง 1-{days_in_current_month}"; ws[f"A{current_row}"].font, ws[f"A{current_row}"].alignment, ws[f"A{current_row}"].border = font_total, align_center, thin_border
    c_idx = 2
    for e in engines_config:
        c_key = e['key']
        ws[f"{get_column_letter(c_idx)}{current_row}"] = round(totals_hours[c_key], 0) if totals_hours[c_key]>0 else "-"
        ws[f"{get_column_letter(c_idx+1)}{current_row}"] = round(totals_liters[c_key], 0) if totals_liters[c_key]>0 else "-"
        ws[f"{get_column_letter(c_idx+2)}{current_row}"] = avg_l_hr[c_key]
        for offset in range(3): ws[f"{get_column_letter(c_idx+offset)}{current_row}"].font, ws[f"{get_column_letter(c_idx+offset)}{current_row}"].alignment, ws[f"{get_column_letter(c_idx+offset)}{current_row}"].border = font_total, align_right, thin_border
        c_idx += 3
    for th, tl, tr in [(tot_toyo_hours, tot_toyo_liters, avg_toyo_rate), (tot_tck_hours, tot_tck_liters, avg_tck_rate)]:
        ws[f"{get_column_letter(c_idx)}{current_row}"] = round(th, 0)
        ws[f"{get_column_letter(c_idx+1)}{current_row}"] = round(tl, 0)
        ws[f"{get_column_letter(c_idx+2)}{current_row}"] = tr
        for offset in range(3): ws[f"{get_column_letter(c_idx+offset)}{current_row}"].font, ws[f"{get_column_letter(c_idx+offset)}{current_row}"].alignment, ws[f"{get_column_letter(c_idx+offset)}{current_row}"].border = font_total, align_right, thin_border
        c_idx += 3
    current_row += 1

    ws[f"A{current_row}"] = "ส่วนต่าง"; ws[f"A{current_row}"].font, ws[f"A{current_row}"].alignment, ws[f"A{current_row}"].border = font_total, align_center, thin_border
    c_idx = 2
    for e in engines_config:
        diff_val = std_target_hours[e['key']] - round(totals_hours[e['key']], 0)
        ws[f"{get_column_letter(c_idx)}{current_row}"] = int(diff_val); ws[f"{get_column_letter(c_idx)}{current_row}"].font, ws[f"{get_column_letter(c_idx)}{current_row}"].alignment, ws[f"{get_column_letter(c_idx)}{current_row}"].border = font_red if diff_val < 0 else font_total, align_center, thin_border
        for offset in [1, 2]: ws[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border
        c_idx += 3
    for diff_val in [tot_target_toyo - round(tot_toyo_hours, 0), tot_target_tck - round(tot_tck_hours, 0)]:
        ws[f"{get_column_letter(c_idx)}{current_row}"] = int(diff_val); ws[f"{get_column_letter(c_idx)}{current_row}"].font, ws[f"{get_column_letter(c_idx)}{current_row}"].alignment, ws[f"{get_column_letter(c_idx)}{current_row}"].border = font_red if diff_val < 0 else font_total, align_center, thin_border
        for offset in [1, 2]: ws[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border
        c_idx += 3
    current_row += 1

    add_summary_row("ชม.รวมทั้งเดือน", std_target_hours, tot_target_toyo, tot_target_tck, fill_blue_sum, font_total, align_center)
    diff_dict = {e['key']: std_target_hours[e['key']] - round(totals_hours[e['key']], 0) for e in engines_config}
    add_summary_row("ชม.คงเหลือทั้งเดือน", diff_dict, tot_target_toyo - round(tot_toyo_hours, 0), tot_target_tck - round(tot_tck_hours, 0), fill_pink_sum, font_red, align_center)

    ws.column_dimensions['A'].width = 16
    for c in range(2, col_idx): ws.column_dimensions[get_column_letter(c)].width = 10

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)

    header_row1 = "".join([f'<th colspan="3" style="border:1px solid #000;padding:3px;font-size:10px;text-align:center;">{e["title"]}</th>' for e in engines_config]) + '<th colspan="3" style="background-color:#FF0000;color:#FFF;border:1px solid #000;padding:3px;font-size:10px;text-align:center;" rowspan="2">toyo</th><th colspan="3" style="background-color:#FFC000;border:1px solid #000;padding:3px;font-size:10px;text-align:center;" rowspan="2">TCK</th>'
    header_row2 = "".join([f'<th colspan="3" style="background-color:#{e["hex"]};color:{"#FFF" if e["hex"]=="FF0000" else "#000"};border:1px solid #000;padding:3px;font-size:10px;text-align:center;">{e["brand"]}</th>' for e in engines_config])
    header_row3 = "".join(['<th style="border:1px solid #000;padding:2px;font-size:8px;width:30px;">ชม.</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:30px;">ลิตร</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:30px;">ล/ชม.</th>' for _ in range(len(engines_config) + 2)])

    body_rows = ""
    for day in range(1, 32):
        body_rows += f'<tr><td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;font-weight:bold;">{day}</td>'
        for e in engines_config:
            item = matrix_data[day][e['key']]
            h_val, l_val, r_val = (f"{item['hours']:,.2f}", f"{item['liters']:,.2f}", f"{(item['liters']/item['hours']):,.2f}") if item['has_data'] and item['hours']>0 else ("-", "-", "-")
            body_rows += f'<td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{h_val}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{l_val}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{r_val}</td>'
        for grp_k in ['toyo', 'tck']:
            grp_item = summary_matrix[day][grp_k]
            th_s, tl_s, tr_s = (f"{grp_item['hours']:,.2f}", f"{grp_item['liters']:,.2f}", f"{(grp_item['liters']/grp_item['hours']):,.2f}") if grp_item['hours']>0 else ("-", "-", "-")
            body_rows += f'<td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{th_s}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{tl_s}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{tr_s}</td>'
        body_rows += '</tr>'

    total_row_html = '<tr><td style="border:1px solid #000;padding:3px;text-align:center;font-size:10px;font-weight:bold;">รวม</td>'
    for e in engines_config:
        c_key = e['key']
        t_h, t_l = f"{totals_hours[c_key]:,.2f}" if totals_hours[c_key] > 0 else "-", f"{totals_liters[c_key]:,.2f}" if totals_liters[c_key] > 0 else "-"
        total_row_html += f'<td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{t_h}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{t_l}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;"></td>'
    for th, tl in [(tot_toyo_hours, tot_toyo_liters), (tot_tck_hours, tot_tck_liters)]:
        total_row_html += f'<td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{th:,.2f}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{tl:,.2f}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;"></td>'
    total_row_html += '</tr>'

    table_full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Print</title><style>@page {{ size: A4 landscape; margin: 4mm; }} body {{ font-family: 'Sarabun', Tahoma, sans-serif; margin: 0; padding: 5px; background-color: #FFFFFF; color: #000000; }} .header-title {{ text-align: center; font-size: 16px; font-weight: bold; margin-bottom: 4px; }} .banner {{ text-align: center; font-size: 14px; font-weight: bold; padding: 5px; margin-bottom: 4px; }} table {{ width: 100%; border-collapse: collapse; }} th, td {{ font-family: 'Sarabun', Tahoma, sans-serif; color: #000000 !important; }}</style></head><body><div class='header-title'>บริษัท วู้ดเวิร์ค จำกัด สาขา {selected_branch_display}</div><div class='banner'>รายงานการใช้เชื้อเพลิงของรถ ประจำเดือน {month_str} {year_buddhist}</div><table><thead><tr><th rowspan='3' style='border:1px solid #000;padding:3px;font-size:10px;width:35px;'>วันที่</th>{header_row1}</tr><tr>{header_row2}</tr><tr>{header_row3}</tr></thead><tbody>{body_rows}{total_row_html}</tbody></table></body></html>"
    
    return raw_data, excel_buffer.getvalue(), json.dumps(table_full_html), engine_lbl_list, engine_details_t2


@st.cache_data(show_spinner=False)
def process_t3(b_id_t3, start_date_str, end_date_str, allowed_tuple, selected_branch_display):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if b_id_t3 == "ทั้งหมด":
                sql = "SELECT r.*, b.branch_name FROM boiler_pressure_records r LEFT JOIN branches b ON r.branch_id = b.id WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date ASC"
                cur.execute(sql, (start_date_str, end_date_str))
            elif b_id_t3 == "รวมเฉพาะที่มีสิทธิ์":
                placeholders = ', '.join(['%s'] * len(allowed_tuple))
                sql = f"SELECT r.*, b.branch_name FROM boiler_pressure_records r LEFT JOIN branches b ON r.branch_id = b.id WHERE r.branch_id IN ({placeholders}) AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date ASC"
                cur.execute(sql, allowed_tuple + (start_date_str, end_date_str))
            else:
                sql = "SELECT r.*, b.branch_name FROM boiler_pressure_records r LEFT JOIN branches b ON r.branch_id = b.id WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date ASC"
                cur.execute(sql, (b_id_t3, start_date_str, end_date_t3))
            raw_data = cur.fetchall()
        conn.close()
    except Exception:
        return [], None, None

    if not raw_data: return [], None, None

    seen_b_keys, branches_config = set(), []
    for r in raw_data:
        b_name = str(r.get('branch_name') or '').strip()
        try: b_code = b_name.split("สาขา ")[1].split()[0]
        except: b_code = b_name or "WU"
        if b_code.lower() not in seen_b_keys:
            seen_b_keys.add(b_code.lower())
            branches_config.append({"code": b_code, "full_name": b_name})

    if not branches_config: branches_config = [{"code": "WU", "full_name": selected_branch_display}]

    matrix_data = {d: {b['code']: {'total': 0.0, 'drop': 0.0, 'pm': 0.0, 'non_pm': 0.0, 'remark': '', 'has_data': False} for b in branches_config} for d in range(1, 32)}
    for r in raw_data:
        d_num = pd.to_datetime(r['record_date']).day
        b_name = str(r.get('branch_name') or '').strip()
        try: b_code = b_name.split("สาขา ")[1].split()[0]
        except: b_code = b_name or "WU"
        for b in branches_config:
            if b['code'].lower() == b_code.lower():
                matrix_data[d_num][b['code']] = {'total': float(r.get('total_count') or 0.0), 'drop': float(r.get('total_drop') or 0.0), 'pm': float(r.get('pm_drop') or 0.0), 'non_pm': float(r.get('non_pm_drop') or 0.0), 'remark': str(r.get('remark') or '').strip(), 'has_data': True}
                break

    branch_totals = {}
    for b in branches_config:
        b_code = b['code']
        tot_c = sum([matrix_data[d][b_code]['total'] for d in range(1, 32)])
        tot_d = sum([matrix_data[d][b_code]['drop'] for d in range(1, 32)])
        pm_d = sum([matrix_data[d][b_code]['pm'] for d in range(1, 32)])
        npm_d = sum([matrix_data[d][b_code]['non_pm'] for d in range(1, 32)])
        branch_totals[b_code] = {'total': tot_c, 'drop': tot_d, 'pm': pm_d, 'non_pm': npm_d, 'p_tot': f"{(tot_d/tot_c*100):.2f}%" if tot_c>0 else "0.00%", 'p_pm': f"{(pm_d/tot_c*100):.2f}%" if tot_c>0 else "0.00%", 'p_npm': f"{(npm_d/tot_c*100):.2f}%" if tot_c>0 else "0.00%"}

    start_dt = pd.to_datetime(start_date_str)
    month_str = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][start_dt.month - 1]
    year_buddhist = start_dt.year + 543

    wb = Workbook()
    ws = wb.active
    ws.title = "Pressure Report Matrix"
    ws.views.sheetView[0].showGridLines = True
    
    font_title, font_banner, font_header_purple, font_total, font_total_red, font_total_blue = Font(name="Sarabun", size=13, bold=True, color="006100"), Font(name="Sarabun", size=12, bold=True), Font(name="Sarabun", size=11, bold=True, color="FFFFFF"), Font(name="Sarabun", size=9, bold=True), Font(name="Sarabun", size=9, bold=True, color="FF0000"), Font(name="Sarabun", size=9, bold=True, color="0000FF")
    align_center, align_right = Alignment(horizontal="center", vertical="center", wrap_text=True), Alignment(horizontal="right", vertical="center")
    thin_border = Border(left=Side(style="thin", color="000000"), right=Side(style="thin", color="000000"), top=Side(style="thin", color="000000"), bottom=Side(style="thin", color="000000"))
    fill_green_banner, fill_yellow_banner, fill_purple, fill_yellow_cell = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid"), PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid"), PatternFill(start_color="E000E0", end_color="E000E0", fill_type="solid"), PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

    last_col_letter = get_column_letter(1 + (len(branches_config) * 8))

    ws.merge_cells(f"A1:{last_col_letter}1"); ws["A1"] = "รายงานการตกของ แรงดันไอน้ำปลายทาง ของบอยเลอร์ แบบเปรียบเทียบ"; ws["A1"].font, ws["A1"].alignment, ws["A1"].fill = font_title, align_center, fill_green_banner
    ws.merge_cells(f"A2:{last_col_letter}2"); ws["A2"] = f"ประจำเดือน {month_str} {year_buddhist}"; ws["A2"].font, ws["A2"].alignment, ws["A2"].fill = font_banner, align_center, fill_yellow_banner
    ws.merge_cells("A3:A5"); ws["A3"] = "วันที่"; ws["A3"].font, ws["A3"].alignment, ws["A3"].fill, ws["A3"].border = font_header_purple, align_center, fill_purple, thin_border
    ws["A4"].border, ws["A5"].border = thin_border, thin_border

    col_idx = 2
    for b in branches_config:
        st_c, en_c = get_column_letter(col_idx), get_column_letter(col_idx + 7)
        ws.merge_cells(f"{st_c}3:{en_c}3"); ws[f"{st_c}3"] = b["code"]; ws[f"{st_c}3"].font, ws[f"{st_c}3"].alignment, ws[f"{st_c}3"].fill = font_header_purple, align_center, fill_purple
        c_cnt, c_drp_st, c_drp_en, c_pct_st, c_pct_en, c_rem = get_column_letter(col_idx), get_column_letter(col_idx + 1), get_column_letter(col_idx + 3), get_column_letter(col_idx + 4), get_column_letter(col_idx + 6), get_column_letter(col_idx + 7)
        ws[f"{c_cnt}4"] = "นับทั้งหมด"; ws.merge_cells(f"{c_drp_st}4:{c_drp_en}4"); ws[f"{c_drp_st}4"] = "แรงดันตก (ครั้ง)"; ws.merge_cells(f"{c_pct_st}4:{c_pct_en}4"); ws[f"{c_pct_st}4"] = "แรงดันตก (%)"; ws[f"{c_rem}4"] = "หมายเหตุ"
        for c_i in range(col_idx, col_idx + 8): cell_h = ws[f"{get_column_letter(c_i)}4"]; cell_h.font, cell_h.alignment, cell_h.fill, cell_h.border = font_header_purple, align_center, fill_purple, thin_border
        sub_cols = ["จำนวน\n(ครั้ง)", "ตกทั้งหมด", "ตกตาม\nเงื่อนไขPM", "เกินนอกเหนือ\nจากการPM", "ตกทั้งหมด", "ตกตาม\nเงื่อนไขPM", "เกินนอกเหนือ\nจากการPM", ""]
        for i, sh in enumerate(sub_cols): cell_ref = f"{get_column_letter(col_idx + i)}5"; ws[cell_ref] = sh; ws[cell_ref].font, ws[cell_ref].alignment, ws[cell_ref].fill, ws[cell_ref].border = font_header_purple, align_center, fill_purple, thin_border
        col_idx += 8

    current_row = 6
    for day in range(1, 32):
        ws[f"A{current_row}"] = day; ws[f"A{current_row}"].font, ws[f"A{current_row}"].alignment, ws[f"A{current_row}"].border = Font(name="Sarabun", size=9, bold=True), align_center, thin_border
        c_idx = 2
        for b in branches_config:
            item = matrix_data[day][b['code']]
            if item['has_data']:
                ws[f"{get_column_letter(c_idx)}{current_row}"].value = item['total']
                ws[f"{get_column_letter(c_idx+1)}{current_row}"].value = item['drop']
                ws[f"{get_column_letter(c_idx+2)}{current_row}"].value = item['pm']
                ws[f"{get_column_letter(c_idx+3)}{current_row}"].value = item['non_pm']
                ws[f"{get_column_letter(c_idx+4)}{current_row}"].value = f"{(item['drop']/item['total']*100):.2f}%" if item['total']>0 else "0.00%"
                ws[f"{get_column_letter(c_idx+5)}{current_row}"].value = f"{(item['pm']/item['total']*100):.2f}%" if item['total']>0 else "0.00%"
                ws[f"{get_column_letter(c_idx+6)}{current_row}"].value = f"{(item['non_pm']/item['total']*100):.2f}%" if item['total']>0 else "0.00%"
                ws[f"{get_column_letter(c_idx+7)}{current_row}"].value = item['remark']
            for offset in range(8):
                cell = ws[f"{get_column_letter(c_idx+offset)}{current_row}"]
                cell.font, cell.border = Font(name="Sarabun", size=9), thin_border
                if offset < 4 and cell.value != "": cell.alignment, cell.fill, cell.font = (align_center if offset==0 else align_right), fill_yellow_cell, font_total
            c_idx += 8
        current_row += 1

    ws[f"A{current_row}"] = "รวม"; ws[f"A{current_row}"].font, ws[f"A{current_row}"].alignment, ws[f"A{current_row}"].border = font_total, align_center, thin_border
    c_idx = 2
    for b in branches_config:
        bt = branch_totals[b['code']]
        ws[f"{get_column_letter(c_idx)}{current_row}"] = bt['total'] if bt['total'] > 0 else "-"
        ws[f"{get_column_letter(c_idx+1)}{current_row}"] = bt['drop'] if bt['drop'] > 0 else "-"
        ws[f"{get_column_letter(c_idx+2)}{current_row}"] = bt['pm'] if bt['pm'] > 0 else "-"
        ws[f"{get_column_letter(c_idx+3)}{current_row}"] = bt['non_pm'] if bt['non_pm'] > 0 else "-"
        ws[f"{get_column_letter(c_idx+4)}{current_row}"] = bt['p_tot']
        ws[f"{get_column_letter(c_idx+5)}{current_row}"] = bt['p_pm']
        ws[f"{get_column_letter(c_idx+6)}{current_row}"] = bt['p_npm']

        for offset in range(4): cell = ws[f"{get_column_letter(c_idx+offset)}{current_row}"]; cell.font, cell.alignment, cell.border = font_total, (align_center if offset==0 else align_right), thin_border
        ws[f"{get_column_letter(c_idx+4)}{current_row}"].font, ws[f"{get_column_letter(c_idx+4)}{current_row}"].alignment, ws[f"{get_column_letter(c_idx+4)}{current_row}"].border = font_total_red, align_right, thin_border
        ws[f"{get_column_letter(c_idx+5)}{current_row}"].font, ws[f"{get_column_letter(c_idx+5)}{current_row}"].alignment, ws[f"{get_column_letter(c_idx+5)}{current_row}"].border = font_total, align_right, thin_border
        ws[f"{get_column_letter(c_idx+6)}{current_row}"].font, ws[f"{get_column_letter(c_idx+6)}{current_row}"].alignment, ws[f"{get_column_letter(c_idx+6)}{current_row}"].border = font_total_blue, align_right, thin_border
        ws[f"{get_column_letter(c_idx+7)}{current_row}"].border = thin_border
        c_idx += 8

    ws.column_dimensions['A'].width = 8
    for c in range(2, col_idx):
        ws.column_dimensions[get_column_letter(c)].width = 13

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_data = excel_buffer.getvalue()

    header_row1 = "".join([f'<th colspan="8" style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:4px;font-size:11px;text-align:center;">{b["code"]}</th>' for b in branches_config])
    header_row2 = "".join(['<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:3px;font-size:9px;">นับทั้งหมด</th><th colspan="3" style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:3px;font-size:9px;">แรงดันตก (ครั้ง)</th><th colspan="3" style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:3px;font-size:9px;">แรงดันตก (%)</th><th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:3px;font-size:9px;">หมายเหตุ</th>' for _ in branches_config])
    header_row3 = "".join(['<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:35px;">จำนวน<br>(ครั้ง)</th><th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:35px;">ตกทั้งหมด</th><th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:35px;">ตกตาม<br>เงื่อนไขPM</th><th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:40px;">เกินนอกเหนือ<br>จากการPM</th><th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:35px;">ตกทั้งหมด</th><th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:35px;">ตกตาม<br>เงื่อนไขPM</th><th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:40px;">เกินนอกเหนือ<br>จากการPM</th><th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:90px;"></th>' for _ in branches_config])

    body_rows = ""
    for day in range(1, 32):
        body_rows += f'<tr><td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;font-weight:bold;">{day}</td>'
        for b in branches_config:
            item = matrix_data[day][b['code']]
            if item['has_data']:
                c_tot_s, c_drp_s = f"{item['total']:,.2f}", f"{item['drop']:,.2f}"
                c_pm_s, c_npm_s = f"{int(item['pm'])}", f"{int(item['non_pm'])}"
                p_drp_s = f"{(item['drop'] / item['total'] * 100):.2f}%" if item['total'] > 0 else "0.00%"
                p_pm_s = f"{(item['pm'] / item['total'] * 100):.2f}%" if item['total'] > 0 else "0.00%"
                p_npm_s = f"{(item['non_pm'] / item['total'] * 100):.2f}%" if item['total'] > 0 else "0.00%"
                rem_s = item['remark']
            else:
                c_tot_s, c_drp_s, c_pm_s, c_npm_s, p_drp_s, p_pm_s, p_npm_s, rem_s = "", "", "", "", "", "", "", ""
            body_rows += f'<td style="background-color:#FFFF00;border:1px solid #000;padding:2px;text-align:center;font-size:9px;font-weight:bold;">{c_tot_s}</td><td style="background-color:#FFFF00;border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{c_drp_s}</td><td style="background-color:#FFFF00;border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{c_pm_s}</td><td style="background-color:#FFFF00;border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{c_npm_s}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{p_drp_s}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{p_pm_s}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{p_npm_s}</td><td style="border:1px solid #000;padding:2px;text-align:left;font-size:9px;">{rem_s}</td>'
        body_rows += '</tr>'

    total_row_html = '<tr><td style="border:1px solid #000;padding:3px;text-align:center;font-size:10px;font-weight:bold;">รวม</td>'
    for b in branches_config:
        bt = branch_totals[b['code']]
        t_cnt_s = f"{int(bt['total']):,}" if bt['total'] > 0 else "-"
        t_drp_s = f"{int(bt['drop']):,}" if bt['drop'] > 0 else "-"
        t_pm_s = f"{int(bt['pm']):,}" if bt['pm'] > 0 else "-"
        t_npm_s = f"{int(bt['non_pm']):,}" if bt['non_pm'] > 0 else "-"
        total_row_html += f'<td style="border:1px solid #000;padding:3px;text-align:center;font-size:9px;font-weight:bold;">{t_cnt_s}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{t_drp_s}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{t_pm_s}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{t_npm_s}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;color:red;">{bt["p_tot"]}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{bt["p_pm"]}</td><td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;color:blue;">{bt["p_npm"]}</td><td style="border:1px solid #000;padding:3px;text-align:left;font-size:9px;"></td>'
    total_row_html += '</tr>'

    table_full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Print</title><style>@page {{ size: A4 landscape; margin: 4mm; }} body {{ font-family: 'Sarabun', Tahoma, sans-serif; margin: 0; padding: 5px; background-color: #FFFFFF; color: #000000; }} .header-banner1 {{ background-color: #00FF00; color: #006100; text-align: center; font-size: 16px; font-weight: bold; padding: 6px; border: 1px solid #000; }} .header-banner2 {{ background-color: #FFFF00; color: #000; text-align: center; font-size: 14px; font-weight: bold; padding: 5px; border: 1px solid #000; margin-bottom: 4px; }} table {{ width: 100%; border-collapse: collapse; }} th, td {{ font-family: 'Sarabun', Tahoma, sans-serif; color: #000000 !important; }}</style></head><body><div class='header-banner1'>รายงานการตกของ แรงดันไอน้ำปลายทาง ของบอยเลอร์ แบบเปรียบเทียบ</div><div class='header-banner2'>ประจำเดือน {month_str} {year_buddhist}</div><table><thead><tr><th rowspan='3' style='background-color:#E000E0;color:#FFF;border:1px solid #000;padding:3px;font-size:10px;width:35px;color:#000000 !important;'>วันที่</th>{header_row1}</tr><tr>{header_row2}</tr><tr>{header_row3}</tr></thead><tbody>{body_rows}{total_row_html}</tbody></table></body></html>"
    
    return raw_data, excel_buffer.getvalue(), json.dumps(table_full_html)

@st.cache_data(show_spinner=False)
def process_t4(b_id_t4, start_date_str, end_date_str, allowed_tuple, selected_branch_display):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if b_id_t4 == "ทั้งหมด":
                sql = "SELECT r.*, b.branch_name FROM boiler_fuel_records r LEFT JOIN branches b ON r.branch_id = b.id WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"
                cur.execute(sql, (start_date_str, end_date_str))
            elif b_id_t4 == "รวมเฉพาะที่มีสิทธิ์":
                placeholders = ', '.join(['%s'] * len(allowed_tuple))
                sql = f"SELECT r.*, b.branch_name FROM boiler_fuel_records r LEFT JOIN branches b ON r.branch_id = b.id WHERE r.branch_id IN ({placeholders}) AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"
                cur.execute(sql, allowed_tuple + (start_date_str, end_date_str))
            else:
                sql = "SELECT r.*, b.branch_name FROM boiler_fuel_records r LEFT JOIN branches b ON r.branch_id = b.id WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"
                cur.execute(sql, (b_id_t4, start_date_str, end_date_t4))
            raw_data = cur.fetchall()
        conn.close()
    except Exception:
        return [], None, None

    if not raw_data: return [], None, None

    pk_col = list(raw_data[0].keys())[0]

    std_fuel_val = 280.00
    df_display = []
    for r in raw_data:
        s_w, w_w, ww_w = float(r.get('sawdust_weight') or 0.0), float(r.get('wood_weight') or 0.0), float(r.get('waste_wood_weight') or 0.0)
        s_p, w_p, ww_p = float(r.get('sawdust_price') or 0.0), float(r.get('wood_price') or 0.0), float(r.get('waste_wood_price') or 0.0)
        steam_prod, w_hours = float(r.get('steam_production') or 1.0), float(r.get('working_hours') or 1.0)
        
        tot_w, tot_p = s_w + w_w + ww_w, s_p + w_p + ww_p
        act_r = (tot_w / steam_prod) * 1000 if steam_prod > 0 else 0.0
        
        df_display.append({
            'ID รายการ': r[pk_col], 'วันที่': str(r.get('record_date')), 'สาขา': r.get('branch_name'),
            'นหน.ขี้เลื่อย (ตัน)': s_w, 'นหน.ปีกไม้ (ตัน)': w_w, 'นหน.เศษไม้เสีย (ตัน)': ww_w,
            '4.1 รวมน้ำหนักเชื้อเพลิง (ตัน)': round(tot_w, 2),
            'ราคาขี้เลื่อย (บาท)': s_p, 'ราคาปีกไม้ (บาท)': w_p, 'ราคาเศษไม้เสีย (บาท)': ww_p,
            '4.2 รวมราคาเชื้อเพลิง (บาท)': round(tot_p, 2),
            'ผลิตไอน้ำ (ตัน/วัน)': steam_prod, 'ชม.ทำงาน': w_hours,
            '4.3 ตันต่อชั่วโมง': round(steam_prod/w_hours, 2) if w_hours > 0 else 0.0,
            '4.4 ค่าเชื้อเพลิง (บาท/ตันไอน้ำ)': round(tot_p/steam_prod, 2) if steam_prod > 0 else 0.0,
            '4.5 ผลงาน (กก./ตันไอน้ำ)': round(act_r, 2), '4.5 ผลต่าง (STD-ผลงาน)': round(std_fuel_val - act_r, 2)
        })

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame(df_display).to_excel(writer, index=False, sheet_name='Boiler Fuel Report')
    
    table_html = pd.DataFrame(df_display).to_html(index=False, classes='report-table')
    
    start_dt = pd.to_datetime(start_date_str)
    month_str = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][start_dt.month - 1]
    year_buddhist = start_dt.year + 543

    table_full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Print</title><style>@page {{ size: A4 landscape; margin: 4mm; }} body {{ font-family: 'Sarabun', Tahoma, sans-serif; margin: 0; padding: 5px; background-color: #FFFFFF; color: #000000; }} .header-title {{ text-align: center; font-size: 16px; font-weight: bold; margin-bottom: 10px; color: #000000 !important; }} table {{ width: 100%; border-collapse: collapse; }} th, td {{ font-family: 'Sarabun', Tahoma, sans-serif; border: 1px solid #000; padding: 6px; font-size: 11px; text-align: center; color: #000000 !important; }} th {{ background-color: #E2EFDA; color: #000000 !important; }}</style></head><body><div class='header-title'>รายงานสรุปเชื้อเพลิงบอยเลอร์ สาขา {selected_branch_display} <br>ประจำเดือน {month_str} {year_buddhist}</div>{table_html}</body></html>"
    
    return raw_data, buffer.getvalue(), json.dumps(table_full_html)

# ==========================================================
# 📊 4. ฟังก์ชันหลักสำหรับ Render Report Tabs
# ==========================================================
def render_all_reports_module(user_branch_name):
    st.markdown("""
        <style>
        div[data-testid="stScrollableContainer"] div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; min-width: 1000px !important; align-items: center !important; padding: 4px 0 !important; }
        div[data-testid="stPopover"] > button { background-color: transparent !important; border: none !important; color: #64748B !important; font-size: 20px !important; font-weight: 900 !important; padding: 0px 8px !important; box-shadow: none !important; }
        div[data-testid="stPopover"] > button:hover { color: #0F172A !important; background-color: #E2E8F0 !important; border-radius: 50% !important; }
        div[data-testid="stPopoverBody"] button { text-align: left !important; width: 100% !important; border: none !important; background: transparent !important; padding: 6px 12px !important; font-size: 14px !important; justify-content: flex-start !important; }
        div[data-testid="stPopoverBody"] button:hover { background-color: #F1F5F9 !important; border-radius: 6px !important; }
        div[data-testid="stPopoverBody"] button:has(div:contains("🗑️")) { color: #E11D48 !important; }
        div[data-testid="stPopoverBody"] button:has(div:contains("🗑️")):hover { background-color: #FFE4E6 !important; }
        </style>
    """, unsafe_allow_html=True)

    raw_role = st.session_state.get('role_tab') or st.session_state.get('role') or 'user'
    current_role = str(raw_role).strip().lower()
    allowed_tabs_list = st.session_state.get('allowed_tabs', [])
    user_allowed_branches = st.session_state.get('allowed_branches', [str(st.session_state.branch_id)])

    all_tabs_config = {
        "1": "⚙️ รายงานสรุปเครื่องจักร & เบรกดาวน์", "2": "🚚 รายงานสรุปการใช้เชื้อเพลิงรถ",
        "3": "💨 รายงานสรุปแรงดันไอน้ำ บอยเลอร์", "4": "🔥 รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)"
    }

    if current_role == "admin":
        visible_tab_keys = ["1", "2", "3", "4"]
    else:
        visible_tab_keys = [k for k in allowed_tabs_list if k in all_tabs_config]

    if current_role in ["admin", "manager", "reporter"]:
        st.header("📑 ระบบรายงานและการจัดการข้อมูล")
    else:
        st.header("📑 รายงานสรุปประจำสาขา")
    st.write("---")

    if not visible_tab_keys:
        st.error("## ⏳ รอการอนุมัติสิทธิ์เลือกแท็บงานจากแอดมิน")
        return

    tab_labels = [all_tabs_config[k] for k in visible_tab_keys]
    created_tabs = st.tabs(tab_labels)
    report_options = ["ทั้งหมดทุกสาขา"] + list(branch_dict.keys())

    for index, key in enumerate(visible_tab_keys):
        current_tab_ctx = created_tabs[index]

        # =========================================================================
        # ⚙️ TAB 1: รายงานสรุปเครื่องจักร & เบรกดาวน์
        # =========================================================================
        if key == "1":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปการทำงานและเบรกดาวน์เครื่องจักร")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1: start_date_t1 = st.date_input("ตั้งแต่วันที่", value=pd.to_datetime("today").replace(day=1), key="s_d1")
                with col_f2: end_date_t1 = st.date_input("ถึงวันที่", value=pd.to_datetime("today"), key="e_d1")
                with col_f3:
                    if current_role in ["admin", "reporter"]:
                        b_label_t1 = st.selectbox("เลือกสาขา:", options=report_options, key="b_s1")
                        b_id_t1 = "ทั้งหมด" if b_label_t1 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t1]
                        selected_branch_display = b_label_t1 if b_label_t1 != "ทั้งหมดทุกสาขา" else "ทุกสาขา"
                    elif len(user_allowed_branches) > 1:
                        allowed_options = ["ทั้งหมดที่มีสิทธิ์"] + [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]
                        b_label_t1 = st.selectbox("เลือกสาขา:", options=allowed_options, key="b_s1")
                        b_id_t1 = "รวมเฉพาะที่มีสิทธิ์" if b_label_t1 == "ทั้งหมดที่มีสิทธิ์" else branch_dict[b_label_t1]
                        selected_branch_display = b_label_t1 if b_label_t1 != "ทั้งหมดที่มีสิทธิ์" else "ทุกสาขาที่มีสิทธิ์"
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t1 = st.session_state.branch_id
                        selected_branch_display = user_branch_name

                raw_data_t1, excel_data_t1, json_html_t1 = process_t1(b_id_t1, str(start_date_t1), str(end_date_t1), tuple(user_allowed_branches), selected_branch_display)

                if raw_data_t1:
                    pk_col_t1 = list(raw_data_t1[0].keys())[0]
                    
                    # 🚀 ระบบแบ่งหน้า (Pagination) ช่วยลดภาระการ Render ทำให้เว็บโหลดเร็วขึ้น
                    ROWS_PER_PAGE = 15
                    total_pages_t1 = max(1, (len(raw_data_t1) - 1) // ROWS_PER_PAGE + 1)
                    
                    pc1, pc2 = st.columns([7, 3])
                    with pc1: st.markdown(f"<div style='font-size:14px; color:#475569; padding-top:8px;'>พบข้อมูลทั้งหมด <b>{len(raw_data_t1)}</b> รายการ</div>", unsafe_allow_html=True)
                    with pc2: page_t1 = st.selectbox("เลือกหน้า", range(1, total_pages_t1 + 1), format_func=lambda x: f"📑 หน้า {x} / {total_pages_t1}", key="pg_t1", label_visibility="collapsed")
                    
                    paginated_t1 = raw_data_t1[(page_t1 - 1) * ROWS_PER_PAGE : page_t1 * ROWS_PER_PAGE]

                    st.markdown("<br>", unsafe_allow_html=True)
                    header_cols = st.columns([0.6, 1.2, 1, 1.6, 0.8, 1, 1.2, 1.5, 0.6])
                    headers = ["ID", "วันที่", "สาขา", "ชื่อเครื่องจักร", "จำนวน", "ชม.ทำงาน", "ชม.เบรกดาวน์", "หมายเหตุ", "ตัวเลือก"]
                    for col, header in zip(header_cols, headers): col.markdown(f"<span style='color:#64748B; font-weight:bold; font-size:14px;'>{header}</span>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 0.2rem 0; border-color: #E2E8F0;'>", unsafe_allow_html=True)

                    with st.container(height=380, border=False):
                        for r in paginated_t1:
                            rec_id = r[pk_col_t1]
                            cols = st.columns([0.6, 1.2, 1, 1.6, 0.8, 1, 1.2, 1.5, 0.6])
                            cols[0].write(rec_id); cols[1].write(r.get('record_date')); cols[2].markdown(f"<span style='background:#F1F5F9; padding:4px 8px; border-radius:4px; font-size:13px; color:#0F172A;'>{r.get('branch_name') or '-'}</span>", unsafe_allow_html=True)
                            cols[3].write(r.get('machine_name') or '-'); cols[4].write(r.get('machine_qty') or 0); cols[5].write(f"{float(r.get('working_hours') or 0.0):.2f}"); cols[6].write(f"{float(r.get('breakdown_hours') or 0.0):.2f}"); cols[7].write(r.get('remarks') or '-')
                            
                            can_crud = current_role == 'admin' or (current_role in ['user', 'manager'] and str(r.get('branch_id')) in user_allowed_branches)
                            if can_crud:
                                with cols[8].popover("⋮"):
                                    st.markdown("<span style='font-size:11px; font-weight:bold; color:#94A3B8; text-transform:uppercase;'>การจัดการ</span>", unsafe_allow_html=True)
                                    if st.button("📝 แก้ไขข้อมูล", key=f"e1_{rec_id}", use_container_width=True): update_record_dialog_t1(r, pk_col_t1)
                                    if st.button("🗑️ ลบรายการ", key=f"d1_{rec_id}", use_container_width=True): delete_record_dialog_t1(r, pk_col_t1)
                            else: cols[8].write("-")
                            st.markdown("<hr style='margin:0; border-color:#F1F5F9;'>", unsafe_allow_html=True)

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1: st.download_button("📥 Export เป็น Excel (.xlsx)", data=excel_data_t1, file_name=f"Summary_Machine_Report_{start_date_t1}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t1")
                    with col_btn2: 
                        if st.button("📊 สรุปรายงาน", use_container_width=True, key="view_t1"): show_summary_report_dialog(json.loads(json_html_t1))
                    with col_btn3: components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="openPrintPreview1()" style="width:100%; height:38px; background-color:#1E293B; border:1px solid #334155; border-radius:8px; color:#F8FAFC; font-family:sans-serif; font-size:14px; font-weight:600; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน</button></body><script>function openPrintPreview1(){{var w = window.open('', '_blank', 'height=750,width=1100,scrollbars=yes'); w.document.write({json_html_t1}); w.document.close(); setTimeout(function(){{ w.print(); }}, 500);}}</script>""", height=40)
                else: st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")

        # =========================================================================
        # 🚚 TAB 2: รายงานสรุปการใช้เชื้อเพลิงรถ
        # =========================================================================
        elif key == "2":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปการใช้เชื้อเพลิงรถยนต์และรถยก")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1: start_date_t2 = st.date_input("ตั้งแต่วันที่", value=pd.to_datetime("today").replace(day=1), key="s_d2")
                with col_f2: end_date_t2 = st.date_input("ถึงวันที่", value=pd.to_datetime("today"), key="e_d2")
                with col_f3:
                    if current_role in ["admin", "reporter"]:
                        b_label_t2 = st.selectbox("เลือกสาขา:", options=report_options, key="b_s2")
                        b_id_t2 = "ทั้งหมด" if b_label_t2 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t2]
                        selected_branch_display = b_label_t2 if b_label_t2 != "ทั้งหมดทุกสาขา" else "ทุกสาขา"
                    elif len(user_allowed_branches) > 1:
                        allowed_options = ["ทั้งหมดที่มีสิทธิ์"] + [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]
                        b_label_t2 = st.selectbox("เลือกสาขา:", options=allowed_options, key="b_s2")
                        b_id_t2 = "รวมเฉพาะที่มีสิทธิ์" if b_label_t2 == "ทั้งหมดที่มีสิทธิ์" else branch_dict[b_label_t2]
                        selected_branch_display = b_label_t2 if b_label_t2 != "ทั้งหมดที่มีสิทธิ์" else "ทุกสาขาที่มีสิทธิ์"
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t2 = st.session_state.branch_id
                        selected_branch_display = user_branch_name

                raw_data_t2, excel_data_t2, json_html_t2, engine_lbl_list, engine_details_t2 = process_t2(b_id_t2, str(start_date_t2), str(end_date_t2), tuple(user_allowed_branches), selected_branch_display)

                if raw_data_t2:
                    pk_col_t2 = list(raw_data_t2[0].keys())[0]
                    
                    # 🚀 ระบบแบ่งหน้า (Pagination)
                    ROWS_PER_PAGE = 15
                    total_pages_t2 = max(1, (len(raw_data_t2) - 1) // ROWS_PER_PAGE + 1)
                    
                    pc1, pc2 = st.columns([7, 3])
                    with pc1: st.markdown(f"<div style='font-size:14px; color:#475569; padding-top:8px;'>พบข้อมูลทั้งหมด <b>{len(raw_data_t2)}</b> รายการ</div>", unsafe_allow_html=True)
                    with pc2: page_t2 = st.selectbox("เลือกหน้า", range(1, total_pages_t2 + 1), format_func=lambda x: f"📑 หน้า {x} / {total_pages_t2}", key="pg_t2", label_visibility="collapsed")
                    
                    paginated_t2 = raw_data_t2[(page_t2 - 1) * ROWS_PER_PAGE : page_t2 * ROWS_PER_PAGE]

                    st.markdown("<br>", unsafe_allow_html=True)
                    header_cols = st.columns([0.6, 1.2, 1.4, 1.4, 1, 1, 1, 1.5, 0.6])
                    headers = ["ID", "วันที่", "สาขา/ประเภท", "ทะเบียนรถ", "ลิตร", "ชม.ทำงาน", "ลิตร/ชม.", "หมายเหตุ", "ตัวเลือก"]
                    for col, header in zip(header_cols, headers): col.markdown(f"<span style='color:#64748B; font-weight:bold; font-size:14px;'>{header}</span>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 0.2rem 0; border-color: #E2E8F0;'>", unsafe_allow_html=True)

                    with st.container(height=380, border=False):
                        for r in paginated_t2:
                            rec_id = r[pk_col_t2]
                            lts, hrs = float(r.get('fuel_liters') or 0.0), float(r.get('working_hours') or 0.0)
                            cols = st.columns([0.6, 1.2, 1.4, 1.4, 1, 1, 1, 1.5, 0.6])
                            cols[0].write(rec_id); cols[1].write(r.get('record_date')); cols[2].write(f"{r.get('branch_name') or '-'} / {r.get('type_name') or '-'}")
                            cols[3].write(r.get('engine_code') or '-'); cols[4].write(f"{lts:.2f}"); cols[5].write(f"{hrs:.2f}"); cols[6].write(f"{(round(lts/hrs, 2) if hrs > 0 else 0.00):.2f}"); cols[7].write(r.get('remark') or '-')
                            
                            can_crud = current_role == 'admin' or (current_role in ['user', 'manager'] and str(r.get('branch_id')) in user_allowed_branches)
                            if can_crud:
                                with cols[8].popover("⋮"):
                                    st.markdown("<span style='font-size:11px; font-weight:bold; color:#94A3B8;'>การจัดการ</span>", unsafe_allow_html=True)
                                    if st.button("📝 แก้ไขข้อมูล", key=f"e2_{rec_id}", use_container_width=True): update_record_dialog_t2(r, pk_col_t2, engine_lbl_list, engine_details_t2)
                                    if st.button("🗑️ ลบรายการ", key=f"d2_{rec_id}", use_container_width=True): delete_record_dialog_t2(r, pk_col_t2)
                            else: cols[8].write("-")
                            st.markdown("<hr style='margin:0; border-color:#F1F5F9;'>", unsafe_allow_html=True)

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1: st.download_button("📥 Export เป็น Excel (.xlsx)", data=excel_data_t2, file_name=f"Summary_Fuel_Report_{start_date_t2}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t2")
                    with col_btn2: 
                        if st.button("📊 สรุปรายงาน", use_container_width=True, key="view_t2"): show_summary_report_dialog(json.loads(json_html_t2))
                    with col_btn3: components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="openPrintPreview2()" style="width:100%; height:38px; background-color:#1E293B; border:1px solid #334155; border-radius:8px; color:#F8FAFC; font-family:sans-serif; font-size:14px; font-weight:600; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน</button></body><script>function openPrintPreview2(){{var w = window.open('', '_blank', 'height=750,width=1100,scrollbars=yes'); w.document.write({json_html_t2}); w.document.close(); setTimeout(function(){{ w.print(); }}, 500);}}</script>""", height=40)
                else: st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")

        # =========================================================================
        # 💨 TAB 3: รายงานสรุปแรงดันไอน้ำ บอยเลอร์
        # =========================================================================
        elif key == "3":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปสถิติแรงดันไอน้ำปลายทางตก")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1: start_date_t3 = st.date_input("ตั้งแต่วันที่", value=pd.to_datetime("today").replace(day=1), key="s_d3")
                with col_f2: end_date_t3 = st.date_input("ถึงวันที่", value=pd.to_datetime("today"), key="e_d3")
                with col_f3:
                    if current_role in ["admin", "reporter"]:
                        b_label_t3 = st.selectbox("เลือกสาขา:", options=report_options, key="b_s3")
                        b_id_t3 = "ทั้งหมด" if b_label_t3 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t3]
                        selected_branch_display = b_label_t3 if b_label_t3 != "ทั้งหมดทุกสาขา" else "ทุกสาขา"
                    elif len(user_allowed_branches) > 1:
                        allowed_options = ["ทั้งหมดที่มีสิทธิ์"] + [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]
                        b_label_t3 = st.selectbox("เลือกสาขา:", options=allowed_options, key="b_s3")
                        b_id_t3 = "รวมเฉพาะที่มีสิทธิ์" if b_label_t3 == "ทั้งหมดที่มีสิทธิ์" else branch_dict[b_label_t3]
                        selected_branch_display = b_label_t3 if b_label_t3 != "ทั้งหมดที่มีสิทธิ์" else "ทุกสาขาที่มีสิทธิ์"
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t3 = st.session_state.branch_id
                        selected_branch_display = user_branch_name

                raw_data_t3, excel_data_t3, json_html_t3 = process_t3(b_id_t3, str(start_date_t3), str(end_date_t3), tuple(user_allowed_branches), selected_branch_display)

                if raw_data_t3:
                    pk_col_t3 = list(raw_data_t3[0].keys())[0]
                    
                    # 🚀 ระบบแบ่งหน้า (Pagination)
                    ROWS_PER_PAGE = 15
                    total_pages_t3 = max(1, (len(raw_data_t3) - 1) // ROWS_PER_PAGE + 1)
                    
                    pc1, pc2 = st.columns([7, 3])
                    with pc1: st.markdown(f"<div style='font-size:14px; color:#475569; padding-top:8px;'>พบข้อมูลทั้งหมด <b>{len(raw_data_t3)}</b> รายการ</div>", unsafe_allow_html=True)
                    with pc2: page_t3 = st.selectbox("เลือกหน้า", range(1, total_pages_t3 + 1), format_func=lambda x: f"📑 หน้า {x} / {total_pages_t3}", key="pg_t3", label_visibility="collapsed")
                    
                    paginated_t3 = raw_data_t3[(page_t3 - 1) * ROWS_PER_PAGE : page_t3 * ROWS_PER_PAGE]

                    st.markdown("<br>", unsafe_allow_html=True)
                    header_cols = st.columns([0.6, 1.2, 1, 1.2, 1.2, 1.2, 1.2, 1.6, 0.6])
                    headers = ["ID", "วันที่", "สาขา", "ทั้งหมด(ครั้ง)", "ตก(ครั้ง)", "ตก PM", "ตกนอก PM", "หมายเหตุ", "ตัวเลือก"]
                    for col, header in zip(header_cols, headers): col.markdown(f"<span style='color:#64748B; font-weight:bold; font-size:14px;'>{header}</span>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 0.2rem 0; border-color: #E2E8F0;'>", unsafe_allow_html=True)

                    with st.container(height=380, border=False):
                        for r in paginated_t3:
                            rec_id = r[pk_col_t3]
                            cols = st.columns([0.6, 1.2, 1, 1.2, 1.2, 1.2, 1.2, 1.6, 0.6])
                            cols[0].write(rec_id); cols[1].write(r.get('record_date')); cols[2].markdown(f"<span style='background:#F1F5F9; padding:4px 8px; border-radius:4px; font-size:13px; color:#0F172A;'>{r.get('branch_name') or '-'}</span>", unsafe_allow_html=True)
                            cols[3].write(r.get('total_count') or 0); cols[4].write(r.get('total_drop') or 0); cols[5].write(r.get('pm_drop') or 0); cols[6].write(r.get('non_pm_drop') or 0); cols[7].write(r.get('remark') or '-')
                            
                            can_crud = current_role == 'admin' or (current_role in ['user', 'manager'] and str(r.get('branch_id')) in user_allowed_branches)
                            if can_crud:
                                with cols[8].popover("⋮"):
                                    st.markdown("<span style='font-size:11px; font-weight:bold; color:#94A3B8;'>การจัดการ</span>", unsafe_allow_html=True)
                                    if st.button("📝 แก้ไขข้อมูล", key=f"e3_{rec_id}", use_container_width=True): update_record_dialog_t3(r, pk_col_t3)
                                    if st.button("🗑️ ลบรายการ", key=f"d3_{rec_id}", use_container_width=True): delete_record_dialog_t3(r, pk_col_t3)
                            else: cols[8].write("-")
                            st.markdown("<hr style='margin:0; border-color:#F1F5F9;'>", unsafe_allow_html=True)

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1: st.download_button("📥 Export เป็น Excel (.xlsx)", data=excel_data_t3, file_name=f"Summary_Pressure_Report_{start_date_t3}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t3")
                    with col_btn2: 
                        if st.button("📊 สรุปรายงาน", use_container_width=True, key="view_t3"): show_summary_report_dialog(json.loads(json_html_t3))
                    with col_btn3: components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="openPrintPreview3()" style="width:100%; height:38px; background-color:#1E293B; border:1px solid #334155; border-radius:8px; color:#F8FAFC; font-family:sans-serif; font-size:14px; font-weight:600; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน</button></body><script>function openPrintPreview3(){{var w = window.open('', '_blank', 'height=750,width=1100,scrollbars=yes'); w.document.write({json_html_t3}); w.document.close(); setTimeout(function(){{ w.print(); }}, 500);}}</script>""", height=40)
                else: st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")

        # =========================================================================
        # 🔥 TAB 4: รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)
        # =========================================================================
        elif key == "4":
            with current_tab_ctx:
                st.subheader("📊 รายงานผลการคำนวณประสิทธิภาพเชื้อเพลิง บอยเลอร์")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1: start_date_t4 = st.date_input("ตั้งแต่วันที่", value=pd.to_datetime("today").replace(day=1), key="s_d4")
                with col_f2: end_date_t4 = st.date_input("ถึงวันที่", value=pd.to_datetime("today"), key="e_d4")
                with col_f3:
                    if current_role in ["admin", "reporter"]:
                        b_label_t4 = st.selectbox("เลือกสาขา:", options=report_options, key="b_s4")
                        b_id_t4 = "ทั้งหมด" if b_label_t4 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t4]
                    elif len(user_allowed_branches) > 1:
                        allowed_options = ["ทั้งหมดที่มีสิทธิ์"] + [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]
                        b_label_t4 = st.selectbox("เลือกสาขา:", options=allowed_options, key="b_s4")
                        b_id_t4 = "รวมเฉพาะที่มีสิทธิ์" if b_label_t4 == "ทั้งหมดที่มีสิทธิ์" else branch_dict[b_label_t4]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t4 = st.session_state.branch_id

                raw_data_t4, excel_data_t4, json_html_t4 = process_t4(b_id_t4, str(start_date_t4), str(end_date_t4), tuple(user_allowed_branches), selected_branch_display)

                if raw_data_t4:
                    pk_col_t4 = list(raw_data_t4[0].keys())[0]
                    
                    # 🚀 ระบบแบ่งหน้า (Pagination)
                    ROWS_PER_PAGE = 15
                    total_pages_t4 = max(1, (len(raw_data_t4) - 1) // ROWS_PER_PAGE + 1)
                    
                    pc1, pc2 = st.columns([7, 3])
                    with pc1: st.markdown(f"<div style='font-size:14px; color:#475569; padding-top:8px;'>พบข้อมูลทั้งหมด <b>{len(raw_data_t4)}</b> รายการ</div>", unsafe_allow_html=True)
                    with pc2: page_t4 = st.selectbox("เลือกหน้า", range(1, total_pages_t4 + 1), format_func=lambda x: f"📑 หน้า {x} / {total_pages_t4}", key="pg_t4", label_visibility="collapsed")
                    
                    paginated_t4 = raw_data_t4[(page_t4 - 1) * ROWS_PER_PAGE : page_t4 * ROWS_PER_PAGE]

                    st.markdown("<br>", unsafe_allow_html=True)
                    header_cols = st.columns([0.6, 1.2, 1, 1.4, 1.4, 1.2, 1.6, 0.6])
                    headers = ["ID", "วันที่", "สาขา", "เชื้อเพลิงรวม(ตัน)", "ผลิตไอน้ำ(ตัน)", "ชม.ทำงาน", "ผลงาน(กก./ตัน)", "ตัวเลือก"]
                    for col, header in zip(header_cols, headers): col.markdown(f"<span style='color:#64748B; font-weight:bold; font-size:13px;'>{header}</span>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 0.2rem 0; border-color: #E2E8F0;'>", unsafe_allow_html=True)

                    with st.container(height=380, border=False):
                        for r in paginated_t4:
                            rec_id = r[pk_col_t4]
                            s_w, w_w, ww_w = float(r.get('sawdust_weight') or 0.0), float(r.get('wood_weight') or 0.0), float(r.get('waste_wood_weight') or 0.0)
                            tot_w = s_w + w_w + ww_w
                            s_prod = float(r.get('steam_production') or 1.0)
                            cols = st.columns([0.6, 1.2, 1, 1.4, 1.4, 1.2, 1.6, 0.6])
                            cols[0].write(rec_id); cols[1].write(r.get('record_date')); cols[2].markdown(f"<span style='background:#F1F5F9; padding:4px 8px; border-radius:4px; font-size:13px; color:#0F172A;'>{r.get('branch_name') or '-'}</span>", unsafe_allow_html=True)
                            cols[3].write(f"{tot_w:.2f}"); cols[4].write(f"{s_prod:.2f}"); cols[5].write(f"{float(r.get('working_hours') or 0.0):.2f}"); cols[6].write(f"{((tot_w / s_prod) * 1000 if s_prod > 0 else 0.0):.2f}")
                            
                            can_crud = current_role == 'admin' or (current_role in ['user', 'manager'] and str(r.get('branch_id')) in user_allowed_branches)
                            if can_crud:
                                with cols[7].popover("⋮"):
                                    st.markdown("<span style='font-size:11px; font-weight:bold; color:#94A3B8;'>การจัดการ</span>", unsafe_allow_html=True)
                                    if st.button("📝 แก้ไขข้อมูล", key=f"e4_{rec_id}", use_container_width=True): update_record_dialog_t4(r, pk_col_t4)
                                    if st.button("🗑️ ลบรายการ", key=f"d4_{rec_id}", use_container_width=True): delete_record_dialog_t4(r, pk_col_t4)
                            else: cols[7].write("-")
                            st.markdown("<hr style='margin:0; border-color:#F1F5F9;'>", unsafe_allow_html=True)

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1: st.download_button("📥 Export เป็น Excel (.xlsx)", data=excel_data_t4, file_name=f"Report_Boiler_Fuel_{start_date_t4}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t4")
                    with col_btn2: 
                        if st.button("📊 สรุปรายงาน", use_container_width=True, key="view_t4"): show_summary_report_dialog(json.loads(json_html_t4))
                    with col_btn3: components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="openPrintPreview4()" style="width:100%; height:38px; background-color:#1E293B; border:1px solid #334155; border-radius:8px; color:#F8FAFC; font-family:sans-serif; font-size:14px; font-weight:600; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน</button></body><script>function openPrintPreview4(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); w.document.write({json_html_t4}); w.document.close(); w.print();}}</script>""", height=40)
                else: st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")