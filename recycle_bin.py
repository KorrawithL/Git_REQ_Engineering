import streamlit as st
import pandas as pd
import time
from database import get_db_connection, log_activity

# โครงสร้างตารางทั้ง 5 หมวดหมู่
TABLE_CONFIG = {
    "⚙️ 1. ระบบเครื่องจักร / เบรกดาวน์": {
        "table": "machine_trans",
        "short_name": "เครื่องจักร/เบรกดาวน์",
        "sql": """
            SELECT t.id AS rec_id, t.record_date, b.branch_name, m.machine_name AS item_name,
                   CONCAT('ชม.ทำงาน: ', t.working_hours, ' | เบรกดาวน์: ', t.breakdown_hours) AS details,
                   t.deleted_by, t.deleted_at
            FROM machine_trans t
            LEFT JOIN branches b ON t.branch_id = b.id
            LEFT JOIN machines_set m ON t.machine_id = m.id
            WHERE t.is_deleted = 1
            ORDER BY t.deleted_at DESC
        """
    },
    "🚚 2. ระบบเชื้อเพลิง (รถยก/เครื่องยนต์)": {
        "table": "fuel_records",
        "short_name": "เชื้อเพลิงรถ",
        "sql": """
            SELECT r.id AS rec_id, r.record_date, b.branch_name, CONCAT(r.engine_code, ' (', r.type_name, ')') AS item_name,
                   CONCAT('น้ำมัน: ', r.fuel_liters, ' ลิตร | ชม.ทำงาน: ', r.working_hours) AS details,
                   r.deleted_by, r.deleted_at
            FROM fuel_records r
            LEFT JOIN branches b ON r.branch_id = b.id
            WHERE r.is_deleted = 1
            ORDER BY r.deleted_at DESC
        """
    },
    "💨 3. แรงดันไอน้ำปลายทาง บอยเลอร์": {
        "table": "boiler_pressure_records",
        "short_name": "แรงดันไอน้ำ",
        "sql": """
            SELECT r.id AS rec_id, r.record_date, b.branch_name, 'ตรวจเช็คแรงดันไอน้ำ' AS item_name,
                   CONCAT('ตรวจทั้งหมด: ', r.total_count, ' ครั้ง | ตก: ', r.total_drop, ' ครั้ง') AS details,
                   r.deleted_by, r.deleted_at
            FROM boiler_pressure_records r
            LEFT JOIN branches b ON r.branch_id = b.id
            WHERE r.is_deleted = 1
            ORDER BY r.deleted_at DESC
        """
    },
    "🔥 4.1 การใช้เชื้อเพลิง บอยเลอร์": {
        "table": "boiler_fuel_records",
        "short_name": "เชื้อเพลิงบอยเลอร์",
        "sql": """
            SELECT r.id AS rec_id, r.record_date, b.branch_name, r.boiler_name AS item_name,
                   CONCAT('ผลิตไอน้ำ: ', r.steam_production, ' ตัน | ชม.ทำงาน: ', r.working_hours) AS details,
                   r.deleted_by, r.deleted_at
            FROM boiler_fuel_records r
            LEFT JOIN branches b ON r.branch_id = b.id
            WHERE r.is_deleted = 1
            ORDER BY r.deleted_at DESC
        """
    },
    "📁 4.2 ยอดรวมสาขา (เตาอบ/ไม้เข้าอบ)": {
        "table": "daily_wood_oven_records",
        "short_name": "ยอดเตาอบ/ไม้อบ",
        "sql": """
            SELECT o.id AS rec_id, o.record_date, b.branch_name, 'ยอดรวมเตาอบประจำวัน' AS item_name,
                   CONCAT('จำนวนเตา: ', o.oven_qty, ' เตา | ไม้เข้าอบ: ', o.wood_out_cubft, ' ลบ.ฟ.') AS details,
                   o.deleted_by, o.deleted_at
            FROM daily_wood_oven_records o
            LEFT JOIN branches b ON o.branch_id = b.id
            WHERE o.is_deleted = 1
            ORDER BY o.deleted_at DESC
        """
    }
}

# =============================================================================
# 📊 ฟังก์ชันดึงจำนวนขยะคงค้างของทุกตาราง
# =============================================================================
def get_trash_counts():
    counts = {}
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for k, v in TABLE_CONFIG.items():
                tbl = v["table"]
                cur.execute(f"SELECT COUNT(*) AS cnt FROM {tbl} WHERE is_deleted = 1")
                res = cur.fetchone()
                counts[k] = int(res['cnt']) if res else 0
        conn.close()
    except Exception:
        for k in TABLE_CONFIG.keys():
            counts[k] = 0
    return counts

# =============================================================================
# 🚨 Popup ยืนยันการลบถาวร (รายการเดียว)
# =============================================================================
@st.dialog("⚠️ ยืนยันการลบข้อมูลถาวร")
def confirm_hard_delete_dialog(table_name, pk_col, rec_id, category_label, summary_text):
    st.error(f"คุณแน่ใจหรือไม่ที่จะลบข้อมูล **ID: {rec_id}** ออกจากฐานข้อมูลอย่างถาวร?")
    st.write(f"**รายละเอียด:** {summary_text}")
    st.markdown("<span style='color:#EF4444; font-size:14px;'>* คำเตือน: เมื่อลบถาวรแล้ว ข้อมูลนี้จะไม่สามารถกู้คืนได้อีก</span>", unsafe_allow_html=True)
    st.write("")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("❌ ยกเลิก", use_container_width=True, key=f"cancel_hd_{rec_id}"):
            st.rerun()
    with c2:
        if st.button("🔥 ยืนยันลบถาวร", type="primary", use_container_width=True, key=f"confirm_hd_{rec_id}"):
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM {table_name} WHERE {pk_col} = %s", (rec_id,))
                    conn.commit()
                conn.close()
                
                st.cache_data.clear()
                log_activity(
                    st.session_state.user_id,
                    st.session_state.username,
                    "DELETE",
                    "Recycle Bin",
                    f"ลบข้อมูลถาวรจาก [{category_label}] ID: {rec_id} ({summary_text})"
                )
                st.success(f"🔥 ลบข้อมูล ID: {rec_id} ถาวรเรียบร้อยแล้ว!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการลบถาวร: {e}")

# =============================================================================
# 🚨 Popup ยืนยันการล้างถังขยะทั้งหมดในหมวดหมู่ (Empty Trash)
# =============================================================================
@st.dialog("🔥 ยืนยันการล้างถังขยะหมวดหมู่นี้")
def confirm_empty_category_dialog(table_name, category_label, item_count):
    st.error(f"คุณแน่ใจหรือไม่ที่จะ **ล้างข้อมูลทั้งหมด ({item_count} รายการ)** ในหมวดหมู่ **{category_label}** อย่างถาวร?")
    st.markdown("<span style='color:#EF4444; font-size:14px;'>* คำเตือน: ข้อมูลที่ถูกลบทั้งหมดในหมวดนี้จะหายไปจากฐานข้อมูลถาวรและกู้คืนไม่ได้</span>", unsafe_allow_html=True)
    st.write("")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("❌ ยกเลิก", use_container_width=True, key=f"cancel_emp_{table_name}"):
            st.rerun()
    with c2:
        if st.button("🔥 ยืนยันล้างถังขยะถาวร", type="primary", use_container_width=True, key=f"confirm_emp_{table_name}"):
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM {table_name} WHERE is_deleted = 1")
                    conn.commit()
                conn.close()
                st.cache_data.clear()
                log_activity(
                    st.session_state.user_id,
                    st.session_state.username,
                    "DELETE",
                    "Recycle Bin",
                    f"ล้างถังขยะถาวรทั้งหมดในหมวด [{category_label}] จำนวน {item_count} รายการ"
                )
                st.success(f"🔥 ล้างถังขยะหมวด {category_label} เรียบร้อยแล้ว!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

# =============================================================================
# 🎯 ฟังก์ชันหลักแสดงหน้าถังขยะกู้คืนข้อมูล
# =============================================================================
def render_recycle_bin_module():
    st.markdown("""
        <style>
        header[data-testid="stHeader"] { display: none !important; }
        .block-container { padding-top: 1rem !important; }
        </style>
    """, unsafe_allow_html=True)

    st.header("🗑️ ถังขยะกู้คืนข้อมูล (Recycle Bin)")
    st.caption("รายการข้อมูลที่ถูกลบจากหน้ารายงาน สามารถกดกู้คืนกลับเข้าสู่ระบบ หรือสั่งลบถาวรได้")

    # 1. ดึงจำนวนรายการที่ถูกลบในแต่ละหมวดหมู่มาแสดงเป็นการ์ดสรุปด้านบน
    trash_counts = get_trash_counts()
    total_trash = sum(trash_counts.values())

    cols_metric = st.columns(5)
    for idx, (cat_key, cfg_item) in enumerate(TABLE_CONFIG.items()):
        cnt = trash_counts.get(cat_key, 0)
        with cols_metric[idx]:
            st.metric(
                label=cfg_item["short_name"],
                value=f"{cnt} รายการ",
                delta="มีขยะค้าง" if cnt > 0 else "สะอาด",
                delta_color="inverse" if cnt > 0 else "normal"
            )

    st.write("")

    # 2. สร้างตัวเลือกหมวดหมู่พร้อมบอกจำนวนรายการชัดเจน
    category_keys = list(TABLE_CONFIG.keys())
    selected_category = st.selectbox(
        "📂 เลือกหมวดหมู่ข้อมูลที่ต้องการตรวจสอบ:",
        options=category_keys,
        format_func=lambda k: f"{k}  —  ({'🔴 พบ ' + str(trash_counts.get(k, 0)) + ' รายการ' if trash_counts.get(k, 0) > 0 else '🟢 ว่าง'})",
        key="rb_sel_cat"
    )

    cfg = TABLE_CONFIG[selected_category]
    table_name = cfg["table"]

    # 3. ดึงข้อมูลและ Primary Key ของตารางที่เลือก
    deleted_rows = []
    pk_col = "id"
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY'")
            pk_res = cur.fetchone()
            if pk_res and pk_res.get('Column_name'):
                pk_col = pk_res['Column_name']

            dynamic_sql = cfg["sql"].replace(".id AS rec_id", f".{pk_col} AS rec_id")
            cur.execute(dynamic_sql)
            deleted_rows = cur.fetchall()
        conn.close()
    except Exception as e:
        st.error(f"⚠️ เกิดข้อผิดพลาดในการดึงข้อมูลถังขยะ: {e}")
        return

    if not deleted_rows:
        st.info(f"✨ ไม่มีข้อมูลที่ถูกลบค้างอยู่ในหมวดหมู่ **{selected_category}**")
        return

    # 4. ส่วนตัวกรองค้นหา (สาขา + คำค้นหา) และปุ่มจัดการแบบกลุ่ม (Bulk Actions)
    available_branches = ["ทั้งหมด"] + sorted(list(set([str(r.get('branch_name') or '-') for r in deleted_rows])))
    
    c_f1, c_f2, c_b1, c_b2 = st.columns([1.2, 2.0, 1.3, 1.3])
    with c_f1:
        sel_branch = st.selectbox("🏢 กรองสาขา:", options=available_branches, key="rb_fil_br")
    with c_f2:
        search_kw = st.text_input("🔎 ค้นหารายการ / ผู้ลบ / วันที่:", placeholder="พิมพ์คำค้นหา...", key="rb_search_kw")
    with c_b1:
        st.write("")
        if st.button("♻️ กู้คืนทั้งหมดในหมวดนี้", use_container_width=True, key="rb_restore_all"):
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute(f"UPDATE {table_name} SET is_deleted = 0, deleted_at = NULL, deleted_by = NULL WHERE is_deleted = 1")
                    conn.commit()
                conn.close()
                st.cache_data.clear()
                log_activity(
                    st.session_state.user_id,
                    st.session_state.username,
                    "UPDATE",
                    "Recycle Bin",
                    f"กู้คืนข้อมูลทั้งหมดในหมวด [{selected_category}] จำนวน {len(deleted_rows)} รายการ"
                )
                st.toast(f"♻️ กู้คืนข้อมูลทั้งหมด {len(deleted_rows)} รายการสำเร็จ!", icon="✅")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
    with c_b2:
        st.write("")
        if st.button("🔥 ล้างถังขยะหมวดนี้", type="primary", use_container_width=True, key="rb_empty_all"):
            confirm_empty_category_dialog(table_name, selected_category, len(deleted_rows))

    # กรองข้อมูลตามสาขาและคำค้นหา
    filtered_rows = []
    for r in deleted_rows:
        b_name = str(r.get('branch_name') or '-')
        if sel_branch != "ทั้งหมด" and b_name != sel_branch:
            continue
        if search_kw.strip():
            kw = search_kw.strip().lower()
            combined_text = f"{r.get('rec_id')} {r.get('record_date')} {b_name} {r.get('item_name')} {r.get('details')} {r.get('deleted_by')}".lower()
            if kw not in combined_text:
                continue
        filtered_rows.append(r)

    st.markdown(f"**แสดงข้อมูล:** `{len(filtered_rows)}` จาก `{len(deleted_rows)}` รายการ")

    # 5. หัวตารางแสดงผล
    h_cols = st.columns([0.8, 1.2, 1.0, 1.5, 2.2, 1.5, 1.6])
    headers = ["ID", "วันที่ข้อมูล", "สาขา", "รายการ", "รายละเอียด", "ผู้ลบ / เวลาที่ลบ", "จัดการ"]
    for col, text in zip(h_cols, headers):
        col.markdown(f"<span style='color:#64748B; font-weight:bold; font-size:14px;'>{text}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 8px 0; border-color: #CBD5E1;'>", unsafe_allow_html=True)

    # 6. แสดงรายการในกล่อง Scrollable เพื่อไม่ให้หน้าเว็บยาวเกินไป
    with st.container(height=420, border=False):
        for r in filtered_rows:
            rec_id = r['rec_id']
            rec_date = pd.to_datetime(r['record_date']).strftime('%d/%m/%Y') if r.get('record_date') else '-'
            b_name = r.get('branch_name') or '-'
            item_name = r.get('item_name') or '-'
            details = r.get('details') or '-'
            del_by = r.get('deleted_by') or 'ไม่ระบุ'
            del_at = pd.to_datetime(r['deleted_at']).strftime('%d/%m/%y %H:%M') if r.get('deleted_at') else '-'

            cols = st.columns([0.8, 1.2, 1.0, 1.5, 2.2, 1.5, 1.6])
            cols[0].write(f"**{rec_id}**")
            cols[1].write(rec_date)
            cols[2].write(b_name)
            cols[3].write(item_name)
            cols[4].write(details)
            cols[5].caption(f"👤 {del_by}\n🕒 {del_at}")

            c_res, c_del = cols[6].columns(2, gap="small")
            if c_res.button("♻️ กู้คืน", key=f"res_{table_name}_{rec_id}", use_container_width=True, help="กู้คืนข้อมูลกลับเข้ารายงาน"):
                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        cur.execute(
                            f"UPDATE {table_name} SET is_deleted = 0, deleted_at = NULL, deleted_by = NULL WHERE {pk_col} = %s",
                            (rec_id,)
                        )
                        conn.commit()
                    conn.close()
                    st.cache_data.clear()
                    log_activity(
                        st.session_state.user_id,
                        st.session_state.username,
                        "UPDATE",
                        "Recycle Bin",
                        f"กู้คืนข้อมูล [{selected_category}] ID: {rec_id} (วันที่: {rec_date}, สาขา: {b_name})"
                    )
                    st.toast(f"♻️ กู้คืนข้อมูล ID: {rec_id} สำเร็จ!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"กู้คืนไม่สำเร็จ: {e}")

            if c_del.button("🔥 ลบ", key=f"hd_{table_name}_{rec_id}", type="primary", use_container_width=True, help="ลบถาวรออกจากฐานข้อมูล"):
                summary_str = f"วันที่ {rec_date} | สาขา {b_name} | {item_name} ({details})"
                confirm_hard_delete_dialog(table_name, pk_col, rec_id, selected_category, summary_str)

            st.markdown("<hr style='margin: 4px 0; border-color: #F1F5F9;'>", unsafe_allow_html=True)