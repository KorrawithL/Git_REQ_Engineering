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

    all_tabs_config = {
        "1": "⚙️ 1. ระบบเครื่องจักร / เบรกดาวน์",
        "2": "🚚 2. ระบบเชื้อเพลิง (รถยก/เครื่องยนต์)",
        "3": "💨 3. แรงดันไอน้ำปลายทาง บอยเลอร์",
        "4": "🔥 4. การใช้เชื้อเพลิง บอยเลอร์"
    }

    if current_role in ["admin", "manager"]:
        visible_tab_keys = ["1", "2", "3", "4"]
    else:
        visible_tab_keys = [k for k in allowed_tabs_list if k in all_tabs_config]

    if not visible_tab_keys:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.error("## ⏳ รอการอนุมัติสิทธิ์เลือกแท็บงานจากแอดมิน")
        st.info("🔒 บัญชีของคุณได้รับการลงทะเบียนเข้าสู่ระบบเรียบร้อยแล้ว กรุณาติดต่อผู้ดูแลระบบเพื่อระบุแท็บงานก่อนเข้าใช้งานครับ")
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
                
                # 📝 ดึงข้อมูลเครื่องจักรจากฐานข้อมูล (หรือจาก Dict เดิม)
                machine_dict = {
                    "โต๊ะเลื่อย (≤ 0.15%)": 7, "พัดลมดูดขี้เลื่อย (≤ 0.15%)": 8, "ตาชั่งใหญ่ (≤ 0.20%)": 9,
                    "ตาชั่งเล็ก (≤ 0.20%)": 10, "รถยก (≤ 0.20%)": 11, "รถคีบ (≤16 ชม.)": 12,
                    "อัดน้ำยา (≤ 0.20%)": 13, "เตาอบปกติ (≤ 0.20%)": 14, "เตาอบ CDK(≤ 0.20%)": 15,
                    "บอยเลอร์ (≤ 0.15%)": 16, "ชิปเปอร์ (≤ 0.15%)": 17,
                }
                
                # พยายามดึงข้อมูลเครื่องจักรจากฐานข้อมูลตาราง machines แบบ Dynamic
                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if current_role in ["admin", "manager"]:
                            cur.execute("SELECT id, CONVERT(machine_name USING utf8mb4) AS machine_name FROM machines")
                        else:
                            cur.execute("SELECT id, CONVERT(machine_name USING utf8mb4) AS machine_name FROM machines WHERE branch_id = %s", (int(st.session_state.branch_id),))
                        
                        db_machines = cur.fetchall()
                        if db_machines:
                            machine_dict = {m['machine_name']: m['id'] for m in db_machines}
                    conn.close()
                except Exception as e:
                    pass # ถ้าตารางยังไม่มี ให้ใช้ default machine_dict ไปก่อน

                machine_select_options = ["-- กรุณาเลือกเครื่องจักร --"] + list(machine_dict.keys())
                
                # --- ฟอร์มบันทึกข้อมูลเครื่องจักรลงตาราง machine_trans ---
                with st.form("machine_form", clear_on_submit=True):
                    st.write(f"### 📝 ฟอร์มบันทึกข้อมูลเครื่องจักรลงตาราง (สังกัด: {current_branch_name})")
                    c1, c2 = st.columns(2)
                    with c1:
                        m_date = st.date_input("วันที่", value=datetime.now(), key="m_date")
                        m_label = st.selectbox("ระบุเครื่องจักรที่ใช้งาน *", options=machine_select_options, index=0)
                        m_qty = st.number_input("จำนวนเครื่องจักร *", min_value=1, step=1, value=None, placeholder="ระบุจำนวน")
                    with c2:
                        m_work_hours = st.number_input("ชั่วโมงทำงาน *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน")
                        m_break_hours = st.number_input("ชั่วโมงเบรกดาวน์ *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงเบรกดาวน์")
                        m_remark = st.text_area("หมายเหตุ / สาเหตุที่ชำรุด")
                        
                    submit_m = st.form_submit_button("💾 บันทึกข้อมูลเครื่องจักร", use_container_width=True)
                    
                    if submit_m:
                        if m_label == "-- กรุณาเลือกเครื่องจักร --" or m_qty is None or m_work_hours is None or m_break_hours is None:
                            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                        else:
                            try:
                                m_select_id = machine_dict[m_label]
                                connection = get_db_connection()
                                with connection.cursor() as cursor:
                                    sql = """INSERT INTO machine_trans (branch_id, record_date, machine_id, machine_qty, working_hours, breakdown_hours, remarks, created_by, created_at, updated_at, status) 
                                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 'active')"""
                                    cursor.execute(sql, (int(st.session_state.branch_id), m_date, int(m_select_id), int(m_qty), float(m_work_hours), float(m_break_hours), m_remark, int(st.session_state.user_id)))
                                connection.commit()
                                connection.close()
                                log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 1 Data Entry", f"บันทึกเครื่องจักร {m_label} วันที่ {m_date}")
                                st.success("✅ บันทึกข้อมูลเครื่องจักรสำเร็จเรียบร้อยแล้ว!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

                # =========================================================
                # ➕ Expander สำหรับเพิ่มเครื่องจักรใหม่เข้าสู่ตาราง "machines"
                # =========================================================
                with st.expander("➕ เพิ่มเครื่องจักรใหม่เข้าสู่ระบบ"):
                    with st.form("add_new_machine_form", clear_on_submit=True):
                        st.write("ฟอร์มลงทะเบียนชื่อเครื่องจักรใหม่เข้าสู่ฐานข้อมูลระบบ")
                        
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            new_machine_name = st.text_input("ชื่อเครื่องจักรใหม่ *", placeholder="เช่น มอเตอร์สายพานลำเลียง")
                        with col_m2:
                            new_machine_branch = st.selectbox("สาขาที่ติดตั้ง *", options=list(branch_dict.keys()), key="branch_sel_t1")
                            
                        submit_new_machine = st.form_submit_button("💾 บันทึกเครื่องจักรใหม่เข้าฐานข้อมูล", use_container_width=True)
                        
                        if submit_new_machine:
                            if not new_machine_name:
                                st.error("⚠️ กรุณาระบุชื่อเครื่องจักรให้ชัดเจน")
                            else:
                                try:
                                    branch_id_for_machine = branch_dict[new_machine_branch]
                                    conn = get_db_connection()
                                    with conn.cursor() as cur:
                                        # เพิ่มข้อมูลลงในตาราง machines
                                        sql_add = "INSERT INTO machines (machine_name, branch_id) VALUES (%s, %s)"
                                        cur.execute(sql_add, (new_machine_name, branch_id_for_machine))
                                        conn.commit()
                                    conn.close()
                                    log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Machine Setup", f"เพิ่มเครื่องจักรใหม่: {new_machine_name}")
                                    st.success(f"✅ เพิ่มเครื่องจักร '{new_machine_name}' สำหรับสาขา '{new_machine_branch}' เข้าสู่ระบบสำเร็จ!")
                                    time.sleep(1.2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"เกิดข้อผิดพลาดในการบันทึกเครื่องจักรใหม่: {e}")


        # =========================================================================
        # 🚚 TAB 2: บันทึกการใช้เชื้อเพลิงรถยนต์ / รถยก
        # =========================================================================
        elif key == "2":
            with current_tab_ctx:
                st.header("2. ระบบการใช้เชื้อเพลิง (เครื่องยนต์/รถยก)")
                
                engine_options = {}
                engine_type_mapping = {}
                engine_code_mapping = {}
                
                try:
                    connection = get_db_connection()
                    with connection.cursor() as cursor:
                        if current_role in ["admin", "manager"]:
                            sql_get_engines = """SELECT e.id AS engine_pk_id, CONVERT(e.engine_code USING utf8mb4) AS engine_code, CONVERT(et.type_name USING utf8mb4) AS type_name, CONVERT(b.branch_name USING utf8mb4) AS branch_name
                                                FROM engines e LEFT JOIN engine_types et ON e.engine_type_id = et.id LEFT JOIN branches b ON e.branch_id = b.id WHERE e.is_active = 1 ORDER BY b.id ASC, e.engine_code ASC"""
                            cursor.execute(sql_get_engines)
                        else:
                            sql_get_engines = """SELECT e.id AS engine_pk_id, CONVERT(e.engine_code USING utf8mb4) AS engine_code, CONVERT(et.type_name USING utf8mb4) AS type_name, CONVERT(b.branch_name USING utf8mb4) AS branch_name
                                                FROM engines e LEFT JOIN engine_types et ON e.engine_type_id = et.id LEFT JOIN branches b ON e.branch_id = b.id WHERE e.branch_id = %s AND e.is_active = 1 ORDER BY e.engine_code ASC"""
                            cursor.execute(sql_get_engines, (int(st.session_state.branch_id),))
                            
                        db_engines = cursor.fetchall()
                        for eng in db_engines:
                            pk_id = eng['engine_pk_id']
                            code = eng['engine_code'] or ''
                            t_name = eng['type_name'] or 'ไม่ระบุประเภท'
                            b_name = eng['branch_name'] or ''
                            try: branch_code = b_name.split("สาขา ")[1].split()[0]
                            except: branch_code = b_name or "N/A"
                            
                            display_label = f"{code} (ประเภท: {t_name}) [{branch_code}]"
                            engine_options[display_label] = pk_id
                            engine_type_mapping[pk_id] = t_name
                            engine_code_mapping[pk_id] = code
                    connection.close()
                except Exception as e:
                    st.error(f"ไม่สามารถดึงข้อมูลตาราง engines ได้: {e}")

                engine_select_options = ["-- กรุณาเลือก รหัสงาน/ทะเบียนรถ --"] + list(engine_options.keys())

                # --- ฟอร์มบันทึกข้อมูลเชื้อเพลิงลงตาราง fuel_records ---
                with st.form("fuel_form", clear_on_submit=True):
                    st.write(f"### 📝 ฟอร์มบันทึกข้อมูลการใช้เชื้อเพลิงรถ (สังกัด: {current_branch_name})")
                    c1, c2 = st.columns(2)
                    with c1:
                        f_date = st.date_input("วันที่", value=datetime.now(), key="f_date")
                        selected_label = st.selectbox("เลือก รหัสงาน / ทะเบียนรถ *", options=engine_select_options, index=0)
                        f_liters = st.number_input("ปริมาณน้ำมัน (ลิตร) *", min_value=0.0, step=1.0, value=None, placeholder="ระบุปริมาณน้ำมัน (ลิตร)")
                    with c2:
                        f_hours = st.number_input("จำนวนชั่วโมงทำงาน (ชม.) *", min_value=0.0, step=0.5, value=None, placeholder="ระบุชั่วโมงทำงาน (ชม.)")
                        f_remark = st.text_area("หมายเหตุ")
                        
                    submit_f = st.form_submit_button("💾 บันทึกข้อมูลเชื้อเพลิงรถ", use_container_width=True)
                    
                    if submit_f:
                        if selected_label == "-- กรุณาเลือก รหัสงาน/ทะเบียนรถ --" or f_liters is None or f_hours is None:
                            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                        else:
                            try:
                                selected_pk_id = engine_options[selected_label]
                                actual_engine_code = engine_code_mapping[selected_pk_id]
                                actual_type_name = engine_type_mapping[selected_pk_id]
                                conn = get_db_connection()
                                with conn.cursor() as cursor:
                                    sql_insert = """INSERT INTO fuel_records (branch_id, record_date, engine_code, type_name, fuel_liters, working_hours, remark) 
                                                    VALUES (%s, %s, CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), %s, %s, CONVERT(%s USING utf8mb4))"""
                                    cursor.execute(sql_insert, (int(st.session_state.branch_id), f_date, actual_engine_code, actual_type_name, float(f_liters), float(f_hours), f_remark))
                                conn.commit()
                                conn.close()
                                log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 2 Data Entry", f"บันทึกเชื้อเพลิงรถ {actual_engine_code} จำนวน {f_liters} ลิตร")
                                st.success(f"✅ บันทึกสำเร็จ! (ทะเบียน: {actual_engine_code} | ประเภท: {actual_type_name})")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

                # =========================================================
                # ➕ Expander สำหรับเพิ่มรหัสงาน / ทะเบียนรถใหม่ (Tab 2)
                # =========================================================
                engine_type_dict = {}
                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        cur.execute("SELECT id, CONVERT(type_name USING utf8mb4) AS type_name FROM engine_types ORDER BY id ASC")
                        for r in cur.fetchall():
                            engine_type_dict[r['type_name']] = r['id']
                    conn.close()
                except Exception as e:
                    st.warning("⚠️ ไม่สามารถดึงข้อมูลประเภทรถจากระบบได้ กรุณาตรวจสอบฐานข้อมูลตาราง engine_types")

                type_options = list(engine_type_dict.keys()) if engine_type_dict else ["-- ไม่มีข้อมูลประเภทรถ --"]

                with st.expander("➕ เพิ่มรหัสงาน / ทะเบียนรถใหม่เข้าสู่ระบบ"):
                    with st.form("add_new_engine_form", clear_on_submit=True):
                        st.write("ฟอร์มลงทะเบียนรหัสงาน/ทะเบียนรถใหม่เข้าสู่ฐานข้อมูลระบบ")
                        
                        col_e1, col_e2, col_e3 = st.columns(3)
                        with col_e1:
                            new_engine_code = st.text_input("รหัสงาน / ทะเบียนรถใหม่ *", placeholder="เช่น TCK-01")
                        with col_e2:
                            new_engine_type = st.selectbox("ชนิดของรถ *", options=type_options)
                        with col_e3:
                            new_engine_branch = st.selectbox("สาขาประจำการ *", options=list(branch_dict.keys()), key="branch_sel_t2")
                            
                        submit_new_engine = st.form_submit_button("💾 บันทึกทะเบียนรถใหม่", use_container_width=True)
                        
                        if submit_new_engine:
                            if not new_engine_code or new_engine_type == "-- ไม่มีข้อมูลประเภทรถ --":
                                st.error("⚠️ กรุณากรอกรหัสงาน/ทะเบียนรถ และเลือกชนิดของรถให้ครบถ้วน")
                            else:
                                try:
                                    b_id = branch_dict[new_engine_branch]
                                    t_id = engine_type_dict[new_engine_type]
                                    
                                    conn = get_db_connection()
                                    with conn.cursor() as cur:
                                        # เพิ่มข้อมูลเข้าตาราง engines
                                        sql_add_eng = "INSERT INTO engines (engine_code, engine_type_id, branch_id, is_active) VALUES (%s, %s, %s, 1)"
                                        cur.execute(sql_add_eng, (new_engine_code, t_id, b_id))
                                        conn.commit()
                                    conn.close()
                                    
                                    log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Fuel System Setup", f"เพิ่มรถใหม่: {new_engine_code}")
                                    st.success(f"✅ เพิ่มรถ '{new_engine_code}' สาขา '{new_engine_branch}' เข้าสู่ระบบสำเร็จ!")
                                    time.sleep(1.2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"เกิดข้อผิดพลาดในการบันทึกทะเบียนรถใหม่: {e}")

        # =========================================================================
        # 💨 TAB 3: บันทึกแรงดันไอน้ำ บอยเลอร์ 
        # =========================================================================
        elif key == "3":
            with current_tab_ctx:
                st.header("3. ระบบแรงดันไอน้ำปลายทางของบอยเลอร์")
                with st.form("pressure_form", clear_on_submit=True):
                    st.write(f"### 📝 บันทึกข้อมูลแรงดันไอน้ำ (สังกัด: {current_branch_name})")
                    col1, col2 = st.columns(2)
                    with col1:
                        p_date = st.date_input("วันที่", value=datetime.now(), key="p_date")
                        total_count = st.number_input("จำนวนครั้งทั้งหมด *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนครั้งทั้งหมด")
                    with col2:
                        pm_drop = st.number_input("จำนวนที่ตกตามเงื่อนไข PM *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนที่ตกตามเงื่อนไข PM")
                        non_pm_drop = st.number_input("จำนวนที่ตกนอกเหนือ PM *", min_value=0, step=1, value=None, placeholder="ระบุจำนวนที่ตกนอกเหนือ PM")
                        p_remark = st.text_input("หมายเหตุ (ลากขี้เถ้า / ซ่อมบำรุง)")
                        
                    submit_p = st.form_submit_button("💾 บันทึกข้อมูลแรงดันไอน้ำ", use_container_width=True)
                    
                    if submit_p:
                        if total_count is None or pm_drop is None or non_pm_drop is None:
                            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                        else:
                            try:
                                conn = get_db_connection()
                                with conn.cursor() as cursor:
                                    sql = """INSERT INTO boiler_pressure_records (branch_id, record_date, total_count, total_drop, pm_drop, non_pm_drop, remark, created_by) 
                                             VALUES (%s, %s, %s, %s, %s, %s, CONVERT(%s USING utf8mb4), %s)"""
                                    cursor.execute(sql, (int(st.session_state.branch_id), p_date, int(total_count), (int(pm_drop) + int(non_pm_drop)), int(pm_drop), int(non_pm_drop), p_remark, int(st.session_state.user_id)))
                                conn.commit()
                                conn.close()
                                log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 3 Data Entry", f"บันทึกแรงดันไอน้ำตก วันที่ {p_date}")
                                st.success("✅ บันทึกข้อมูลแรงดันไอน้ำเรียบร้อยแล้ว!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

        # =========================================================================
        # 🔥 TAB 4: การใช้เชื้อเพลิง บอยเลอร์
        # =========================================================================
        elif key == "4":
            with current_tab_ctx:
                st.header("4. SYSTEM - การใช้เชื้อเพลิงบอยเลอร์")
                std_fuel_val = 280.00
                st.info(f"ค่ามาตรฐาน (STD เชื้อเพลิง) ปัจจุบันกำหนดไว้ที่: **{std_fuel_val:.2f}** กิโลกรัม/ตันไอน้ำ")
                
                with st.form("boiler_fuel_form", clear_on_submit=True):
                    st.write(f"### 📝 บันทึกปริมาณเชื้อเพลิงรายวัน (สังกัด: {current_branch_name})")
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
                        
                    submit_bf = st.form_submit_button("💾 บันทึกข้อมูลเชื้อเพลิงบอยเลอร์", use_container_width=True)
                    
                    if submit_bf:
                        inputs = [saw_w, wood_w, waste_wood_w, saw_p, wood_p, waste_wood_p, prod_val, work_hours]
                        if any(x is None for x in inputs):
                            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                        else:
                            try:
                                conn = get_db_connection()
                                with conn.cursor() as cursor:
                                    sql = """INSERT INTO boiler_fuel_records (branch_id, record_date, sawdust_weight, wood_weight, waste_wood_weight, sawdust_price, wood_price, waste_wood_price, steam_production, working_hours, created_by) 
                                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                                    cursor.execute(sql, (int(st.session_state.branch_id), bf_date, float(saw_w), float(wood_w), float(waste_wood_w), float(saw_p), float(wood_p), float(waste_wood_p), float(prod_val), float(work_hours), int(st.session_state.user_id)))
                                conn.commit()
                                conn.close()
                                log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Tab 4 Data Entry", f"บันทึกเชื้อเพลิงบอยเลอร์ วันที่ {bf_date}")
                                st.success("✅ บันทึกข้อมูลเชื้อเพลิงบอยเลอร์สำเร็จแล้ว!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")