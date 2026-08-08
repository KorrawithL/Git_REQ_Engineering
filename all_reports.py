import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import io
import time
from database import get_db_connection, log_activity
from config import branch_dict

def render_all_reports_module(user_branch_name):
    # 🎯 1. ตรวจสอบสิทธิ์การใช้งาน
    raw_role = st.session_state.get('role_tab') or st.session_state.get('role') or 'user'
    current_role = str(raw_role).strip().lower()
    allowed_tabs_list = st.session_state.get('allowed_tabs', [])

    # 🏷️ ตั้งชื่อแท็บรายงานสรุปอย่างเป็นทางการ
    all_tabs_config = {
        "1": "⚙️ รายงานสรุปเครื่องจักร & เบรกดาวน์",
        "2": "🚚 รายงานสรุปการใช้เชื้อเพลิงรถ",
        "3": "💨 รายงานสรุปแรงดันไอน้ำ บอยเลอร์",
        "4": "🔥 รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)"
    }

    # จัดสรรแท็บที่จะแสดงผลตามสิทธิ์
    if current_role in ["admin", "manager"]:
        visible_tab_keys = ["1", "2", "3", "4"]
        st.header("📑 รายงานรวมทุกระบบและการจัดการข้อมูล (All Report)")
        st.caption("ศูนย์รวมรายงานสรุป การส่งออกข้อมูล (Export/Print) และเครื่องมือแก้ไข-ลบข้อมูลสำหรับ Admin/Manager")
        st.write("---")
    else:
        visible_tab_keys = [k for k in allowed_tabs_list if k in all_tabs_config]

    if not visible_tab_keys:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.error("## ⏳ รอการอนุมัติสิทธิ์เลือกแท็บงานจากแอดมิน")
        st.info("🔒 บัญชีของคุณได้รับการลงทะเบียนเรียบร้อยแล้ว แต่ในขณะนี้ยังไม่ได้รับสิทธิ์เข้าถึงแท็บรายงานใดๆ กรุณาติดต่อผู้ดูแลระบบเพื่อทำการระบุแท็บงานก่อนครับ")
        return

    # 🎯 2. สร้างแท็บแบบ Dynamic
    tab_labels = [all_tabs_config[k] for k in visible_tab_keys]
    created_tabs = st.tabs(tab_labels)

    report_options = ["ทั้งหมดทุกสาขา"] + list(branch_dict.keys())

    for index, key in enumerate(visible_tab_keys):
        current_tab_ctx = created_tabs[index]

        # =========================================================================
        # ⚙️ TAB 1 REPORT: รายงานสรุปเครื่องจักร & เบรกดาวน์
        # =========================================================================
        if key == "1":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปการทำงานและเบรกดาวน์เครื่องจักร")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t1 = st.date_input("ตั้งแต่วันที่ (Tab 1)", value=pd.to_datetime("today").replace(day=1), key="s_date_t1")
                with col_f2:
                    end_date_t1 = st.date_input("ถึงวันที่ (Tab 1)", value=pd.to_datetime("today"), key="e_date_t1")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t1 = st.selectbox("เลือกสาขา (Tab 1):", options=report_options, key="b_sel_t1")
                        b_id_t1 = "ทั้งหมด" if b_label_t1 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t1]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t1 = st.session_state.branch_id

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t1 == "ทั้งหมด":
                            sql = """SELECT t.*, b.branch_name, m.machine_name 
                                     FROM machine_trans t 
                                     LEFT JOIN branches b ON t.branch_id = b.id 
                                     LEFT JOIN machines m ON t.machine_id = m.id
                                     WHERE t.record_date BETWEEN %s AND %s ORDER BY t.record_date DESC"""
                            cur.execute(sql, (start_date_t1, end_date_t1))
                        else:
                            sql = """SELECT t.*, b.branch_name, m.machine_name 
                                     FROM machine_trans t 
                                     LEFT JOIN branches b ON t.branch_id = b.id 
                                     LEFT JOIN machines m ON t.machine_id = m.id
                                     WHERE t.branch_id = %s AND t.record_date BETWEEN %s AND %s ORDER BY t.record_date DESC"""
                            cur.execute(sql, (b_id_t1, start_date_t1, end_date_t1))
                        raw_data_t1 = cur.fetchall()
                    conn.close()

                    if raw_data_t1:
                        pk_col_t1 = list(raw_data_t1[0].keys())[0]
                        
                        df_display_t1 = []
                        for r in raw_data_t1:
                            df_display_t1.append({
                                'ID รายการ': r[pk_col_t1],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'ชื่อเครื่องจักร': r.get('machine_name'),
                                'จำนวน': r.get('machine_qty'),
                                'ชม.ทำงาน': r.get('working_hours'),
                                'ชม.เบรกดาวน์': r.get('breakdown_hours'),
                                'หมายเหตุ': r.get('remarks')
                            })
                        df_t1 = pd.DataFrame(df_display_t1)
                        st.dataframe(df_t1, use_container_width=True)

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_t1.to_excel(writer, index=False, sheet_name='Machine Report')
                            st.download_button("📥 Export เป็น Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Report_Machine_{start_date_t1}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t1")
                        with col_btn2:
                            table_html_t1 = df_t1.to_html(index=False, classes='report-table')
                            components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="window.parent.openPrintPreview1 ? window.parent.openPrintPreview1() : openPrintPreview1()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน (Tab 1)</button></body><script>function openPrintPreview1(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); var content = `<html><head><title>Print Preview - Tab 1</title></head><body><h2>รายงานสรุปการทำงานของเครื่องจักร</h2><br>{table_html_t1}</body></html>`; w.document.write(content); w.document.close(); w.print();}}</script>""", height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            record_map_t1 = {f"ID: {r[pk_col_t1]} | วันที่: {r.get('record_date')} | เครื่อง: {r.get('machine_name')} ({r.get('branch_name')})": (r[pk_col_t1], r) for r in raw_data_t1}
                            selected_label_t1 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 1):", options=list(record_map_t1.keys()), key="select_t1")
                            target_pk_t1, target_rec_t1 = record_map_t1[selected_label_t1]

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 1)", expanded=True):
                                e_col1, e_col2 = st.columns(2)
                                with e_col1:
                                    e_date_t1 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t1.get('record_date')), key="e_date_t1_in")
                                    e_qty_t1 = st.number_input("แก้ไข จำนวนเครื่องจักร", min_value=1, value=int(target_rec_t1.get('machine_qty') or 1), key="e_qty_t1_in")
                                with e_col2:
                                    e_work_t1 = st.number_input("แก้ไข ชม.ทำงาน", min_value=0.0, step=0.5, value=float(target_rec_t1.get('working_hours') or 0.0), key="e_work_t1_in")
                                    e_break_t1 = st.number_input("แก้ไข ชม.เบรกดาวน์", min_value=0.0, step=0.5, value=float(target_rec_t1.get('breakdown_hours') or 0.0), key="e_break_t1_in")
                                e_remark_t1 = st.text_area("แก้ไข หมายเหตุ", value=str(target_rec_t1.get('remarks') or ''), key="e_remark_t1_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 1)", key="btn_up_t1", use_container_width=True):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                sql_u = f"UPDATE machine_trans SET record_date=%s, machine_qty=%s, working_hours=%s, breakdown_hours=%s, remarks=%s, updated_at=NOW() WHERE {pk_col_t1}=%s"
                                                cur.execute(sql_u, (e_date_t1, e_qty_t1, e_work_t1, e_break_t1, e_remark_t1, target_pk_t1))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 1", f"แก้ไขข้อมูล ID: {target_pk_t1}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t1} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 1)", type="primary", use_container_width=True, key="del_btn_t1"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM machine_trans WHERE {pk_col_t1} = %s", (target_pk_t1,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 1", f"ลบข้อมูล ID: {target_pk_t1}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t1} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 1: {e}")

        # =========================================================================
        # 🚚 TAB 2 REPORT: รายงานสรุปการใช้เชื้อเพลิงรถ
        # =========================================================================
        elif key == "2":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปการใช้เชื้อเพลิงรถยนต์และรถยก")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t2 = st.date_input("ตั้งแต่วันที่ (Tab 2)", value=pd.to_datetime("today").replace(day=1), key="s_date_t2")
                with col_f2:
                    end_date_t2 = st.date_input("ถึงวันที่ (Tab 2)", value=pd.to_datetime("today"), key="e_date_t2")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t2 = st.selectbox("เลือกสาขา (Tab 2):", options=report_options, key="b_sel_t2")
                        b_id_t2 = "ทั้งหมด" if b_label_t2 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t2]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t2 = st.session_state.branch_id

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t2 == "ทั้งหมด":
                            sql = """SELECT r.*, b.branch_name 
                                     FROM fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (start_date_t2, end_date_t2))
                        else:
                            sql = """SELECT r.*, b.branch_name 
                                     FROM fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (b_id_t2, start_date_t2, end_date_t2))
                        raw_data_t2 = cur.fetchall()
                    conn.close()

                    if raw_data_t2:
                        pk_col_t2 = list(raw_data_t2[0].keys())[0]
                        
                        df_display_t2 = []
                        for r in raw_data_t2:
                            liters = float(r.get('fuel_liters') or 0.0)
                            hours = float(r.get('working_hours') or 0.0)
                            liters_per_hour = round(liters / hours, 2) if hours > 0 else 0.00

                            df_display_t2.append({
                                'ID รายการ': r[pk_col_t2],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'ประเภทรถ': r.get('type_name'),
                                'รหัสงาน/ทะเบียน': r.get('engine_code'),
                                'ปริมาณน้ำมัน (ลิตร)': liters,
                                'ชม.ทำงาน': hours,
                                'ลิตร/ชม.': liters_per_hour,
                                'หมายเหตุ': r.get('remark')
                            })
                        df_t2 = pd.DataFrame(df_display_t2)
                        st.dataframe(df_t2, use_container_width=True)

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_t2.to_excel(writer, index=False, sheet_name='Fuel Report')
                            st.download_button("📥 Export เป็น Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Report_Fuel_{start_date_t2}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t2")
                        with col_btn2:
                            table_html_t2 = df_t2.to_html(index=False, classes='report-table')
                            components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="window.parent.openPrintPreview2 ? window.parent.openPrintPreview2() : openPrintPreview2()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน (Tab 2)</button></body><script>function openPrintPreview2(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); var content = `<html><head><title>Print Preview - Tab 2</title></head><body><h2>รายงานสรุปเชื้อเพลิงรถ</h2><br>{table_html_t2}</body></html>`; w.document.write(content); w.document.close(); w.print();}}</script>""", height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            engine_options_t2 = {}
                            engine_details_t2 = {}
                            try:
                                conn_eng = get_db_connection()
                                with conn_eng.cursor() as cur_eng:
                                    sql_eng = """SELECT e.id, CONVERT(e.engine_code USING utf8mb4) AS engine_code, 
                                                        CONVERT(et.type_name USING utf8mb4) AS type_name, 
                                                        CONVERT(b.branch_name USING utf8mb4) AS branch_name
                                                 FROM engines e 
                                                 LEFT JOIN engine_types et ON e.engine_type_id = et.id 
                                                 LEFT JOIN branches b ON e.branch_id = b.id 
                                                 WHERE e.is_active = 1 ORDER BY b.id ASC, e.engine_code ASC"""
                                    cur_eng.execute(sql_eng)
                                    for eng in cur_eng.fetchall():
                                        code = eng['engine_code'] or ''
                                        t_name = eng['type_name'] or 'ไม่ระบุประเภท'
                                        b_name = eng['branch_name'] or ''
                                        try: branch_code = b_name.split("สาขา ")[1].split()[0]
                                        except: branch_code = b_name or "N/A"
                                        
                                        lbl = f"{code} (ประเภท: {t_name}) [{branch_code}]"
                                        engine_options_t2[lbl] = eng['id']
                                        engine_details_t2[lbl] = {'code': code, 'type': t_name}
                                conn_eng.close()
                            except Exception as e_eng:
                                print(f"Error fetching engines for edit: {e_eng}")

                            record_map_t2 = {f"ID: {r[pk_col_t2]} | วันที่: {r.get('record_date')} | ทะเบียน: {r.get('engine_code')} ({r.get('branch_name')})": (r[pk_col_t2], r) for r in raw_data_t2}
                            selected_label_t2 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 2):", options=list(record_map_t2.keys()), key="select_t2")
                            target_pk_t2, target_rec_t2 = record_map_t2[selected_label_t2]

                            curr_code_t2 = str(target_rec_t2.get('engine_code') or '')
                            curr_type_t2 = str(target_rec_t2.get('type_name') or '')
                            
                            default_eng_idx = 0
                            engine_lbl_list = list(engine_options_t2.keys())
                            for idx, lbl in enumerate(engine_lbl_list):
                                info = engine_details_t2[lbl]
                                if info['code'] == curr_code_t2 and info['type'] == curr_type_t2:
                                    default_eng_idx = idx
                                    break

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 2)", expanded=True):
                                e_col1, e_col2 = st.columns(2)
                                with e_col1:
                                    e_date_t2 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t2.get('record_date')), key="e_date_t2_in")
                                    selected_engine_edit_label = st.selectbox(
                                        "แก้ไข รหัสงาน / ทะเบียนรถ (แยกตามประเภทและสาขา):",
                                        options=engine_lbl_list if engine_lbl_list else ["-- ไม่พบข้อมูลรถ --"],
                                        index=default_eng_idx,
                                        key="e_engine_select_t2"
                                    )
                                with e_col2:
                                    e_liters_t2 = st.number_input("แก้ไข น้ำมัน (ลิตร)", min_value=0.0, value=float(target_rec_t2.get('fuel_liters') or 0.0), key="e_liters_t2_in")
                                    e_work_t2 = st.number_input("แก้ไข ชม.ทำงาน", min_value=0.0, step=0.5, value=float(target_rec_t2.get('working_hours') or 0.0), key="e_work_t2_in")
                                e_remark_t2 = st.text_area("แก้ไข หมายเหตุ", value=str(target_rec_t2.get('remark') or ''), key="e_remark_t2_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 2)", key="btn_up_t2", use_container_width=True):
                                        try:
                                            eng_info = engine_details_t2.get(selected_engine_edit_label, {'code': curr_code_t2, 'type': curr_type_t2})
                                            up_code = eng_info['code']
                                            up_type = eng_info['type']
                                            up_liter_hr = round(e_liters_t2 / e_work_t2, 2) if e_work_t2 > 0 else 0.00

                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                # อัปเดตข้อมูลรวมถึงคอลัมน์ liter_hr ด้วย
                                                sql_u = f"""UPDATE fuel_records 
                                                            SET record_date=%s, engine_code=CONVERT(%s USING utf8mb4), type_name=CONVERT(%s USING utf8mb4), 
                                                                fuel_liters=%s, working_hours=%s, liter_hr=%s, remark=CONVERT(%s USING utf8mb4) 
                                                            WHERE {pk_col_t2}=%s"""
                                                cur.execute(sql_u, (e_date_t2, up_code, up_type, e_liters_t2, e_work_t2, up_liter_hr, e_remark_t2, target_pk_t2))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 2", f"แก้ไขข้อมูล ID: {target_pk_t2}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t2} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 2)", type="primary", use_container_width=True, key="del_btn_t2"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM fuel_records WHERE {pk_col_t2} = %s", (target_pk_t2,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 2", f"ลบข้อมูล ID: {target_pk_t2}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t2} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 2: {e}")

        # =========================================================================
        # 💨 TAB 3 REPORT: รายงานสรุปแรงดันไอน้ำ บอยเลอร์
        # =========================================================================
        elif key == "3":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปสถิติแรงดันไอน้ำปลายทางตก")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t3 = st.date_input("ตั้งแต่วันที่ (Tab 3)", value=pd.to_datetime("today").replace(day=1), key="s_date_t3")
                with col_f2:
                    end_date_t3 = st.date_input("ถึงวันที่ (Tab 3)", value=pd.to_datetime("today"), key="e_date_t3")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t3 = st.selectbox("เลือกสาขา (Tab 3):", options=report_options, key="b_sel_t3")
                        b_id_t3 = "ทั้งหมด" if b_label_t3 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t3]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t3 = st.session_state.branch_id

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t3 == "ทั้งหมด":
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_pressure_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (start_date_t3, end_date_t3))
                        else:
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_pressure_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (b_id_t3, start_date_t3, end_date_t3))
                        raw_data_t3 = cur.fetchall()
                    conn.close()

                    if raw_data_t3:
                        pk_col_t3 = list(raw_data_t3[0].keys())[0]
                        
                        df_display_t3 = []
                        for r in raw_data_t3:
                            tot_c = r.get('total_count') or 0
                            tot_d = r.get('total_drop') or 0
                            pm_d = r.get('pm_drop') or 0
                            df_display_t3.append({
                                'ID รายการ': r[pk_col_t3],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'จำนวนครั้งทั้งหมด': tot_c,
                                'ตกทั้งหมด (ครั้ง)': tot_d,
                                'ตกตามเงื่อนไข PM': pm_d,
                                'ตกนอกเหนือ PM': r.get('non_pm_drop') or 0,
                                'หมายเหตุ': r.get('remark')
                            })

                        df_t3 = pd.DataFrame(df_display_t3)
                        df_t3['ตกทั้งหมด (%)'] = ((df_t3['ตกทั้งหมด (ครั้ง)'] / df_t3['จำนวนครั้งทั้งหมด'].replace(0, 1)) * 100).round(2).astype(str) + '%'
                        df_t3['ตกตาม PM (%)'] = ((df_t3['ตกตามเงื่อนไข PM'] / df_t3['จำนวนครั้งทั้งหมด'].replace(0, 1)) * 100).round(2).astype(str) + '%'
                        st.dataframe(df_t3, use_container_width=True)

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_t3.to_excel(writer, index=False, sheet_name='Pressure Report')
                            st.download_button("📥 Export เป็น Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Report_Pressure_{start_date_t3}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t3")
                        with col_btn2:
                            table_html_t3 = df_t3.to_html(index=False, classes='report-table')
                            components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="window.parent.openPrintPreview3 ? window.parent.openPrintPreview3() : openPrintPreview3()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน (Tab 3)</button></body><script>function openPrintPreview3(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); var content = `<html><head><title>Print Preview - Tab 3</title></head><body><h2>รายงานสรุปแรงดันไอน้ำ</h2><br>{table_html_t3}</body></html>`; w.document.write(content); w.document.close(); w.print();}}</script>""", height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            record_map_t3 = {f"ID: {r[pk_col_t3]} | วันที่: {r.get('record_date')} | สาขา: {r.get('branch_name')}": (r[pk_col_t3], r) for r in raw_data_t3}
                            selected_label_t3 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 3):", options=list(record_map_t3.keys()), key="select_t3")
                            target_pk_t3, target_rec_t3 = record_map_t3[selected_label_t3]

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 3)", expanded=True):
                                e_col1, e_col2 = st.columns(2)
                                with e_col1:
                                    e_date_t3 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t3.get('record_date')), key="e_date_t3_in")
                                    e_total_t3 = st.number_input("แก้ไข จำนวนครั้งทั้งหมด", min_value=0, value=int(target_rec_t3.get('total_count') or 0), key="e_total_t3_in")
                                with e_col2:
                                    e_pm_t3 = st.number_input("แก้ไข ตกตามเงื่อนไข PM", min_value=0, value=int(target_rec_t3.get('pm_drop') or 0), key="e_pm_t3_in")
                                    e_non_pm_t3 = st.number_input("แก้ไข ตกนอกเหนือ PM", min_value=0, value=int(target_rec_t3.get('non_pm_drop') or 0), key="e_non_pm_t3_in")
                                e_remark_t3 = st.text_input("แก้ไข หมายเหตุ", value=str(target_rec_t3.get('remark') or ''), key="e_remark_t3_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 3)", key="btn_up_t3", use_container_width=True):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                sql_u = f"UPDATE boiler_pressure_records SET record_date=%s, total_count=%s, total_drop=%s, pm_drop=%s, non_pm_drop=%s, remark=%s WHERE {pk_col_t3}=%s"
                                                cur.execute(sql_u, (e_date_t3, e_total_t3, (e_pm_t3 + e_non_pm_t3), e_pm_t3, e_non_pm_t3, e_remark_t3, target_pk_t3))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 3", f"แก้ไขข้อมูล ID: {target_pk_t3}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t3} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 3)", type="primary", use_container_width=True, key="del_btn_t3"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM boiler_pressure_records WHERE {pk_col_t3} = %s", (target_pk_t3,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 3", f"ลบข้อมูล ID: {target_pk_t3}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t3} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 3: {e}")

        # =========================================================================
        # 🔥 TAB 4 REPORT: รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)
        # =========================================================================
        elif key == "4":
            with current_tab_ctx:
                st.subheader("📊 รายงานผลการคำนวณประสิทธิภาพเชื้อเพลิง บอยเลอร์")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t4 = st.date_input("ตั้งแต่วันที่ (Tab 4)", value=pd.to_datetime("today").replace(day=1), key="s_date_t4")
                with col_f2:
                    end_date_t4 = st.date_input("ถึงวันที่ (Tab 4)", value=pd.to_datetime("today"), key="e_date_t4")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t4 = st.selectbox("เลือกสาขา (Tab 4):", options=report_options, key="b_sel_t4")
                        b_id_t4 = "ทั้งหมด" if b_label_t4 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t4]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t4 = st.session_state.branch_id

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t4 == "ทั้งหมด":
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (start_date_t4, end_date_t4))
                        else:
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (b_id_t4, start_date_t4, end_date_t4))
                        raw_data_t4 = cur.fetchall()
                    conn.close()

                    if raw_data_t4:
                        pk_col_t4 = list(raw_data_t4[0].keys())[0]
                        std_fuel_val = 280.00
                        
                        df_display_t4 = []
                        for r in raw_data_t4:
                            s_w = float(r.get('sawdust_weight') or 0.0)
                            w_w = float(r.get('wood_weight') or 0.0)
                            ww_w = float(r.get('waste_wood_weight') or 0.0)
                            
                            s_p = float(r.get('sawdust_price') or 0.0)
                            w_p = float(r.get('wood_price') or 0.0)
                            ww_p = float(r.get('waste_wood_price') or 0.0)
                            
                            steam_prod = float(r.get('steam_production') or 1.0)
                            w_hours = float(r.get('working_hours') or 1.0)
                            
                            total_fuel_weight = s_w + w_w + ww_w
                            total_fuel_price = s_p + w_p + ww_p
                            tons_per_hour = steam_prod / w_hours if w_hours > 0 else 0.0
                            fuel_cost_per_steam_ton = total_fuel_price / steam_prod if steam_prod > 0 else 0.0
                            actual_result = (total_fuel_weight / steam_prod) * 1000 if steam_prod > 0 else 0.0
                            diff_result = std_fuel_val - actual_result
                            
                            df_display_t4.append({
                                'ID รายการ': r[pk_col_t4],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'นหน.ขี้เลื่อย (ตัน)': s_w,
                                'นหน.ปีกไม้ (ตัน)': w_w,
                                'นหน.เศษไม้เสีย (ตัน)': ww_w,
                                '4.1 รวมน้ำหนักเชื้อเพลิง (ตัน)': round(total_fuel_weight, 2),
                                'ราคาขี้เลื่อย (บาท)': s_p,
                                'ราคาปีกไม้ (บาท)': w_p,
                                'ราคาเศษไม้เสีย (บาท)': ww_p,
                                '4.2 รวมราคาเชื้อเพลิง (บาท)': round(total_fuel_price, 2),
                                'ผลิตไอน้ำ (ตัน/วัน)': steam_prod,
                                'ชม.ทำงาน': w_hours,
                                '4.3 ตันต่อชั่วโมง': round(tons_per_hour, 2),
                                '4.4 ค่าเชื้อเพลิง (บาท/ตันไอน้ำ)': round(fuel_cost_per_steam_ton, 2),
                                '4.5 ผลงาน (กก./ตันไอน้ำ)': round(actual_result, 2),
                                '4.5 ผลต่าง (STD-ผลงาน)': round(diff_result, 2)
                            })

                        df_t4 = pd.DataFrame(df_display_t4)
                        st.dataframe(df_t4, use_container_width=True)

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_t4.to_excel(writer, index=False, sheet_name='Boiler Fuel Report')
                            st.download_button("📥 Export เป็น Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Report_Boiler_Fuel_{start_date_t4}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t4")
                        with col_btn2:
                            table_html_t4 = df_t4.to_html(index=False, classes='report-table')
                            components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="window.parent.openPrintPreview4 ? window.parent.openPrintPreview4() : openPrintPreview4()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน (Tab 4)</button></body><script>function openPrintPreview4(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); var content = `<html><head><title>Print Preview - Tab 4</title></head><body><h2>รายงานสรุปเชื้อเพลิงบอยเลอร์</h2><br>{table_html_t4}</body></html>`; w.document.write(content); w.document.close(); w.print();}}</script>""", height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            record_map_t4 = {f"ID: {r[pk_col_t4]} | วันที่: {r.get('record_date')} | สาขา: {r.get('branch_name')}": (r[pk_col_t4], r) for r in raw_data_t4}
                            selected_label_t4 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 4):", options=list(record_map_t4.keys()), key="select_t4")
                            target_pk_t4, target_rec_t4 = record_map_t4[selected_label_t4]

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 4)", expanded=True):
                                e_col1, e_col2, e_col3 = st.columns(3)
                                with e_col1:
                                    e_date_t4 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t4.get('record_date')), key="e_date_t4_in")
                                    e_saw_w_t4 = st.number_input("แก้ไข นหน.ขี้เลื่อย", min_value=0.0, value=float(target_rec_t4.get('sawdust_weight') or 0.0), key="e_saw_w_t4_in")
                                    e_wood_w_t4 = st.number_input("แก้ไข นหน.ปีกไม้", min_value=0.0, value=float(target_rec_t4.get('wood_weight') or 0.0), key="e_wood_w_t4_in")
                                    e_waste_w_t4 = st.number_input("แก้ไข นหน.เศษไม้เสีย", min_value=0.0, value=float(target_rec_t4.get('waste_wood_weight') or 0.0), key="e_waste_w_t4_in")
                                with e_col2:
                                    e_saw_p_t4 = st.number_input("แก้ไข ราคาขี้เลื่อย", min_value=0.0, value=float(target_rec_t4.get('sawdust_price') or 0.0), key="e_saw_p_t4_in")
                                    e_wood_p_t4 = st.number_input("แก้ไข ราคาปีกไม้", min_value=0.0, value=float(target_rec_t4.get('wood_price') or 0.0), key="e_wood_p_t4_in")
                                    e_waste_p_t4 = st.number_input("แก้ไข ราคาเศษไม้เสีย", min_value=0.0, value=float(target_rec_t4.get('waste_wood_price') or 0.0), key="e_waste_p_t4_in")
                                with e_col3:
                                    e_prod_t4 = st.number_input("แก้ไข การผลิตไอน้ำ (ตัน)", min_value=0.1, value=float(target_rec_t4.get('steam_production') or 100.0), key="e_prod_t4_in")
                                    e_hours_t4 = st.number_input("แก้ไข ชม.ทำงาน", min_value=0.1, value=float(target_rec_t4.get('working_hours') or 8.0), key="e_hours_t4_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 4)", key="btn_up_t4", use_container_width=True):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                sql_u = f"UPDATE boiler_fuel_records SET record_date=%s, sawdust_weight=%s, wood_weight=%s, waste_wood_weight=%s, sawdust_price=%s, wood_price=%s, waste_wood_price=%s, steam_production=%s, working_hours=%s WHERE {pk_col_t4}=%s"
                                                cur.execute(sql_u, (e_date_t4, e_saw_w_t4, e_wood_w_t4, e_waste_w_t4, e_saw_p_t4, e_wood_p_t4, e_waste_p_t4, e_prod_t4, e_hours_t4, target_pk_t4))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 4", f"แก้ไขข้อมูล ID: {target_pk_t4}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t4} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 4)", type="primary", use_container_width=True, key="del_btn_t4"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM boiler_fuel_records WHERE {pk_col_t4} = %s", (target_pk_t4,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 4", f"ลบข้อมูล ID: {target_pk_t4}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t4} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 4: {e}")