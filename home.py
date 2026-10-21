import streamlit as st
import pandas as pd
import altair as alt
from database import get_db_connection
from config import branch_dict  # 🌟 นำเข้ารายชื่อสาขา

# =============================================================================
# 🚀 1. ฟังก์ชันดึงข้อมูลจริงทำหน้า Dashboard (รองรับเลือกสาขาเดียว หรือ รวมทุกสาขา)
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
    
    # 🌟 สร้างเงื่อนไขการกรองสาขาแบบไดนามิก
    if branch_filter and branch_filter != "ALL":
        b_sql = "AND branch_id = %s"
        b_params = (int(branch_filter),)
    elif allowed_branches and len(allowed_branches) > 0:
        valid_bids = [int(x) for x in allowed_branches if str(x).isdigit()]
        placeholders = ', '.join(['%s'] * len(valid_bids))
        b_sql = f"AND branch_id IN ({placeholders})"
        b_params = tuple(valid_bids)
    else:
        b_sql = ""
        b_params = ()

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. เครื่องจักรทำงานวันนี้
            cur.execute(f"""
                SELECT COUNT(id) AS count FROM machine_trans 
                WHERE record_date = CURDATE() {b_sql} AND is_deleted = 0
            """, b_params)
            res = cur.fetchone()
            if res and res['count']: data["active_machines"] = res['count']

            # 2. แจ้งซ่อม/เบรกดาวน์วันนี้
            cur.execute(f"""
                SELECT COUNT(id) AS count FROM machine_trans 
                WHERE record_date = CURDATE() AND breakdown_hours > 0 {b_sql} AND is_deleted = 0
            """, b_params)
            res = cur.fetchone()
            if res and res['count']: data["breakdown_count"] = res['count']

            # 3. เชื้อเพลิง 7 วันล่าสุด
            cur.execute(f"""
                SELECT SUM(fuel_liters) AS total FROM fuel_records  
                WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) 
                  AND record_date <= CURDATE() 
                  {b_sql}
                  AND is_deleted = 0
            """, b_params)
            res = cur.fetchone()
            if res and res['total']: data["fuel_usage"] = round(float(res['total']), 2)

            # 4. แรงดันตกวันนี้
            cur.execute(f"""
                SELECT SUM(total_drop) AS drops FROM boiler_pressure_records  
                WHERE record_date = CURDATE() {b_sql} AND is_deleted = 0
            """, b_params)
            res = cur.fetchone()
            if res and res['drops']: data["boiler_drop"] = int(res['drops'])

            # ==========================================
            # 🌟 ข้อมูลเปรียบเทียบ เดือนนี้ vs เดือนที่แล้ว
            # ==========================================
            # 5. ข้อมูลรวมเดือนนี้
            cur.execute(f"""
                SELECT SUM(fuel_liters) as tot_fuel, SUM(working_hours) as tot_hrs 
                FROM fuel_records 
                WHERE MONTH(record_date) = MONTH(CURDATE()) 
                  AND YEAR(record_date) = YEAR(CURDATE())
                  {b_sql}
                  AND is_deleted = 0
            """, b_params)
            cur_res = cur.fetchone()
            if cur_res:
                data['cur_fuel'] = float(cur_res['tot_fuel'] or 0.0)
                data['cur_hrs'] = float(cur_res['tot_hrs'] or 0.0)
                data['cur_rate'] = data['cur_fuel'] / data['cur_hrs'] if data['cur_hrs'] > 0 else 0.0

            # 6. ข้อมูลรวมเดือนที่แล้ว
            cur.execute(f"""
                SELECT SUM(fuel_liters) as tot_fuel, SUM(working_hours) as tot_hrs 
                FROM fuel_records 
                WHERE MONTH(record_date) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) 
                  AND YEAR(record_date) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
                  {b_sql}
                  AND is_deleted = 0
            """, b_params)
            prev_res = cur.fetchone()
            if prev_res:
                data['prev_fuel'] = float(prev_res['tot_fuel'] or 0.0)
                data['prev_hrs'] = float(prev_res['tot_hrs'] or 0.0)
                data['prev_rate'] = data['prev_fuel'] / data['prev_hrs'] if data['prev_hrs'] > 0 else 0.0

            # ==========================================
            # 🌟 สร้างโครงสร้างปฏิทิน 7 วันย้อนหลัง
            # ==========================================
            today = pd.Timestamp.today().normalize()
            date_range = pd.date_range(end=today, periods=7)
            df_template = pd.DataFrame({'วันที่': date_range})

            # ------------------------------------------
            # 📉 กราฟเชื้อเพลิง (7 วัน)
            # ------------------------------------------
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
            
            df_fuel_full = df_template.copy()
            if fuel_rows:
                df_f = pd.DataFrame(fuel_rows)
                df_f['วันที่'] = pd.to_datetime(df_f['log_date'])
                df_f['ปริมาณเชื้อเพลิง (ลิตร)'] = df_f['total_liters'].astype(float)
                df_fuel_full = pd.merge(df_fuel_full, df_f[['วันที่', 'ปริมาณเชื้อเพลิง (ลิตร)']], on='วันที่', how='left')
            else:
                df_fuel_full['ปริมาณเชื้อเพลิง (ลิตร)'] = 0.0
                
            df_fuel_full['ปริมาณเชื้อเพลิง (ลิตร)'] = df_fuel_full['ปริมาณเชื้อเพลิง (ลิตร)'].fillna(0.0)
            data["fuel_chart_df"] = df_fuel_full

            # ------------------------------------------
            # 🚀 กราฟแรงดันตก (7 วัน)
            # ------------------------------------------
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
            
            df_pres_full = df_template.copy()
            if pres_rows:
                df_p = pd.DataFrame(pres_rows)
                df_p['วันที่'] = pd.to_datetime(df_p['log_date'])
                df_p['จำนวนครั้งที่ตก'] = df_p['total_drops'].astype(float)
                df_pres_full = pd.merge(df_pres_full, df_p[['วันที่', 'จำนวนครั้งที่ตก']], on='วันที่', how='left')
            else:
                df_pres_full['จำนวนครั้งที่ตก'] = 0.0
                
            df_pres_full['จำนวนครั้งที่ตก'] = df_pres_full['จำนวนครั้งที่ตก'].fillna(0.0)
            data["pressure_chart_df"] = df_pres_full

    except Exception as e:
        st.error(f"⚠️ พบข้อผิดพลาดในการดึงข้อมูลแสดงกราฟ: {e}")
    finally:
        if conn: conn.close()
    return data

# =============================================================================
# 🎯 2. ฟังก์ชันวาดหน้าจอ Dashboard
# =============================================================================
def render_dashboard(current_branch_id, disp_name, role_th, current_branch, user_position, current_access, access_color, access_desc):
    st.markdown("<h1 class='dash-title' style='color: #333333; font-weight: 800;'>หน้าหลัก (Dashboard)</h1>", unsafe_allow_html=True)

    # 🌟 ตรวจสอบสิทธิ์เพื่อสร้างตัวเลือกสลับสาขา
    raw_role = str(st.session_state.get('role_tab', 'user')).strip().lower()
    user_allowed_branches = st.session_state.get('allowed_branches', [str(current_branch_id)])

    target_branch_id = current_branch_id
    target_branch_name = current_branch

    # ถ้าเป็น Admin หรือ User ที่มีสิทธิ์มากกว่า 1 สาขา จะมี Dropdown ให้เลือก
    if raw_role == "admin" or len(user_allowed_branches) > 1:
        if raw_role == "admin":
            branch_options = ["🌐 รวมทุกสาขาในเครือ (ภาพรวมบริษัท)"] + list(branch_dict.keys())
        else:
            available_user_branches = [k for k, v in branch_dict.items() if str(v) in user_allowed_branches]
            branch_options = ["🏢 รวมเฉพาะสาขาที่มีสิทธิ์"] + available_user_branches

        col_sel1, col_sel2 = st.columns([1.6, 2.4])
        with col_sel1:
            sel_b_label = st.selectbox("🏢 เลือกมุมมองสาขาที่ต้องการดูแดชบอร์ด:", options=branch_options, key="dash_branch_view")
            
            if sel_b_label in ["🌐 รวมทุกสาขาในเครือ (ภาพรวมบริษัท)", "🏢 รวมเฉพาะสาขาที่มีสิทธิ์"]:
                target_branch_id = "ALL"
                target_branch_name = sel_b_label
            else:
                target_branch_id = branch_dict[sel_b_label]
                target_branch_name = sel_b_label

    # ดึงข้อมูลตามสาขาที่เลือก
    db_data = get_dashboard_data(
        branch_filter=target_branch_id,
        allowed_branches=user_allowed_branches if raw_role != "admin" else None
    )

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

    # คำนวณส่วนต่าง (Diff) สำหรับ 3 หัวข้อรายเดือน
    diff_fuel = db_data.get('cur_fuel', 0) - db_data.get('prev_fuel', 0)
    diff_hrs = db_data.get('cur_hrs', 0) - db_data.get('prev_hrs', 0)
    diff_rate = db_data.get('cur_rate', 0) - db_data.get('prev_rate', 0)

    def get_diff_pill(diff, unit, invert_color=False):
        if abs(diff) < 0.01:
            return f'<span style="background-color: #F1F5F9; color: #475569; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">- 0 {unit}</span>'
        is_pos = diff > 0
        arrow = "↑" if is_pos else "↓"
        if (is_pos and not invert_color) or (not is_pos and invert_color):
            bg, text = "#D1FAE5", "#059669" # สีเขียว
        else:
            bg, text = "#FEE2E2", "#DC2626" # สีแดง
        return f'<span style="background-color: {bg}; color: {text}; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">{arrow} {abs(diff):,.2f} {unit}</span>'

    val_fuel = f"{db_data.get('cur_fuel', 0):,.2f}"
    pill_fuel = get_diff_pill(diff_fuel, "ลิตร", invert_color=True)

    val_hrs = f"{db_data.get('cur_hrs', 0):,.2f}"
    pill_hrs = get_diff_pill(diff_hrs, "ชม.", invert_color=False)

    val_rate = f"{db_data.get('cur_rate', 0):,.2f}"
    pill_rate = get_diff_pill(diff_rate, "ล/ชม.", invert_color=True)

    # ข้อมูล 4 กล่องล่าง
    val_active = db_data.get('active_machines', 0)
    pill_active = '<span style="background-color: #E0F2FE; color: #0284C7; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">อัปเดตวันนี้</span>'

    val_bd = db_data.get('breakdown_count', 0)
    pill_bd = '<span style="background-color: #FEE2E2; color: #DC2626; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">🔴 ค้างซ่อม</span>' if val_bd > 0 else '<span style="background-color: #D1FAE5; color: #059669; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">✅ ปกติ</span>'

    val_f7 = f"{db_data.get('fuel_usage', 0.0):,.1f}"
    pill_f7 = '<span style="background-color: #F1F5F9; color: #475569; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">📅 7 วันล่าสุด</span>'

    val_drop = db_data.get('boiler_drop', 0)
    pill_drop = '<span style="background-color: #FEF3C7; color: #D97706; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">⚠️ แจ้งเตือน</span>' if val_drop > 0 else '<span style="background-color: #D1FAE5; color: #059669; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;">✅ ปกติ</span>'

    custom_metric_html = f"""
<div style="background-color: #FCFBF8; padding: 25px; border-radius: 12px; margin-bottom: 25px; border: 1px solid #D6D3D1; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.05); font-family: 'Sarabun', sans-serif;">

<!-- แถวที่ 1: ภาพรวมรายเดือน -->
<div style="color: #D97706; font-size: 18px; font-weight: bold; margin-bottom: 15px;">📊 ภาพรวมการใช้เชื้อเพลิงประจำเดือน: <span style="color:#0F172A;">{target_branch_name}</span></div>
<div style="display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between; margin-bottom: 25px;">
<div style="flex: 1; min-width: 180px;">
<div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">ปริมาณน้ำมันรวม</div>
<div style="color: #333333; font-size: 36px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_fuel} <span style="font-size: 20px; font-weight: normal; color: #666666;">ลิตร</span></div>
{pill_fuel}
</div>
<div style="flex: 1; min-width: 180px;">
<div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">ชั่วโมงทำงานรวม</div>
<div style="color: #333333; font-size: 36px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_hrs} <span style="font-size: 20px; font-weight: normal; color: #666666;">ชม.</span></div>
{pill_hrs}
</div>
<div style="flex: 1; min-width: 180px;">
<div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">อัตราสิ้นเปลืองเฉลี่ย</div>
<div style="color: #333333; font-size: 36px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_rate} <span style="font-size: 20px; font-weight: normal; color: #666666;">ล/ชม.</span></div>
{pill_rate}
</div>
</div>

<hr style="border: none; border-top: 1px dashed #D6D3D1; margin: 0 0 20px 0;">

<!-- แถวที่ 2: ข้อมูลอัปเดตล่าสุด -->
<div style="color: #0F172A; font-size: 18px; font-weight: bold; margin-bottom: 15px;">⚡ สถานะปฏิบัติงาน (ข้อมูลอัปเดตล่าสุด)</div>
<div style="display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between;">
<div style="flex: 1; min-width: 150px;">
<div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">⚙️ เครื่องจักรทำงาน (วันนี้)</div>
<div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_active} <span style="font-size: 16px; font-weight: normal; color: #666666;">เครื่อง</span></div>
{pill_active}
</div>
<div style="flex: 1; min-width: 150px;">
<div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">⚠️ แจ้งซ่อม (ค้างซ่อม)</div>
<div style="color: #333333; font-size: 28px; font-weight: bold; margin-bottom: 10px; line-height: 1;">{val_bd} <span style="font-size: 16px; font-weight: normal; color: #666666;">รายการ</span></div>
{pill_bd}
</div>
<div style="flex: 1; min-width: 150px;">
<div style="color: #64748B; font-size: 14px; font-weight: 600; margin-bottom: 8px;">🚚 เชื้อเพลิง 7 วัน</div>
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

    c_chart1, c_chart2 = st.columns(2)
    
    # ---------------- กราฟที่ 1: เชื้อเพลิง ----------------
    with c_chart1:
        st.markdown(f"<h4 style='color: #333333; font-size: 20px; font-weight:bold; margin-bottom: 10px;'>📉 ปริมาณเชื้อเพลิง (7 วัน) - {target_branch_name}</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            if not db_data["fuel_chart_df"].empty:
                df_f = db_data["fuel_chart_df"].reset_index()
                area_f = alt.Chart(df_f).mark_area(interpolate='monotone', color='#6366F1', opacity=0.15).encode(x=alt.X('วันที่:T', axis=alt.Axis(labelAngle=-45, grid=False, title=None, format='%d/%m/%Y')), y=alt.Y('ปริมาณเชื้อเพลิง (ลิตร):Q', axis=alt.Axis(grid=True, gridColor='#E8E3DD', title=None)))
                line_f = alt.Chart(df_f).mark_line(interpolate='monotone', color='#6366F1', strokeWidth=3).encode(x='วันที่:T', y='ปริมาณเชื้อเพลิง (ลิตร):Q')
                points_f = alt.Chart(df_f).mark_circle(size=80, color='#FCFBF8', stroke='#6366F1', strokeWidth=2).encode(x='วันที่:T', y='ปริมาณเชื้อเพลิง (ลิตร):Q', tooltip=[alt.Tooltip('วันที่:T', title='วันที่', format='%d/%m/%Y'), alt.Tooltip('ปริมาณเชื้อเพลิง (ลิตร):Q', title='ลิตร')])
                chart_f = (area_f + line_f + points_f).configure(font='"TH Sarabun PSK", Sarabun, sans-serif').configure_view(strokeWidth=0).configure_axis(domain=False, tickColor='transparent', labelColor='#666666', labelFontSize=14)
                st.altair_chart(chart_f, use_container_width=True)
            else:
                st.info("📊 ยังไม่มีข้อมูลปริมาณเชื้อเพลิงใน 7 วันล่าสุด")
            
    # ---------------- กราฟที่ 2: แรงดันตก ----------------
    with c_chart2:
        st.markdown(f"<h4 style='color: #333333; font-size: 20px; font-weight:bold; margin-bottom: 10px;'>🚀 แรงดันไอน้ำตกสะสม (7 วัน) - {target_branch_name}</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            if not db_data["pressure_chart_df"].empty:
                df_p = db_data["pressure_chart_df"].reset_index()
                area_p = alt.Chart(df_p).mark_area(interpolate='monotone', color='#F59E0B', opacity=0.15).encode(x=alt.X('วันที่:T', axis=alt.Axis(labelAngle=-45, grid=False, title=None, format='%d/%m/%Y')), y=alt.Y('จำนวนครั้งที่ตก:Q', axis=alt.Axis(grid=True, gridColor='#E8E3DD', title=None)))
                line_p = alt.Chart(df_p).mark_line(interpolate='monotone', color='#F59E0B', strokeWidth=3).encode(x='วันที่:T', y='จำนวนครั้งที่ตก:Q')
                points_p = alt.Chart(df_p).mark_circle(size=80, color='#FCFBF8', stroke='#F59E0B', strokeWidth=2).encode(x='วันที่:T', y='จำนวนครั้งที่ตก:Q', tooltip=[alt.Tooltip('วันที่:T', title='วันที่', format='%d/%m/%Y'), alt.Tooltip('จำนวนครั้งที่ตก:Q', title='ครั้ง')])
                chart_p = (area_p + line_p + points_p).configure(font='"TH Sarabun PSK", Sarabun, sans-serif').configure_view(strokeWidth=0).configure_axis(domain=False, tickColor='transparent', labelColor='#666666', labelFontSize=14)
                st.altair_chart(chart_p, use_container_width=True)
            else:
                st.info("🔥 ยังไม่มีการบันทึกแรงดันไอน้ำตกใน 7 วันล่าสุด")