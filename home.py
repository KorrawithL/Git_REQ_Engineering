import streamlit as st
import pandas as pd
import altair as alt
from database import get_db_connection

# =============================================================================
# 🚀 1. ฟังก์ชันดึงข้อมูลจริงทำหน้า Dashboard (ย้ายมาจาก app.py)
# =============================================================================
def get_dashboard_data(user_branch_id):
    data = {
        "active_machines": 0,
        "breakdown_count": 0,
        "fuel_usage": 0.0,
        "boiler_drop": 0,
        "fuel_chart_df": pd.DataFrame(),
        "pressure_chart_df": pd.DataFrame()
    }
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # เครื่องจักรทำงาน
            cur.execute("""
                SELECT COUNT(id) AS count FROM machine_trans 
                WHERE record_date = CURDATE() AND branch_id = %s AND status = 'active'
            """, (user_branch_id,))
            res = cur.fetchone()
            if res and res['count']: data["active_machines"] = res['count']

            # แจ้งซ่อม
            cur.execute("""
                SELECT COUNT(id) AS count FROM machine_trans 
                WHERE record_date = CURDATE() AND breakdown_hours > 0 AND branch_id = %s AND status = 'active'
            """, (user_branch_id,))
            res = cur.fetchone()
            if res and res['count']: data["breakdown_count"] = res['count']

            # เชื้อเพลิง 7 วัน
            cur.execute("""
                SELECT SUM(fuel_liters) AS total FROM fuel_records  
                WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) AND record_date <= CURDATE() AND branch_id = %s 
            """, (user_branch_id,))
            res = cur.fetchone()
            if res and res['total']: data["fuel_usage"] = round(float(res['total']), 2)

            # แรงดันตก
            cur.execute("""
                SELECT SUM(total_drop) AS drops FROM boiler_pressure_records  
                WHERE record_date = CURDATE() AND branch_id = %s 
            """, (user_branch_id,))
            res = cur.fetchone()
            if res and res['drops']: data["boiler_drop"] = int(res['drops'])

            # กราฟเชื้อเพลิง
            cur.execute("""
                SELECT DATE(record_date) AS log_date, SUM(fuel_liters) AS total_liters
                FROM fuel_records  
                WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) AND record_date <= CURDATE() AND branch_id = %s 
                GROUP BY DATE(record_date) ORDER BY DATE(record_date) ASC
            """, (user_branch_id,))
            fuel_rows = cur.fetchall()
            if fuel_rows:
                df_fuel = pd.DataFrame(fuel_rows)
                df_fuel['วันที่'] = pd.to_datetime(df_fuel['log_date']).dt.strftime('%d/%m/%Y')
                df_fuel['ปริมาณเชื้อเพลิง (ลิตร)'] = df_fuel['total_liters'].astype(float)
                df_fuel = df_fuel[['วันที่', 'ปริมาณเชื้อเพลิง (ลิตร)']].set_index('วันที่')
                data["fuel_chart_df"] = df_fuel

            # กราฟแรงดัน
            cur.execute("""
                SELECT DATE(record_date) AS log_date, SUM(total_drop) AS total_drops
                FROM boiler_pressure_records 
                WHERE record_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) AND record_date <= CURDATE() AND branch_id = %s 
                GROUP BY DATE(record_date) ORDER BY DATE(record_date) ASC
            """, (user_branch_id,))
            pres_rows = cur.fetchall()
            if pres_rows:
                df_pres = pd.DataFrame(pres_rows)
                df_pres['วันที่'] = pd.to_datetime(df_pres['log_date']).dt.strftime('%d/%m/%Y')
                df_pres['จำนวนครั้งที่ตก'] = df_pres['total_drops'].astype(float) 
                df_pres = df_pres[['วันที่', 'จำนวนครั้งที่ตก']].set_index('วันที่')
                data["pressure_chart_df"] = df_pres

    except Exception as e:
        st.error(f"⚠️ พบข้อผิดพลาดในการดึงข้อมูลแสดงกราฟ: {e}")
    finally:
        if conn: conn.close()
    return data

# =============================================================================
# 🎯 2. ฟังก์ชันวาดหน้าจอ Dashboard
# =============================================================================
def render_dashboard(current_branch_id, disp_name, role_th, current_branch, user_position, current_access, access_color, access_desc):
    db_data = get_dashboard_data(current_branch_id)
    
    st.markdown(f"<h1 class='dash-title' style='color: #333333; font-weight: 800;'>หน้าหลัก (Dashboard)</h1>", unsafe_allow_html=True)
    
    welcome_html = f"""
    <div style="background-color: #FCFBF8; border-radius: 12px; padding: 20px; margin-bottom: 25px; border: 1px solid #D6D3D1; border-left: 6px solid #D97706; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.08);">
        <h3 class='welcome-title' style="color: #D97706; margin-top: 0; font-weight: 800; margin-bottom: 8px;">😊 ยินดีต้อนรับเข้าสู่ระบบ</h3>
        <p class='welcome-desc' style="color: #666666; margin-bottom: 15px;">สวัสดีคุณ <strong style="color: #333333;">{disp_name}</strong></p>
        <div class='welcome-details' style="color: #333333; line-height: 1.8;">
            <div><span style="font-weight: 600; color: #64748B;">👤 กลุ่มสิทธิ์:</span> {role_th}</div>
            <div><span style="font-weight: 600; color: #64748B;">🏢 สาขา:</span> {current_branch}</div>
            <div><span style="font-weight: 600; color: #64748B;">💼 ตำแหน่ง:</span> {user_position}</div>
            <div style="margin-top: 4px;"><span style="font-weight: 600; color: #64748B;">👑 ระดับสิทธิ์:</span> {current_access} — <strong style="color: {access_color};">{access_desc}</strong></div>
        </div>
    </div>
    """
    st.markdown(welcome_html, unsafe_allow_html=True)
    
    fuel_display = f"{db_data['fuel_usage']:,.1f}" if db_data['fuel_usage'] > 0 else "0.0"

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True): st.metric("⚙️ เครื่องจักรทำงาน (วันนี้)", f"{db_data['active_machines']} เครื่อง")
    with col2:
        with st.container(border=True): st.metric("⚠️ แจ้งซ่อม (ค้างซ่อม)", f"{db_data['breakdown_count']} รายการ")
    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True): st.metric("🚚 เชื้อเพลิง 7 วัน (ลิตร)", fuel_display)
    with col4:
        with st.container(border=True): st.metric("💨 แรงดันตก (วันนี้)", f"{db_data['boiler_drop']} ครั้ง")

    st.markdown("<br>", unsafe_allow_html=True)

    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        st.markdown(f"<h4 style='color: #333333; font-size: 20px; font-weight:bold; margin-bottom: 10px;'>📉 ปริมาณเชื้อเพลิง (7 วัน)</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            if not db_data["fuel_chart_df"].empty:
                df_f = db_data["fuel_chart_df"].reset_index()
                area_f = alt.Chart(df_f).mark_area(interpolate='monotone', color='#6366F1', opacity=0.15).encode(x=alt.X('วันที่:O', axis=alt.Axis(labelAngle=-45, grid=False, title=None)), y=alt.Y('ปริมาณเชื้อเพลิง (ลิตร):Q', axis=alt.Axis(grid=True, gridColor='#E8E3DD', title=None)))
                line_f = alt.Chart(df_f).mark_line(interpolate='monotone', color='#6366F1', strokeWidth=3).encode(x='วันที่:O', y='ปริมาณเชื้อเพลิง (ลิตร):Q')
                points_f = alt.Chart(df_f).mark_circle(size=80, color='#FCFBF8', stroke='#6366F1', strokeWidth=2).encode(x='วันที่:O', y='ปริมาณเชื้อเพลิง (ลิตร):Q', tooltip=[alt.Tooltip('วันที่', title='วันที่'), alt.Tooltip('ปริมาณเชื้อเพลิง (ลิตร)', title='ลิตร')])
                chart_f = (area_f + line_f + points_f).configure(font='"TH Sarabun PSK", Sarabun, sans-serif').configure_view(strokeWidth=0).configure_axis(domain=False, tickColor='transparent', labelColor='#666666', labelFontSize=14)
                st.altair_chart(chart_f, use_container_width=True)
            else:
                st.info("📊 ยังไม่มีข้อมูลปริมาณเชื้อเพลิงใน 7 วันล่าสุด")
            
    with c_chart2:
        st.markdown(f"<h4 style='color: #333333; font-size: 20px; font-weight:bold; margin-bottom: 10px;'>🚀 แรงดันไอน้ำตกสะสม (7 วัน)</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            if not db_data["pressure_chart_df"].empty:
                df_p = db_data["pressure_chart_df"].reset_index()
                area_p = alt.Chart(df_p).mark_area(interpolate='monotone', color='#F59E0B', opacity=0.15).encode(x=alt.X('วันที่:O', axis=alt.Axis(labelAngle=-45, grid=False, title=None)), y=alt.Y('จำนวนครั้งที่ตก:Q', axis=alt.Axis(grid=True, gridColor='#E8E3DD', title=None)))
                line_p = alt.Chart(df_p).mark_line(interpolate='monotone', color='#F59E0B', strokeWidth=3).encode(x='วันที่:O', y='จำนวนครั้งที่ตก:Q')
                points_p = alt.Chart(df_p).mark_circle(size=80, color='#FCFBF8', stroke='#F59E0B', strokeWidth=2).encode(x='วันที่:O', y='จำนวนครั้งที่ตก:Q', tooltip=[alt.Tooltip('วันที่', title='วันที่'), alt.Tooltip('จำนวนครั้งที่ตก', title='ครั้ง')])
                chart_p = (area_p + line_p + points_p).configure(font='"TH Sarabun PSK", Sarabun, sans-serif').configure_view(strokeWidth=0).configure_axis(domain=False, tickColor='transparent', labelColor='#666666', labelFontSize=14)
                st.altair_chart(chart_p, use_container_width=True)
            else:
                st.info("🔥 ยังไม่มีการบันทึกแรงดันไอน้ำตกใน 7 วันล่าสุด")