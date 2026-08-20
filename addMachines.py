import streamlit as st
import time
from database import get_db_connection, log_activity
from config import branch_dict

def render_add_new_equipment():
    st.header("🛠️ โมดูลลงทะเบียนอุปกรณ์ใหม่เข้าสู่ระบบ")
    st.caption("หน้าจอสำหรับแอดมิน เพื่อเพิ่มรายชื่อเครื่องจักร และ รหัสงาน/ทะเบียนรถใหม่ เข้าสู่ฐานข้อมูล")
    st.write("---")
    
    # แบ่งเป็น 2 แท็บย่อยเพื่อความสะอาดตา
    tab_m1, tab_m2 = st.tabs(["⚙️ 1. เพิ่มเครื่องจักรใหม่ (สำหรับ Tab 1)", "🚚 2. เพิ่มรหัสงาน/ทะเบียนรถใหม่ (สำหรับ Tab 2)"])
    
    # ==========================================
    # ⚙️ ส่วนที่ 1: เพิ่มเครื่องจักรใหม่
    # ==========================================
    with tab_m1:
        st.subheader("➕ เพิ่มเครื่องจักรใหม่เข้าสู่ระบบ")
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

    # ==========================================
    # 🚚 ส่วนที่ 2: เพิ่มรหัสงาน/ทะเบียนรถใหม่
    # ==========================================
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
            st.warning("⚠️ ไม่สามารถดึงข้อมูลประเภทรถจากระบบได้ กรุณาตรวจสอบฐานข้อมูล")

        type_options = list(engine_type_dict.keys()) if engine_type_dict else ["-- ไม่มีข้อมูลประเภทรถ --"]

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