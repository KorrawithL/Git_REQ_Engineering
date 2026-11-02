import time
import pandas as pd
import streamlit as st
from all_reports import process_t1, process_t2, process_t3, process_t4
from config import branch_dict
from database import get_db_connection, log_activity

# =============================================================================
# 📌 1. ค่าคงที่และสไตล์ CSS (Constants & Styles)
# =============================================================================
TAB_VIEWS_CSS = """
<style>
header[data-testid="stHeader"] { display: none !important; }
#header { visibility: hidden !important; }
#MainMenu { visibility: hidden !important; }
.block-container { padding-top: 1rem !important; margin-top: -20px !important; }
</style>
"""

SUB_MENU_MAPPING = {
    "⚙️ ระบบเครื่องจักร / เบรกดาวน์": "1",
    "🚚 ระบบเชื้อเพลิง (รถยก/เครื่องยนต์)": "2",
    "💨 แรงดันไอน้ำปลายทาง บอยเลอร์": "3",
    "🔥 การใช้เชื้อเพลิง บอยเลอร์": "4",
}


# =============================================================================
# 🚀 2. ฟังก์ชันจัดการฐานข้อมูลและ UI ส่วนกลาง (DB & UI Helpers)
# =============================================================================
def render_branch_and_date_selector(available_options, current_branch_name, branch_key, date_key):
    """วาดส่วนเลือกสาขาและวันที่ด้านบนของฟอร์มบันทึกข้อมูล คืนค่า (target_branch_id, selected_date, is_branch_invalid)"""
    c_top1, c_top2 = st.columns([1.5, 1])
    target_branch_id = None

    with c_top1:
        if len(available_options) > 1:
            branch_label = st.selectbox("🏢 ระบุสาขาที่ต้องการบันทึก *", options=["-- เลือกสาขา --"] + available_options, key=branch_key)
            branch_invalid = (branch_label == "-- เลือกสาขา --")
            if not branch_invalid:
                target_branch_id = branch_dict[branch_label]
        else:
            branch_label = available_options[0] if available_options else current_branch_name
            st.write(f"**(สังกัด: {branch_label})**")
            target_branch_id = branch_dict.get(branch_label, int(st.session_state.branch_id))
            branch_invalid = False

    today = pd.to_datetime("today").date()
    with c_top2:
        rec_date = st.date_input(
            "วันที่",
            format="DD/MM/YYYY",
            value=today,
            max_value=today,
            key=date_key,
            disabled=branch_invalid,
            help="เลือกได้เฉพาะวันนี้หรือวันย้อนหลัง"
        )

    return target_branch_id, rec_date, branch_invalid


def get_available_machines_t1(branch_id, rec_date):
    """ดึงรายชื่อเครื่องจักรที่ยังไม่ได้บันทึกข้อมูลในวันที่เลือก"""
    machine_dict = {}
    conn = None
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
            cur.execute(sql, (branch_id, branch_id, rec_date))
            for m in cur.fetchall():
                machine_dict[m["machine_name"]] = m["id"]
    except Exception as e:
        st.warning(f"ไม่สามารถโหลดข้อมูลเครื่องจักรได้: {e}")
    finally:
        if conn and conn.open:
            conn.close()
    return machine_dict


def get_available_engines_t2(branch_id, rec_date):
    """ดึงรายชื่อรถยนต์/รถยกที่ยังไม่ได้บันทึกข้อมูลในวันที่เลือก"""
    conn = None
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
            cur.execute(sql_eng, (branch_id, branch_id, rec_date))
            return cur.fetchall()
    except Exception as e:
        st.warning(f"ไม่สามารถโหลดข้อมูลรถได้: {e}")
        return []
    finally:
        if conn and conn.open:
            conn.close()


def check_daily_record_exists(table_name, branch_id, rec_date):
    """ตรวจสอบว่าสาขานี้มีการบันทึกข้อมูลรายวันในตารางที่ระบุไปแล้วหรือไม่"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(f"SELECT 1 FROM {table_name} WHERE branch_id=%s AND record_date=%s AND is_deleted = 0 LIMIT 1", (branch_id, rec_date))
            return bool(cur.fetchone())
    except Exception:
        return False
    finally:
        if conn and conn.open:
            conn.close()


def get_available_boilers_t4(branch_id, rec_date):
    """ดึงรายชื่อบอยเลอร์ที่ยังไม่ได้บันทึกข้อมูลเชื้อเพลิงในวันที่เลือก"""
    boiler_options = []
    conn = None
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
            cur.execute(sql, (branch_id, branch_id, rec_date))
            for r in cur.fetchall():
                if r.get("b_name"):
                    boiler_options.append(r["b_name"])
    except Exception as e:
        st.warning(f"ไม่สามารถโหลดข้อมูลบอยเลอร์ได้: {e}")
    finally:
        if conn and conn.open:
            conn.close()
    return boiler_options


def execute_insert_and_refresh(sql, params, cache_func, log_module, log_detail, toast_msg, toast_icon, reset_state_key):
    """รันคำสั่ง INSERT ข้อมูล, ล้างแคชรายงาน, บันทึก Log, แจ้งเตือน Toast และรีเซ็ตฟอร์ม"""
    with st.spinner("กำลังบันทึกข้อมูล..."):
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()

            cache_func.clear()
            log_activity(st.session_state.user_id, st.session_state.username, "INSERT", log_module, log_detail)
            st.toast(toast_msg, icon=toast_icon)

            st.session_state[reset_state_key] += 1
            time.sleep(1.2)
            st.rerun()
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
        finally:
            if conn and conn.open:
                conn.close()


# =============================================================================
# 📝 3. ฟังก์ชันวาดฟอร์มบันทึกข้อมูลแยกตามแท็บ (Tab 1 - Tab 4)
# =============================================================================
def _render_tab1_machines(available_options, current_branch_name):
    st.subheader("ระบบการทำงานของเครื่องจักร / เบรกดาวน์")

    with st.container(border=True):
        st.write("### 📝 ฟอร์มบันทึกข้อมูลเครื่องจักรลงตาราง")
        st.caption("💡 *หมายเหตุ: เครื่องจักรที่ถูกบันทึกข้อมูลในวันที่เลือกไปแล้ว จะถูกซ่อนออกจากตัวเลือกอัตโนมัติเพื่อป้องกันการบันทึกซ้ำ*")

        target_branch_id, m_date, t1_branch_invalid = render_branch_and_date_selector(
            available_options, current_branch_name, "t1_branch", "m_date"
        )

        machine_dict = get_available_machines_t1(target_branch_id, m_date) if not t1_branch_invalid else {}
        if machine_dict:
            machine_select_options = ["-- กรุณาเลือกเครื่องจักร --"] + list(machine_dict.keys())
        else:
            machine_select_options = ["-- บันทึกข้อมูลครบทุกเครื่องแล้ว --"] if not t1_branch_invalid else ["-- กรุณาเลือกเครื่องจักร --"]

        if "reset_t1" not in st.session_state:
            st.session_state.reset_t1 = 0
        rk1 = st.session_state.reset_t1

        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            m_label = st.selectbox(
                "🚜 ระบุเครื่องจักรที่ใช้งาน *",
                options=machine_select_options,
                index=0,
                disabled=t1_branch_invalid,
                key=f"t1_m_label_{rk1}",
                help="แสดงเฉพาะเครื่องจักรที่ยังไม่ได้บันทึกข้อมูลในวันที่เลือก (หากต้องการแก้ไขรายการที่บันทึกไปแล้ว ให้ไปที่หน้า 'รายงานรวม')"
            )
            is_m_not_selected = t1_branch_invalid or (m_label in ["-- กรุณาเลือกเครื่องจักร --", "-- บันทึกข้อมูลครบทุกเครื่องแล้ว --"])
            m_qty = st.number_input(
                "จำนวนเครื่องจักร *",
                min_value=1,
                step=1,
                value=None,
                placeholder="ระบุจำนวน",
                disabled=is_m_not_selected,
                key=f"t1_qty_{rk1}",
                help="จำนวนเครื่องจักรที่เปิดใช้งาน (ใช้คำนวณเพดานชั่วโมงสูงสุด = จำนวนเครื่อง x 24 ชม.)"
            )
        with c2:
            m_work_hours = st.number_input(
                "ชั่วโมงทำงาน *",
                min_value=0.0,
                step=0.5,
                value=None,
                placeholder="ระบุชั่วโมงทำงาน",
                disabled=is_m_not_selected,
                key=f"t1_work_{rk1}",
                help="ชั่วโมงทำงานรวมกับชั่วโมงเบรกดาวน์ ต้องไม่เกิน 24 ชั่วโมงต่อ 1 เครื่อง"
            )
            m_break_hours = st.number_input(
                "ชั่วโมงเบรกดาวน์ *",
                min_value=0.0,
                step=0.5,
                value=None,
                placeholder="ระบุชั่วโมงเบรกดาวน์",
                disabled=is_m_not_selected,
                key=f"t1_break_{rk1}",
                help="หากไม่มีการเสียหรือหยุดเครื่อง ให้กรอกเลข 0"
            )

        m_remark = st.text_area(
            "หมายเหตุ / สาเหตุที่ชำรุด",
            disabled=is_m_not_selected,
            key=f"t1_rem_{rk1}",
            placeholder="ระบุอาการเสียหรือสาเหตุการหยุดเครื่อง (ถ้ามี)..."
        )

        if st.button("💾 บันทึกข้อมูลเครื่องจักร", use_container_width=True, type="primary", disabled=is_m_not_selected):
            if m_qty is None or m_work_hours is None or m_break_hours is None:
                st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
            elif (m_work_hours + m_break_hours) > (m_qty * 24.0):
                max_hrs = m_qty * 24.0
                total_hrs = m_work_hours + m_break_hours
                st.error(f"⚠️ ไม่สามารถบันทึกได้: ชั่วโมงทำงานรวมกับเบรกดาวน์ ({total_hrs} ชม.) เกินกำหนด ต้องไม่เกิน {max_hrs} ชม. (สำหรับเครื่องจักร {m_qty} เครื่อง)")
            else:
                sql = """
                    INSERT INTO machine_trans 
                    (branch_id, record_date, machine_id, machine_qty, working_hours, breakdown_hours, remarks, created_by, created_at, updated_at, status) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 'active')
                """
                params = (
                    target_branch_id, m_date, int(machine_dict[m_label]),
                    int(m_qty), float(m_work_hours), float(m_break_hours),
                    m_remark, int(st.session_state.user_id)
                )
                execute_insert_and_refresh(
                    sql=sql,
                    params=params,
                    cache_func=process_t1,
                    log_module="Tab 1 Data Entry",
                    log_detail=f"บันทึกเครื่องจักร {m_label} วันที่ {m_date}",
                    toast_msg=f"✅ บันทึกข้อมูล {m_label} สำเร็จเรียบร้อย!",
                    toast_icon="🎉",
                    reset_state_key="reset_t1"
                )


def _render_tab2_fuel(available_options, current_branch_name):
    st.subheader("ระบบการใช้เชื้อเพลิง (เครื่องยนต์/รถยก)")

    with st.container(border=True):
        st.write("### 📝 ฟอร์มบันทึกข้อมูลการใช้เชื้อเพลิงรถ")
        st.caption("💡 *หมายเหตุ: รถที่ถูกบันทึกข้อมูลในวันที่เลือกไปแล้ว จะถูกซ่อนออกจากตัวเลือกอัตโนมัติ*")

        if "reset_t2" not in st.session_state:
            st.session_state.reset_t2 = 0
        rk2 = st.session_state.reset_t2

        target_branch_id_t2, f_date, t2_branch_invalid = render_branch_and_date_selector(
            available_options, current_branch_name, "t2_br", "f_date"
        )

        all_engines_filtered = get_available_engines_t2(target_branch_id_t2, f_date) if not t2_branch_invalid else []

        c_sel1, c_sel2 = st.columns(2)
        if all_engines_filtered:
            available_types = sorted(list({e["type_name"] for e in all_engines_filtered if e.get("type_name")}))
            type_options = ["-- เลือกประเภท --"] + available_types
            f2_type_disabled = False
        else:
            type_options = ["-- บันทึกข้อมูลครบทุกคันแล้ว --"] if not t2_branch_invalid else ["-- เลือกประเภท --"]
            f2_type_disabled = True

        with c_sel1:
            f2_type = st.selectbox(
                "🚜 ระบุ ชนิด / ประเภทรถ ที่ต้องการบันทึก *",
                type_options,
                key="f2_ty",
                disabled=f2_type_disabled,
                help="เลือกยี่ห้อหรือประเภทรถ (เช่น TOYOTA, TCK)"
            )

        f2_code_disabled = (f2_type in ["-- เลือกประเภท --", "-- บันทึกข้อมูลครบทุกคันแล้ว --"]) or f2_type_disabled
        if not f2_code_disabled:
            available_codes = sorted(list({e["engine_code"] for e in all_engines_filtered if e.get("type_name") == f2_type}))
            code_options = ["-- เลือกรถ --"] + available_codes
        else:
            code_options = ["-- เลือกรถ --"]

        with c_sel2:
            f2_code = st.selectbox(
                "🏷️ ระบุ รหัสงาน / ทะเบียนรถ ที่ต้องการบันทึก *",
                code_options,
                key=f"f2_cd_{rk2}",
                disabled=f2_code_disabled,
                help="แสดงเฉพาะทะเบียนรถที่ยังไม่ได้ลงบันทึกในวันที่เลือก"
            )

        inputs_disabled = (f2_code == "-- เลือกรถ --") or f2_code_disabled
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            f_liters = st.number_input(
                "ปริมาณน้ำมัน (ลิตร) *",
                min_value=0.0,
                step=1.0,
                value=None,
                placeholder="ระบุปริมาณน้ำมัน",
                disabled=inputs_disabled,
                key=f"t2_lit_{rk2}",
                help="ระบุปริมาณน้ำมันดีเซลที่เติม (หากไม่ได้เติมน้ำมันในวันนั้นให้ใส่ 0)"
            )
        with c2:
            f_hours = st.number_input(
                "จำนวนชั่วโมงทำงาน (ชม.) *",
                min_value=0.0,
                step=0.5,
                value=None,
                placeholder="ระบุชั่วโมงทำงาน",
                disabled=inputs_disabled,
                key=f"t2_hrs_{rk2}",
                help="ชั่วโมงการทำงานของรถต้องไม่เกิน 24 ชั่วโมงต่อวัน"
            )

        f_remark = st.text_area("หมายเหตุ", disabled=inputs_disabled, key=f"t2_rem_{rk2}")

        if st.button("💾 บันทึกข้อมูลเชื้อเพลิงรถ", use_container_width=True, type="primary", disabled=inputs_disabled):
            if inputs_disabled or f_liters is None or f_hours is None:
                st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
            elif f_hours > 24.0:
                st.error("⚠️ ไม่สามารถบันทึกได้: ชั่วโมงทำงานรถยนต์ต้องไม่เกิน 24 ชั่วโมงต่อวัน")
            else:
                sql = """
                    INSERT INTO fuel_records 
                    (branch_id, record_date, engine_code, type_name, fuel_liters, working_hours, remark) 
                    VALUES (%s, %s, CONVERT(%s USING utf8mb4), CONVERT(%s USING utf8mb4), %s, %s, CONVERT(%s USING utf8mb4))
                """
                params = (target_branch_id_t2, f_date, f2_code, f2_type, float(f_liters), float(f_hours), f_remark)
                execute_insert_and_refresh(
                    sql=sql,
                    params=params,
                    cache_func=process_t2,
                    log_module="Tab 2 Data Entry",
                    log_detail=f"บันทึกเชื้อเพลิงรถ {f2_code} จำนวน {f_liters} ลิตร",
                    toast_msg=f"✅ บันทึกสำเร็จ! ({f2_code})",
                    toast_icon="🚚",
                    reset_state_key="reset_t2"
                )


def _render_tab3_pressure(available_options, current_branch_name):
    st.subheader("ระบบแรงดันไอน้ำปลายทางของบอยเลอร์")

    with st.container(border=True):
        st.write("### 📝 บันทึกข้อมูลแรงดันไอน้ำ")
        st.caption("💡 *หมายเหตุ: บันทึกสรุปวันละ 1 รายการต่อสาขา โดยผลรวมจำนวนครั้งที่แรงดันตก (PM + นอก PM) ต้องไม่เกินจำนวนครั้งที่ตรวจเช็คทั้งหมด*")

        target_branch_id, p_date, t3_branch_invalid = render_branch_and_date_selector(
            available_options, current_branch_name, "t3_branch", "p_date"
        )

        has_t3_record = check_daily_record_exists("boiler_pressure_records", target_branch_id, p_date) if not t3_branch_invalid else False
        is_t3_disabled = t3_branch_invalid or has_t3_record

        if has_t3_record:
            st.warning("⚠️ มีการบันทึกข้อมูลแรงดันไอน้ำของสาขานี้ ในวันที่เลือกไปแล้ว (หากต้องการแก้ไข กรุณาไปที่หน้า 'รายงานรวม')")

        if "reset_t3" not in st.session_state:
            st.session_state.reset_t3 = 0
        rk3 = st.session_state.reset_t3

        col1, col2 = st.columns(2)
        with col1:
            total_count = st.number_input(
                "จำนวนครั้งทั้งหมด *",
                min_value=0,
                step=1,
                value=None,
                placeholder="ระบุจำนวนครั้งทั้งหมด",
                disabled=is_t3_disabled,
                key=f"t3_tot_{rk3}",
                help="จำนวนครั้งที่ตรวจวัดแรงดันไอน้ำทั้งหมดในวันนั้น (เช่น ตรวจทุก 15 นาที = 96 ครั้ง/วัน)"
            )
            pm_drop = st.number_input(
                "จำนวนที่ตกตามเงื่อนไข PM *",
                min_value=0,
                step=1,
                value=None,
                placeholder="ระบุจำนวนที่ตกตามเงื่อนไข PM",
                disabled=is_t3_disabled,
                key=f"t3_pm_{rk3}",
                help="จำนวนครั้งที่แรงดันต่ำกว่าเกณฑ์เนื่องจากอยู่ในช่วงลากขี้เถ้าหรือบำรุงรักษาตามรอบ PM"
            )
        with col2:
            non_pm_drop = st.number_input(
                "จำนวนที่ตกนอกเหนือ PM *",
                min_value=0,
                step=1,
                value=None,
                placeholder="ระบุจำนวนที่ตกนอกเหนือ PM",
                disabled=is_t3_disabled,
                key=f"t3_npm_{rk3}",
                help="จำนวนครั้งที่แรงดันตกผิดปกตินอกรอบ PM (เมื่อรวมกับตกตาม PM แล้วต้องไม่เกินจำนวนครั้งทั้งหมด)"
            )
            p_remark = st.text_input("หมายเหตุ (ลากขี้เถ้า / ซ่อมบำรุง)", disabled=is_t3_disabled, key=f"t3_rem_{rk3}")

        if st.button("💾 บันทึกข้อมูลแรงดันไอน้ำ", use_container_width=True, type="primary", disabled=is_t3_disabled):
            if total_count is None or pm_drop is None or non_pm_drop is None:
                st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
            elif (pm_drop + non_pm_drop) > total_count:
                st.error("⚠️ ไม่สามารถบันทึกได้: จำนวนครั้งที่ 'แรงดันตก' รวมกัน ต้องไม่มากกว่า 'จำนวนครั้งทั้งหมด'")
            else:
                sql = """
                    INSERT INTO boiler_pressure_records 
                    (branch_id, record_date, total_count, total_drop, pm_drop, non_pm_drop, remark, created_by) 
                    VALUES (%s, %s, %s, %s, %s, %s, CONVERT(%s USING utf8mb4), %s)
                """
                params = (
                    target_branch_id, p_date, int(total_count),
                    int(pm_drop) + int(non_pm_drop), int(pm_drop), int(non_pm_drop),
                    p_remark, int(st.session_state.user_id)
                )
                execute_insert_and_refresh(
                    sql=sql,
                    params=params,
                    cache_func=process_t3,
                    log_module="Tab 3 Data Entry",
                    log_detail=f"บันทึกแรงดันไอน้ำตก วันที่ {p_date}",
                    toast_msg="✅ บันทึกข้อมูลแรงดันไอน้ำเรียบร้อยแล้ว!",
                    toast_icon="💨",
                    reset_state_key="reset_t3"
                )


def _render_tab4_boiler_fuel(available_options, current_branch_name):
    st.subheader("ระบบการใช้เชื้อเพลิงบอยเลอร์")
    st.info(
        "📌 **ข้อแนะนำสำคัญ:** เพื่อให้รายงานสรุปรวม (บอยเลอร์ 1+2) คำนวณข้อมูลรายวันได้ครบถ้วน "
        "กรุณาบันทึกข้อมูลทั้งในแท็บ **'📁 ยอดรวมสาขา'** และแท็บ **'🏭 ปริมาณเชื้อเพลิงบอยเลอร์ (ทั้งบอยเลอร์ 1 และ 2)'** ของวันนั้นให้ครบ"
    )

    if "reset_t4" not in st.session_state:
        st.session_state.reset_t4 = 0
    rk4 = st.session_state.reset_t4

    sub_tab1, sub_tab2 = st.tabs(["📁 บันทึกข้อมูลยอดรวมสาขา (เตา/ไม้อบ/แรงดัน)", "🏭 บันทึกปริมาณเชื้อเพลิงบอยเลอร์"])

    # แท็บย่อยที่ 1: บันทึกข้อมูลยอดรวมของสาขา
    with sub_tab1:
        with st.container(border=True):
            st.write("### 📁 บันทึกข้อมูลยอดรวมของสาขาประจำวัน")

            target_branch_id_1, bf_date_1, t4_ov_invalid = render_branch_and_date_selector(
                available_options, current_branch_name, "t4_br1", "bf_dt1"
            )

            has_t4_ov_record = check_daily_record_exists("daily_wood_oven_records", target_branch_id_1, bf_date_1) if not t4_ov_invalid else False
            is_t4_ov_disabled = t4_ov_invalid or has_t4_ov_record

            if has_t4_ov_record:
                st.warning("⚠️ มีการบันทึกข้อมูลยอดรวมของสาขานี้ ในวันที่เลือกไปแล้ว (หากต้องการแก้ไข กรุณาไปที่หน้า 'รายงานรวม')")

            c_ov1, c_ov2, c_ov3 = st.columns(3)
            with c_ov1:
                oven_qty = st.number_input(
                    "จำนวนเตาที่อบ (เตา) *",
                    min_value=0,
                    step=1,
                    value=None,
                    placeholder="ระบุจำนวนเตา",
                    disabled=is_t4_ov_disabled,
                    key=f"t4_ov_{rk4}",
                    help="จำนวนเตาอบไม้ที่เปิดเดินเครื่องในวันนั้น (ใช้คำนวณเป้าหมายไอน้ำมาตรฐาน)"
                )
            with c_ov2:
                wood_out = st.number_input(
                    "ไม้เข้าอบ (ลบ.ฟ.) *",
                    min_value=0.0,
                    step=0.001,
                    format="%.3f",
                    value=None,
                    placeholder="ระบุปริมาณ",
                    disabled=is_t4_ov_disabled,
                    key=f"t4_wo_{rk4}",
                    help="ปริมาตรไม้เข้าอบรวม (ลูกบาศก์ฟุต) รองรับทศนิยม 3 ตำแหน่ง"
                )
            with c_ov3:
                avg_pressure = st.number_input(
                    "แรงดันปลายทางเฉลี่ย *",
                    min_value=0.0,
                    step=0.1,
                    value=None,
                    placeholder="ระบุแรงดัน",
                    disabled=is_t4_ov_disabled,
                    key=f"t4_avgp_{rk4}",
                    help="ค่าแรงดันไอน้ำปลายทางเฉลี่ยของวันนั้น (Bar)"
                )

            if st.button("💾 บันทึกข้อมูลยอดรวมสาขา", use_container_width=True, type="primary", disabled=is_t4_ov_disabled):
                if any(x is None for x in [oven_qty, wood_out, avg_pressure]):
                    st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                else:
                    sql_oven = """
                        INSERT INTO daily_wood_oven_records 
                        (branch_id, record_date, oven_qty, wood_out_cubft, avg_terminal_pressure, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    params_oven = (
                        target_branch_id_1, bf_date_1, int(oven_qty),
                        float(wood_out), float(avg_pressure), int(st.session_state.user_id)
                    )
                    execute_insert_and_refresh(
                        sql=sql_oven,
                        params=params_oven,
                        cache_func=process_t4,
                        log_module="Tab 4 Oven Entry",
                        log_detail=f"บันทึกยอดรวมสาขา วันที่ {bf_date_1}",
                        toast_msg="✅ บันทึกข้อมูลยอดรวมสาขาสำเร็จแล้ว!",
                        toast_icon="📁",
                        reset_state_key="reset_t4"
                    )

    # แท็บย่อยที่ 2: บันทึกปริมาณเชื้อเพลิงบอยเลอร์
    with sub_tab2:
        with st.container(border=True):
            st.write("### 🏭 บันทึกปริมาณเชื้อเพลิงแยกตามบอยเลอร์")

            target_branch_id_2, bf_date_2, t4_bf_invalid = render_branch_and_date_selector(
                available_options, current_branch_name, "t4_br2", "bf_dt2"
            )

            boiler_options = get_available_boilers_t4(target_branch_id_2, bf_date_2) if not t4_bf_invalid else []
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
                "🚜 ระบุเครื่องบอยเลอร์ที่ใช้งาน *",
                b_list,
                disabled=is_boiler_invalid,
                key="t4_boiler",
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
                    "จำนวนชั่วโมงทำงาน (ชม.) *",
                    min_value=0.1,
                    step=0.5,
                    value=None,
                    placeholder="ระบุชั่วโมงทำงาน",
                    disabled=disable_t4_inputs,
                    key=f"t4_wh_{rk4}",
                    help="ชั่วโมงเดินเครื่องบอยเลอร์ต้องไม่เกิน 24 ชั่วโมงต่อวัน"
                )

            if st.button("💾 บันทึกข้อมูลเชื้อเพลิงบอยเลอร์", use_container_width=True, type="primary", disabled=disable_t4_inputs):
                inputs_bf = [saw_w, wood_w, waste_wood_w, saw_p, wood_p, waste_wood_p, prod_val, work_hours]
                if any(x is None for x in inputs_bf):
                    st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง!")
                elif work_hours > 24.0:
                    st.error("⚠️ ไม่สามารถบันทึกได้: ชั่วโมงทำงานต้องไม่เกิน 24 ชั่วโมงต่อวัน")
                else:
                    sql_fuel = """
                        INSERT INTO boiler_fuel_records 
                        (branch_id, record_date, boiler_name, sawdust_weight, wood_weight, waste_wood_weight, 
                         sawdust_price, wood_price, waste_wood_price, steam_production, working_hours, created_by) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    params_fuel = (
                        target_branch_id_2, bf_date_2, boiler_name_input,
                        float(saw_w), float(wood_w), float(waste_wood_w),
                        float(saw_p), float(wood_p), float(waste_wood_p),
                        float(prod_val), float(work_hours), int(st.session_state.user_id)
                    )
                    execute_insert_and_refresh(
                        sql=sql_fuel,
                        params=params_fuel,
                        cache_func=process_t4,
                        log_module="Tab 4 Boiler Entry",
                        log_detail=f"บันทึกเชื้อเพลิง {boiler_name_input} วันที่ {bf_date_2}",
                        toast_msg=f"✅ บันทึกข้อมูล {boiler_name_input} สำเร็จแล้ว!",
                        toast_icon="🔥",
                        reset_state_key="reset_t4"
                    )


# =============================================================================
# 🎯 4. ฟังก์ชันหลักสำหรับควบคุมการแสดงผลหน้าบันทึกข้อมูลประจำวัน
# =============================================================================
def render_engineering_system_tabs(current_branch_name, selected_sub_menu=None):
    st.markdown(TAB_VIEWS_CSS, unsafe_allow_html=True)

    raw_role = st.session_state.get("role_tab") or st.session_state.get("role") or "user"
    current_role = str(raw_role).strip().lower()
    allowed_tabs_list = st.session_state.get("allowed_tabs", [])
    user_allowed_branches = st.session_state.get("allowed_branches", [str(st.session_state.get("branch_id"))])

    key = SUB_MENU_MAPPING.get(selected_sub_menu, "1") if selected_sub_menu else "1"

    if current_role != "admin" and key not in allowed_tabs_list:
        st.error("## ⏳ คุณไม่ได้รับสิทธิ์เข้าถึงหัวข้อนี้")
        return

    if current_role == "admin":
        available_options = list(branch_dict.keys())
    else:
        available_options = [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]

    with st.container():
        if key == "1":
            _render_tab1_machines(available_options, current_branch_name)
        elif key == "2":
            _render_tab2_fuel(available_options, current_branch_name)
        elif key == "3":
            _render_tab3_pressure(available_options, current_branch_name)
        elif key == "4":
            _render_tab4_boiler_fuel(available_options, current_branch_name)