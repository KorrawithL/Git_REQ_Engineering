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

                    machine_dict = {}
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            sql = "SELECT id, CONVERT(machine_name USING utf8mb4) AS machine_name FROM machines_set WHERE machine_type = 'machine' AND branch_id = %s AND is_active = 1"
                            cur.execute(sql, (target_branch_id,))
                            db_machines = cur.fetchall()
                            if db_machines: 
                                machine_dict = {m['machine_name']: m['id'] for m in db_machines}
                        conn.close()
                    except Exception: 
                        pass

                    machine_select_options = ["-- กรุณาเลือกเครื่องจักร --"] + list(machine_dict.keys())

                    # 🌟 1. สร้างตัวแปรนับรอบ (Dynamic Key)
                    if "reset_t1" not in st.session_state: st.session_state.reset_t1 = 0
                    rk1 = st.session_state.reset_t1

                    c1, c2 = st.columns(2)
                    with c1:
                        m_label = st.selectbox("ระบุเครื่องจักรที่ใช้งาน *", options=machine_select_options, index=0, key=f"t1_m_label_{rk1}")
                        is_m_not_selected = (m_label == "-- กรุณาเลือกเครื่องจักร --")
                        m_date = st.date_input("วันที่", value=datetime.now(), key="m_date", disabled=is_m_not_selected)
                        m_qty = st.number_input("จำนวนเครื่องจักร *", min_value=1, step=1, value=None, placeholder="ระบุจำนวน", disabled=is_m_not_selected, key=f"t1_qty_{rk1}")
                    with c2:
                        m_work_hours = st.number_input("ชั่วโมงทำงาน *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน", disabled=is_m_not_selected, key=f"t1_work_{rk1}")
                        m_break_hours = st.number_input("ชั่วโมงเบรกดาวน์ *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงเบรกดาวน์", disabled=is_m_not_selected, key=f"t1_break_{rk1}")
                        m_remark = st.text_area("หมายเหตุ / สาเหตุที่ชำรุด", disabled=is_m_not_selected, key=f"t1_rem_{rk1}")
                        
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
                                
                                # 🌟 2. สั่งบวกเลขเพื่อล้างฟอร์ม
                                st.session_state.reset_t1 += 1
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
                    
                    # 🌟 1. สร้างตัวแปรนับรอบ (Dynamic Key)
                    if "reset_t2" not in st.session_state: st.session_state.reset_t2 = 0
                    rk2 = st.session_state.reset_t2

                    c_sel1, c_sel2, c_sel3 = st.columns(3)
                    available_branch_names = sorted(list(set([eng['branch_name'] for eng in all_engines if eng['branch_name']])))
                    f2_branch = c_sel1.selectbox("🏢 1. สาขา *", ["-- เลือกสาขา --"] + available_branch_names, key="f2_br")
                    
                    f2_type_disabled = (f2_branch == "-- เลือกสาขา --")
                    if not f2_type_disabled:
                        filtered_by_branch = [e for e in all_engines if e['branch_name'] == f2_branch]
                        available_types = sorted(list(set([e['type_name'] for e in filtered_by_branch if e['type_name']])))
                    else:
                        available_types = []; filtered_by_branch = []
                        
                    f2_type = c_sel2.selectbox("🚜 2. ชนิด / ประเภทรถ *", ["-- เลือกประเภท --"] + available_types, key="f2_ty", disabled=f2_type_disabled)
                    
                    f2_code_disabled = (f2_type == "-- เลือกประเภท --") or f2_type_disabled
                    if not f2_code_disabled:
                        filtered_by_type = [e for e in filtered_by_branch if e['type_name'] == f2_type]
                        available_codes = sorted(list(set([e['engine_code'] for e in filtered_by_type if e['engine_code']])))
                    else:
                        available_codes = []; filtered_by_type = []
                        
                    f2_code = c_sel3.selectbox("🏷️ 3. รหัสงาน / ทะเบียนรถ *", ["-- เลือกรถ --"] + available_codes, key=f"f2_cd_{rk2}", disabled=f2_code_disabled)
                    inputs_disabled = (f2_code == "-- เลือกรถ --") or f2_code_disabled
                    
                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        f_date = st.date_input("วันที่", value=datetime.now(), key="f_date", disabled=inputs_disabled)
                        f_liters = st.number_input("ปริมาณน้ำมัน (ลิตร) *", min_value=0.0, step=1.0, value=None, placeholder="ระบุปริมาณน้ำมัน", disabled=inputs_disabled, key=f"t2_lit_{rk2}")
                    with c2:
                        f_hours = st.number_input("จำนวนชั่วโมงทำงาน (ชม.) *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน", disabled=inputs_disabled, key=f"t2_hrs_{rk2}")
                        f_remark = st.text_area("หมายเหตุ", disabled=inputs_disabled, key=f"t2_rem_{rk2}")
                        
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
                                    
                                    # 🌟 2. สั่งบวกเลขเพื่อล้างฟอร์ม
                                    st.session_state.reset_t2 += 1
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

                    # 🌟 1. สร้างตัวแปรนับรอบ (Dynamic Key)
                    if "reset_t3" not in st.session_state: st.session_state.reset_t3 = 0
                    rk3 = st.session_state.reset_t3

                    col1, col2 = st.columns(2)
                    with col1:
                        p_date = st.date_input("วันที่", value=datetime.now(), key="p_date")
                        total_count = st.number_input("จำนวนครั้งทั้งหมด *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนครั้งทั้งหมด", key=f"t3_tot_{rk3}")
                    with col2:
                        pm_drop = st.number_input("จำนวนที่ตกตามเงื่อนไข PM *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนที่ตกตามเงื่อนไข PM", key=f"t3_pm_{rk3}")
                        non_pm_drop = st.number_input("จำนวนที่ตกนอกเหนือ PM *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนที่ตกนอกเหนือ PM", key=f"t3_npm_{rk3}")
                        
                    p_remark = st.text_input("หมายเหตุ (ลากขี้เถ้า / ซ่อมบำรุง)", key=f"t3_rem_{rk3}")
                        
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
                                
                                # 🌟 2. สั่งบวกเลขเพื่อล้างฟอร์ม
                                st.session_state.reset_t3 += 1
                                time.sleep(1)
                                st.rerun()
                            except Exception as e: st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

        # =========================================================================
        # 🔥 TAB 4: การใช้เชื้อเพลิง บอยเลอร์
        # =========================================================================
        elif key == "4":
            with current_tab_ctx:
                st.subheader("4. SYSTEM - การใช้เชื้อเพลิงบอยเลอร์")
                
                # (หากต้องการเปิดแสดงกล่องสีฟ้าค่า STD ให้เอาเครื่องหมาย """ ออกครับ)
                """
                # 🎯 ดึงค่า STD จากฐานข้อมูลแบบ Real-time มาแสดงที่กล่องสีฟ้า
                std_fuel_val = 280.00 # ค่าสำรองฉุกเฉิน
                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        cur.execute("SELECT std_fuel_kg_per_steam_ton FROM std_settings WHERE id = 1")
                        std_res = cur.fetchone()
                        if std_res: std_fuel_val = float(std_res['std_fuel_kg_per_steam_ton'])
                    conn.close()
                except Exception: pass
                
                st.info(f"ค่ามาตรฐาน (STD เชื้อเพลิง) ปัจจุบันกำหนดไว้ที่: **{std_fuel_val:,.2f}** กิโลกรัม/ตันไอน้ำ")
                """

                if "reset_t4" not in st.session_state: st.session_state.reset_t4 = 0
                rk4 = st.session_state.reset_t4

                # 🎯 สร้าง 2 แท็บย่อยด้านใน Tab 4
                sub_tab1, sub_tab2 = st.tabs(["🏭 บันทึกปริมาณเชื้อเพลิงบอยเลอร์", "📁 บันทึกข้อมูลยอดรวมสาขา (เตา/ไม้อบ/แรงดัน)"])

                # ==========================================
                # แท็บย่อยที่ 1: บันทึกปริมาณเชื้อเพลิงบอยเลอร์
                # ==========================================
                with sub_tab1:
                    with st.container(border=True):
                        st.write("### 🏭 บันทึกปริมาณเชื้อเพลิงแยกตามบอยเลอร์")
                        
                        c_top1, c_top2 = st.columns([1.5, 1])
                        with c_top1:
                            if len(available_options) > 1:
                                t4_branch_lbl_2 = st.selectbox("ระบุสาขาที่ต้องการบันทึก *", options=available_options, key="t4_br2")
                                target_branch_id_2 = branch_dict[t4_branch_lbl_2]
                            else:
                                t4_branch_lbl_2 = available_options[0] if available_options else current_branch_name
                                st.write(f"**(สังกัด: {t4_branch_lbl_2})**")
                                target_branch_id_2 = branch_dict.get(t4_branch_lbl_2, int(st.session_state.branch_id))
                        with c_top2:
                            bf_date_2 = st.date_input("วันที่", value=datetime.now(), key="bf_dt2")

                        boiler_options = []
                        try:
                            conn = get_db_connection()
                            with conn.cursor() as cur:
                                cur.execute("SELECT CONVERT(boiler_name USING utf8mb4) AS b_name FROM boilers WHERE branch_id = %s AND is_active = 1 ORDER BY id ASC", (target_branch_id_2,))
                                for r in cur.fetchall():
                                    if r['b_name']: boiler_options.append(r['b_name'])
                            conn.close()
                        except Exception: pass
                        
                        if not boiler_options: boiler_options = ["-- ไม่มีข้อมูลบอยเลอร์ --"]
                        
                        boiler_name_input = st.selectbox("ระบุเครื่องบอยเลอร์ที่ใช้งาน *", boiler_options, key="t4_boiler")
                        is_boiler_invalid = (boiler_name_input == "-- ไม่มีข้อมูลบอยเลอร์ --")

                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.write("**📦 ส่วนที่ 4.1: เชื้อเพลิงที่ใช้ (ตัน/วัน)**")
                            saw_w = st.number_input("น้ำหนักขี้เลื่อย (ตัน) *", min_value=0.0, step=0.1, value=None, placeholder="ระบุน้ำหนักขี้เลื่อย", key=f"t4_sw_{rk4}")
                            wood_w = st.number_input("น้ำหนักปีกไม้ (ตัน) *", min_value=0.0, step=0.1, value=None, placeholder="ระบุน้ำหนักปีกไม้", key=f"t4_ww_{rk4}")
                            waste_wood_w = st.number_input("น้ำหนักเศษไม้เสีย (ตัน) *", min_value=0.0, step=0.1, value=None, placeholder="ระบุน้ำหนักเศษไม้เสีย", key=f"t4_www_{rk4}")
                        with c2:
                            st.write("**💰 ส่วนที่ 4.2: ราคาเชื้อเพลิง (ต่อตัน)**")
                            saw_p = st.number_input("ราคาขี้เลื่อย (บาท) *", min_value=0.0, step=50.0, value=None, placeholder="ระบุราคาขี้เลื่อย", key=f"t4_sp_{rk4}")
                            wood_p = st.number_input("ราคาปีกไม้ (บาท) *", min_value=0.0, step=50.0, value=None, placeholder="ระบุราคาปีกไม้", key=f"t4_wp_{rk4}")
                            waste_wood_p = st.number_input("ราคาเศษไม้เสีย (บาท) *", min_value=0.0, step=50.0, value=None, placeholder="ระบุราคาเศษไม้เสีย", key=f"t4_wwp_{rk4}")
                        with c3:
                            st.write("**💨 ส่วนที่ 4.3: การผลิตไอน้ำ (ตัน/วัน)**")
                            prod_val = st.number_input("ปริมาณการผลิต (ตัน/วัน) *", min_value=0.1, step=1.0, value=None, placeholder="ระบุการผลิตไอน้ำ", key=f"t4_prod_{rk4}")
                            work_hours = st.number_input("จำนวนชั่วโมงทำงาน (ชม.) *", min_value=0.1, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน", key=f"t4_wh_{rk4}")
                            
                        submit_bf = st.button("💾 บันทึกข้อมูลเชื้อเพลิงบอยเลอร์", use_container_width=True, type="primary", disabled=is_boiler_invalid)
                        
                        if submit_bf:
                            inputs_bf = [saw_w, wood_w, waste_wood_w, saw_p, wood_p, waste_wood_p, prod_val, work_hours]
                            if any(x is None for x in inputs_bf):
                                st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                            else:
                                try:
                                    conn = get_db_connection()
                                    with conn.cursor() as cur:
                                        sql_fuel = """INSERT INTO boiler_fuel_records (branch_id, record_date, boiler_name, sawdust_weight, wood_weight, waste_wood_weight, sawdust_price, wood_price, waste_wood_price, steam_production, working_hours, created_by) 
                                                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                                        cur.execute(sql_fuel, (target_branch_id_2, bf_date_2, boiler_name_input, float(saw_w), float(wood_w), float(waste_wood_w), float(saw_p), float(wood_p), float(waste_wood_p), float(prod_val), float(work_hours), int(st.session_state.user_id)))
                                    conn.commit()
                                    conn.close()
                                    
                                    st.cache_data.clear()
                                    log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 4 Boiler Entry", f"บันทึกเชื้อเพลิง {boiler_name_input} วันที่ {bf_date_2}")
                                    st.success(f"✅ บันทึกข้อมูลเชื้อเพลิงบอยเลอร์สำเร็จแล้ว!")
                                    st.session_state.reset_t4 += 1
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e: st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")



                # ==========================================
                # แท็บย่อยที่ 2: บันทึกข้อมูลยอดรวมของสาขา
                # ==========================================
                with sub_tab2:
                    with st.container(border=True):
                        st.write("### 📁 บันทึกข้อมูลยอดรวมของสาขาประจำวัน")
                        
                        c_top1, c_top2 = st.columns([1.5, 1])
                        with c_top1:
                            if len(available_options) > 1:
                                t4_branch_lbl_1 = st.selectbox("ระบุสาขาที่ต้องการบันทึก *", options=available_options, key="t4_br1")
                                target_branch_id_1 = branch_dict[t4_branch_lbl_1]
                            else:
                                t4_branch_lbl_1 = available_options[0] if available_options else current_branch_name
                                st.write(f"**(สังกัด: {t4_branch_lbl_1})**")
                                target_branch_id_1 = branch_dict.get(t4_branch_lbl_1, int(st.session_state.branch_id))
                        with c_top2:
                            bf_date_1 = st.date_input("วันที่", value=datetime.now(), key="bf_dt1")

                        c_ov1, c_ov2, c_ov3 = st.columns(3)
                        with c_ov1:
                            oven_qty = st.number_input("จำนวนเตาที่อบ (เตา) *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนเตา", key=f"t4_ov_{rk4}")
                        with c_ov2:
                            wood_out = st.number_input("ไม้อบออก (ลบ.ฟ.) *", min_value=0.0, step=1.0, value=None, placeholder="ระบุปริมาณ", key=f"t4_wo_{rk4}")
                        with c_ov3:
                            avg_pressure = st.number_input("แรงดันปลายทางเฉลี่ย *", min_value=0.0, step=0.1, value=None, placeholder="ระบุแรงดัน", key=f"t4_avgp_{rk4}")

                        submit_oven = st.button("💾 บันทึกข้อมูลยอดรวมสาขา", use_container_width=True, type="primary")
                        
                        if submit_oven:
                            inputs_ov = [oven_qty, wood_out, avg_pressure]
                            if any(x is None for x in inputs_ov):
                                st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                            else:
                                try:
                                    conn = get_db_connection()
                                    with conn.cursor() as cur:
                                        sql_oven = """INSERT INTO daily_wood_oven_records (branch_id, record_date, oven_qty, wood_out_cubft, avg_terminal_pressure, created_by)
                                                      VALUES (%s, %s, %s, %s, %s, %s)
                                                      ON DUPLICATE KEY UPDATE oven_qty=VALUES(oven_qty), wood_out_cubft=VALUES(wood_out_cubft), avg_terminal_pressure=VALUES(avg_terminal_pressure)"""
                                        cur.execute(sql_oven, (target_branch_id_1, bf_date_1, int(oven_qty), float(wood_out), float(avg_pressure), int(st.session_state.user_id)))
                                    conn.commit()
                                    conn.close()
                                    
                                    st.cache_data.clear()
                                    log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 4 Oven Entry", f"บันทึกยอดรวมสาขา วันที่ {bf_date_1}")
                                    st.success(f"✅ บันทึกข้อมูลยอดรวมสาขาสำเร็จแล้ว!")
                                    st.session_state.reset_t4 += 1
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e: st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

                