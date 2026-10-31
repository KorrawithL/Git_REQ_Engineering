import streamlit as st
import pymysql
import time
import pandas as pd
from datetime import datetime
from database import get_db_connection, log_activity
from config import branch_dict
from all_reports import process_t1, process_t2, process_t3, process_t4

def render_engineering_system_tabs(current_branch_name, selected_sub_menu=None):
    st.markdown("""
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        #header { visibility: hidden !important; }
        #MainMenu { visibility: hidden !important; }
        .block-container { padding-top: 1rem !important; margin-top: -20px !important; }
        </style>
    """, unsafe_allow_html=True)

    raw_role = st.session_state.get('role_tab') or st.session_state.get('role') or 'user'
    current_role = str(raw_role).strip().lower()
    allowed_tabs_list = st.session_state.get('allowed_tabs', [])
    user_allowed_branches = st.session_state.get('allowed_branches', [str(st.session_state.get('branch_id'))])

    mapping = {
        "⚙️ ระบบเครื่องจักร / เบรกดาวน์": "1",
        "🚚 ระบบเชื้อเพลิง (รถยก/เครื่องยนต์)": "2",
        "💨 แรงดันไอน้ำปลายทาง บอยเลอร์": "3",
        "🔥 การใช้เชื้อเพลิง บอยเลอร์": "4"
    }
    
    key = mapping.get(selected_sub_menu, "1") if selected_sub_menu else "1"

    if current_role != "admin" and key not in allowed_tabs_list:
        st.error("## ⏳ คุณไม่ได้รับสิทธิ์เข้าถึงหัวข้อนี้")
        return

    if current_role == 'admin':
        available_options = list(branch_dict.keys())
    else:
        available_options = [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]

    current_tab_ctx = st.container()

    # =========================================================================
    # 🔹 TAB 1: บันทึกข้อมูลเครื่องจักร & เบรกดาวน์
    # =========================================================================
    if key == "1":
        with current_tab_ctx:
            st.subheader("ระบบการทำงานของเครื่องจักร / เบรกดาวน์")

            with st.container(border=True):
                st.write("### 📝 ฟอร์มบันทึกข้อมูลเครื่องจักรลงตาราง")
                st.caption("💡 *หมายเหตุ: เครื่องจักรที่ถูกบันทึกข้อมูลในวันที่เลือกไปแล้ว จะถูกซ่อนออกจากตัวเลือกอัตโนมัติเพื่อป้องกันการบันทึกซ้ำ*")
                
                c_top1, c_top2 = st.columns([1.5, 1])
                with c_top1:
                    if len(available_options) > 1:
                        t1_branch_label = st.selectbox("🏢 ระบุสาขาที่ต้องการบันทึก *", options=["-- เลือกสาขา --"] + available_options, key="t1_branch")
                        t1_branch_invalid = (t1_branch_label == "-- เลือกสาขา --")
                        if not t1_branch_invalid:
                            target_branch_id = branch_dict[t1_branch_label]
                    else:
                        t1_branch_label = available_options[0] if available_options else current_branch_name
                        st.write(f"**(สังกัด: {t1_branch_label})**")
                        target_branch_id = branch_dict.get(t1_branch_label, int(st.session_state.branch_id))
                        t1_branch_invalid = False
                
                with c_top2:
                    m_date = st.date_input(
                        "วันที่", format="DD/MM/YYYY", value=pd.to_datetime("today").date(), 
                        max_value=pd.to_datetime("today").date(), key="m_date", disabled=t1_branch_invalid,
                        help="เลือกได้เฉพาะวันนี้หรือวันย้อนหลัง"
                    )

                machine_dict = {}
                conn = None 
                if not t1_branch_invalid:
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            sql = """
                                SELECT id, CONVERT(machine_name USING utf8mb4) AS machine_name 
                                FROM machines_set 
                                WHERE machine_type = 'machine' 
                                    AND branch_id = %s 
                                    AND is_active = 1
                                    AND id NOT IN (
                                        SELECT machine_id 
                                        FROM machine_trans 
                                        WHERE branch_id = %s AND record_date = %s AND is_deleted = 0
                                    )
                            """
                            cur.execute(sql, (target_branch_id, target_branch_id, m_date))
                            db_machines = cur.fetchall()
                            if db_machines: 
                                machine_dict = {m['machine_name']: m['id'] for m in db_machines}
                    except Exception as e: 
                        st.warning(f"ไม่สามารถโหลดข้อมูลเครื่องจักรได้: {e}") 
                    finally:
                        if conn and conn.open: conn.close()

                if machine_dict:
                    machine_select_options = ["-- กรุณาเลือกเครื่องจักร --"] + list(machine_dict.keys())
                else:
                    machine_select_options = ["-- บันทึกข้อมูลครบทุกเครื่องแล้ว --"] if not t1_branch_invalid else ["-- กรุณาเลือกเครื่องจักร --"]

                if "reset_t1" not in st.session_state: st.session_state.reset_t1 = 0
                rk1 = st.session_state.reset_t1
                
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    m_label = st.selectbox(
                        "🚜 ระบุเครื่องจักรที่ใช้งาน *", options=machine_select_options, index=0, 
                        disabled=t1_branch_invalid, key=f"t1_m_label_{rk1}",
                        help="แสดงเฉพาะเครื่องจักรที่ยังไม่ได้บันทึกข้อมูลในวันที่เลือก (หากต้องการแก้ไขรายการที่บันทึกไปแล้ว ให้ไปที่หน้า 'รายงานรวม')"
                    )
                    is_m_not_selected = t1_branch_invalid or (m_label in ["-- กรุณาเลือกเครื่องจักร --", "-- บันทึกข้อมูลครบทุกเครื่องแล้ว --"])
                    m_qty = st.number_input(
                        "จำนวนเครื่องจักร *", min_value=1, step=1, value=None, placeholder="ระบุจำนวน", 
                        disabled=is_m_not_selected, key=f"t1_qty_{rk1}",
                        help="จำนวนเครื่องจักรที่เปิดใช้งาน (ใช้คำนวณเพดานชั่วโมงสูงสุด = จำนวนเครื่อง x 24 ชม.)"
                    )
                with c2:
                    m_work_hours = st.number_input(
                        "ชั่วโมงทำงาน *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน", 
                        disabled=is_m_not_selected, key=f"t1_work_{rk1}",
                        help="ชั่วโมงทำงานรวมกับชั่วโมงเบรกดาวน์ ต้องไม่เกิน 24 ชั่วโมงต่อ 1 เครื่อง"
                    )
                    m_break_hours = st.number_input(
                        "ชั่วโมงเบรกดาวน์ *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงเบรกดาวน์", 
                        disabled=is_m_not_selected, key=f"t1_break_{rk1}",
                        help="หากไม่มีการเสียหรือหยุดเครื่อง ให้กรอกเลข 0"
                    )
                    
                c3 = st.columns(1)[0]
                with c3:
                    m_remark = st.text_area("หมายเหตุ / สาเหตุที่ชำรุด", disabled=is_m_not_selected, key=f"t1_rem_{rk1}", placeholder="ระบุอาการเสียหรือสาเหตุการหยุดเครื่อง (ถ้ามี)...")
                    
                submit_m = st.button("💾 บันทึกข้อมูลเครื่องจักร", use_container_width=True, type="primary", disabled=is_m_not_selected)
                
                if submit_m:
                    if m_qty is None or m_work_hours is None or m_break_hours is None:
                        st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                    elif (m_work_hours + m_break_hours) > (m_qty * 24.0):
                        max_hrs = m_qty * 24.0
                        total_hrs = m_work_hours + m_break_hours
                        st.error(f"⚠️ ไม่สามารถบันทึกได้: ชั่วโมงทำงานรวมกับเบรกดาวน์ ({total_hrs} ชม.) เกินกำหนด ต้องไม่เกิน {max_hrs} ชม. (สำหรับเครื่องจักร {m_qty} เครื่อง)")
                    else:
                        with st.spinner("กำลังบันทึกข้อมูล..."):
                            conn_insert = None 
                            try:
                                m_select_id = machine_dict[m_label]
                                conn_insert = get_db_connection()
                                with conn_insert.cursor() as cur:
                                    sql = """INSERT INTO machine_trans (branch_id, record_date, machine_id, machine_qty, working_hours, breakdown_hours, remarks, created_by, created_at, updated_at, status) 
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 'active')"""
                                    cur.execute(sql, (target_branch_id, m_date, int(m_select_id), int(m_qty), float(m_work_hours), float(m_break_hours), m_remark, int(st.session_state.user_id)))
                                conn_insert.commit()
                                
                                process_t1.clear() 
                                log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 1 Data Entry", f"บันทึกเครื่องจักร {m_label} วันที่ {m_date}")
                                st.toast(f"✅ บันทึกข้อมูล {m_label} สำเร็จเรียบร้อย!", icon="🎉")
                                
                                st.session_state.reset_t1 += 1
                                time.sleep(1.2)
                                st.rerun()
                            except Exception as e: 
                                st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
                            finally:
                                if conn_insert and conn_insert.open: conn_insert.close() 

    # =========================================================================
    # 🚚 TAB 2: บันทึกการใช้เชื้อเพลิงรถยนต์ / รถยก
    # =========================================================================
    elif key == "2":
        with current_tab_ctx:
            st.subheader("ระบบการใช้เชื้อเพลิง (เครื่องยนต์/รถยก)")
            
            with st.container(border=True):
                st.write("### 📝 ฟอร์มบันทึกข้อมูลการใช้เชื้อเพลิงรถ")
                st.caption("💡 *หมายเหตุ: รถที่ถูกบันทึกข้อมูลในวันที่เลือกไปแล้ว จะถูกซ่อนออกจากตัวเลือกอัตโนมัติ*")
                
                if "reset_t2" not in st.session_state: st.session_state.reset_t2 = 0
                rk2 = st.session_state.reset_t2

                c_top1, c_top2 = st.columns([1.5, 1])
                with c_top1:
                    if len(available_options) > 1:
                        t2_branch_lbl = st.selectbox("🏢 ระบุสาขาที่ต้องการบันทึก *", ["-- เลือกสาขา --"] + available_options, key="t2_br")
                        t2_branch_invalid = (t2_branch_lbl == "-- เลือกสาขา --")
                        if not t2_branch_invalid:
                            target_branch_id_t2 = branch_dict[t2_branch_lbl]
                    else:
                        t2_branch_lbl = available_options[0] if available_options else current_branch_name
                        st.write(f"**(สังกัด: {t2_branch_lbl})**")
                        target_branch_id_t2 = branch_dict.get(t2_branch_lbl, int(st.session_state.branch_id))
                        t2_branch_invalid = False
                with c_top2:
                    f_date = st.date_input(
                        "วันที่", format="DD/MM/YYYY", value=pd.to_datetime("today").date(), 
                        max_value=pd.to_datetime("today").date(), key="f_date", disabled=t2_branch_invalid,
                        help="เลือกได้เฉพาะวันนี้หรือวันย้อนหลัง"
                    )
                all_engines_filtered = []
                conn = None
                if not t2_branch_invalid:
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            sql_eng = """
                                SELECT CONVERT(m.machine_name USING utf8mb4) AS engine_code, 
                                        CONVERT(et.type_name USING utf8mb4) AS type_name
                                FROM machines_set m 
                                LEFT JOIN engine_types et ON m.engine_type_id = et.id 
                                WHERE m.branch_id = %s 
                                    AND m.machine_type = 'engine' 
                                    AND m.is_active = 1
                                    AND NOT EXISTS (
                                        SELECT 1 
                                        FROM fuel_records fr 
                                        WHERE fr.branch_id = %s 
                                        AND fr.record_date = %s
                                        AND fr.engine_code = CONVERT(m.machine_name USING utf8mb4)
                                        AND fr.type_name = CONVERT(et.type_name USING utf8mb4)
                                        AND fr.is_deleted = 0
                                    )
                            """
                            cur.execute(sql_eng, (target_branch_id_t2, target_branch_id_t2, f_date))
                            all_engines_filtered = cur.fetchall()
                    except Exception as e: 
                        st.warning(f"ไม่สามารถโหลดข้อมูลรถได้: {e}")
                    finally:
                        if conn and conn.open: conn.close() 

                c_sel1, c_sel2 = st.columns(2)
                
                if all_engines_filtered:
                    available_types = sorted(list(set([e['type_name'] for e in all_engines_filtered if e['type_name']])))
                    type_options = ["-- เลือกประเภท --"] + available_types
                    f2_type_disabled = False
                else:
                    type_options = ["-- บันทึกข้อมูลครบทุกคันแล้ว --"] if not t2_branch_invalid else ["-- เลือกประเภท --"]
                    f2_type_disabled = True
                    
                with c_sel1:
                    f2_type = st.selectbox(
                        "🚜 ระบุ ชนิด / ประเภทรถ ที่ต้องการบันทึก *", type_options, key="f2_ty", 
                        disabled=f2_type_disabled,
                        help="เลือกยี่ห้อหรือประเภทรถ (เช่น TOYOTA, TCK)"
                    )
                
                f2_code_disabled = (f2_type in ["-- เลือกประเภท --", "-- บันทึกข้อมูลครบทุกคันแล้ว --"]) or f2_type_disabled
                if not f2_code_disabled:
                    available_codes = sorted(list(set([e['engine_code'] for e in all_engines_filtered if e['type_name'] == f2_type])))
                    code_options = ["-- เลือกรถ --"] + available_codes
                else:
                    code_options = ["-- เลือกรถ --"]
                    
                with c_sel2:
                    f2_code = st.selectbox(
                        "🏷️ ระบุ รหัสงาน / ทะเบียนรถ ที่ต้องการบันทึก *", code_options, key=f"f2_cd_{rk2}", 
                        disabled=f2_code_disabled,
                        help="แสดงเฉพาะทะเบียนรถที่ยังไม่ได้ลงบันทึกในวันที่เลือก"
                    )
                    
                inputs_disabled = (f2_code == "-- เลือกรถ --") or f2_code_disabled
                
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    f_liters = st.number_input(
                        "ปริมาณน้ำมัน (ลิตร) *", min_value=0.0, step=1.0, value=None, placeholder="ระบุปริมาณน้ำมัน", 
                        disabled=inputs_disabled, key=f"t2_lit_{rk2}",
                        help="ระบุปริมาณน้ำมันดีเซลที่เติม (หากไม่ได้เติมน้ำมันในวันนั้นให้ใส่ 0)"
                    )
                with c2:
                    f_hours = st.number_input(
                        "จำนวนชั่วโมงทำงาน (ชม.) *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน", 
                        disabled=inputs_disabled, key=f"t2_hrs_{rk2}",
                        help="ชั่วโมงการทำงานของรถต้องไม่เกิน 24 ชั่วโมงต่อวัน"
                    )
                c3 = st.columns(1)[0]
                with c3:    
                    f_remark = st.text_area("หมายเหตุ", disabled=inputs_disabled, key=f"t2_rem_{rk2}")
                    
                submit_f = st.button("💾 บันทึกข้อมูลเชื้อเพลิงรถ", use_container_width=True, type="primary", disabled=inputs_disabled)
                
                if submit_f:
                    if inputs_disabled or f_liters is None or f_hours is None:
                        st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                    elif f_hours > 24.0:
                        st.error("⚠️ ไม่สามารถบันทึกได้: ชั่วโมงทำงานรถยนต์ต้องไม่เกิน 24 ชั่วโมงต่อวัน")
                    else:
                        with st.spinner("กำลังบันทึกข้อมูล..."):
                            conn_insert = None
                            try:
                                conn_insert = get_db_connection()
                                with conn_insert.cursor() as cur:
                                    sql = """INSERT INTO fuel_records (branch_id, record_date, engine_code, type_name, fuel_liters, working_hours, remark) 
                                                VALUES (%s, %s, CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), %s, %s, CONVERT(%s USING utf8mb4))"""
                                    cur.execute(sql, (target_branch_id_t2, f_date, f2_code, f2_type, float(f_liters), float(f_hours), f_remark))
                                conn_insert.commit()
                                
                                process_t2.clear() 
                                log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 2 Data Entry", f"บันทึกเชื้อเพลิงรถ {f2_code} จำนวน {f_liters} ลิตร")
                                st.toast(f"✅ บันทึกสำเร็จ! ({f2_code})", icon="🚚")
                                
                                st.session_state.reset_t2 += 1
                                time.sleep(1.2)
                                st.rerun()
                            except Exception as e: 
                                st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
                            finally:
                                if conn_insert and conn_insert.open: conn_insert.close() 

    # =========================================================================
    # 💨 TAB 3: บันทึกแรงดันไอน้ำ บอยเลอร์ 
    # =========================================================================
    elif key == "3":
        with current_tab_ctx:
            st.subheader("ระบบแรงดันไอน้ำปลายทางของบอยเลอร์")
            
            with st.container(border=True):
                st.write("### 📝 บันทึกข้อมูลแรงดันไอน้ำ")
                st.caption("💡 *หมายเหตุ: บันทึกสรุปวันละ 1 รายการต่อสาขา โดยผลรวมจำนวนครั้งที่แรงดันตก (PM + นอก PM) ต้องไม่เกินจำนวนครั้งที่ตรวจเช็คทั้งหมด*")
                
                c_top1, c_top2 = st.columns([1.5, 1])
                with c_top1:
                    if len(available_options) > 1:
                        t3_branch_label = st.selectbox("🏢 ระบุสาขาที่ต้องการบันทึก *", options=["-- เลือกสาขา --"] + available_options, key="t3_branch")
                        t3_branch_invalid = (t3_branch_label == "-- เลือกสาขา --")
                        if not t3_branch_invalid:
                            target_branch_id = branch_dict[t3_branch_label]
                    else:
                        t3_branch_label = available_options[0] if available_options else current_branch_name
                        st.write(f"**(สังกัด: {t3_branch_label})**")
                        target_branch_id = branch_dict.get(t3_branch_label, int(st.session_state.branch_id))
                        t3_branch_invalid = False
                with c_top2:
                    p_date = st.date_input(
                        "วันที่", format="DD/MM/YYYY", value=pd.to_datetime("today").date(), 
                        max_value=pd.to_datetime("today").date(), key="p_date", disabled=t3_branch_invalid,
                        help="เลือกได้เฉพาะวันนี้หรือวันย้อนหลัง"
                        )

                has_t3_record = False
                conn = None
                if not t3_branch_invalid:
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            cur.execute("SELECT 1 FROM boiler_pressure_records WHERE branch_id=%s AND record_date=%s AND is_deleted = 0", (target_branch_id, p_date))
                            if cur.fetchone(): has_t3_record = True
                    except Exception: 
                        pass
                    finally:
                        if conn and conn.open: conn.close() 
                        
                is_t3_disabled = t3_branch_invalid or has_t3_record

                if has_t3_record:
                    st.warning("⚠️ มีการบันทึกข้อมูลแรงดันไอน้ำของสาขานี้ ในวันที่เลือกไปแล้ว (หากต้องการแก้ไข กรุณาไปที่หน้า 'รายงานรวม')")

                if "reset_t3" not in st.session_state: st.session_state.reset_t3 = 0
                rk3 = st.session_state.reset_t3

                col1, col2 = st.columns(2)
                with col1:
                    total_count = st.number_input(
                        "จำนวนครั้งทั้งหมด *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนครั้งทั้งหมด", 
                        disabled=is_t3_disabled, key=f"t3_tot_{rk3}",
                        help="จำนวนครั้งที่ตรวจวัดแรงดันไอน้ำทั้งหมดในวันนั้น (เช่น ตรวจทุก 15 นาที = 96 ครั้ง/วัน)"
                    )
                    pm_drop = st.number_input(
                        "จำนวนที่ตกตามเงื่อนไข PM *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนที่ตกตามเงื่อนไข PM", 
                        disabled=is_t3_disabled, key=f"t3_pm_{rk3}",
                        help="จำนวนครั้งที่แรงดันต่ำกว่าเกณฑ์เนื่องจากอยู่ในช่วงลากขี้เถ้าหรือบำรุงรักษาตามรอบ PM"
                    )
                with col2:
                    non_pm_drop = st.number_input(
                        "จำนวนที่ตกนอกเหนือ PM *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนที่ตกนอกเหนือ PM", 
                        disabled=is_t3_disabled, key=f"t3_npm_{rk3}",
                        help="จำนวนครั้งที่แรงดันตกผิดปกตินอกรอบ PM (เมื่อรวมกับตกตาม PM แล้วต้องไม่เกินจำนวนครั้งทั้งหมด)"
                    )
                    p_remark = st.text_input("หมายเหตุ (ลากขี้เถ้า / ซ่อมบำรุง)", disabled=is_t3_disabled, key=f"t3_rem_{rk3}")
                    
                submit_p = st.button("💾 บันทึกข้อมูลแรงดันไอน้ำ", use_container_width=True, type="primary", disabled=is_t3_disabled)
                
                if submit_p:
                    if total_count is None or pm_drop is None or non_pm_drop is None:
                        st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                    elif (pm_drop + non_pm_drop) > total_count:
                        st.error("⚠️ ไม่สามารถบันทึกได้: จำนวนครั้งที่ 'แรงดันตก' รวมกัน ต้องไม่มากกว่า 'จำนวนครั้งทั้งหมด'")
                    else:
                        with st.spinner("กำลังบันทึกข้อมูล..."):
                            conn_insert = None
                            try:
                                conn_insert = get_db_connection()
                                with conn_insert.cursor() as cur:
                                    sql = """INSERT INTO boiler_pressure_records (branch_id, record_date, total_count, total_drop, pm_drop, non_pm_drop, remark, created_by) 
                                                VALUES (%s, %s, %s, %s, %s, %s, CONVERT(%s USING utf8mb4), %s)"""
                                    cur.execute(sql, (target_branch_id, p_date, int(total_count), (int(pm_drop) + int(non_pm_drop)), int(pm_drop), int(non_pm_drop), p_remark, int(st.session_state.user_id)))
                                conn_insert.commit()
                                
                                process_t3.clear() 
                                log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 3 Data Entry", f"บันทึกแรงดันไอน้ำตก วันที่ {p_date}")
                                st.toast("✅ บันทึกข้อมูลแรงดันไอน้ำเรียบร้อยแล้ว!", icon="💨")
                                
                                st.session_state.reset_t3 += 1
                                time.sleep(1.2)
                                st.rerun()
                            except Exception as e: 
                                st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
                            finally:
                                if conn_insert and conn_insert.open: conn_insert.close() 

    # =========================================================================
    # 🔥 TAB 4: การใช้เชื้อเพลิง บอยเลอร์
    # =========================================================================
    elif key == "4":
        with current_tab_ctx:
            st.subheader("ระบบการใช้เชื้อเพลิงบอยเลอร์")
            st.info(
                "📌 **ข้อแนะนำสำคัญ:** เพื่อให้รายงานสรุปรวม (บอยเลอร์ 1+2) คำนวณข้อมูลรายวันได้ครบถ้วน "
                "กรุณาบันทึกข้อมูลทั้งในแท็บ **'📁 ยอดรวมสาขา'** และแท็บ **'🏭 ปริมาณเชื้อเพลิงบอยเลอร์ (ทั้งบอยเลอร์ 1 และ 2)'** ของวันนั้นให้ครบ"
            )

            if "reset_t4" not in st.session_state: st.session_state.reset_t4 = 0
            rk4 = st.session_state.reset_t4

            sub_tab1, sub_tab2 = st.tabs(["📁 บันทึกข้อมูลยอดรวมสาขา (เตา/ไม้อบ/แรงดัน)", "🏭 บันทึกปริมาณเชื้อเพลิงบอยเลอร์"])

            # แท็บย่อยที่ 1: บันทึกข้อมูลยอดรวมของสาขา
            with sub_tab1:
                with st.container(border=True):
                    st.write("### 📁 บันทึกข้อมูลยอดรวมของสาขาประจำวัน")
                    
                    c_top1, c_top2 = st.columns([1.5, 1])
                    with c_top1:
                        if len(available_options) > 1:
                            t4_branch_lbl_1 = st.selectbox("🏢 ระบุสาขาที่ต้องการบันทึก *", options=["-- เลือกสาขา --"] + available_options, key="t4_br1")
                            t4_ov_invalid = (t4_branch_lbl_1 == "-- เลือกสาขา --")
                            if not t4_ov_invalid:
                                target_branch_id_1 = branch_dict[t4_branch_lbl_1]
                        else:
                            t4_branch_lbl_1 = available_options[0] if available_options else current_branch_name
                            st.write(f"**(สังกัด: {t4_branch_lbl_1})**")
                            target_branch_id_1 = branch_dict.get(t4_branch_lbl_1, int(st.session_state.branch_id))
                            t4_ov_invalid = False
                    with c_top2:
                        bf_date_1 = st.date_input(
                            "วันที่", format="DD/MM/YYYY", value=pd.to_datetime("today").date(), 
                            max_value=pd.to_datetime("today").date(), key="bf_dt1", disabled=t4_ov_invalid,
                            help="เลือกได้เฉพาะวันนี้หรือวันย้อนหลัง"
                            )

                    has_t4_ov_record = False
                    conn = None
                    if not t4_ov_invalid:
                        try:
                            conn = get_db_connection()
                            with conn.cursor() as cur:
                                cur.execute("SELECT id FROM daily_wood_oven_records WHERE branch_id=%s AND record_date=%s AND is_deleted = 0", (target_branch_id_1, bf_date_1))
                                if cur.fetchone(): has_t4_ov_record = True
                        except Exception: pass
                        finally:
                            if conn and conn.open: conn.close() 
                            
                    is_t4_ov_disabled = t4_ov_invalid or has_t4_ov_record
                    
                    if has_t4_ov_record:
                        st.warning("⚠️ มีการบันทึกข้อมูลยอดรวมของสาขานี้ ในวันที่เลือกไปแล้ว (หากต้องการแก้ไข กรุณาไปที่หน้า 'รายงานรวม')")

                    c_ov1, c_ov2, c_ov3 = st.columns(3)
                    with c_ov1:
                        oven_qty = st.number_input(
                            "จำนวนเตาที่อบ (เตา) *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนเตา", 
                            disabled=is_t4_ov_disabled, key=f"t4_ov_{rk4}",
                            help="จำนวนเตาอบไม้ที่เปิดเดินเครื่องในวันนั้น (ใช้คำนวณเป้าหมายไอน้ำมาตรฐาน)"
                        )
                    with c_ov2:
                        wood_out = st.number_input(
                            "ไม้เข้าอบ (ลบ.ฟ.) *", min_value=0.0, step=0.001, format="%.3f", value=None, placeholder="ระบุปริมาณ", 
                            disabled=is_t4_ov_disabled, key=f"t4_wo_{rk4}",
                            help="ปริมาตรไม้เข้าอบรวม (ลูกบาศก์ฟุต) รองรับทศนิยม 3 ตำแหน่ง"
                        )
                    with c_ov3:
                        avg_pressure = st.number_input(
                            "แรงดันปลายทางเฉลี่ย *", min_value=0.0, step=0.1, value=None, placeholder="ระบุแรงดัน", 
                            disabled=is_t4_ov_disabled, key=f"t4_avgp_{rk4}",
                            help="ค่าแรงดันไอน้ำปลายทางเฉลี่ยของวันนั้น (Bar)"
                        )

                    submit_oven = st.button("💾 บันทึกข้อมูลยอดรวมสาขา", use_container_width=True, type="primary", disabled=is_t4_ov_disabled)
                    
                    if submit_oven:
                        inputs_ov = [oven_qty, wood_out, avg_pressure]
                        if any(x is None for x in inputs_ov):
                            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                        else:
                            with st.spinner("กำลังบันทึกข้อมูล..."):
                                conn_insert = None
                                try:
                                    conn_insert = get_db_connection()
                                    with conn_insert.cursor() as cur:
                                        sql_oven = """INSERT INTO daily_wood_oven_records (branch_id, record_date, oven_qty, wood_out_cubft, avg_terminal_pressure, created_by)
                                                        VALUES (%s, %s, %s, %s, %s, %s)"""
                                        cur.execute(sql_oven, (target_branch_id_1, bf_date_1, int(oven_qty), float(wood_out), float(avg_pressure), int(st.session_state.user_id)))
                                    conn_insert.commit()
                                    
                                    process_t4.clear() 
                                    log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 4 Oven Entry", f"บันทึกยอดรวมสาขา วันที่ {bf_date_1}")
                                    st.toast("✅ บันทึกข้อมูลยอดรวมสาขาสำเร็จแล้ว!", icon="📁")
                                    
                                    st.session_state.reset_t4 += 1
                                    time.sleep(1.2)
                                    st.rerun()
                                except Exception as e: 
                                    st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
                                finally:
                                    if conn_insert and conn_insert.open: conn_insert.close() 

            # แท็บย่อยที่ 2: บันทึกปริมาณเชื้อเพลิงบอยเลอร์
            with sub_tab2:
                with st.container(border=True):
                    st.write("### 🏭 บันทึกปริมาณเชื้อเพลิงแยกตามบอยเลอร์")
                    
                    c_top1, c_top2 = st.columns([1.5, 1])
                    with c_top1:
                        if len(available_options) > 1:
                            t4_branch_lbl_2 = st.selectbox("🏢 ระบุสาขาที่ต้องการบันทึก *", options=["-- เลือกสาขา --"] + available_options, key="t4_br2")
                            t4_bf_invalid = (t4_branch_lbl_2 == "-- เลือกสาขา --")
                            if not t4_bf_invalid:
                                target_branch_id_2 = branch_dict[t4_branch_lbl_2]
                        else:
                            t4_branch_lbl_2 = available_options[0] if available_options else current_branch_name
                            st.write(f"**(สังกัด: {t4_branch_lbl_2})**")
                            target_branch_id_2 = branch_dict.get(t4_branch_lbl_2, int(st.session_state.branch_id))
                            t4_bf_invalid = False
                    with c_top2:
                        bf_date_2 = st.date_input(
                            "วันที่", format="DD/MM/YYYY", value=pd.to_datetime("today").date(), 
                            max_value=pd.to_datetime("today").date(), key="bf_dt2", disabled=t4_bf_invalid,
                            help="เลือกได้เฉพาะวันนี้หรือวันย้อนหลัง"
                            )

                    boiler_options = []
                    conn = None
                    if not t4_bf_invalid:
                        try:
                            conn = get_db_connection()
                            with conn.cursor() as cur:
                                sql = """
                                    SELECT CONVERT(b.boiler_name USING utf8mb4) AS b_name 
                                    FROM boilers b
                                    WHERE b.branch_id = %s 
                                        AND b.is_active = 1
                                        AND NOT EXISTS (
                                            SELECT 1 
                                            FROM boiler_fuel_records bfr 
                                            WHERE bfr.branch_id = %s 
                                            AND bfr.record_date = %s
                                            AND CONVERT(bfr.boiler_name USING utf8mb4) = CONVERT(b.boiler_name USING utf8mb4)
                                            AND bfr.is_deleted = 0
                                        ) 
                                    ORDER BY b.id ASC
                                """
                                cur.execute(sql, (target_branch_id_2, target_branch_id_2, bf_date_2))
                                for r in cur.fetchall():
                                    if r['b_name']: boiler_options.append(r['b_name'])
                        except Exception as e: 
                            st.warning(f"ไม่สามารถโหลดข้อมูลบอยเลอร์ได้: {e}")
                        finally:
                            if conn and conn.open: conn.close() 
                    
                    if not t4_bf_invalid:
                        if boiler_options:
                            b_list = ["-- เลือกบอยเลอร์ --"] + boiler_options
                            is_boiler_invalid = False
                        else:
                            b_list = ["-- บันทึกข้อมูลครบทุกเครื่องแล้ว --"]
                            is_boiler_invalid = True
                    else:
                        b_list = ["-- เลือกบอยเลอร์ --"]
                        is_boiler_invalid = True
                        
                    boiler_name_input = st.selectbox(
                        "🚜 ระบุเครื่องบอยเลอร์ที่ใช้งาน *", b_list, disabled=is_boiler_invalid, key="t4_boiler",
                        help="เลือกบอยเลอร์ที่ต้องการบันทึก (แสดงเฉพาะเครื่องที่ยังไม่ได้บันทึกในวันนั้น)"
                    )
                    disable_t4_inputs = is_boiler_invalid or (boiler_name_input == "-- เลือกบอยเลอร์ --")

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write("**📦 ส่วนที่ 1: เชื้อเพลิงที่ใช้ (ตัน/วัน)**")
                        saw_w = st.number_input("น้ำหนักขี้เลื่อย (ตัน) *", min_value=0.0, step=0.1, value=None, placeholder="ระบุน้ำหนักขี้เลื่อย", disabled=disable_t4_inputs, key=f"t4_sw_{rk4}")
                        wood_w = st.number_input("น้ำหนักปีกไม้ (ตัน) *", min_value=0.0, step=0.001, format="%.3f", value=None, placeholder="ระบุน้ำหนักปีกไม้", disabled=disable_t4_inputs, key=f"t4_ww_{rk4}")
                        waste_wood_w = st.number_input("น้ำหนักเศษไม้เสีย (ตัน) *", min_value=0.0, step=0.1, value=None, placeholder="ระบุน้ำหนักเศษไม้เสีย", disabled=disable_t4_inputs, key=f"t4_www_{rk4}")
                    with c2:
                        st.write("**💰 ส่วนที่ 2: ราคาเชื้อเพลิง (ต่อตัน)**")
                        saw_p = st.number_input("ราคาขี้เลื่อย (บาท) *", min_value=0.0, step=50.0, value=None, placeholder="ระบุราคาขี้เลื่อย", disabled=disable_t4_inputs, key=f"t4_sp_{rk4}")
                        wood_p = st.number_input("ราคาปีกไม้ (บาท) *", min_value=0.0, step=50.0, value=None, placeholder="ระบุราคาปีกไม้", disabled=disable_t4_inputs, key=f"t4_wp_{rk4}")
                        waste_wood_p = st.number_input("ราคาเศษไม้เสีย (บาท) *", min_value=0.0, step=50.0, value=None, placeholder="ระบุราคาเศษไม้เสีย", disabled=disable_t4_inputs, key=f"t4_wwp_{rk4}")
                    with c3:
                        st.write("**💨 ส่วนที่ 3: การผลิตไอน้ำ (ตัน/วัน)**")
                        prod_val = st.number_input("ปริมาณการผลิต (ตัน/วัน) *", min_value=0.1, step=1.0, value=None, placeholder="ระบุการผลิตไอน้ำ", disabled=disable_t4_inputs, key=f"t4_prod_{rk4}")
                        work_hours = st.number_input(
                            "จำนวนชั่วโมงทำงาน (ชม.) *", min_value=0.1, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน", 
                            disabled=disable_t4_inputs, key=f"t4_wh_{rk4}",
                            help="ชั่วโมงเดินเครื่องบอยเลอร์ต้องไม่เกิน 24 ชั่วโมงต่อวัน"
                        )
                        
                    submit_bf = st.button("💾 บันทึกข้อมูลเชื้อเพลิงบอยเลอร์", use_container_width=True, type="primary", disabled=disable_t4_inputs)
                    
                    if submit_bf:
                        inputs_bf = [saw_w, wood_w, waste_wood_w, saw_p, wood_p, waste_wood_p, prod_val, work_hours]
                        if any(x is None for x in inputs_bf):
                            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                        elif work_hours > 24.0:
                            st.error("⚠️ ไม่สามารถบันทึกได้: ชั่วโมงทำงานต้องไม่เกิน 24 ชั่วโมงต่อวัน")
                        else:
                            with st.spinner("กำลังบันทึกข้อมูล..."):
                                conn_insert = None
                                try:
                                    conn_insert = get_db_connection()
                                    with conn_insert.cursor() as cur:
                                        sql_fuel = """INSERT INTO boiler_fuel_records (branch_id, record_date, boiler_name, sawdust_weight, wood_weight, waste_wood_weight, sawdust_price, wood_price, waste_wood_price, steam_production, working_hours, created_by) 
                                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                                        cur.execute(sql_fuel, (target_branch_id_2, bf_date_2, boiler_name_input, float(saw_w), float(wood_w), float(waste_wood_w), float(saw_p), float(wood_p), float(waste_wood_p), float(prod_val), float(work_hours), int(st.session_state.user_id)))
                                    conn_insert.commit()
                                    
                                    process_t4.clear() 
                                    log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 4 Boiler Entry", f"บันทึกเชื้อเพลิง {boiler_name_input} วันที่ {bf_date_2}")
                                    st.toast(f"✅ บันทึกข้อมูล {boiler_name_input} สำเร็จแล้ว!", icon="🔥")
                                    
                                    st.session_state.reset_t4 += 1
                                    time.sleep(1.2)
                                    st.rerun()
                                except Exception as e: 
                                    st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
                                finally:
                                    if conn_insert and conn_insert.open: conn_insert.close()