import streamlit as st
import pymysql
import time
from datetime import datetime
from database import get_db_connection, log_activity
from config import branch_dict

def render_engineering_system_tabs(current_branch_name):
    raw_role = st.session_state.get('role_tab') or st.session_state.get('role') or 'user'
    current_role = str(raw_role).strip().lower()
    allowed_tabs_list = st.session_state.get('allowed_tabs', [])
    
    # 🎯 ดึงสิทธิ์สาขาทั้งหมดของผู้ใช้งาน
    user_allowed_branches = st.session_state.get('allowed_branches', [str(st.session_state.branch_id)])

    all_tabs_config = {
        "1": "⚙️ 1. ระบบเครื่องจักร / เบรกดาวน์", "2": "🚚 2. ระบบเชื้อเพลิง (รถยก/เครื่องยนต์)",
        "3": "💨 3. แรงดันไอน้ำปลายทาง บอยเลอร์", "4": "🔥 4. การใช้เชื้อเพลิง บอยเลอร์"
    }

    # ให้เฉพาะ admin เท่านั้นที่มีสิทธิ์เข้าถึงทุกแท็บโดยไม่ต้องรออนุมัติ
    if current_role == "admin": 
        visible_tab_keys = ["1", "2", "3", "4"]
    else: 
        visible_tab_keys = [k for k in allowed_tabs_list if k in all_tabs_config]

    if not visible_tab_keys:
        st.error("## ⏳ รอการอนุมัติสิทธิ์เลือกแท็บงานจากแอดมิน")
        return

    tab_labels = [all_tabs_config[k] for k in visible_tab_keys]
    created_tabs = st.tabs(tab_labels)

    for index, key in enumerate(visible_tab_keys):
        current_tab_ctx = created_tabs[index]

        # =========================================================================
        # 🔹 TAB 1: บันทึกข้อมูลเครื่องจักร & เบรกดาวน์
        # =========================================================================
        if key == "1":
            with current_tab_ctx:
                st.header("1. ระบบการทำงานของเครื่องจักร / เบรกดาวน์")
                
                if current_role == 'admin':
                    available_options = list(branch_dict.keys())
                else:
                    available_options = [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]

                machine_dict = {}
                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        # 🎯 ดึงจากตารางใหม่ machines_set
                        if current_role == "admin":
                            cur.execute("SELECT id, CONVERT(machine_name USING utf8mb4) AS machine_name FROM machines_set WHERE machine_type = 'machine' AND is_active = 1")
                        else:
                            placeholders = ', '.join(['%s'] * len(user_allowed_branches))
                            cur.execute(f"SELECT id, CONVERT(machine_name USING utf8mb4) AS machine_name FROM machines_set WHERE machine_type = 'machine' AND branch_id IN ({placeholders}) AND is_active = 1", tuple(user_allowed_branches))
                        
                        db_machines = cur.fetchall()
                        if db_machines: machine_dict = {m['machine_name']: m['id'] for m in db_machines}
                    conn.close()
                except Exception: pass

                machine_select_options = ["-- กรุณาเลือกเครื่องจักร --"] + list(machine_dict.keys())
                
                # 🎯 ถอด st.form ออก เพื่อให้หน้าเว็บอัปเดตแบบโต้ตอบได้
                with st.container(border=True):
                    st.write("### 📝 ฟอร์มบันทึกข้อมูลเครื่องจักรลงตาราง")
                    
                    if len(available_options) > 1:
                        t1_branch_label = st.selectbox("ระบุสาขาที่ต้องการบันทึก *", options=available_options, key="t1_branch")
                        target_branch_id = branch_dict[t1_branch_label]
                    else:
                        t1_branch_label = available_options[0] if available_options else current_branch_name
                        st.write(f"**(สังกัด: {t1_branch_label})**")
                        target_branch_id = branch_dict.get(t1_branch_label, int(st.session_state.branch_id))

                    c1, c2 = st.columns(2)
                    with c1:
                        m_label = st.selectbox("ระบุเครื่องจักรที่ใช้งาน *", options=machine_select_options, index=0)
                        
                        # 🎯 ล็อกช่องกรอกข้อมูลจนกว่าจะเลือกเครื่องจักร
                        is_m_not_selected = (m_label == "-- กรุณาเลือกเครื่องจักร --")
                        
                        m_date = st.date_input("วันที่", value=datetime.now(), key="m_date", disabled=is_m_not_selected)
                        m_qty = st.number_input("จำนวนเครื่องจักร *", min_value=1, step=1, value=None, placeholder="ระบุจำนวน", disabled=is_m_not_selected)
                    with c2:
                        m_work_hours = st.number_input("ชั่วโมงทำงาน *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน", disabled=is_m_not_selected)
                        m_break_hours = st.number_input("ชั่วโมงเบรกดาวน์ *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงเบรกดาวน์", disabled=is_m_not_selected)
                        m_remark = st.text_area("หมายเหตุ / สาเหตุที่ชำรุด", disabled=is_m_not_selected)
                        
                    submit_m = st.button("💾 บันทึกข้อมูลเครื่องจักร", use_container_width=True, type="primary", disabled=is_m_not_selected)
                    
                    if submit_m:
                        if m_label == "-- กรุณาเลือกเครื่องจักร --" or m_qty is None or m_work_hours is None or m_break_hours is None:
                            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                        else:
                            try:
                                m_select_id = machine_dict[m_label]
                                conn = get_db_connection()
                                with conn.cursor() as cur:
                                    sql = """INSERT INTO machine_trans (branch_id, record_date, machine_id, machine_qty, working_hours, breakdown_hours, remarks, created_by, created_at, updated_at, status) 
                                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 'active')"""
                                    cur.execute(sql, (target_branch_id, m_date, int(m_select_id), int(m_qty), float(m_work_hours), float(m_break_hours), m_remark, int(st.session_state.user_id)))
                                conn.commit()
                                conn.close()
                                
                                st.cache_data.clear()
                                log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 1 Data Entry", f"บันทึกเครื่องจักร {m_label} วันที่ {m_date}")
                                st.success("✅ บันทึกข้อมูลเครื่องจักรสำเร็จเรียบร้อยแล้ว!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e: st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

        # =========================================================================
        # 🚚 TAB 2: บันทึกการใช้เชื้อเพลิงรถยนต์ / รถยก (เปลี่ยนเป็น 3 ช่อง)
        # =========================================================================
        elif key == "2":
            with current_tab_ctx:
                st.header("2. ระบบการใช้เชื้อเพลิง (เครื่องยนต์/รถยก)")
                
                all_engines = []
                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        # 🎯 ดึงจากตารางใหม่ machines_set
                        if current_role == "admin":
                            sql_eng = """SELECT m.id AS engine_pk_id, CONVERT(m.machine_name USING utf8mb4) AS engine_code, 
                                        CONVERT(et.type_name USING utf8mb4) AS type_name, 
                                        CONVERT(b.branch_name USING utf8mb4) AS branch_name, m.branch_id
                                        FROM machines_set m 
                                        LEFT JOIN engine_types et ON m.engine_type_id = et.id 
                                        LEFT JOIN branches b ON m.branch_id = b.id 
                                        WHERE m.machine_type = 'engine' AND m.is_active = 1 
                                        ORDER BY b.id ASC, m.machine_name ASC"""
                            cur.execute(sql_eng)
                        else:
                            placeholders = ', '.join(['%s'] * len(user_allowed_branches))
                            sql_eng = f"""SELECT m.id AS engine_pk_id, CONVERT(m.machine_name USING utf8mb4) AS engine_code, 
                                        CONVERT(et.type_name USING utf8mb4) AS type_name, 
                                        CONVERT(b.branch_name USING utf8mb4) AS branch_name, m.branch_id
                                        FROM machines_set m 
                                        LEFT JOIN engine_types et ON m.engine_type_id = et.id 
                                        LEFT JOIN branches b ON m.branch_id = b.id 
                                        WHERE m.branch_id IN ({placeholders}) AND m.machine_type = 'engine' AND m.is_active = 1 
                                        ORDER BY m.machine_name ASC"""
                            cur.execute(sql_eng, tuple(user_allowed_branches))
                            
                        all_engines = cur.fetchall()
                    conn.close()
                except Exception as e: st.error(f"ไม่สามารถดึงข้อมูลรถยนต์ได้: {e}")

                # 🎯 ถอด st.form ออก เพื่อให้ Dropdown อัปเดตแบบเรียลไทม์
                with st.container(border=True):
                    st.write("### 📝 ฟอร์มบันทึกข้อมูลการใช้เชื้อเพลิงรถ")
                    
                    # 🎯 ส่วนที่ 1: แตกช่องเลือกข้อมูลเป็น 3 ส่วน (Cascading Dropdowns)
                    c_sel1, c_sel2, c_sel3 = st.columns(3)
                    
                    # 1. เลือกสาขา
                    available_branch_names = sorted(list(set([eng['branch_name'] for eng in all_engines if eng['branch_name']])))
                    f2_branch = c_sel1.selectbox("🏢 1. สาขา *", ["-- เลือกสาขา --"] + available_branch_names, key="f2_br")
                    
                    # 2. เลือกชนิด/ประเภท (กรองตามสาขา)
                    f2_type_disabled = (f2_branch == "-- เลือกสาขา --")
                    if not f2_type_disabled:
                        filtered_by_branch = [e for e in all_engines if e['branch_name'] == f2_branch]
                        available_types = sorted(list(set([e['type_name'] for e in filtered_by_branch if e['type_name']])))
                    else:
                        available_types = []
                        filtered_by_branch = []
                        
                    f2_type = c_sel2.selectbox("🚜 2. ชนิด / ประเภทรถ *", ["-- เลือกประเภท --"] + available_types, key="f2_ty", disabled=f2_type_disabled)
                    
                    # 3. เลือกรหัส/ทะเบียนรถ (กรองตามชนิด)
                    f2_code_disabled = (f2_type == "-- เลือกประเภท --") or f2_type_disabled
                    if not f2_code_disabled:
                        filtered_by_type = [e for e in filtered_by_branch if e['type_name'] == f2_type]
                        available_codes = sorted(list(set([e['engine_code'] for e in filtered_by_type if e['engine_code']])))
                    else:
                        available_codes = []
                        filtered_by_type = []
                        
                    f2_code = c_sel3.selectbox("🏷️ 3. รหัสงาน / ทะเบียนรถ *", ["-- เลือกรถ --"] + available_codes, key="f2_cd", disabled=f2_code_disabled)

                    # 🎯 ล็อกช่องกรอกข้อมูลด้านล่าง หากยังเลือกรถไม่เสร็จ
                    inputs_disabled = (f2_code == "-- เลือกรถ --") or f2_code_disabled
                    
                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        f_date = st.date_input("วันที่", value=datetime.now(), key="f_date", disabled=inputs_disabled)
                        f_liters = st.number_input("ปริมาณน้ำมัน (ลิตร) *", min_value=0.0, step=1.0, value=None, placeholder="ระบุปริมาณน้ำมัน (ลิตร)", disabled=inputs_disabled)
                    with c2:
                        f_hours = st.number_input("จำนวนชั่วโมงทำงาน (ชม.) *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน (ชม.)", disabled=inputs_disabled)
                        f_remark = st.text_area("หมายเหตุ", disabled=inputs_disabled)
                        
                    submit_f = st.button("💾 บันทึกข้อมูลเชื้อเพลิงรถ", use_container_width=True, type="primary", disabled=inputs_disabled)
                    
                    if submit_f:
                        if inputs_disabled or f_liters is None or f_hours is None:
                            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                        else:
                            target_engine = next((e for e in filtered_by_type if e['engine_code'] == f2_code), None)
                            if target_engine:
                                try:
                                    conn = get_db_connection()
                                    with conn.cursor() as cur:
                                        sql = """INSERT INTO fuel_records (branch_id, record_date, engine_code, type_name, fuel_liters, working_hours, remark) 
                                                 VALUES (%s, %s, CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), %s, %s, CONVERT(%s USING utf8mb4))"""
                                        cur.execute(sql, (target_engine['branch_id'], f_date, target_engine['engine_code'], target_engine['type_name'], float(f_liters), float(f_hours), f_remark))
                                    conn.commit()
                                    conn.close()
                                    
                                    st.cache_data.clear()
                                    log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 2 Data Entry", f"บันทึกเชื้อเพลิงรถ {target_engine['engine_code']} จำนวน {f_liters} ลิตร")
                                    st.success(f"✅ บันทึกสำเร็จ! (ทะเบียน: {target_engine['engine_code']} | ประเภท: {target_engine['type_name']})")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e: st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

        # =========================================================================
        # 💨 TAB 3: บันทึกแรงดันไอน้ำ บอยเลอร์ 
        # =========================================================================
        elif key == "3":
            with current_tab_ctx:
                st.header("3. ระบบแรงดันไอน้ำปลายทางของบอยเลอร์")
                
                if current_role == 'admin': available_options = list(branch_dict.keys())
                else: available_options = [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]

                with st.container(border=True):
                    st.write("### 📝 บันทึกข้อมูลแรงดันไอน้ำ")
                    
                    if len(available_options) > 1:
                        t3_branch_label = st.selectbox("ระบุสาขาที่ต้องการบันทึก *", options=available_options, key="t3_branch")
                        target_branch_id = branch_dict[t3_branch_label]
                    else:
                        t3_branch_label = available_options[0] if available_options else current_branch_name
                        st.write(f"**(สังกัด: {t3_branch_label})**")
                        target_branch_id = branch_dict.get(t3_branch_label, int(st.session_state.branch_id))

                    col1, col2 = st.columns(2)
                    with col1:
                        p_date = st.date_input("วันที่", value=datetime.now(), key="p_date")
                        total_count = st.number_input("จำนวนครั้งทั้งหมด *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนครั้งทั้งหมด")
                    with col2:
                        pm_drop = st.number_input("จำนวนที่ตกตามเงื่อนไข PM *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนที่ตกตามเงื่อนไข PM")
                        non_pm_drop = st.number_input("จำนวนที่ตกนอกเหนือ PM *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนที่ตกนอกเหนือ PM")
                        p_remark = st.text_input("หมายเหตุ (ลากขี้เถ้า / ซ่อมบำรุง)")
                        
                    submit_p = st.button("💾 บันทึกข้อมูลแรงดันไอน้ำ", use_container_width=True, type="primary")
                    
                    if submit_p:
                        if total_count is None or pm_drop is None or non_pm_drop is None:
                            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                        else:
                            try:
                                conn = get_db_connection()
                                with conn.cursor() as cur:
                                    sql = """INSERT INTO boiler_pressure_records (branch_id, record_date, total_count, total_drop, pm_drop, non_pm_drop, remark, created_by) 
                                             VALUES (%s, %s, %s, %s, %s, %s, CONVERT(%s USING utf8mb4), %s)"""
                                    cur.execute(sql, (target_branch_id, p_date, int(total_count), (int(pm_drop) + int(non_pm_drop)), int(pm_drop), int(non_pm_drop), p_remark, int(st.session_state.user_id)))
                                conn.commit()
                                conn.close()
                                
                                st.cache_data.clear()
                                log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 3 Data Entry", f"บันทึกแรงดันไอน้ำตก วันที่ {p_date}")
                                st.success("✅ บันทึกข้อมูลแรงดันไอน้ำเรียบร้อยแล้ว!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e: st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

        # =========================================================================
        # 🔥 TAB 4: การใช้เชื้อเพลิง บอยเลอร์
        # =========================================================================
        elif key == "4":
            with current_tab_ctx:
                st.header("4. SYSTEM - การใช้เชื้อเพลิงบอยเลอร์")
                std_fuel_val = 280.00
                st.info(f"ค่ามาตรฐาน (STD เชื้อเพลิง) ปัจจุบันกำหนดไว้ที่: **{std_fuel_val:.2f}** กิโลกรัม/ตันไอน้ำ")
                
                if current_role == 'admin': available_options = list(branch_dict.keys())
                else: available_options = [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]

                with st.container(border=True):
                    st.write("### 📝 บันทึกปริมาณเชื้อเพลิงรายวัน")
                    
                    if len(available_options) > 1:
                        t4_branch_label = st.selectbox("ระบุสาขาที่ต้องการบันทึก *", options=available_options, key="t4_branch")
                        target_branch_id = branch_dict[t4_branch_label]
                    else:
                        t4_branch_label = available_options[0] if available_options else current_branch_name
                        st.write(f"**(สังกัด: {t4_branch_label})**")
                        target_branch_id = branch_dict.get(t4_branch_label, int(st.session_state.branch_id))

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write("**📦 ส่วนที่ 4.1: เชื้อเพลิงที่ใช้ (ตัน/วัน)**")
                        saw_w = st.number_input("น้ำหนักขี้เลื่อย (ตัน) *", min_value=0.0, step=0.1, value=None, placeholder="ระบุน้ำหนักขี้เลื่อย")
                        wood_w = st.number_input("น้ำหนักปีกไม้ (ตัน) *", min_value=0.0, step=0.1, value=None, placeholder="ระบุน้ำหนักปีกไม้")
                        waste_wood_w = st.number_input("น้ำหนักเศษไม้เสีย (ตัน) *", min_value=0.0, step=0.1, value=None, placeholder="ระบุน้ำหนักเศษไม้เสีย")
                    with c2:
                        st.write("**💰 ส่วนที่ 4.2: ราคาเชื้อเพลิง (ต่อตัน)**")
                        saw_p = st.number_input("ราคาขี้เลื่อย (บาท) *", min_value=0.0, step=50.0, value=None, placeholder="ระบุราคาขี้เลื่อย")
                        wood_p = st.number_input("ราคาปีกไม้ (บาท) *", min_value=0.0, step=50.0, value=None, placeholder="ระบุราคาปีกไม้")
                        waste_wood_p = st.number_input("ราคาเศษไม้เสีย (บาท) *", min_value=0.0, step=50.0, value=None, placeholder="ระบุราคาเศษไม้เสีย")
                    with c3:
                        st.write("**💨 ส่วนที่ 4.3: การผลิตไอน้ำ (ตัน/วัน)**")
                        bf_date = st.date_input("วันที่", value=datetime.now(), key="bf_date")
                        prod_val = st.number_input("ปริมาณการผลิต (ตัน/วัน) *", min_value=0.1, step=1.0, value=None, placeholder="ระบุการผลิตไอน้ำ")
                        work_hours = st.number_input("จำนวนชั่วโมงทำงาน (ชม.) *", min_value=0.1, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน")
                        
                    submit_bf = st.button("💾 บันทึกข้อมูลเชื้อเพลิงบอยเลอร์", use_container_width=True, type="primary")
                    
                    if submit_bf:
                        inputs = [saw_w, wood_w, waste_wood_w, saw_p, wood_p, waste_wood_p, prod_val, work_hours]
                        if any(x is None for x in inputs):
                            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                        else:
                            try:
                                conn = get_db_connection()
                                with conn.cursor() as cur:
                                    sql = """INSERT INTO boiler_fuel_records (branch_id, record_date, sawdust_weight, wood_weight, waste_wood_weight, sawdust_price, wood_price, waste_wood_price, steam_production, working_hours, created_by) 
                                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                                    cur.execute(sql, (target_branch_id, bf_date, float(saw_w), float(wood_w), float(waste_wood_w), float(saw_p), float(wood_p), float(waste_wood_p), float(prod_val), float(work_hours), int(st.session_state.user_id)))
                                conn.commit()
                                conn.close()
                                
                                st.cache_data.clear()
                                log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 4 Data Entry", f"บันทึกเชื้อเพลิงบอยเลอร์ วันที่ {bf_date}")
                                st.success("✅ บันทึกข้อมูลเชื้อเพลิงบอยเลอร์สำเร็จแล้ว!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e: st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")