import streamlit as st
import pandas as pd
import time
from datetime import datetime
from database import get_db_connection, log_activity
from config import branch_dict

def render_add_new_equipment():
    st.header("🛠️ ลงทะเบียนอุปกรณ์ใหม่เข้าสู่ระบบ")
    st.caption("หน้าจอสำหรับแอดมิน เพื่อเพิ่ม แก้ไข และลบ รายชื่อเครื่องจักร รวมถึงรหัสงาน/ทะเบียนรถ เข้าสู่ฐานข้อมูล")
    st.write("---")
    
    # แบ่งเป็น 2 แท็บย่อยเพื่อความสะอาดตา
    tab_m1, tab_m2 = st.tabs(["⚙️ 1. จัดการเครื่องจักร (สำหรับ Tab 1)", "🚚 2. จัดการรหัสงาน/ทะเบียนรถ (สำหรับ Tab 2)"])
    
    # ==========================================
    # ⚙️ ส่วนที่ 1: จัดการเครื่องจักร
    # ==========================================
    with tab_m1:
        st.subheader("➕ เพิ่มเครื่องจักรใหม่เข้าสู่ระบบ")
        with st.form("add_new_machine_form", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                new_machine_name = st.text_input("ชื่อเครื่องจักรใหม่ *", placeholder="เช่น มอเตอร์สายพานลำเลียง")
                new_m_reg_date = st.date_input("วันที่ลงทะเบียนอุปกรณ์ *", value=datetime.today())
            with col_m2:
                new_machine_branch = st.selectbox("สาขาที่ติดตั้ง *", options=list(branch_dict.keys()), key="add_m_branch")
                new_m_exp_date = st.date_input("วันหมดอายุการใช้งาน", value=None)
                
            new_m_remark = st.text_area("หมายเหตุ", placeholder="ระบุหมายเหตุเพิ่มเติม (ถ้ามี)")
                
            submit_new_machine = st.form_submit_button("➕ บันทึกเครื่องจักรใหม่", use_container_width=True)
            
            if submit_new_machine:
                if not new_machine_name:
                    st.error("⚠️ กรุณาระบุชื่อเครื่องจักรให้ชัดเจน")
                else:
                    try:
                        branch_id_for_machine = branch_dict[new_machine_branch]
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            # 🎯 ใช้ created_at เป็นวันที่ลงทะเบียนอุปกรณ์
                            sql_add = "INSERT INTO machines (machine_name, branch_id, created_at, expiration_date, remark) VALUES (%s, %s, %s, %s, %s)"
                            cur.execute(sql_add, (new_machine_name, branch_id_for_machine, new_m_reg_date, new_m_exp_date, new_m_remark))
                            conn.commit()
                        conn.close()
                        log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Machine Setup", f"เพิ่มเครื่องจักรใหม่: {new_machine_name}")
                        st.success(f"✅ เพิ่มเครื่องจักร '{new_machine_name}' สำเร็จ!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการบันทึกเครื่องจักรใหม่: {e}")

        st.write("---")
        st.subheader("📋 รายการเครื่องจักรในระบบ")
        
        # ดึงข้อมูลเครื่องจักรมาแสดงผล
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT m.id, CONVERT(m.machine_name USING utf8mb4) AS machine_name, 
                           m.branch_id, CONVERT(b.branch_name USING utf8mb4) AS branch_name,
                           m.created_at, m.expiration_date, CONVERT(m.remark USING utf8mb4) AS remark
                    FROM machines m 
                    LEFT JOIN branches b ON m.branch_id = b.id 
                    ORDER BY m.id DESC
                """)
                machines_data = cur.fetchall()
            conn.close()
        except Exception as e:
            st.error(f"ไม่สามารถดึงข้อมูลเครื่องจักรได้: {e}")
            machines_data = []

        if machines_data:
            # 1. แสดงเป็นตาราง
            df_m = pd.DataFrame(machines_data)
            df_m.rename(columns={
                'id': 'ID', 'machine_name': 'ชื่อเครื่องจักร', 'branch_name': 'สาขา',
                'created_at': 'วันที่ลงทะเบียน', 'expiration_date': 'วันหมดอายุ', 'remark': 'หมายเหตุ'
            }, inplace=True)
            st.dataframe(df_m[['ID', 'ชื่อเครื่องจักร', 'สาขา', 'วันที่ลงทะเบียน', 'วันหมดอายุ', 'หมายเหตุ']], use_container_width=True, height=250)

            # 2. ฟอร์มสำหรับแก้ไขและลบ
            with st.expander("✏️ / 🗑️ แก้ไข หรือ ลบ ข้อมูลเครื่องจักร", expanded=False):
                machine_options = {f"ID: {m['id']} - {m['machine_name']} ({m['branch_name']})": m for m in machines_data}
                selected_m_label = st.selectbox("เลือกเครื่องจักรที่ต้องการจัดการ:", options=list(machine_options.keys()))
                selected_m_data = machine_options[selected_m_label]

                with st.form("edit_machine_form"):
                    e_col1, e_col2 = st.columns(2)
                    with e_col1:
                        edit_m_name = st.text_input("แก้ไข ชื่อเครื่องจักร", value=selected_m_data['machine_name'])
                        m_reg_val = pd.to_datetime(selected_m_data['created_at']) if selected_m_data.get('created_at') else datetime.today()
                        edit_m_reg_date = st.date_input("แก้ไข วันที่ลงทะเบียน", value=m_reg_val)
                    with e_col2:
                        branch_names = list(branch_dict.keys())
                        b_idx = 0
                        for i, b_name in enumerate(branch_names):
                            if branch_dict[b_name] == selected_m_data['branch_id']:
                                b_idx = i
                                break
                        edit_m_branch = st.selectbox("แก้ไข สาขา", options=branch_names, index=b_idx)
                        m_exp_val = pd.to_datetime(selected_m_data['expiration_date']) if selected_m_data.get('expiration_date') else None
                        edit_m_exp_date = st.date_input("แก้ไข วันหมดอายุการใช้งาน", value=m_exp_val)
                        
                    edit_m_remark = st.text_area("แก้ไข หมายเหตุ", value=selected_m_data.get('remark') or "")

                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                    confirm_del_m = st.checkbox("⚠️ ยืนยันการลบข้อมูล (ติ๊กถูกก่อนกดปุ่มลบ)", key="chk_del_m")

                    act_c1, act_c2 = st.columns(2)
                    with act_c1:
                        if st.form_submit_button("💾 อัปเดตข้อมูล (Update)", use_container_width=True):
                            try:
                                conn = get_db_connection()
                                with conn.cursor() as cur:
                                    cur.execute("UPDATE machines SET machine_name=%s, branch_id=%s, created_at=%s, expiration_date=%s, remark=%s WHERE id=%s", 
                                                (edit_m_name, branch_dict[edit_m_branch], edit_m_reg_date, edit_m_exp_date, edit_m_remark, selected_m_data['id']))
                                    conn.commit()
                                conn.close()
                                log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "Machine Setup", f"แก้ไขเครื่องจักร ID: {selected_m_data['id']}")
                                st.success("✅ อัปเดตข้อมูลสำเร็จ!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาดในการอัปเดต: {e}")
                    
                    with act_c2:
                        if st.form_submit_button("🗑️ ลบข้อมูล (Delete)", use_container_width=True):
                            if confirm_del_m:
                                try:
                                    conn = get_db_connection()
                                    with conn.cursor() as cur:
                                        cur.execute("DELETE FROM machines WHERE id=%s", (selected_m_data['id'],))
                                        conn.commit()
                                    conn.close()
                                    log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "Machine Setup", f"ลบเครื่องจักร ID: {selected_m_data['id']}")
                                    st.success("🗑️ ลบข้อมูลเรียบร้อยแล้ว!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"ไม่สามารถลบได้ (อาจมีข้อมูลอ้างอิงอยู่): {e}")
                            else:
                                st.error("⚠️ กรุณาติ๊กถูกยืนยันการลบก่อนกดปุ่ม")
        else:
            st.info("ยังไม่มีข้อมูลเครื่องจักรในระบบ")


    # ==========================================================
    # 🚚 ส่วนที่ 2: จัดการรหัสงาน/ทะเบียนรถ
    # ==========================================================
    with tab_m2:
        st.subheader("➕ เพิ่มรหัสงาน / ทะเบียนรถใหม่เข้าสู่ระบบ")
        
        # ดึงชนิดของรถมาทำ Dropdown
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

        with st.form("add_new_engine_form", clear_on_submit=True):
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                new_engine_code = st.text_input("รหัสงาน / ทะเบียนรถใหม่ *", placeholder="เช่น TCK-01")
                new_e_reg_date = st.date_input("วันที่ลงทะเบียนอุปกรณ์ *", value=datetime.today(), key="add_e_reg")
            with col_e2:
                new_engine_type = st.selectbox("ชนิดของรถ *", options=type_options)
                new_e_exp_date = st.date_input("วันหมดอายุการใช้งาน", value=None, key="add_e_exp")
            with col_e3:
                new_engine_branch = st.selectbox("สาขาประจำการ *", options=list(branch_dict.keys()), key="add_e_branch")
                
            new_e_remark = st.text_area("หมายเหตุ", placeholder="ระบุหมายเหตุเพิ่มเติม (ถ้ามี)", key="add_e_rem")
                
            submit_new_engine = st.form_submit_button("➕ บันทึกทะเบียนรถใหม่", use_container_width=True)
            
            if submit_new_engine:
                if not new_engine_code or new_engine_type == "-- ไม่มีข้อมูลประเภทรถ --":
                    st.error("⚠️ กรุณากรอกรหัสงาน/ทะเบียนรถ และเลือกชนิดของรถให้ครบถ้วน")
                else:
                    try:
                        b_id = branch_dict[new_engine_branch]
                        t_id = engine_type_dict[new_engine_type]
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            # 🎯 ใช้ created_at เป็นวันที่ลงทะเบียนอุปกรณ์
                            sql_add_eng = "INSERT INTO engines (engine_code, engine_type_id, branch_id, is_active, created_at, expiration_date, remark) VALUES (%s, %s, %s, 1, %s, %s, %s)"
                            cur.execute(sql_add_eng, (new_engine_code, t_id, b_id, new_e_reg_date, new_e_exp_date, new_e_remark))
                            conn.commit()
                        conn.close()
                        log_activity(st.session_state.user_id, st.session_state.username, "INSERT", "Fuel System Setup", f"เพิ่มรถใหม่: {new_engine_code}")
                        st.success(f"✅ เพิ่มรถ '{new_engine_code}' เข้าสู่ระบบสำเร็จ!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการบันทึกทะเบียนรถใหม่: {e}")

        st.write("---")
        st.subheader("📋 รายการรหัสงาน / ทะเบียนรถ ในระบบ")
        
        # ดึงข้อมูล Engine
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT e.id, CONVERT(e.engine_code USING utf8mb4) AS engine_code, 
                           e.engine_type_id, CONVERT(et.type_name USING utf8mb4) AS type_name, 
                           e.branch_id, CONVERT(b.branch_name USING utf8mb4) AS branch_name,
                           e.created_at, e.expiration_date, CONVERT(e.remark USING utf8mb4) AS remark
                    FROM engines e 
                    LEFT JOIN engine_types et ON e.engine_type_id = et.id 
                    LEFT JOIN branches b ON e.branch_id = b.id 
                    ORDER BY e.id DESC
                """)
                engines_data = cur.fetchall()
            conn.close()
        except Exception as e:
            st.error(f"ไม่สามารถดึงข้อมูลรถได้: {e}")
            engines_data = []

        if engines_data:
            # 1. แสดงผล DataFrame
            df_e = pd.DataFrame(engines_data)
            df_e.rename(columns={
                'id': 'ID', 'engine_code': 'รหัส/ทะเบียน', 'type_name': 'ชนิดของรถ', 'branch_name': 'สาขา',
                'created_at': 'วันที่ลงทะเบียน', 'expiration_date': 'วันหมดอายุ', 'remark': 'หมายเหตุ'
            }, inplace=True)
            st.dataframe(df_e[['ID', 'รหัส/ทะเบียน', 'ชนิดของรถ', 'สาขา', 'วันที่ลงทะเบียน', 'วันหมดอายุ', 'หมายเหตุ']], use_container_width=True, height=250)

            # 2. ฟอร์มแก้ไข / ลบ
            with st.expander("✏️ / 🗑️ แก้ไข หรือ ลบ ข้อมูลรถ/เครื่องยนต์", expanded=False):
                eng_options = {f"ID: {e['id']} - {e['engine_code']} ({e['type_name']}) [{e['branch_name']}]": e for e in engines_data}
                selected_e_label = st.selectbox("เลือกรถที่ต้องการจัดการ:", options=list(eng_options.keys()))
                selected_e_data = eng_options[selected_e_label]

                with st.form("edit_engine_form"):
                    ee_col1, ee_col2, ee_col3 = st.columns(3)
                    with ee_col1:
                        edit_e_code = st.text_input("แก้ไข ทะเบียนรถ", value=selected_e_data['engine_code'])
                        e_reg_val = pd.to_datetime(selected_e_data['created_at']) if selected_e_data.get('created_at') else datetime.today()
                        edit_e_reg_date = st.date_input("แก้ไข วันที่ลงทะเบียน", value=e_reg_val, key="edit_e_reg")
                    with ee_col2:
                        t_idx = 0
                        for i, (k, v) in enumerate(engine_type_dict.items()):
                            if v == selected_e_data['engine_type_id']:
                                t_idx = i
                                break
                        edit_e_type = st.selectbox("แก้ไข ชนิดของรถ", options=type_options, index=t_idx)
                        e_exp_val = pd.to_datetime(selected_e_data['expiration_date']) if selected_e_data.get('expiration_date') else None
                        edit_e_exp_date = st.date_input("แก้ไข วันหมดอายุการใช้งาน", value=e_exp_val, key="edit_e_exp")
                    with ee_col3:
                        branch_names = list(branch_dict.keys())
                        b_idx = 0
                        for i, b_name in enumerate(branch_names):
                            if branch_dict[b_name] == selected_e_data['branch_id']:
                                b_idx = i
                                break
                        edit_e_branch = st.selectbox("แก้ไข สาขา", options=branch_names, index=b_idx)
                    
                    edit_e_remark = st.text_area("แก้ไข หมายเหตุ", value=selected_e_data.get('remark') or "", key="edit_e_rem")

                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                    confirm_del_e = st.checkbox("⚠️ ยืนยันการลบข้อมูล (ติ๊กถูกก่อนกดปุ่มลบ)", key="chk_del_e")

                    act_e1, act_e2 = st.columns(2)
                    with act_e1:
                        if st.form_submit_button("💾 อัปเดตข้อมูล (Update)", use_container_width=True):
                            try:
                                conn = get_db_connection()
                                with conn.cursor() as cur:
                                    cur.execute("UPDATE engines SET engine_code=%s, engine_type_id=%s, branch_id=%s, created_at=%s, expiration_date=%s, remark=%s WHERE id=%s", 
                                                (edit_e_code, engine_type_dict[edit_e_type], branch_dict[edit_e_branch], edit_e_reg_date, edit_e_exp_date, edit_e_remark, selected_e_data['id']))
                                    conn.commit()
                                conn.close()
                                log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "Fuel System Setup", f"แก้ไขรถ ID: {selected_e_data['id']}")
                                st.success("✅ อัปเดตข้อมูลสำเร็จ!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาดในการอัปเดต: {e}")
                    
                    with act_e2:
                        if st.form_submit_button("🗑️ ลบข้อมูล (Delete)", use_container_width=True):
                            if confirm_del_e:
                                try:
                                    conn = get_db_connection()
                                    with conn.cursor() as cur:
                                        cur.execute("DELETE FROM engines WHERE id=%s", (selected_e_data['id'],))
                                        conn.commit()
                                    conn.close()
                                    log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "Fuel System Setup", f"ลบรถ ID: {selected_e_data['id']}")
                                    st.success("🗑️ ลบข้อมูลเรียบร้อยแล้ว!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"ไม่สามารถลบได้ (อาจมีข้อมูลอ้างอิงอยู่): {e}")
                            else:
                                st.error("⚠️ กรุณาติ๊กถูกยืนยันการลบก่อนกดปุ่ม")
        else:
            st.info("ยังไม่มีข้อมูลรถในระบบ")