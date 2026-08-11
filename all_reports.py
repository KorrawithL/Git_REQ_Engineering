import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import io
import time
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from database import get_db_connection, log_activity
from config import branch_dict

def render_all_reports_module(user_branch_name):
    # 🎯 1. ตรวจสอบสิทธิ์การใช้งาน
    raw_role = st.session_state.get('role_tab') or st.session_state.get('role') or 'user'
    current_role = str(raw_role).strip().lower()
    allowed_tabs_list = st.session_state.get('allowed_tabs', [])

    # 🏷️ ตั้งชื่อแท็บรายงานสรุปอย่างเป็นทางการ
    all_tabs_config = {
        "1": "⚙️ รายงานสรุปเครื่องจักร & เบรกดาวน์",
        "2": "🚚 รายงานสรุปการใช้เชื้อเพลิงรถ",
        "3": "💨 รายงานสรุปแรงดันไอน้ำ บอยเลอร์",
        "4": "🔥 รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)"
    }

    # จัดสรรแท็บที่จะแสดงผลตามสิทธิ์
    if current_role in ["admin", "manager"]:
        visible_tab_keys = ["1", "2", "3", "4"]
        st.header("📑 รายงานรวมทุกระบบและการจัดการข้อมูล (All Report)")
        st.caption("ศูนย์รวมรายงานสรุป การส่งออกข้อมูล (Export/Print) และเครื่องมือแก้ไข-ลบข้อมูลสำหรับ Admin/Manager")
        st.write("---")
    else:
        visible_tab_keys = [k for k in allowed_tabs_list if k in all_tabs_config]

    if not visible_tab_keys:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.error("## ⏳ รอการอนุมัติสิทธิ์เลือกแท็บงานจากแอดมิน")
        st.info("🔒 บัญชีของคุณได้รับการลงทะเบียนเรียบร้อยแล้ว แต่ในขณะนี้ยังไม่ได้รับสิทธิ์เข้าถึงแท็บรายงานใดๆ กรุณาติดต่อผู้ดูแลระบบเพื่อทำการระบุแท็บงานก่อนครับ")
        return

    # 🎯 2. สร้างแท็บแบบ Dynamic
    tab_labels = [all_tabs_config[k] for k in visible_tab_keys]
    created_tabs = st.tabs(tab_labels)

    report_options = ["ทั้งหมดทุกสาขา"] + list(branch_dict.keys())

    for index, key in enumerate(visible_tab_keys):
        current_tab_ctx = created_tabs[index]

        # =========================================================================
        # ⚙️ TAB 1 REPORT: รายงานสรุปเครื่องจักร & เบรกดาวน์
        # =========================================================================
        if key == "1":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปการทำงานและเบรกดาวน์เครื่องจักร")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t1 = st.date_input("ตั้งแต่วันที่ (Tab 1)", value=pd.to_datetime("today").replace(day=1), key="s_date_t1")
                with col_f2:
                    end_date_t1 = st.date_input("ถึงวันที่ (Tab 1)", value=pd.to_datetime("today"), key="e_date_t1")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t1 = st.selectbox("เลือกสาขา (Tab 1):", options=report_options, key="b_sel_t1")
                        b_id_t1 = "ทั้งหมด" if b_label_t1 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t1]
                        selected_branch_display = b_label_t1 if b_label_t1 != "ทั้งหมดทุกสาขา" else "ทุกสาขา"
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t1 = st.session_state.branch_id
                        selected_branch_display = user_branch_name

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t1 == "ทั้งหมด":
                            sql = """SELECT t.*, b.branch_name, m.machine_name 
                                     FROM machine_trans t 
                                     LEFT JOIN branches b ON t.branch_id = b.id 
                                     LEFT JOIN machines m ON t.machine_id = m.id
                                     WHERE t.record_date BETWEEN %s AND %s ORDER BY t.record_date ASC"""
                            cur.execute(sql, (start_date_t1, end_date_t1))
                        else:
                            sql = """SELECT t.*, b.branch_name, m.machine_name 
                                     FROM machine_trans t 
                                     LEFT JOIN branches b ON t.branch_id = b.id 
                                     LEFT JOIN machines m ON t.machine_id = m.id
                                     WHERE t.branch_id = %s AND t.record_date BETWEEN %s AND %s ORDER BY t.record_date ASC"""
                            cur.execute(sql, (b_id_t1, start_date_t1, end_date_t1))
                        raw_data_t1 = cur.fetchall()
                    conn.close()

                    if raw_data_t1:
                        pk_col_t1 = list(raw_data_t1[0].keys())[0]

                        # 1. แสดง DataFrame บนหน้าจอ Streamlit
                        df_display_t1 = []
                        for r in raw_data_t1:
                            df_display_t1.append({
                                'ID รายการ': r[pk_col_t1],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'ชื่อเครื่องจักร': r.get('machine_name'),
                                'จำนวน': r.get('machine_qty'),
                                'ชม.ทำงาน': r.get('working_hours'),
                                'ชม.เบรกดาวน์': r.get('breakdown_hours'),
                                'หมายเหตุ': r.get('remarks')
                            })
                        df_t1 = pd.DataFrame(df_display_t1)
                        st.dataframe(df_t1, use_container_width=True)


                        # 2. จัดเตรียมข้อมูล Matrix 1-31 วัน
                        
                        machines_config = [
                            {"name": "โต๊ะเลื่อย (≤ 0.15%)", "hex": "E2EFDA"},
                            {"name": "พัดลมดูดขี้เลื่อย(≤ 0.15%)", "hex": "F2F2F2"},
                            {"name": "ตาชั่งใหญ่(≤ 0.20%)", "hex": "EDEDED"},
                            {"name": "ตาชั่งเล็ก(≤ 0.20%)", "hex": "F2F2F2"},
                            {"name": "รถยก(≤ 0.20%)", "hex": "FCE4D6"},
                            {"name": "รถคีบ (≤16 ชม.)", "hex": "FFF2CC"},
                            {"name": "อัดน้ำยา(≤ 0.20%)", "hex": "E2EFDA"},
                            {"name": "เตาอบปกติ (≤ 0.20%)", "hex": "D9E1F2"},
                            {"name": "เตาอบ CDK(≤ 0.20%)", "hex": "D9E1F2"},
                            {"name": "บอยเลอร์(≤ 0.15%)", "hex": "FCE4D6"},
                            {"name": "ชิปเปอร์(≤ 0.15%)", "hex": "FFF2CC"}
                        ]

                        matrix_data = {d: {m['name']: {'qty': '', 'work': 0.0, 'break': 0.0, 'has_data': False} for m in machines_config} for d in range(1, 32)}
                        breakdown_remarks_list = []

                        for row_m in raw_data_t1:
                            d_num = pd.to_datetime(row_m['record_date']).day
                            m_db_name = str(row_m.get('machine_name') or '')
                            
                            for m in machines_config:
                                m_clean = m['name'].split('(')[0].strip()
                                if m_clean.lower() in m_db_name.lower():
                                    w_hr = float(row_m.get('working_hours') or 0.0)
                                    b_hr = float(row_m.get('breakdown_hours') or 0.0)
                                    qty = int(row_m.get('machine_qty') or 0)
                                    rem = str(row_m.get('remarks') or '').strip()

                                    matrix_data[d_num][m['name']] = {
                                        'qty': qty,
                                        'work': w_hr,
                                        'break': b_hr,
                                        'has_data': True
                                    }

                                    if b_hr > 0 and rem:
                                        d_str = pd.to_datetime(row_m['record_date']).strftime('%d/%m/%y')
                                        breakdown_remarks_list.append({
                                            'date': d_str,
                                            'machine': m_clean,
                                            'break': b_hr,
                                            'remark': rem
                                        })
                                    break

                        # คำนวณผลรวม Sum และ %                        
                        totals_work = {}
                        totals_break = {}
                        percentages = {}

                        for m in machines_config:
                            m_n = m['name']
                            tot_w = sum([matrix_data[d][m_n]['work'] for d in range(1, 32)])
                            tot_b = sum([matrix_data[d][m_n]['break'] for d in range(1, 32)])
                            
                            totals_work[m_n] = tot_w
                            totals_break[m_n] = tot_b
                            percentages[m_n] = f"{(tot_b / tot_w * 100):.2f}%" if tot_w > 0 else "0.00%"

                        month_thai = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
                        start_dt = pd.to_datetime(start_date_t1)
                        month_str = month_thai[start_dt.month - 1]
                        year_buddhist = start_dt.year + 543

                        # -------------------------------------------------------------------------
                        # 3. สร้างไฟล์ EXCEL (.xlsx) จัดรูปแบบเต็ม Matrix ด้วย OpenPyXL
                        # -------------------------------------------------------------------------
                        # Excel export logic
                        wb = Workbook()
                        ws = wb.active
                        ws.title = "Summary Machine Report"
                        ws.views.sheetView[0].showGridLines = True

                        # Styles
                        font_title = Font(name="Sarabun", size=14, bold=True)
                        font_banner = Font(name="Sarabun", size=12, bold=True)
                        font_header = Font(name="Sarabun", size=9, bold=True)
                        font_body = Font(name="Sarabun", size=9)
                        font_total = Font(name="Sarabun", size=9, bold=True)
                        font_pct = Font(name="Sarabun", size=10, bold=True, color="FF0000")

                        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        align_right = Alignment(horizontal="right", vertical="center")
                        align_left = Alignment(horizontal="left", vertical="center")

                        thin_border = Border(
                            left=Side(style="thin", color="000000"),
                            right=Side(style="thin", color="000000"),
                            top=Side(style="thin", color="000000"),
                            bottom=Side(style="thin", color="000000")
                        )

                        fill_banner = PatternFill(start_color="F8CBAD", end_color="F8CBAD", fill_type="solid")
                        fill_green = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

                        # Total columns = 1 (วันที่) + 11 * 3 = 34 columns (A to AH)
                        last_col_letter = get_column_letter(1 + len(machines_config) * 3)

                        # Row 1: Title
                        ws.merge_cells(f"A1:{last_col_letter}1")
                        ws["A1"] = f"บริษัท วู้ดเวิร์ค จำกัด สาขา {selected_branch_display}"
                        ws["A1"].font = font_title
                        ws["A1"].alignment = align_center

                        # Row 2: Banner
                        ws.merge_cells(f"A2:{last_col_letter}2")
                        ws["A2"] = f"สรุปชั่วโมงการทำงานของเครื่องจักร/เบรกดาวน์ ประจำเดือน....{month_str}................... {year_buddhist}"
                        ws["A2"].font = font_banner
                        ws["A2"].alignment = align_center
                        ws["A2"].fill = fill_banner
                        ws.row_dimensions[2].height = 25

                        # Row 3 & 4: Headers
                        ws.merge_cells("A3:A4")
                        ws["A3"] = "วันที่"
                        ws["A3"].font = font_header
                        ws["A3"].alignment = align_center
                        ws["A3"].fill = fill_green
                        ws["A3"].border = thin_border
                        ws["A4"].border = thin_border

                        col_idx = 2
                        for m in machines_config:
                            start_c = get_column_letter(col_idx)
                            end_c = get_column_letter(col_idx + 2)

                            # Row 3 Group Name                            
                            ws.merge_cells(f"{start_c}3:{end_c}3")
                            ws[f"{start_c}3"] = m["name"]
                            ws[f"{start_c}3"].font = font_header
                            ws[f"{start_c}3"].alignment = align_center
                            ws[f"{start_c}3"].fill = PatternFill(start_color=m["hex"], end_color=m["hex"], fill_type="solid")
                            
                            for c in range(col_idx, col_idx + 3):
                                ws[f"{get_column_letter(c)}3"].border = thin_border

                            # Row 4 Sub-headers
                            sub_headers = ["เครื่องจักร\nใช้งาน\n(เครื่อง)", "ชั่วโมง\nทำงาน\n(ชม.)", "ชั่วโมง\nเบรกดาวน์\n(ชม.)"]
                            for i, sh in enumerate(sub_headers):
                                cell_ref = f"{get_column_letter(col_idx + i)}4"
                                ws[cell_ref] = sh
                                ws[cell_ref].font = Font(name="Sarabun", size=8, bold=True)
                                ws[cell_ref].alignment = align_center
                                ws[cell_ref].border = thin_border

                            col_idx += 3

                        ws.row_dimensions[3].height = 20
                        ws.row_dimensions[4].height = 35

                        # Row 5 to 35: Days 1 to 31
                        current_row = 5
                        for day in range(1, 32):
                            ws[f"A{current_row}"] = day
                            ws[f"A{current_row}"].font = font_header
                            ws[f"A{current_row}"].alignment = align_center
                            ws[f"A{current_row}"].border = thin_border

                            c_idx = 2
                            for m in machines_config:
                                item = matrix_data[day][m['name']]
                                cell_q = ws[f"{get_column_letter(c_idx)}{current_row}"]
                                cell_w = ws[f"{get_column_letter(c_idx+1)}{current_row}"]
                                cell_b = ws[f"{get_column_letter(c_idx+2)}{current_row}"]

                                if item['has_data']:
                                    cell_q.value = item['qty']
                                    cell_w.value = item['work'] if item['work'] > 0 else "-"
                                    cell_b.value = item['break'] if item['break'] > 0 else "-"
                                else:
                                    cell_q.value = ""
                                    cell_w.value = ""
                                    cell_b.value = ""

                                cell_q.font = font_body
                                cell_q.alignment = align_center
                                cell_q.border = thin_border

                                cell_w.font = font_body
                                cell_w.alignment = align_right if isinstance(cell_w.value, (int, float)) else align_center
                                cell_w.border = thin_border
                                if isinstance(cell_w.value, (int, float)):
                                    cell_w.number_format = '#,##0.00'

                                cell_b.font = font_body
                                cell_b.alignment = align_right if isinstance(cell_b.value, (int, float)) else align_center
                                cell_b.border = thin_border
                                if isinstance(cell_b.value, (int, float)):
                                    cell_b.number_format = '#,##0.00'

                                c_idx += 3
                            current_row += 1

                        # Row 36: แถว "รวม" (Total Row)
                        ws[f"A{current_row}"] = "รวม"
                        ws[f"A{current_row}"].font = font_total
                        ws[f"A{current_row}"].alignment = align_center
                        ws[f"A{current_row}"].fill = fill_green
                        ws[f"A{current_row}"].border = thin_border

                        c_idx = 2
                        for m in machines_config:
                            m_n = m['name']
                            cell_q = ws[f"{get_column_letter(c_idx)}{current_row}"]
                            cell_w = ws[f"{get_column_letter(c_idx+1)}{current_row}"]
                            cell_b = ws[f"{get_column_letter(c_idx+2)}{current_row}"]

                            cell_q.value = "-"
                            cell_q.font = font_total
                            cell_q.alignment = align_center
                            cell_q.fill = fill_green
                            cell_q.border = thin_border

                            cell_w.value = totals_work[m_n] if totals_work[m_n] > 0 else "-"
                            cell_w.font = font_total
                            cell_w.alignment = align_right if totals_work[m_n] > 0 else align_center
                            cell_w.fill = fill_green
                            cell_w.border = thin_border
                            if totals_work[m_n] > 0:
                                cell_w.number_format = '#,##0.00'

                            cell_b.value = totals_break[m_n] if totals_break[m_n] > 0 else "-"
                            cell_b.font = font_total
                            cell_b.alignment = align_right if totals_break[m_n] > 0 else align_center
                            cell_b.fill = fill_green
                            cell_b.border = thin_border
                            if totals_break[m_n] > 0:
                                cell_b.number_format = '#,##0.00'

                            c_idx += 3

                        current_row += 1

                        # Row 37: แถว "คิดเป็น%" (Percentage Row)
                        ws[f"A{current_row}"] = "คิดเป็น%"
                        ws[f"A{current_row}"].font = font_pct
                        ws[f"A{current_row}"].alignment = align_center
                        ws[f"A{current_row}"].border = thin_border

                        c_idx = 2
                        for m in machines_config:
                            start_c = get_column_letter(c_idx)
                            end_c = get_column_letter(c_idx + 2)
                            
                            ws.merge_cells(f"{start_c}{current_row}:{end_c}{current_row}")
                            cell_p = ws[f"{start_c}{current_row}"]
                            cell_p.value = percentages[m['name']]
                            cell_p.font = font_pct
                            cell_p.alignment = align_center
                            
                            for c in range(c_idx, c_idx + 3):
                                ws[f"{get_column_letter(c)}{current_row}"].border = thin_border

                            c_idx += 3

                        current_row += 2  # เว้น 1 แถว

                        # Section: ตารางหมายเหตุเบรกดาวน์ด้านล่าง
                        ws[f"A{current_row}"] = "รายการ"
                        ws[f"B{current_row}"] = "วันที่"
                        ws.merge_cells(f"C{current_row}:K{current_row}")
                        ws[f"C{current_row}"] = "สาเหตุการเบรกดาวน์ / หมายเหตุ"

                        for c in ["A", "B"]:
                            ws[f"{c}{current_row}"].font = font_header
                            ws[f"{c}{current_row}"].alignment = align_center
                            ws[f"{c}{current_row}"].fill = fill_green
                            ws[f"{c}{current_row}"].border = thin_border

                        ws[f"C{current_row}"].font = font_header
                        ws[f"C{current_row}"].alignment = align_center
                        ws[f"C{current_row}"].fill = fill_green
                        
                        for col_i in range(3, 12):
                            ws[f"{get_column_letter(col_i)}{current_row}"].border = thin_border

                        current_row += 1

                        if breakdown_remarks_list:
                            for idx, rem in enumerate(breakdown_remarks_list, 1):
                                ws[f"A{current_row}"] = idx
                                ws[f"B{current_row}"] = rem["date"]
                                ws.merge_cells(f"C{current_row}:K{current_row}")
                                ws[f"C{current_row}"] = f'[{rem["machine"]}] {rem["remark"]} ({rem["break"]} ชม.)'

                                ws[f"A{current_row}"].font = font_body
                                ws[f"A{current_row}"].alignment = align_center
                                ws[f"A{current_row}"].border = thin_border

                                ws[f"B{current_row}"].font = font_body
                                ws[f"B{current_row}"].alignment = align_center
                                ws[f"B{current_row}"].border = thin_border

                                ws[f"C{current_row}"].font = font_body
                                ws[f"C{current_row}"].alignment = align_left

                                for col_i in range(3, 12):
                                    ws[f"{get_column_letter(col_i)}{current_row}"].border = thin_border

                                current_row += 1
                        else:
                            ws[f"A{current_row}"] = "-"
                            ws[f"B{current_row}"] = "-"
                            ws.merge_cells(f"C{current_row}:K{current_row}")
                            ws[f"C{current_row}"] = "ไม่มีรายการเครื่องจักรเบรกดาวน์ในช่วงเวลานี้"

                            ws[f"A{current_row}"].alignment = align_center
                            ws[f"B{current_row}"].alignment = align_center
                            ws[f"C{current_row}"].alignment = align_center

                            for col_i in range(1, 12):
                                ws[f"{get_column_letter(col_i)}{current_row}"].border = thin_border
                        # ตั้งค่าความกว้างคอลัมน์ Excel ให้สวยงาม
                        ws.column_dimensions['A'].width = 8
                        for c in range(2, 35):
                            ws.column_dimensions[get_column_letter(c)].width = 11

                        # Save to BytesIO
                        excel_buffer = io.BytesIO()
                        wb.save(excel_buffer)
                        excel_data = excel_buffer.getvalue()

                        # -------------------------------------------------------------------------
                        # 4. สร้าง HTML สำหรับสั่งปริ้นเปิดในเบราว์เซอร์
                        # -------------------------------------------------------------------------
                        header_row1 = "".join([f'<th colspan="3" style="background-color:{m["hex"]};border:1px solid #000;padding:3px;font-size:10px;text-align:center;">{m["name"]}</th>' for m in machines_config])
                        header_row2 = "".join(['<th style="border:1px solid #000;padding:2px;font-size:8px;width:28px;">เครื่องจักร<br>ใช้งาน</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:32px;">ชั่วโมง<br>ทำงาน</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:32px;">ชั่วโมง<br>เบรกดาวน์</th>' for _ in machines_config])

                        body_rows = ""
                        for day in range(1, 32):
                            body_rows += f'<tr><td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;font-weight:bold;">{day}</td>'
                            for m in machines_config:
                                item = matrix_data[day][m['name']]
                                if item['has_data']:
                                    q_val = str(item['qty'])
                                    w_val = f"{item['work']:,.2f}" if item['work'] > 0 else "-"
                                    b_val = f"{item['break']:,.2f}" if item['break'] > 0 else "-"
                                else:
                                    q_val, w_val, b_val = "", "", ""
                                
                                body_rows += f'<td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;">{q_val}</td>'
                                body_rows += f'<td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{w_val}</td>'
                                body_rows += f'<td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{b_val}</td>'
                            body_rows += '</tr>'

                        total_row_html = '<tr><td style="border:1px solid #000;padding:3px;text-align:center;font-size:10px;font-weight:bold;background-color:#E2EFDA;">รวม</td>'
                        for m in machines_config:
                            m_n = m['name']
                            tw_s = f"{totals_work[m_n]:,.2f}" if totals_work[m_n] > 0 else '-'
                            tb_s = f"{totals_break[m_n]:,.2f}" if totals_break[m_n] > 0 else '-'
                            total_row_html += f'<td style="border:1px solid #000;padding:3px;text-align:center;font-size:9px;font-weight:bold;background-color:#E2EFDA;">-</td>'
                            total_row_html += f'<td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;background-color:#E2EFDA;">{tw_s}</td>'
                            total_row_html += f'<td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;background-color:#E2EFDA;">{tb_s}</td>'
                        total_row_html += '</tr>'

                        pct_row_html = '<tr><td style="border:1px solid #000;padding:3px;text-align:center;font-size:10px;font-weight:bold;color:red;">คิดเป็น%</td>'
                        for m in machines_config:
                            pct_row_html += f'<td colspan="3" style="border:1px solid #000;padding:3px;text-align:center;font-size:10px;font-weight:bold;color:red;">{percentages[m["name"]]}</td>'
                        pct_row_html += '</tr>'

                        if breakdown_remarks_list:
                            rem_rows = "".join([f'<tr><td style="border:1px solid #000;text-align:center;font-size:9px;">{i+1}</td><td style="border:1px solid #000;text-align:center;font-size:9px;">{r["date"]}</td><td style="border:1px solid #000;font-size:9px;padding-left:4px;">[{r["machine"]}] {r["remark"]} ({r["break"]} ชม.)</td></tr>' for i, r in enumerate(breakdown_remarks_list)])
                        else:
                            rem_rows = '<tr><td colspan="3" style="border:1px solid #000;text-align:center;font-size:9px;color:#777;">ไม่มีรายการเครื่องจักรเบรกดาวน์ในช่วงเวลานี้</td></tr>'

                        table_full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Print Summary Machine Report</title>
    <style>
        @page {{ size: A4 landscape; margin: 4mm; }}
        body {{ font-family: 'Sarabun', Tahoma, sans-serif; margin: 0; padding: 5px; }}
        .header-title {{ text-align: center; font-size: 16px; font-weight: bold; margin-bottom: 4px; }}
        .banner {{ background-color: #F8CBAD; text-align: center; font-size: 14px; font-weight: bold; padding: 5px; border: 1px solid #000; margin-bottom: 4px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ font-family: 'Sarabun', Tahoma, sans-serif; }}
    </style>
</head>
<body>
    <div class="header-title">บริษัท วู้ดเวิร์ค จำกัด สาขา {selected_branch_display}</div>
    <div class="banner">สรุปชั่วโมงการทำงานของเครื่องจักร/เบรกดาวน์ ประจำเดือน....{month_str}................... {year_buddhist}</div>
    <table>
        <thead>
            <tr>
                <th rowspan="2" style="background-color:#E2EFDA;border:1px solid #000;padding:3px;font-size:10px;width:35px;">วันที่</th>
                {header_row1}
            </tr>
            <tr>
                {header_row2}
            </tr>
        </thead>
        <tbody>
            {body_rows}
            {total_row_html}
            {pct_row_html}
        </tbody>
    </table>
    <br>
    <table style="width:50%;border-collapse:collapse;margin-top:10px;">
        <thead>
            <tr style="background-color:#E2EFDA;">
                <th style="border:1px solid #000;padding:3px;font-size:9px;width:40px;">รายการ</th>
                <th style="border:1px solid #000;padding:3px;font-size:9px;width:70px;">วันที่</th>
                <th style="border:1px solid #000;padding:3px;font-size:9px;">สาเหตุการเบรกดาวน์/หมายเหตุ</th>
            </tr>
        </thead>
        <tbody>
            {rem_rows}
        </tbody>
    </table>
</body>
</html>"""

                        json_print_html_t1 = json.dumps(table_full_html)

                        # 🎯 กำหนดข้อความปุ่มปริ้นท์ตามระดับสิทธิ์ (Admin/Manager vs User)
                        print_btn_label_t1 = "🖨️ ปริ้นเอกสารรายงาน (Tab 1)" if current_role in ["admin", "manager"] else "🖨️ ปริ้นเอกสารรายงาน"

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.download_button(
                                label="📥 Export เป็น Excel (.xlsx)",
                                data=excel_data,
                                file_name=f"Summary_Machine_Report_{start_date_t1}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key="dl_t1"
                            )
                        with col_btn2:
                            components.html(f"""
                            <body style="margin:0;padding:0;overflow:hidden;">
                                <button onclick="openPrintPreview1()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">
                                    {print_btn_label_t1}
                                </button>
                            </body>
                            <script>
                            function openPrintPreview1(){{
                                var htmlData = {json_print_html_t1};
                                var w = window.open('', '_blank', 'height=750,width=1100,scrollbars=yes');
                                if (w) {{
                                    w.document.open();
                                    w.document.write(htmlData);
                                    w.document.close();
                                    w.focus();
                                    setTimeout(function(){{ w.print(); }}, 500);
                                }}
                            }}
                            </script>
                            """, height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            record_map_t1 = {f"ID: {r[pk_col_t1]} | วันที่: {r.get('record_date')} | เครื่อง: {r.get('machine_name')} ({r.get('branch_name')})": (r[pk_col_t1], r) for r in raw_data_t1}
                            selected_label_t1 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 1):", options=list(record_map_t1.keys()), key="select_t1")
                            target_pk_t1, target_rec_t1 = record_map_t1[selected_label_t1]

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 1)", expanded=True):
                                e_col1, e_col2 = st.columns(2)
                                with e_col1:
                                    e_date_t1 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t1.get('record_date')), key="e_date_t1_in")
                                    e_qty_t1 = st.number_input("แก้ไข จำนวนเครื่องจักร", min_value=1, value=int(target_rec_t1.get('machine_qty') or 1), key="e_qty_t1_in")
                                with e_col2:
                                    e_work_t1 = st.number_input("แก้ไข ชม.ทำงาน", min_value=0.0, step=0.5, value=float(target_rec_t1.get('working_hours') or 0.0), key="e_work_t1_in")
                                    e_break_t1 = st.number_input("แก้ไข ชม.เบรกดาวน์", min_value=0.0, step=0.5, value=float(target_rec_t1.get('breakdown_hours') or 0.0), key="e_break_t1_in")
                                e_remark_t1 = st.text_area("แก้ไข หมายเหตุ", value=str(target_rec_t1.get('remarks') or ''), key="e_remark_t1_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 1)", key="btn_up_t1", use_container_width=True):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                sql_u = f"UPDATE machine_trans SET record_date=%s, machine_qty=%s, working_hours=%s, breakdown_hours=%s, remarks=%s, updated_at=NOW() WHERE {pk_col_t1}=%s"
                                                cur.execute(sql_u, (e_date_t1, e_qty_t1, e_work_t1, e_break_t1, e_remark_t1, target_pk_t1))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 1", f"แก้ไขข้อมูล ID: {target_pk_t1}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t1} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 1)", type="primary", use_container_width=True, key="del_btn_t1"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM machine_trans WHERE {pk_col_t1} = %s", (target_pk_t1,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 1", f"ลบข้อมูล ID: {target_pk_t1}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t1} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 1: {e}")

        # =========================================================================
        # 🚚 TAB 2 REPORT: รายงานสรุปการใช้เชื้อเพลิงรถ
        # =========================================================================
        elif key == "2":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปการใช้เชื้อเพลิงรถยนต์และรถยก")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t2 = st.date_input("ตั้งแต่วันที่ (Tab 2)", value=pd.to_datetime("today").replace(day=1), key="s_date_t2")
                with col_f2:
                    end_date_t2 = st.date_input("ถึงวันที่ (Tab 2)", value=pd.to_datetime("today"), key="e_date_t2")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t2 = st.selectbox("เลือกสาขา (Tab 2):", options=report_options, key="b_sel_t2")
                        b_id_t2 = "ทั้งหมด" if b_label_t2 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t2]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t2 = st.session_state.branch_id

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t2 == "ทั้งหมด":
                            sql = """SELECT r.*, b.branch_name 
                                     FROM fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (start_date_t2, end_date_t2))
                        else:
                            sql = """SELECT r.*, b.branch_name 
                                     FROM fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (b_id_t2, start_date_t2, end_date_t2))
                        raw_data_t2 = cur.fetchall()
                    conn.close()

                    if raw_data_t2:
                        pk_col_t2 = list(raw_data_t2[0].keys())[0]
                        
                        df_display_t2 = []
                        for r in raw_data_t2:
                            liters = float(r.get('fuel_liters') or 0.0)
                            hours = float(r.get('working_hours') or 0.0)
                            liters_per_hour = round(liters / hours, 2) if hours > 0 else 0.00

                            df_display_t2.append({
                                'ID รายการ': r[pk_col_t2],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'ประเภทรถ': r.get('type_name'),
                                'รหัสงาน/ทะเบียน': r.get('engine_code'),
                                'ปริมาณน้ำมัน (ลิตร)': liters,
                                'ชม.ทำงาน': hours,
                                'ลิตร/ชม.': liters_per_hour,
                                'หมายเหตุ': r.get('remark')
                            })
                        df_t2 = pd.DataFrame(df_display_t2)
                        st.dataframe(df_t2, use_container_width=True)

                        print_btn_label_t2 = "🖨️ ปริ้นเอกสารรายงาน (Tab 2)" if current_role in ["admin", "manager"] else "🖨️ ปริ้นเอกสารรายงาน"

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_t2.to_excel(writer, index=False, sheet_name='Fuel Report')
                            st.download_button("📥 Export เป็น Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Report_Fuel_{start_date_t2}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t2")
                        with col_btn2:
                            table_html_t2 = df_t2.to_html(index=False, classes='report-table')
                            components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="window.parent.openPrintPreview2 ? window.parent.openPrintPreview2() : openPrintPreview2()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">{print_btn_label_t2}</button></body><script>function openPrintPreview2(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); var content = `<html><head><title>Print Preview - Tab 2</title></head><body><h2>รายงานสรุปเชื้อเพลิงรถ</h2><br>{table_html_t2}</body></html>`; w.document.write(content); w.document.close(); w.print();}}</script>""", height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            engine_options_t2 = {}
                            engine_details_t2 = {}
                            try:
                                conn_eng = get_db_connection()
                                with conn_eng.cursor() as cur_eng:
                                    sql_eng = """SELECT e.id, CONVERT(e.engine_code USING utf8mb4) AS engine_code, 
                                                        CONVERT(et.type_name USING utf8mb4) AS type_name, 
                                                        CONVERT(b.branch_name USING utf8mb4) AS branch_name
                                                 FROM engines e 
                                                 LEFT JOIN engine_types et ON e.engine_type_id = et.id 
                                                 LEFT JOIN branches b ON e.branch_id = b.id 
                                                 WHERE e.is_active = 1 ORDER BY b.id ASC, e.engine_code ASC"""
                                    cur_eng.execute(sql_eng)
                                    for eng in cur_eng.fetchall():
                                        code = eng['engine_code'] or ''
                                        t_name = eng['type_name'] or 'ไม่ระบุประเภท'
                                        b_name = eng['branch_name'] or ''
                                        try: branch_code = b_name.split("สาขา ")[1].split()[0]
                                        except: branch_code = b_name or "N/A"
                                        
                                        lbl = f"{code} (ประเภท: {t_name}) [{branch_code}]"
                                        engine_options_t2[lbl] = eng['id']
                                        engine_details_t2[lbl] = {'code': code, 'type': t_name}
                                conn_eng.close()
                            except Exception as e_eng:
                                print(f"Error fetching engines for edit: {e_eng}")

                            record_map_t2 = {f"ID: {r[pk_col_t2]} | วันที่: {r.get('record_date')} | ทะเบียน: {r.get('engine_code')} ({r.get('branch_name')})": (r[pk_col_t2], r) for r in raw_data_t2}
                            selected_label_t2 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 2):", options=list(record_map_t2.keys()), key="select_t2")
                            target_pk_t2, target_rec_t2 = record_map_t2[selected_label_t2]

                            curr_code_t2 = str(target_rec_t2.get('engine_code') or '')
                            curr_type_t2 = str(target_rec_t2.get('type_name') or '')
                            
                            default_eng_idx = 0
                            engine_lbl_list = list(engine_options_t2.keys())
                            for idx, lbl in enumerate(engine_lbl_list):
                                info = engine_details_t2[lbl]
                                if info['code'] == curr_code_t2 and info['type'] == curr_type_t2:
                                    default_eng_idx = idx
                                    break

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 2)", expanded=True):
                                e_col1, e_col2 = st.columns(2)
                                with e_col1:
                                    e_date_t2 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t2.get('record_date')), key="e_date_t2_in")
                                    selected_engine_edit_label = st.selectbox(
                                        "แก้ไข รหัสงาน / ทะเบียนรถ (แยกตามประเภทและสาขา):",
                                        options=engine_lbl_list if engine_lbl_list else ["-- ไม่พบข้อมูลรถ --"],
                                        index=default_eng_idx,
                                        key="e_engine_select_t2"
                                    )
                                with e_col2:
                                    e_liters_t2 = st.number_input("แก้ไข น้ำมัน (ลิตร)", min_value=0.0, value=float(target_rec_t2.get('fuel_liters') or 0.0), key="e_liters_t2_in")
                                    e_work_t2 = st.number_input("แก้ไข ชม.ทำงาน", min_value=0.0, step=0.5, value=float(target_rec_t2.get('working_hours') or 0.0), key="e_work_t2_in")
                                e_remark_t2 = st.text_area("แก้ไข หมายเหตุ", value=str(target_rec_t2.get('remark') or ''), key="e_remark_t2_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 2)", key="btn_up_t2", use_container_width=True):
                                        try:
                                            eng_info = engine_details_t2.get(selected_engine_edit_label, {'code': curr_code_t2, 'type': curr_type_t2})
                                            up_code = eng_info['code']
                                            up_type = eng_info['type']
                                            up_liter_hr = round(e_liters_t2 / e_work_t2, 2) if e_work_t2 > 0 else 0.00

                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                sql_u = f"""UPDATE fuel_records 
                                                            SET record_date=%s, engine_code=CONVERT(%s USING utf8mb4), type_name=CONVERT(%s USING utf8mb4), 
                                                                fuel_liters=%s, working_hours=%s, liter_hr=%s, remark=CONVERT(%s USING utf8mb4) 
                                                            WHERE {pk_col_t2}=%s"""
                                                cur.execute(sql_u, (e_date_t2, up_code, up_type, e_liters_t2, e_work_t2, up_liter_hr, e_remark_t2, target_pk_t2))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 2", f"แก้ไขข้อมูล ID: {target_pk_t2}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t2} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 2)", type="primary", use_container_width=True, key="del_btn_t2"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM fuel_records WHERE {pk_col_t2} = %s", (target_pk_t2,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 2", f"ลบข้อมูล ID: {target_pk_t2}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t2} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 2: {e}")

        # =========================================================================
        # 💨 TAB 3 REPORT: รายงานสรุปแรงดันไอน้ำ บอยเลอร์
        # =========================================================================
        elif key == "3":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปสถิติแรงดันไอน้ำปลายทางตก")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t3 = st.date_input("ตั้งแต่วันที่ (Tab 3)", value=pd.to_datetime("today").replace(day=1), key="s_date_t3")
                with col_f2:
                    end_date_t3 = st.date_input("ถึงวันที่ (Tab 3)", value=pd.to_datetime("today"), key="e_date_t3")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t3 = st.selectbox("เลือกสาขา (Tab 3):", options=report_options, key="b_sel_t3")
                        b_id_t3 = "ทั้งหมด" if b_label_t3 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t3]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t3 = st.session_state.branch_id

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t3 == "ทั้งหมด":
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_pressure_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (start_date_t3, end_date_t3))
                        else:
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_pressure_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (b_id_t3, start_date_t3, end_date_t3))
                        raw_data_t3 = cur.fetchall()
                    conn.close()

                    if raw_data_t3:
                        pk_col_t3 = list(raw_data_t3[0].keys())[0]
                        
                        df_display_t3 = []
                        for r in raw_data_t3:
                            tot_c = r.get('total_count') or 0
                            tot_d = r.get('total_drop') or 0
                            pm_d = r.get('pm_drop') or 0
                            df_display_t3.append({
                                'ID รายการ': r[pk_col_t3],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'จำนวนครั้งทั้งหมด': tot_c,
                                'ตกทั้งหมด (ครั้ง)': tot_d,
                                'ตกตามเงื่อนไข PM': pm_d,
                                'ตกนอกเหนือ PM': r.get('non_pm_drop') or 0,
                                'หมายเหตุ': r.get('remark')
                            })

                        df_t3 = pd.DataFrame(df_display_t3)
                        df_t3['ตกทั้งหมด (%)'] = ((df_t3['ตกทั้งหมด (ครั้ง)'] / df_t3['จำนวนครั้งทั้งหมด'].replace(0, 1)) * 100).round(2).astype(str) + '%'
                        df_t3['ตกตาม PM (%)'] = ((df_t3['ตกตามเงื่อนไข PM'] / df_t3['จำนวนครั้งทั้งหมด'].replace(0, 1)) * 100).round(2).astype(str) + '%'
                        st.dataframe(df_t3, use_container_width=True)

                        print_btn_label_t3 = "🖨️ ปริ้นเอกสารรายงาน (Tab 3)" if current_role in ["admin", "manager"] else "🖨️ ปริ้นเอกสารรายงาน"

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_t3.to_excel(writer, index=False, sheet_name='Pressure Report')
                            st.download_button("📥 Export เป็น Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Report_Pressure_{start_date_t3}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t3")
                        with col_btn2:
                            table_html_t3 = df_t3.to_html(index=False, classes='report-table')
                            components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="window.parent.openPrintPreview3 ? window.parent.openPrintPreview3() : openPrintPreview3()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">{print_btn_label_t3}</button></body><script>function openPrintPreview3(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); var content = `<html><head><title>Print Preview - Tab 3</title></head><body><h2>รายงานสรุปแรงดันไอน้ำ</h2><br>{table_html_t3}</body></html>`; w.document.write(content); w.document.close(); w.print();}}</script>""", height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            record_map_t3 = {f"ID: {r[pk_col_t3]} | วันที่: {r.get('record_date')} | สาขา: {r.get('branch_name')}": (r[pk_col_t3], r) for r in raw_data_t3}
                            selected_label_t3 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 3):", options=list(record_map_t3.keys()), key="select_t3")
                            target_pk_t3, target_rec_t3 = record_map_t3[selected_label_t3]

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 3)", expanded=True):
                                e_col1, e_col2 = st.columns(2)
                                with e_col1:
                                    e_date_t3 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t3.get('record_date')), key="e_date_t3_in")
                                    e_total_t3 = st.number_input("แก้ไข จำนวนครั้งทั้งหมด", min_value=0, value=int(target_rec_t3.get('total_count') or 0), key="e_total_t3_in")
                                with e_col2:
                                    e_pm_t3 = st.number_input("แก้ไข ตกตามเงื่อนไข PM", min_value=0, value=int(target_rec_t3.get('pm_drop') or 0), key="e_pm_t3_in")
                                    e_non_pm_t3 = st.number_input("แก้ไข ตกนอกเหนือ PM", min_value=0, value=int(target_rec_t3.get('non_pm_drop') or 0), key="e_non_pm_t3_in")
                                e_remark_t3 = st.text_input("แก้ไข หมายเหตุ", value=str(target_rec_t3.get('remark') or ''), key="e_remark_t3_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 3)", key="btn_up_t3", use_container_width=True):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                sql_u = f"UPDATE boiler_pressure_records SET record_date=%s, total_count=%s, total_drop=%s, pm_drop=%s, non_pm_drop=%s, remark=%s WHERE {pk_col_t3}=%s"
                                                cur.execute(sql_u, (e_date_t3, e_total_t3, (e_pm_t3 + e_non_pm_t3), e_pm_t3, e_non_pm_t3, e_remark_t3, target_pk_t3))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 3", f"แก้ไขข้อมูล ID: {target_pk_t3}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t3} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 3)", type="primary", use_container_width=True, key="del_btn_t3"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM boiler_pressure_records WHERE {pk_col_t3} = %s", (target_pk_t3,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 3", f"ลบข้อมูล ID: {target_pk_t3}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t3} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 3: {e}")

        # =========================================================================
        # 🔥 TAB 4 REPORT: รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)
        # =========================================================================
        elif key == "4":
            with current_tab_ctx:
                st.subheader("📊 รายงานผลการคำนวณประสิทธิภาพเชื้อเพลิง บอยเลอร์")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t4 = st.date_input("ตั้งแต่วันที่ (Tab 4)", value=pd.to_datetime("today").replace(day=1), key="s_date_t4")
                with col_f2:
                    end_date_t4 = st.date_input("ถึงวันที่ (Tab 4)", value=pd.to_datetime("today"), key="e_date_t4")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t4 = st.selectbox("เลือกสาขา (Tab 4):", options=report_options, key="b_sel_t4")
                        b_id_t4 = "ทั้งหมด" if b_label_t4 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t4]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t4 = st.session_state.branch_id

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t4 == "ทั้งหมด":
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (start_date_t4, end_date_t4))
                        else:
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (b_id_t4, start_date_t4, end_date_t4))
                        raw_data_t4 = cur.fetchall()
                    conn.close()

                    if raw_data_t4:
                        pk_col_t4 = list(raw_data_t4[0].keys())[0]
                        std_fuel_val = 280.00
                        
                        df_display_t4 = []
                        for r in raw_data_t4:
                            s_w = float(r.get('sawdust_weight') or 0.0)
                            w_w = float(r.get('wood_weight') or 0.0)
                            ww_w = float(r.get('waste_wood_weight') or 0.0)
                            
                            s_p = float(r.get('sawdust_price') or 0.0)
                            w_p = float(r.get('wood_price') or 0.0)
                            ww_p = float(r.get('waste_wood_price') or 0.0)
                            
                            steam_prod = float(r.get('steam_production') or 1.0)
                            w_hours = float(r.get('working_hours') or 1.0)
                            
                            total_fuel_weight = s_w + w_w + ww_w
                            total_fuel_price = s_p + w_p + ww_p
                            tons_per_hour = steam_prod / w_hours if w_hours > 0 else 0.0
                            fuel_cost_per_steam_ton = total_fuel_price / steam_prod if steam_prod > 0 else 0.0
                            actual_result = (total_fuel_weight / steam_prod) * 1000 if steam_prod > 0 else 0.0
                            diff_result = std_fuel_val - actual_result
                            
                            df_display_t4.append({
                                'ID รายการ': r[pk_col_t4],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'นหน.ขี้เลื่อย (ตัน)': s_w,
                                'นหน.ปีกไม้ (ตัน)': w_w,
                                'นหน.เศษไม้เสีย (ตัน)': ww_w,
                                '4.1 รวมน้ำหนักเชื้อเพลิง (ตัน)': round(total_fuel_weight, 2),
                                'ราคาขี้เลื่อย (บาท)': s_p,
                                'ราคาปีกไม้ (บาท)': w_p,
                                'ราคาเศษไม้เสีย (บาท)': ww_p,
                                '4.2 รวมราคาเชื้อเพลิง (บาท)': round(total_fuel_price, 2),
                                'ผลิตไอน้ำ (ตัน/วัน)': steam_prod,
                                'ชม.ทำงาน': w_hours,
                                '4.3 ตันต่อชั่วโมง': round(tons_per_hour, 2),
                                '4.4 ค่าเชื้อเพลิง (บาท/ตันไอน้ำ)': round(fuel_cost_per_steam_ton, 2),
                                '4.5 ผลงาน (กก./ตันไอน้ำ)': round(actual_result, 2),
                                '4.5 ผลต่าง (STD-ผลงาน)': round(diff_result, 2)
                            })

                        df_t4 = pd.DataFrame(df_display_t4)
                        st.dataframe(df_t4, use_container_width=True)

                        print_btn_label_t4 = "🖨️ ปริ้นเอกสารรายงาน (Tab 4)" if current_role in ["admin", "manager"] else "🖨️ ปริ้นเอกสารรายงาน"

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_t4.to_excel(writer, index=False, sheet_name='Boiler Fuel Report')
                            st.download_button("📥 Export เป็น Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Report_Boiler_Fuel_{start_date_t4}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t4")
                        with col_btn2:
                            table_html_t4 = df_t4.to_html(index=False, classes='report-table')
                            components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="window.parent.openPrintPreview4 ? window.parent.openPrintPreview4() : openPrintPreview4()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">{print_btn_label_t4}</button></body><script>function openPrintPreview4(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); var content = `<html><head><title>Print Preview - Tab 4</title></head><body><h2>รายงานสรุปเชื้อเพลิงบอยเลอร์</h2><br>{table_html_t4}</body></html>`; w.document.write(content); w.document.close(); w.print();}}</script>""", height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            record_map_t4 = {f"ID: {r[pk_col_t4]} | วันที่: {r.get('record_date')} | สาขา: {r.get('branch_name')}": (r[pk_col_t4], r) for r in raw_data_t4}
                            selected_label_t4 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 4):", options=list(record_map_t4.keys()), key="select_t4")
                            target_pk_t4, target_rec_t4 = record_map_t4[selected_label_t4]

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 4)", expanded=True):
                                e_col1, e_col2, e_col3 = st.columns(3)
                                with e_col1:
                                    e_date_t4 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t4.get('record_date')), key="e_date_t4_in")
                                    e_saw_w_t4 = st.number_input("แก้ไข นหน.ขี้เลื่อย", min_value=0.0, value=float(target_rec_t4.get('sawdust_weight') or 0.0), key="e_saw_w_t4_in")
                                    e_wood_w_t4 = st.number_input("แก้ไข นหน.ปีกไม้", min_value=0.0, value=float(target_rec_t4.get('wood_weight') or 0.0), key="e_wood_w_t4_in")
                                    e_waste_w_t4 = st.number_input("แก้ไข นหน.เศษไม้เสีย", min_value=0.0, value=float(target_rec_t4.get('waste_wood_weight') or 0.0), key="e_waste_w_t4_in")
                                with e_col2:
                                    e_saw_p_t4 = st.number_input("แก้ไข ราคาขี้เลื่อย", min_value=0.0, value=float(target_rec_t4.get('sawdust_price') or 0.0), key="e_saw_p_t4_in")
                                    e_wood_p_t4 = st.number_input("แก้ไข ราคาปีกไม้", min_value=0.0, value=float(target_rec_t4.get('wood_price') or 0.0), key="e_wood_p_t4_in")
                                    e_waste_p_t4 = st.number_input("แก้ไข ราคาเศษไม้เสีย", min_value=0.0, value=float(target_rec_t4.get('waste_wood_price') or 0.0), key="e_waste_p_t4_in")
                                with e_col3:
                                    e_prod_t4 = st.number_input("แก้ไข การผลิตไอน้ำ (ตัน)", min_value=0.1, value=float(target_rec_t4.get('steam_production') or 100.0), key="e_prod_t4_in")
                                    e_hours_t4 = st.number_input("แก้ไข ชม.ทำงาน", min_value=0.1, value=float(target_rec_t4.get('working_hours') or 8.0), key="e_hours_t4_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 4)", key="btn_up_t4", use_container_width=True):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                sql_u = f"UPDATE boiler_fuel_records SET record_date=%s, sawdust_weight=%s, wood_weight=%s, waste_wood_weight=%s, sawdust_price=%s, wood_price=%s, waste_wood_price=%s, steam_production=%s, working_hours=%s WHERE {pk_col_t4}=%s"
                                                cur.execute(sql_u, (e_date_t4, e_saw_w_t4, e_wood_w_t4, e_waste_w_t4, e_saw_p_t4, e_wood_p_t4, e_waste_p_t4, e_prod_t4, e_hours_t4, target_pk_t4))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 4", f"แก้ไขข้อมูล ID: {target_pk_t4}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t4} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 4)", type="primary", use_container_width=True, key="del_btn_t4"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM boiler_fuel_records WHERE {pk_col_t4} = %s", (target_pk_t4,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 4", f"ลบข้อมูล ID: {target_pk_t4}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t4} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 4: {e}")  
                    
        # =========================================================================
        # 🚚 TAB 2 REPORT: รายงานสรุปการใช้เชื้อเพลิงรถ
        # =========================================================================
        elif key == "2":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปการใช้เชื้อเพลิงรถยนต์และรถยก")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t2 = st.date_input("ตั้งแต่วันที่ (Tab 2)", value=pd.to_datetime("today").replace(day=1), key="s_date_t2")
                with col_f2:
                    end_date_t2 = st.date_input("ถึงวันที่ (Tab 2)", value=pd.to_datetime("today"), key="e_date_t2")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t2 = st.selectbox("เลือกสาขา (Tab 2):", options=report_options, key="b_sel_t2")
                        b_id_t2 = "ทั้งหมด" if b_label_t2 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t2]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t2 = st.session_state.branch_id

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t2 == "ทั้งหมด":
                            sql = """SELECT r.*, b.branch_name 
                                     FROM fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (start_date_t2, end_date_t2))
                        else:
                            sql = """SELECT r.*, b.branch_name 
                                     FROM fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (b_id_t2, start_date_t2, end_date_t2))
                        raw_data_t2 = cur.fetchall()
                    conn.close()

                    if raw_data_t2:
                        pk_col_t2 = list(raw_data_t2[0].keys())[0]
                        
                        df_display_t2 = []
                        for r in raw_data_t2:
                            liters = float(r.get('fuel_liters') or 0.0)
                            hours = float(r.get('working_hours') or 0.0)
                            liters_per_hour = round(liters / hours, 2) if hours > 0 else 0.00

                            df_display_t2.append({
                                'ID รายการ': r[pk_col_t2],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'ประเภทรถ': r.get('type_name'),
                                'รหัสงาน/ทะเบียน': r.get('engine_code'),
                                'ปริมาณน้ำมัน (ลิตร)': liters,
                                'ชม.ทำงาน': hours,
                                'ลิตร/ชม.': liters_per_hour,
                                'หมายเหตุ': r.get('remark')
                            })
                        df_t2 = pd.DataFrame(df_display_t2)
                        st.dataframe(df_t2, use_container_width=True)

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_t2.to_excel(writer, index=False, sheet_name='Fuel Report')
                            st.download_button("📥 Export เป็น Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Report_Fuel_{start_date_t2}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t2")
                        with col_btn2:
                            table_html_t2 = df_t2.to_html(index=False, classes='report-table')
                            components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="window.parent.openPrintPreview2 ? window.parent.openPrintPreview2() : openPrintPreview2()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน (Tab 2)</button></body><script>function openPrintPreview2(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); var content = `<html><head><title>Print Preview - Tab 2</title></head><body><h2>รายงานสรุปเชื้อเพลิงรถ</h2><br>{table_html_t2}</body></html>`; w.document.write(content); w.document.close(); w.print();}}</script>""", height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            engine_options_t2 = {}
                            engine_details_t2 = {}
                            try:
                                conn_eng = get_db_connection()
                                with conn_eng.cursor() as cur_eng:
                                    sql_eng = """SELECT e.id, CONVERT(e.engine_code USING utf8mb4) AS engine_code, 
                                                        CONVERT(et.type_name USING utf8mb4) AS type_name, 
                                                        CONVERT(b.branch_name USING utf8mb4) AS branch_name
                                                 FROM engines e 
                                                 LEFT JOIN engine_types et ON e.engine_type_id = et.id 
                                                 LEFT JOIN branches b ON e.branch_id = b.id 
                                                 WHERE e.is_active = 1 ORDER BY b.id ASC, e.engine_code ASC"""
                                    cur_eng.execute(sql_eng)
                                    for eng in cur_eng.fetchall():
                                        code = eng['engine_code'] or ''
                                        t_name = eng['type_name'] or 'ไม่ระบุประเภท'
                                        b_name = eng['branch_name'] or ''
                                        try: branch_code = b_name.split("สาขา ")[1].split()[0]
                                        except: branch_code = b_name or "N/A"
                                        
                                        lbl = f"{code} (ประเภท: {t_name}) [{branch_code}]"
                                        engine_options_t2[lbl] = eng['id']
                                        engine_details_t2[lbl] = {'code': code, 'type': t_name}
                                conn_eng.close()
                            except Exception as e_eng:
                                print(f"Error fetching engines for edit: {e_eng}")

                            record_map_t2 = {f"ID: {r[pk_col_t2]} | วันที่: {r.get('record_date')} | ทะเบียน: {r.get('engine_code')} ({r.get('branch_name')})": (r[pk_col_t2], r) for r in raw_data_t2}
                            selected_label_t2 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 2):", options=list(record_map_t2.keys()), key="select_t2")
                            target_pk_t2, target_rec_t2 = record_map_t2[selected_label_t2]

                            curr_code_t2 = str(target_rec_t2.get('engine_code') or '')
                            curr_type_t2 = str(target_rec_t2.get('type_name') or '')
                            
                            default_eng_idx = 0
                            engine_lbl_list = list(engine_options_t2.keys())
                            for idx, lbl in enumerate(engine_lbl_list):
                                info = engine_details_t2[lbl]
                                if info['code'] == curr_code_t2 and info['type'] == curr_type_t2:
                                    default_eng_idx = idx
                                    break

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 2)", expanded=True):
                                e_col1, e_col2 = st.columns(2)
                                with e_col1:
                                    e_date_t2 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t2.get('record_date')), key="e_date_t2_in")
                                    selected_engine_edit_label = st.selectbox(
                                        "แก้ไข รหัสงาน / ทะเบียนรถ (แยกตามประเภทและสาขา):",
                                        options=engine_lbl_list if engine_lbl_list else ["-- ไม่พบข้อมูลรถ --"],
                                        index=default_eng_idx,
                                        key="e_engine_select_t2"
                                    )
                                with e_col2:
                                    e_liters_t2 = st.number_input("แก้ไข น้ำมัน (ลิตร)", min_value=0.0, value=float(target_rec_t2.get('fuel_liters') or 0.0), key="e_liters_t2_in")
                                    e_work_t2 = st.number_input("แก้ไข ชม.ทำงาน", min_value=0.0, step=0.5, value=float(target_rec_t2.get('working_hours') or 0.0), key="e_work_t2_in")
                                e_remark_t2 = st.text_area("แก้ไข หมายเหตุ", value=str(target_rec_t2.get('remark') or ''), key="e_remark_t2_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 2)", key="btn_up_t2", use_container_width=True):
                                        try:
                                            eng_info = engine_details_t2.get(selected_engine_edit_label, {'code': curr_code_t2, 'type': curr_type_t2})
                                            up_code = eng_info['code']
                                            up_type = eng_info['type']
                                            up_liter_hr = round(e_liters_t2 / e_work_t2, 2) if e_work_t2 > 0 else 0.00

                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                # อัปเดตข้อมูลรวมถึงคอลัมน์ liter_hr ด้วย
                                                sql_u = f"""UPDATE fuel_records 
                                                            SET record_date=%s, engine_code=CONVERT(%s USING utf8mb4), type_name=CONVERT(%s USING utf8mb4), 
                                                                fuel_liters=%s, working_hours=%s, liter_hr=%s, remark=CONVERT(%s USING utf8mb4) 
                                                            WHERE {pk_col_t2}=%s"""
                                                cur.execute(sql_u, (e_date_t2, up_code, up_type, e_liters_t2, e_work_t2, up_liter_hr, e_remark_t2, target_pk_t2))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 2", f"แก้ไขข้อมูล ID: {target_pk_t2}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t2} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 2)", type="primary", use_container_width=True, key="del_btn_t2"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM fuel_records WHERE {pk_col_t2} = %s", (target_pk_t2,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 2", f"ลบข้อมูล ID: {target_pk_t2}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t2} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 2: {e}")

        # =========================================================================
        # 💨 TAB 3 REPORT: รายงานสรุปแรงดันไอน้ำ บอยเลอร์
        # =========================================================================
        elif key == "3":
            with current_tab_ctx:
                st.subheader("📊 รายงานสรุปสถิติแรงดันไอน้ำปลายทางตก")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t3 = st.date_input("ตั้งแต่วันที่ (Tab 3)", value=pd.to_datetime("today").replace(day=1), key="s_date_t3")
                with col_f2:
                    end_date_t3 = st.date_input("ถึงวันที่ (Tab 3)", value=pd.to_datetime("today"), key="e_date_t3")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t3 = st.selectbox("เลือกสาขา (Tab 3):", options=report_options, key="b_sel_t3")
                        b_id_t3 = "ทั้งหมด" if b_label_t3 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t3]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t3 = st.session_state.branch_id

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t3 == "ทั้งหมด":
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_pressure_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (start_date_t3, end_date_t3))
                        else:
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_pressure_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (b_id_t3, start_date_t3, end_date_t3))
                        raw_data_t3 = cur.fetchall()
                    conn.close()

                    if raw_data_t3:
                        pk_col_t3 = list(raw_data_t3[0].keys())[0]
                        
                        df_display_t3 = []
                        for r in raw_data_t3:
                            tot_c = r.get('total_count') or 0
                            tot_d = r.get('total_drop') or 0
                            pm_d = r.get('pm_drop') or 0
                            df_display_t3.append({
                                'ID รายการ': r[pk_col_t3],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'จำนวนครั้งทั้งหมด': tot_c,
                                'ตกทั้งหมด (ครั้ง)': tot_d,
                                'ตกตามเงื่อนไข PM': pm_d,
                                'ตกนอกเหนือ PM': r.get('non_pm_drop') or 0,
                                'หมายเหตุ': r.get('remark')
                            })

                        df_t3 = pd.DataFrame(df_display_t3)
                        df_t3['ตกทั้งหมด (%)'] = ((df_t3['ตกทั้งหมด (ครั้ง)'] / df_t3['จำนวนครั้งทั้งหมด'].replace(0, 1)) * 100).round(2).astype(str) + '%'
                        df_t3['ตกตาม PM (%)'] = ((df_t3['ตกตามเงื่อนไข PM'] / df_t3['จำนวนครั้งทั้งหมด'].replace(0, 1)) * 100).round(2).astype(str) + '%'
                        st.dataframe(df_t3, use_container_width=True)

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_t3.to_excel(writer, index=False, sheet_name='Pressure Report')
                            st.download_button("📥 Export เป็น Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Report_Pressure_{start_date_t3}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t3")
                        with col_btn2:
                            table_html_t3 = df_t3.to_html(index=False, classes='report-table')
                            components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="window.parent.openPrintPreview3 ? window.parent.openPrintPreview3() : openPrintPreview3()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน (Tab 3)</button></body><script>function openPrintPreview3(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); var content = `<html><head><title>Print Preview - Tab 3</title></head><body><h2>รายงานสรุปแรงดันไอน้ำ</h2><br>{table_html_t3}</body></html>`; w.document.write(content); w.document.close(); w.print();}}</script>""", height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            record_map_t3 = {f"ID: {r[pk_col_t3]} | วันที่: {r.get('record_date')} | สาขา: {r.get('branch_name')}": (r[pk_col_t3], r) for r in raw_data_t3}
                            selected_label_t3 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 3):", options=list(record_map_t3.keys()), key="select_t3")
                            target_pk_t3, target_rec_t3 = record_map_t3[selected_label_t3]

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 3)", expanded=True):
                                e_col1, e_col2 = st.columns(2)
                                with e_col1:
                                    e_date_t3 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t3.get('record_date')), key="e_date_t3_in")
                                    e_total_t3 = st.number_input("แก้ไข จำนวนครั้งทั้งหมด", min_value=0, value=int(target_rec_t3.get('total_count') or 0), key="e_total_t3_in")
                                with e_col2:
                                    e_pm_t3 = st.number_input("แก้ไข ตกตามเงื่อนไข PM", min_value=0, value=int(target_rec_t3.get('pm_drop') or 0), key="e_pm_t3_in")
                                    e_non_pm_t3 = st.number_input("แก้ไข ตกนอกเหนือ PM", min_value=0, value=int(target_rec_t3.get('non_pm_drop') or 0), key="e_non_pm_t3_in")
                                e_remark_t3 = st.text_input("แก้ไข หมายเหตุ", value=str(target_rec_t3.get('remark') or ''), key="e_remark_t3_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 3)", key="btn_up_t3", use_container_width=True):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                sql_u = f"UPDATE boiler_pressure_records SET record_date=%s, total_count=%s, total_drop=%s, pm_drop=%s, non_pm_drop=%s, remark=%s WHERE {pk_col_t3}=%s"
                                                cur.execute(sql_u, (e_date_t3, e_total_t3, (e_pm_t3 + e_non_pm_t3), e_pm_t3, e_non_pm_t3, e_remark_t3, target_pk_t3))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 3", f"แก้ไขข้อมูล ID: {target_pk_t3}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t3} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 3)", type="primary", use_container_width=True, key="del_btn_t3"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM boiler_pressure_records WHERE {pk_col_t3} = %s", (target_pk_t3,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 3", f"ลบข้อมูล ID: {target_pk_t3}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t3} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 3: {e}")

        # =========================================================================
        # 🔥 TAB 4 REPORT: รายงานสรุปการใช้เชื้อเพลิงบอยเลอร์ (SYSTEM)
        # =========================================================================
        elif key == "4":
            with current_tab_ctx:
                st.subheader("📊 รายงานผลการคำนวณประสิทธิภาพเชื้อเพลิง บอยเลอร์")
                col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                with col_f1:
                    start_date_t4 = st.date_input("ตั้งแต่วันที่ (Tab 4)", value=pd.to_datetime("today").replace(day=1), key="s_date_t4")
                with col_f2:
                    end_date_t4 = st.date_input("ถึงวันที่ (Tab 4)", value=pd.to_datetime("today"), key="e_date_t4")
                with col_f3:
                    if current_role in ["admin", "manager"]:
                        b_label_t4 = st.selectbox("เลือกสาขา (Tab 4):", options=report_options, key="b_sel_t4")
                        b_id_t4 = "ทั้งหมด" if b_label_t4 == "ทั้งหมดทุกสาขา" else branch_dict[b_label_t4]
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t4 = st.session_state.branch_id

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t4 == "ทั้งหมด":
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (start_date_t4, end_date_t4))
                        else:
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_fuel_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date DESC"""
                            cur.execute(sql, (b_id_t4, start_date_t4, end_date_t4))
                        raw_data_t4 = cur.fetchall()
                    conn.close()

                    if raw_data_t4:
                        pk_col_t4 = list(raw_data_t4[0].keys())[0]
                        std_fuel_val = 280.00
                        
                        df_display_t4 = []
                        for r in raw_data_t4:
                            s_w = float(r.get('sawdust_weight') or 0.0)
                            w_w = float(r.get('wood_weight') or 0.0)
                            ww_w = float(r.get('waste_wood_weight') or 0.0)
                            
                            s_p = float(r.get('sawdust_price') or 0.0)
                            w_p = float(r.get('wood_price') or 0.0)
                            ww_p = float(r.get('waste_wood_price') or 0.0)
                            
                            steam_prod = float(r.get('steam_production') or 1.0)
                            w_hours = float(r.get('working_hours') or 1.0)
                            
                            total_fuel_weight = s_w + w_w + ww_w
                            total_fuel_price = s_p + w_p + ww_p
                            tons_per_hour = steam_prod / w_hours if w_hours > 0 else 0.0
                            fuel_cost_per_steam_ton = total_fuel_price / steam_prod if steam_prod > 0 else 0.0
                            actual_result = (total_fuel_weight / steam_prod) * 1000 if steam_prod > 0 else 0.0
                            diff_result = std_fuel_val - actual_result
                            
                            df_display_t4.append({
                                'ID รายการ': r[pk_col_t4],
                                'วันที่': r.get('record_date'),
                                'สาขา': r.get('branch_name'),
                                'นหน.ขี้เลื่อย (ตัน)': s_w,
                                'นหน.ปีกไม้ (ตัน)': w_w,
                                'นหน.เศษไม้เสีย (ตัน)': ww_w,
                                '4.1 รวมน้ำหนักเชื้อเพลิง (ตัน)': round(total_fuel_weight, 2),
                                'ราคาขี้เลื่อย (บาท)': s_p,
                                'ราคาปีกไม้ (บาท)': w_p,
                                'ราคาเศษไม้เสีย (บาท)': ww_p,
                                '4.2 รวมราคาเชื้อเพลิง (บาท)': round(total_fuel_price, 2),
                                'ผลิตไอน้ำ (ตัน/วัน)': steam_prod,
                                'ชม.ทำงาน': w_hours,
                                '4.3 ตันต่อชั่วโมง': round(tons_per_hour, 2),
                                '4.4 ค่าเชื้อเพลิง (บาท/ตันไอน้ำ)': round(fuel_cost_per_steam_ton, 2),
                                '4.5 ผลงาน (กก./ตันไอน้ำ)': round(actual_result, 2),
                                '4.5 ผลต่าง (STD-ผลงาน)': round(diff_result, 2)
                            })

                        df_t4 = pd.DataFrame(df_display_t4)
                        st.dataframe(df_t4, use_container_width=True)

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_t4.to_excel(writer, index=False, sheet_name='Boiler Fuel Report')
                            st.download_button("📥 Export เป็น Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Report_Boiler_Fuel_{start_date_t4}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_t4")
                        with col_btn2:
                            table_html_t4 = df_t4.to_html(index=False, classes='report-table')
                            components.html(f"""<body style="margin:0;padding:0;overflow:hidden;"><button onclick="window.parent.openPrintPreview4 ? window.parent.openPrintPreview4() : openPrintPreview4()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">🖨️ ปริ้นเอกสารรายงาน (Tab 4)</button></body><script>function openPrintPreview4(){{var w = window.open('', '_blank', 'height=600,width=900,scrollbars=yes'); var content = `<html><head><title>Print Preview - Tab 4</title></head><body><h2>รายงานสรุปเชื้อเพลิงบอยเลอร์</h2><br>{table_html_t4}</body></html>`; w.document.write(content); w.document.close(); w.print();}}</script>""", height=40)

                        if current_role in ['admin', 'manager']:
                            st.write("---")
                            st.markdown("### 🛠️ เครื่องมือจัดการข้อมูล (Admin/Manager)")
                            
                            record_map_t4 = {f"ID: {r[pk_col_t4]} | วันที่: {r.get('record_date')} | สาขา: {r.get('branch_name')}": (r[pk_col_t4], r) for r in raw_data_t4}
                            selected_label_t4 = st.selectbox("เลือกรายการที่ต้องการแก้ไข/ลบ (Tab 4):", options=list(record_map_t4.keys()), key="select_t4")
                            target_pk_t4, target_rec_t4 = record_map_t4[selected_label_t4]

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 4)", expanded=True):
                                e_col1, e_col2, e_col3 = st.columns(3)
                                with e_col1:
                                    e_date_t4 = st.date_input("แก้ไข วันที่", value=pd.to_datetime(target_rec_t4.get('record_date')), key="e_date_t4_in")
                                    e_saw_w_t4 = st.number_input("แก้ไข นหน.ขี้เลื่อย", min_value=0.0, value=float(target_rec_t4.get('sawdust_weight') or 0.0), key="e_saw_w_t4_in")
                                    e_wood_w_t4 = st.number_input("แก้ไข นหน.ปีกไม้", min_value=0.0, value=float(target_rec_t4.get('wood_weight') or 0.0), key="e_wood_w_t4_in")
                                    e_waste_w_t4 = st.number_input("แก้ไข นหน.เศษไม้เสีย", min_value=0.0, value=float(target_rec_t4.get('waste_wood_weight') or 0.0), key="e_waste_w_t4_in")
                                with e_col2:
                                    e_saw_p_t4 = st.number_input("แก้ไข ราคาขี้เลื่อย", min_value=0.0, value=float(target_rec_t4.get('sawdust_price') or 0.0), key="e_saw_p_t4_in")
                                    e_wood_p_t4 = st.number_input("แก้ไข ราคาปีกไม้", min_value=0.0, value=float(target_rec_t4.get('wood_price') or 0.0), key="e_wood_p_t4_in")
                                    e_waste_p_t4 = st.number_input("แก้ไข ราคาเศษไม้เสีย", min_value=0.0, value=float(target_rec_t4.get('waste_wood_price') or 0.0), key="e_waste_p_t4_in")
                                with e_col3:
                                    e_prod_t4 = st.number_input("แก้ไข การผลิตไอน้ำ (ตัน)", min_value=0.1, value=float(target_rec_t4.get('steam_production') or 100.0), key="e_prod_t4_in")
                                    e_hours_t4 = st.number_input("แก้ไข ชม.ทำงาน", min_value=0.1, value=float(target_rec_t4.get('working_hours') or 8.0), key="e_hours_t4_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 4)", key="btn_up_t4", use_container_width=True):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                sql_u = f"UPDATE boiler_fuel_records SET record_date=%s, sawdust_weight=%s, wood_weight=%s, waste_wood_weight=%s, sawdust_price=%s, wood_price=%s, waste_wood_price=%s, steam_production=%s, working_hours=%s WHERE {pk_col_t4}=%s"
                                                cur.execute(sql_u, (e_date_t4, e_saw_w_t4, e_wood_w_t4, e_waste_w_t4, e_saw_p_t4, e_wood_p_t4, e_waste_p_t4, e_prod_t4, e_hours_t4, target_pk_t4))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "UPDATE", "All Report: Tab 4", f"แก้ไขข้อมูล ID: {target_pk_t4}")
                                            st.toast(f"✅ แก้ไขข้อมูล ID {target_pk_t4} สำเร็จแล้ว!", icon="💾")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการแก้ไข: {ex}", icon="⚠️")
                                with act_col2:
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 4)", type="primary", use_container_width=True, key="del_btn_t4"):
                                        try:
                                            conn = get_db_connection()
                                            with conn.cursor() as cur:
                                                cur.execute(f"DELETE FROM boiler_fuel_records WHERE {pk_col_t4} = %s", (target_pk_t4,))
                                                conn.commit()
                                            conn.close()
                                            log_activity(st.session_state.user_id, st.session_state.username, "DELETE", "All Report: Tab 4", f"ลบข้อมูล ID: {target_pk_t4}")
                                            st.toast(f"🗑️ ลบรายการ ID {target_pk_t4} เรียบร้อยแล้ว!", icon="🚨")
                                            time.sleep(1.2)
                                            st.rerun()
                                        except Exception as ex:
                                            st.toast(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {ex}", icon="⚠️")
                    else:
                        st.info("ไม่พบข้อมูลรายงานตามช่วงเวลาที่เลือก")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการดึงรายงาน Tab 4: {e}")