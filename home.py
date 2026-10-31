import streamlit as st
import pandas as pd
import altair as alt
from database import get_db_connection
from config import branch_dict

# =============================================================================
# 📌 1. ฟังก์ชันช่วยเหลือสำหรับจัดการข้อมูลและสร้างป้ายสถานะ (Helpers)
# =============================================================================
def _build_branch_where_clause(branch_filter, allowed_branches):
    """สร้างเงื่อนไข SQL และพารามิเตอร์สำหรับกรองสาขา"""
    if branch_filter and branch_filter != "ALL":
        return "AND branch_id = %s", (int(branch_filter),)
    if allowed_branches:
        valid_bids = [int(x) for x in allowed_branches if str(x).isdigit()]
        if valid_bids:
            placeholders = ", ".join(["%s"] * len(valid_bids))
            return f"AND branch_id IN ({placeholders})", tuple(valid_bids)
    return "", ()


def _build_7day_series(df_template, rows, db_col, label_col):
    """รวมข้อมูลรายวันจากฐานข้อมูลเข้ากับโครงร่างวันที่ย้อนหลัง 7 วัน"""
    df_full = df_template.copy()
    if rows:
        df_raw = pd.DataFrame(rows)
        df_raw["วันที่"] = pd.to_datetime(df_raw["log_date"])
        df_raw[label_col] = df_raw[db_col].astype(float)
        df_full = pd.merge(df_full, df_raw[["วันที่", label_col]], on="วันที่", how="left")
    else:
        df_full[label_col] = 0.0

    df_full[label_col] = df_full[label_col].fillna(0.0)
    return df_full


def get_diff_pill(diff, unit, invert_color=False, metric_name=""):
    """สร้างป้าย HTML แสดงผลต่างเทียบกับเดือนก่อนหน้าพร้อมลูกศรและสีตามเงื่อนไข"""
    if abs(diff) < 0.01:
        return f'<span style="background-color: #F1F5F9; color: #475569; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">- 0 {unit} (เท่าเดือนก่อน)</span>'
    
    is_pos = diff > 0
    arrow = "↑" if is_pos else "↓"
    direction_txt = "เพิ่มขึ้นจากเดือนที่แล้ว" if is_pos else "ลดลงจากเดือนที่แล้ว"
    
    if (is_pos and not invert_color) or (not is_pos and invert_color):
        bg, text = "#D1FAE5", "#059669"
    else:
        bg, text = "#FEE2E2", "#DC2626"
        
    return (
        f'<span style="background-color: {bg}; color: {text}; padding: 4px 10px; border-radius: 20px; '
        f'font-size: 13px; font-weight: bold; cursor: help;" '
        f'title="{metric_name}: {direction_txt} {abs(diff):,.2f} {unit}">'
        f'{arrow} {abs(diff):,.2f} {unit}</span>'
    )


def get_badge_pill(text, bg_color, text_color):
    """สร้างป้ายกำกับสถานะขนาดเล็ก"""
    return f'<span style="background-color: {bg_color}; color: {text_color}; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">{text}</span>'


# =============================================================================
# 🚀 2. ฟังก์ชันดึงข้อมูลจริงทำหน้า Dashboard
# =============================================================================
def get_dashboard_data(branch_filter="ALL", allowed_branches=None):
    data = {
        "active_machines": 0,
        "breakdown_count": 0,
        "fuel_usage": 0.0,
        "boiler_drop": 0,
        "cur_fuel": 0.0,
        "cur_hrs": 0.0,
        "cur_rate": 0.0,
        "prev_fuel": 0.0,
        "prev_hrs": 0.0,
        "prev_rate": 0.0,
        "fuel_chart_df": pd.DataFrame(),
        "pressure_chart_df": pd.DataFrame()
    }

    b_sql, b_params = _build_branch_where_clause(branch_filter, allowed_branches)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. เครื่องจักรทำงานวันนี้ & แจ้งซ่อม/เบรกดาวน์วันนี้ (รวมในคิวรีเดียว)
            cur.execute(f"""
                SELECT COUNT(id) AS active_cnt,
                       COALESCE(SUM(CASE WHEN breakdown_hours > 0 THEN 1 ELSE 0 END), 0) AS bd_cnt
                FROM machine_trans 
                WHERE record_date = CURDATE() {b_sql} AND is_deleted = 0
            """, b_params)
            m_res = cur.fetchone()
            if m_res:
                data["active_machines"] = int(m_res.get("active_cnt") or 0)
                data["breakdown_count"] = int(m_res.get("bd_cnt") or 0)

            # 2. แรงดันตกวันนี้
            cur.execute(f"""
                SELECT SUM(total_drop) AS drops 
                FROM boiler_pressure_records  
                WHERE record_date = CURDATE() {b_sql} AND is_deleted = 0
            """, b_params)
            drop_res = cur.fetchone()
            if drop_res and drop_res.get("drops"):
                data["boiler_drop"] = int(drop_res["drops"])

            # 3. ข้อมูลเชื้อเพลิงและชั่วโมงทำงานรวมเดือนนี้
            cur.execute(f"""
                SELECT SUM(fuel_liters) AS tot_fuel, SUM(working_hours) AS tot_hrs 
                FROM fuel_records 
                WHERE MONTH(record_date) = MONTH(CURDATE()) 
                  AND YEAR(record_date) = YEAR(CURDATE())
                  {b_sql}
                  AND is_deleted = 0
            """, b_params)
            cur_res = cur.fetchone()
            if cur_res:
                data["cur_fuel"] = float(cur_res.get("tot_fuel") or 0.0)
                data["cur_hrs"] = float(cur_res.get("tot_hrs") or 0.0)
                data["cur_rate"] = data["cur_fuel"] / data["cur_hrs"] if data["cur_hrs"] > 0 else 0.0

            # 4. ข้อมูลเชื้อเพลิงและชั่วโมงทำงานรวมเดือนที่แล้ว
            cur.execute(f"""
                SELECT SUM(fuel_liters) AS tot_fuel, SUM(working_hours) AS tot_hrs 
                FROM fuel_records 
                WHERE MONTH(record_date) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) 
                  AND YEAR(record_date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
                  {b_sql}
                  AND is_deleted = 0
            """, b_params)
            prev_res = cur.fetchone()
            if prev_res:
                data["prev_fuel"] = float(prev_res.get("tot_fuel") or 0.0)
                data["prev_hrs"] = float(prev_res.get("tot_hrs") or 0.0)
                data["prev_rate"] = data["prev_fuel"] / data["prev_hrs"] if data["prev_hrs"] > 0 else 0.0

            # เตรียมโครงสร้างวันที่ย้อนหลัง 7 วัน
            today = pd.Timestamp.today().normalize()
            df_template = pd.DataFrame({"วันที่": pd.date_range(end=today, periods=7)})

            # 5. กราฟและยอดรวมเชื้อเพลิง 7 วันล่าสุด
            cur.execute(f"""
                SELECT DATE(record_date) AS log_date, SUM(fuel_liters) AS total_liters
                FROM fuel_records  
                WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) 
                  AND record_date <= CURDATE() 
                  {b_sql}
                  AND is_deleted = 0
                GROUP BY DATE(record_date) ORDER BY DATE(record_date) ASC
            """, b_params)
            fuel_rows = cur.fetchall()
            df_fuel_full = _build_7day_series(df_template, fuel_rows, "total_liters", "ปริมาณเชื้อเพลิง (ลิตร)")
            data["fuel_chart_df"] = df_fuel_full
            data["fuel_usage"] = round(float(df_fuel_full["ปริมาณเชื้อเพลิง (ลิตร)"].sum()), 2)

            # 6. กราฟแรงดันไอน้ำตก 7 วันล่าสุด
            cur.execute(f"""
                SELECT DATE(record_date) AS log_date, SUM(total_drop) AS total_drops
                FROM boiler_pressure_records 
                WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) 
                  AND record_date <= CURDATE() 
                  {b_sql}
                  AND is_deleted = 0
                GROUP BY DATE(record_date) ORDER BY DATE(record_date) ASC
            """, b_params)
            pres_rows = cur.fetchall()
            data["pressure_chart_df"] = _build_7day_series(df_template, pres_rows, "total_drops", "จำนวนครั้งที่ตก")

    except Exception as e:
        st.error(f"⚠️ พบข้อผิดพลาดในการดึงข้อมูลแสดงกราฟ: {e}")
    finally:
        if conn:
            conn.close()
    return data


# =============================================================================
# 📈 3. ฟังก์ชันกลางสำหรับวาดกราฟแนวโน้ม 7 วัน (Altair Chart Builder)
# =============================================================================
def render_7day_trend_chart(df, y_col, color_hex, tooltip_unit, empty_message):
    """วาดกราฟเส้นพร้อมพื้นที่ใต้กราฟและจุด Tooltip สำหรับหน้า Dashboard"""
    if df.empty:
        st.info(empty_message)
        return

    df_plot = df.reset_index()
    area = alt.Chart(df_plot).mark_area(interpolate="monotone", color=color_hex, opacity=0.15).encode(
        x=alt.X("วันที่:T", axis=alt.Axis(labelAngle=-45, grid=False, title=None, format="%d/%m/%Y")),
        y=alt.Y(f"{y_col}:Q", axis=alt.Axis(grid=True, gridColor="#E8E3DD", title=None))
    )
    line = alt.Chart(df_plot).mark_line(interpolate="monotone", color=color_hex, strokeWidth=3).encode(
        x="วันที่:T",
        y=f"{y_col}:Q"
    )
    points = alt.Chart(df_plot).mark_circle(size=80, color="#FCFBF8", stroke=color_hex, strokeWidth=2).encode(
        x="วันที่:T",
        y=f"{y_col}:Q",
        tooltip=[
            alt.Tooltip("วันที่:T", title="วันที่", format="%d/%m/%Y"),
            alt.Tooltip(f"{y_col}:Q", title=tooltip_unit)
        ]
    )
    chart = (
        (area + line + points)
        .configure(font='"TH Sarabun PSK", Sarabun, sans-serif')
        .configure_view(strokeWidth=0)
        .configure_axis(domain=False, tickColor="transparent", labelColor="#666666", labelFontSize=14)
    )
    st.altair_chart(chart, use_container_width=True)


# =============================================================================
# 🎯 4. ฟังก์ชันหลักสำหรับวาดหน้าจอ Dashboard
# =============================================================================
def render_dashboard(current_branch_id, disp_name, role_th, current_branch, user_position, current_access, access_color, access_desc):
    st.markdown("<h1 class='dash-title' style='color: #333333; font-weight: 800;'>หน้าหลัก (Dashboard)</h1>", unsafe_allow_html=True)

    raw_role = str(st.session_state.get("role_tab", "user")).strip().lower()
    user_allowed_branches = st.session_state.get("allowed_branches", [str(current_branch_id)])

    target_branch_id = current_branch_id
    target_branch_name = current_branch

    # ตัวเลือกสลับมุมมองสาขาสำหรับ Admin หรือผู้ที่มีสิทธิ์หลายสาขา
    if raw_role == "admin" or len(user_allowed_branches) > 1:
        if raw_role == "admin":
            branch_options = ["🌐 รวมทุกสาขาในเครือ (ภาพรวมบริษัท)"] + list(branch_dict.keys())
        else:
            available_user_branches = [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]
            branch_options = ["🏢 รวมเฉพาะสาขาที่มีสิทธิ์"] + available_user_branches

        col_sel1, _ = st.columns([1.6, 2.4])
        with col_sel1:
            sel_b_label = st.selectbox(
                "🏢 เลือกมุมมองสาขาที่ต้องการดูแดชบอร์ด:",
                options=branch_options,
                key="dash_branch_view",
                help="สลับดูข้อมูลสถิติและกราฟของเฉพาะสาขาที่เลือก หรือดูภาพรวมทุกสาขาที่มีสิทธิ์เข้าถึง"
            )
            if sel_b_label in ["🌐 รวมทุกสาขาในเครือ (ภาพรวมบริษัท)", "🏢 รวมเฉพาะสาขาที่มีสิทธิ์"]:
                target_branch_id = "ALL"
                target_branch_name = sel_b_label
            else:
                target_branch_id = branch_dict[sel_b_label]
                target_branch_name = sel_b_label

    db_data = get_dashboard_data(
        branch_filter=target_branch_id,
        allowed_branches=user_allowed_branches if raw_role != "admin" else None
    )

    # 1. การ์ดต้อนรับผู้ใช้งาน
    welcome_html = f"""
    <div style="background-color: #FCFBF8; border-radius: 12px; padding: 20px; margin-bottom: 25px; border: 1px solid #D6D3D1; border-left: 6px solid #D97706; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.08);">
        <h3 class='welcome-title' style="color: #D97706; margin-top: 0; font-weight: 800; margin-bottom: 8px;">😊 ยินดีต้อนรับเข้าสู่ระบบ </h3>
        <p class='welcome-desc' style="color: #666666; margin-bottom: 15px;">สวัสดีคุณ <strong style="color: #333333;">{disp_name}</strong></p>
        <div class='welcome-details' style="color: #333333; line-height: 1.8;">
            <div><span style="font-weight: 600; color: #64748B;">👤 กลุ่มสิทธิ์:</span> {role_th}</div>
            <div><span style="font-weight: 600; color: #64748B;">🏢 สังกัดประจำตัว:</span> {current_branch}</div>
            <div><span style="font-weight: 600; color: #64748B;">💼 ตำแหน่ง:</span> {user_position}</div>
            <div style="margin-top: 4px;"><span style="font-weight: 600; color: #64748B;">👑 ระดับสิทธิ์:</span> {current_access} — <strong style="color: {access_color};">{access_desc}</strong></div>
        </div>
    </div>
    """
    st.markdown(welcome_html, unsafe_allow_html=True)

    # 2. เตรียมข้อมูลตัวเลขและป้ายสถานะสำหรับการ์ด KPI
    val_fuel = f"{db_data.get('cur_fuel', 0):,.2f}"
    pill_fuel = get_diff_pill(db_data.get("cur_fuel", 0) - db_data.get("prev_fuel", 0), "ลิตร", invert_color=True, metric_name="ปริมาณน้ำมันรวม")

    val_hrs = f"{db_data.get('cur_hrs', 0):,.2f}"
    pill_hrs = get_diff_pill(db_data.get("cur_hrs", 0) - db_data.get("prev_hrs", 0), "ชม.", invert_color=False, metric_name="ชั่วโมงทำงานรวม")

    val_rate = f"{db_data.get('cur_rate', 0):,.2f}"
    pill_rate = get_diff_pill(db_data.get("cur_rate", 0) - db_data.get("prev_rate", 0), "ล/ชม.", invert_color=True, metric_name="อัตราสิ้นเปลืองเฉลี่ย")

    val_active = db_data.get("active_machines", 0)
    pill_active = get_badge_pill("อัปเดตวันนี้", "#E0F2FE", "#0284C7")

    val_bd = db_data.get("breakdown_count", 0)
    pill_bd = get_badge_pill("🔴 ค้างซ่อม", "#FEE2E2", "#DC2626") if val_bd > 0 else get_badge_pill("✅ ปกติ", "#D1FAE5", "#059669")

    val_f7 = f"{db_data.get('fuel_usage', 0.0):,.1f}"
    pill_f7 = get_badge_pill("📅 7 วันล่าสุด", "#F1F5F9", "#475569")

    val_drop = db_data.get("boiler_drop", 0)
    pill_drop = get_badge_pill("⚠️ แจ้งเตือน", "#FEF3C7", "#D97706") if val_drop > 0 else get_badge_pill("✅ ปกติ", "#D1FAE5", "#059669")

    # 3. การ์ดแสดงผลสถิติ (KPI Metrics)
    custom_metric_html = f"""
<div style="background-color: #FCFBF8; padding: 25px; border-radius: 12px; margin-bottom: 25px; border: 1px solid #D6D3D1; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.05); font-family: 'Sarabun', sans-serif;">
    <div style="margin-bottom: 15px;">
        <div style="color: #D97706; font-size: 18px; font-weight: bold; margin-bottom: 4px;">📊 ภาพรวมการใช้เชื้อเพลิงประจำเดือน: <span style="color:#0F172A;">{target_branch_name}</span></div>
        <div style="color: #64748B; font-size: 13px;">
            💡 <i>ป้ายผลต่างเทียบเดือนที่แล้ว (<b>↑ เพิ่มขึ้น</b> / <b>↓ ลดลง</b>) — <b>น้ำมัน & อัตราสิ้นเปลือง:</b> ↑ เพิ่มขึ้น = สีแดง, ↓ ลดลง = สีเขียว | <b>ชั่วโมงทำงาน:</b> ↑ เพิ่มขึ้น = สีเขียว, ↓ ลดลง = สีแดง</i>
        </div>
    </div>
    <div style="display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between; margin-bottom: 25px;">
        <div style="flex: 1; min-width: 180px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">ปริมาณน้ำมันรวม (เดือนนี้)</div>
            <div style="color: #333333; font-size: 36px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_fuel} <span style="font-size: 20px; font-weight: normal; color: #666666;">ลิตร</span></div>
            {pill_fuel}
        </div>
        <div style="flex: 1; min-width: 180px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">ชั่วโมงทำงานรวม (เดือนนี้)</div>
            <div style="color: #333333; font-size: 36px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_hrs} <span style="font-size: 20px; font-weight: normal; color: #666666;">ชม.</span></div>
            {pill_hrs}
        </div>
        <div style="flex: 1; min-width: 180px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">อัตราสิ้นเปลืองเฉลี่ย (เดือนนี้)</div>
            <div style="color: #333333; font-size: 36px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_rate} <span style="font-size: 20px; font-weight: normal; color: #666666;">ล/ชม.</span></div>
            {pill_rate}
        </div>
    </div>

    <hr style="border: none; border-top: 1px dashed #D6D3D1; margin: 0 0 20px 0;">

    <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; margin-bottom: 15px;">
        <div style="color: #0F172A; font-size: 18px; font-weight: bold;">⚡ สถานะปฏิบัติงาน (ข้อมูลอัปเดตล่าสุด)</div>
        <div style="color: #64748B; font-size: 13px;">🕒 <i>สรุปยอดการบันทึกข้อมูลของวันนี้และ 7 วันย้อนหลัง</i></div>
    </div>
    <div style="display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between;">
        <div style="flex: 1; min-width: 150px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">⚙️ เครื่องจักรทำงาน (วันนี้)</div>
            <div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_active} <span style="font-size: 16px; font-weight: normal; color: #666666;">เครื่อง</span></div>
            {pill_active}
        </div>
        <div style="flex: 1; min-width: 150px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">⚠️ แจ้งซ่อม (เบรกดาวน์วันนี้)</div>
            <div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_bd} <span style="font-size: 16px; font-weight: normal; color: #666666;">รายการ</span></div>
            {pill_bd}
        </div>
        <div style="flex: 1; min-width: 150px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">🚚 เชื้อเพลิงสะสม 7 วัน</div>
            <div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_f7} <span style="font-size: 16px; font-weight: normal; color: #666666;">ลิตร</span></div>
            {pill_f7}
        </div>
        <div style="flex: 1; min-width: 150px;">
            <div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">💨 แรงดันตก (วันนี้)</div>
            <div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_drop} <span style="font-size: 16px; font-weight: normal; color: #666666;">ครั้ง</span></div>
            {pill_drop}
        </div>
    </div>
</div>
"""
    st.markdown(custom_metric_html, unsafe_allow_html=True)

    # 4. ส่วนแสดงกราฟแนวโน้ม 7 วัน
    c_chart1, c_chart2 = st.columns(2)

    with c_chart1:
        st.markdown(f"<h4 style='color: #333333; font-size: 20px; font-weight:bold; margin-bottom: 2px;'>📉 ปริมาณเชื้อเพลิง (7 วัน) - {target_branch_name}</h4>", unsafe_allow_html=True)
        st.caption("ℹ️ *นำเมาส์ชี้ที่จุดวงกลมบนเส้นกราฟเพื่อดูปริมาณการใช้น้ำมันรายวัน*")
        with st.container(border=True):
            render_7day_trend_chart(
                df=db_data["fuel_chart_df"],
                y_col="ปริมาณเชื้อเพลิง (ลิตร)",
                color_hex="#6366F1",
                tooltip_unit="ลิตร",
                empty_message="📊 ยังไม่มีข้อมูลปริมาณเชื้อเพลิงใน 7 วันล่าสุด"
            )

    with c_chart2:
        st.markdown(f"<h4 style='color: #333333; font-size: 20px; font-weight:bold; margin-bottom: 2px;'>🚀 แรงดันไอน้ำตกสะสม (7 วัน) - {target_branch_name}</h4>", unsafe_allow_html=True)
        st.caption("ℹ️ *นำเมาส์ชี้ที่จุดวงกลมบนเส้นกราฟเพื่อดูจำนวนครั้งที่แรงดันไอน้ำตกรายวัน*")
        with st.container(border=True):
            render_7day_trend_chart(
                df=db_data["pressure_chart_df"],
                y_col="จำนวนครั้งที่ตก",
                color_hex="#F59E0B",
                tooltip_unit="ครั้ง",
                empty_message="🔥 ยังไม่มีการบันทึกแรงดันไอน้ำตกใน 7 วันล่าสุด"
            )