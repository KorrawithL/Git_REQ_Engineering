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
        # ⚙️ TAB 1 REPORT: รายงานสรุปเครื่องจักร & เบรกดาวน์ (รวมค่า ID ที่ลงซ้ำวันเดียวกัน)
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

                        matrix_data = {d: {m['name']: {'qty': 0, 'work': 0.0, 'break': 0.0, 'has_data': False} for m in machines_config} for d in range(1, 32)}
                        breakdown_remarks_list = []

                        # 🎯 วนลูปและบวกค่าเพิ่มกรณีพบเครื่องจักรเดียวกันในวันเดียวกัน
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

                                    # บวกสะสมค่าตัวเลข (Sum)
                                    matrix_data[d_num][m['name']]['qty'] += qty
                                    matrix_data[d_num][m['name']]['work'] += w_hr
                                    matrix_data[d_num][m['name']]['break'] += b_hr
                                    matrix_data[d_num][m['name']]['has_data'] = True

                                    # หากมีเบรกดาวน์ บันทึกหมายเหตุแยกรายการตามเดิม
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

                        # Excel export logic
                        wb = Workbook()
                        ws = wb.active
                        ws.title = "Summary Machine Report"
                        ws.views.sheetView[0].showGridLines = True

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
                            left=Side(style="thin", color="000000"), right=Side(style="thin", color="000000"),
                            top=Side(style="thin", color="000000"), bottom=Side(style="thin", color="000000")
                        )

                        fill_banner = PatternFill(start_color="F8CBAD", end_color="F8CBAD", fill_type="solid")
                        fill_green = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

                        last_col_letter = get_column_letter(1 + len(machines_config) * 3)

                        ws.merge_cells(f"A1:{last_col_letter}1")
                        ws["A1"] = f"บริษัท วู้ดเวิร์ค จำกัด สาขา {selected_branch_display}"
                        ws["A1"].font = font_title
                        ws["A1"].alignment = align_center

                        ws.merge_cells(f"A2:{last_col_letter}2")
                        ws["A2"] = f"สรุปชั่วโมงการทำงานของเครื่องจักร/เบรกดาวน์ ประจำเดือน....{month_str}................... {year_buddhist}"
                        ws["A2"].font = font_banner
                        ws["A2"].alignment = align_center
                        ws["A2"].fill = fill_banner
                        ws.row_dimensions[2].height = 25

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
                            
                            ws.merge_cells(f"{start_c}3:{end_c}3")
                            ws[f"{start_c}3"] = m["name"]
                            ws[f"{start_c}3"].font = font_header
                            ws[f"{start_c}3"].alignment = align_center
                            ws[f"{start_c}3"].fill = PatternFill(start_color=m["hex"], end_color=m["hex"], fill_type="solid")
                            
                            for c in range(col_idx, col_idx + 3):
                                ws[f"{get_column_letter(c)}3"].border = thin_border

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
                                    cell_q.value = item['qty'] if item['qty'] > 0 else "-"
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

                        current_row += 2

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

                        ws.column_dimensions['A'].width = 8
                        for c in range(2, 35):
                            ws.column_dimensions[get_column_letter(c)].width = 11

                        excel_buffer = io.BytesIO()
                        wb.save(excel_buffer)
                        excel_data = excel_buffer.getvalue()

                        # HTML สำหรับเปิดพิมพ์
                        header_row1 = "".join([f'<th colspan="3" style="background-color:{m["hex"]};border:1px solid #000;padding:3px;font-size:10px;text-align:center;">{m["name"]}</th>' for m in machines_config])
                        header_row2 = "".join(['<th style="border:1px solid #000;padding:2px;font-size:8px;width:28px;">เครื่องจักร<br>ใช้งาน</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:32px;">ชั่วโมง<br>ทำงาน</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:32px;">ชั่วโมง<br>เบรกดาวน์</th>' for _ in machines_config])

                        body_rows = ""
                        for day in range(1, 32):
                            body_rows += f'<tr><td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;font-weight:bold;">{day}</td>'
                            for m in machines_config:
                                item = matrix_data[day][m['name']]
                                if item['has_data']:
                                    q_val = str(item['qty']) if item['qty'] > 0 else "-"
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

                            # 🎯 ซิงค์ค่าใน session_state อัตโนมัติเมื่อเลือก ID ใหม่
                            if st.session_state.get('prev_selected_t1') != selected_label_t1:
                                st.session_state['e_date_t1_in'] = pd.to_datetime(target_rec_t1.get('record_date'))
                                st.session_state['e_qty_t1_in'] = int(target_rec_t1.get('machine_qty') or 1)
                                st.session_state['e_work_t1_in'] = float(target_rec_t1.get('working_hours') or 0.0)
                                st.session_state['e_break_t1_in'] = float(target_rec_t1.get('breakdown_hours') or 0.0)
                                st.session_state['e_remark_t1_in'] = str(target_rec_t1.get('remarks') or '')
                                st.session_state['prev_selected_t1'] = selected_label_t1

                            with st.expander("📝 ฟอร์มปรับปรุงแก้ไขข้อมูล (Update Tab 1)", expanded=True):
                                e_col1, e_col2 = st.columns(2)
                                with e_col1:
                                    e_date_t1 = st.date_input("แก้ไข วันที่", key="e_date_t1_in")
                                    e_qty_t1 = st.number_input("แก้ไข จำนวนเครื่องจักร", min_value=1, key="e_qty_t1_in")
                                with e_col2:
                                    e_work_t1 = st.number_input("แก้ไข ชม.ทำงาน", min_value=0.0, step=0.5, key="e_work_t1_in")
                                    e_break_t1 = st.number_input("แก้ไข ชม.เบรกดาวน์", min_value=0.0, step=0.5, key="e_break_t1_in")
                                e_remark_t1 = st.text_area("แก้ไข หมายเหตุ", key="e_remark_t1_in")

                                act_col1, act_col2 = st.columns(2)
                                with act_col1:
                                    # 🎯 ใส่ ID กำกับหลัง key เพื่อป้องกันชื่อซ้ำ
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 1)", key=f"btn_up_t1_{target_pk_t1}", use_container_width=True):
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
                                    # 🎯 ใส่ ID กำกับหลัง key เพื่อแก้ไขข้อผิดพลาด del_btn_t1 ซ้ำ
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 1)", type="primary", use_container_width=True, key=f"del_btn_t1_{target_pk_t1}"):
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
        # 🚚 TAB 2 REPORT: รายงานสรุปการใช้เชื้อเพลิงรถ (ปรับสูตร ชม.เป้าหมาย รถหลัก 20 ชม. / รถสำรอง 4 ชม.)
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
                        selected_branch_display = b_label_t2 if b_label_t2 != "ทั้งหมดทุกสาขา" else "ทุกสาขา"
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t2 = st.session_state.branch_id
                        selected_branch_display = user_branch_name

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t2 == "ทั้งหมด":
                            sql_eng = """SELECT e.id, 
                                                CONVERT(e.engine_code USING utf8mb4) AS engine_code, 
                                                CONVERT(et.type_name USING utf8mb4) AS type_name,
                                                CONVERT(b.branch_name USING utf8mb4) AS branch_name
                                         FROM engines e 
                                         LEFT JOIN engine_types et ON e.engine_type_id = et.id 
                                         LEFT JOIN branches b ON e.branch_id = b.id
                                         WHERE e.is_active = 1 ORDER BY b.id ASC, e.id ASC"""
                            cur.execute(sql_eng)
                            engines_list = cur.fetchall()

                            sql_trans = """SELECT r.*, b.branch_name 
                                           FROM fuel_records r 
                                           LEFT JOIN branches b ON r.branch_id = b.id
                                           WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date ASC"""
                            cur.execute(sql_trans, (start_date_t2, end_date_t2))
                            raw_data_t2 = cur.fetchall()
                        else:
                            sql_eng = """SELECT e.id, 
                                                CONVERT(e.engine_code USING utf8mb4) AS engine_code, 
                                                CONVERT(et.type_name USING utf8mb4) AS type_name,
                                                CONVERT(b.branch_name USING utf8mb4) AS branch_name
                                         FROM engines e 
                                         LEFT JOIN engine_types et ON e.engine_type_id = et.id 
                                         LEFT JOIN branches b ON e.branch_id = b.id
                                         WHERE e.branch_id = %s AND e.is_active = 1 ORDER BY e.id ASC"""
                            cur.execute(sql_eng, (b_id_t2,))
                            engines_list = cur.fetchall()

                            sql_trans = """SELECT r.*, b.branch_name 
                                           FROM fuel_records r 
                                           LEFT JOIN branches b ON r.branch_id = b.id
                                           WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date ASC"""
                            cur.execute(sql_trans, (b_id_t2, start_date_t2, end_date_t2))
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

                        # 1. สร้าง Mapping ประเภทรถ
                        real_type_map = {}
                        for r in raw_data_t2:
                            code = str(r.get('engine_code') or '').strip()
                            b_name = str(r.get('branch_name') or '').strip()
                            t_name = str(r.get('type_name') or '').strip()
                            if b_id_t2 == "ทั้งหมด" and b_name:
                                try: b_short = b_name.split("สาขา ")[1].split()[0]
                                except: b_short = b_name
                                k = f"{code}_{b_short}".lower()
                            else:
                                k = code.lower()
                            if t_name:
                                real_type_map[k] = t_name

                        # 2. ดึงรายชื่อรถที่ไม่ซ้ำ
                        seen_keys = set()
                        all_engines_config = []
                        
                        if engines_list:
                            for eng in engines_list:
                                code = str(eng.get('engine_code') or '').strip()
                                b_name = str(eng.get('branch_name') or '').strip()
                                
                                if b_id_t2 == "ทั้งหมด" and b_name:
                                    try: b_short = b_name.split("สาขา ")[1].split()[0]
                                    except: b_short = b_name
                                    eng_key = f"{code}_{b_short}"
                                    title_name = f"{code} [{b_short}]"
                                else:
                                    eng_key = code
                                    title_name = code

                                if not code or eng_key.lower() in seen_keys:
                                    continue
                                seen_keys.add(eng_key.lower())
                                
                                type_nm = real_type_map.get(eng_key.lower()) or str(eng.get('type_name') or 'TOYOTA')
                                hex_color = "FFC000" if "tck" in type_nm.lower() else "FF0000"

                                all_engines_config.append({
                                    "key": eng_key,
                                    "code": code,
                                    "title": title_name,
                                    "brand": type_nm,
                                    "branch": b_name,
                                    "hex": hex_color
                                })
                        else:
                            for r in raw_data_t2:
                                code = str(r.get('engine_code') or '').strip()
                                b_name = str(r.get('branch_name') or '').strip()
                                if b_id_t2 == "ทั้งหมด" and b_name:
                                    try: b_short = b_name.split("สาขา ")[1].split()[0]
                                    except: b_short = b_name
                                    eng_key = f"{code}_{b_short}"
                                    title_name = f"{code} [{b_short}]"
                                else:
                                    eng_key = code
                                    title_name = code

                                if not code or eng_key.lower() in seen_keys:
                                    continue
                                seen_keys.add(eng_key.lower())

                                type_nm = real_type_map.get(eng_key.lower()) or str(r.get('type_name') or 'TOYOTA')
                                hex_color = "FFC000" if "tck" in type_nm.lower() else "FF0000"

                                all_engines_config.append({
                                    "key": eng_key,
                                    "code": code,
                                    "title": title_name,
                                    "brand": type_nm,
                                    "branch": b_name,
                                    "hex": hex_color
                                })

                        # 3. Map ข้อมูลวันที่ 1-31
                        matrix_data_t2 = {d: {e['key']: {'liters': 0.0, 'hours': 0.0, 'has_data': False} for e in all_engines_config} for d in range(1, 32)}

                        for r in raw_data_t2:
                            d_num = pd.to_datetime(r['record_date']).day
                            e_code = str(r.get('engine_code') or '').strip()
                            b_name = str(r.get('branch_name') or '').strip()
                            
                            if b_id_t2 == "ทั้งหมด" and b_name:
                                try: b_short = b_name.split("สาขา ")[1].split()[0]
                                except: b_short = b_name
                                match_key = f"{e_code}_{b_short}"
                            else:
                                match_key = e_code
                            
                            for e in all_engines_config:
                                if e['key'].lower() == match_key.lower():
                                    matrix_data_t2[d_num][e['key']]['liters'] += float(r.get('fuel_liters') or 0.0)
                                    matrix_data_t2[d_num][e['key']]['hours'] += float(r.get('working_hours') or 0.0)
                                    matrix_data_t2[d_num][e['key']]['has_data'] = True
                                    break

                        # 4. แสดงเฉพาะคอลัมน์รถที่มีข้อมูลบันทึกจริง
                        active_engines_config = []
                        for e in all_engines_config:
                            c_key = e['key']
                            has_any_record = any([matrix_data_t2[d][c_key]['has_data'] for d in range(1, 32)])
                            if has_any_record:
                                active_engines_config.append(e)

                        engines_config = active_engines_config if active_engines_config else all_engines_config

                        # 5. คำนวณวันจริงของเดือนที่กำลังแสดงผล (เช่น 31, 30, 28, 29 วัน)
                        start_dt = pd.to_datetime(start_date_t2)
                        days_in_current_month = pd.Period(start_dt, freq='M').days_in_month

                        # 6. แยกกลุ่ม toyo vs TCK
                        toyo_keys = [e['key'] for e in engines_config if "tck" not in e['brand'].lower()]
                        tck_keys = [e['key'] for e in engines_config if "tck" in e['brand'].lower()]

                        totals_days_t2 = {}
                        totals_hours_t2 = {}
                        totals_liters_t2 = {}
                        avg_l_hr_t2 = {}
                        std_target_hours = {}

                        # 🎯 คำนวณเป้าหมายชั่วโมงตามเงื่อนไข: รถสำรอง 4 ชม./วัน, รถหลัก 20 ชม./วัน × จำนวนวันจริงของเดือน
                        for e in engines_config:
                            c_key = e['key']
                            tot_d = sum([1 for d in range(1, 32) if matrix_data_t2[d][c_key]['has_data']])
                            tot_h = sum([matrix_data_t2[d][c_key]['hours'] for d in range(1, 32)])
                            tot_l = sum([matrix_data_t2[d][c_key]['liters'] for d in range(1, 32)])
                            
                            totals_days_t2[c_key] = tot_d
                            totals_hours_t2[c_key] = tot_h
                            totals_liters_t2[c_key] = tot_l
                            avg_l_hr_t2[c_key] = f"{(tot_l / tot_h):.2f}" if tot_h > 0 else "0.00"
                            
                            # ตรวจสอบคำว่า "สำรอง" ในชื่อหรือรหัสรถ
                            is_backup_car = "สำรอง" in e['title'] or "สำรอง" in e['code'] or "สำรอง" in e.get('brand', '')
                            daily_standard = 4 if is_backup_car else 20
                            std_target_hours[c_key] = daily_standard * days_in_current_month

                        # คำนวณสรุปกลุ่มท้ายตาราง
                        summary_matrix_t2 = {}
                        for d in range(1, 32):
                            toyo_h = sum([matrix_data_t2[d][k]['hours'] for k in toyo_keys])
                            toyo_l = sum([matrix_data_t2[d][k]['liters'] for k in toyo_keys])
                            toyo_has = any([matrix_data_t2[d][k]['has_data'] for k in toyo_keys])
                            
                            tck_h = sum([matrix_data_t2[d][k]['hours'] for k in tck_keys])
                            tck_l = sum([matrix_data_t2[d][k]['liters'] for k in tck_keys])
                            tck_has = any([matrix_data_t2[d][k]['has_data'] for k in tck_keys])

                            summary_matrix_t2[d] = {
                                'toyo': {'days': 1 if toyo_has else 0, 'hours': toyo_h, 'liters': toyo_l, 'has_data': toyo_has},
                                'tck': {'days': 1 if tck_has else 0, 'hours': tck_h, 'liters': tck_l, 'has_data': tck_has}
                            }

                        tot_toyo_days = sum([summary_matrix_t2[d]['toyo']['days'] for d in range(1, 32)])
                        tot_toyo_hours = sum([summary_matrix_t2[d]['toyo']['hours'] for d in range(1, 32)])
                        tot_toyo_liters = sum([summary_matrix_t2[d]['toyo']['liters'] for d in range(1, 32)])
                        avg_toyo_rate = f"{(tot_toyo_liters / tot_toyo_hours):.2f}" if tot_toyo_hours > 0 else "0.00"

                        tot_tck_days = sum([summary_matrix_t2[d]['tck']['days'] for d in range(1, 32)])
                        tot_tck_hours = sum([summary_matrix_t2[d]['tck']['hours'] for d in range(1, 32)])
                        tot_tck_liters = sum([summary_matrix_t2[d]['tck']['liters'] for d in range(1, 32)])
                        avg_tck_rate = f"{(tot_tck_liters / tot_tck_hours):.2f}" if tot_tck_hours > 0 else "0.00"

                        tot_target_toyo = sum([std_target_hours[k] for k in toyo_keys])
                        tot_target_tck = sum([std_target_hours[k] for k in tck_keys])

                        month_thai = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
                        month_str = month_thai[start_dt.month - 1]
                        year_buddhist = start_dt.year + 543

                        # -------------------------------------------------------------------------
                        # 7. สร้างไฟล์ EXCEL (.xlsx) Cross-tab Matrix + 5 แถวสรุปท้ายตาราง
                        # -------------------------------------------------------------------------
                        wb2 = Workbook()
                        ws2 = wb2.active
                        ws2.title = "Fuel Report Matrix"
                        ws2.views.sheetView[0].showGridLines = True

                        font_title = Font(name="Sarabun", size=14, bold=True)
                        font_header = Font(name="Sarabun", size=9, bold=True)
                        font_header_white = Font(name="Sarabun", size=9, bold=True, color="FFFFFF")
                        font_body = Font(name="Sarabun", size=9)
                        font_total = Font(name="Sarabun", size=9, bold=True)
                        font_red = Font(name="Sarabun", size=9, bold=True, color="FF0000")

                        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        align_right = Alignment(horizontal="right", vertical="center")

                        thin_border = Border(
                            left=Side(style="thin", color="000000"), right=Side(style="thin", color="000000"),
                            top=Side(style="thin", color="000000"), bottom=Side(style="thin", color="000000")
                        )

                        fill_magenta = PatternFill(start_color="D90082", end_color="D90082", fill_type="solid")
                        fill_green_sum = PatternFill(start_color="A9D08E", end_color="A9D08E", fill_type="solid")
                        fill_blue_sum = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
                        fill_pink_sum = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

                        last_col_idx = 1 + (len(engines_config) * 4) + 8
                        last_col_letter_t2 = get_column_letter(last_col_idx)

                        ws2.merge_cells(f"A1:{last_col_letter_t2}1")
                        ws2["A1"] = f"บริษัท วู้ดเวิร์ค จำกัด สาขา {selected_branch_display}"
                        ws2["A1"].font = font_title
                        ws2["A1"].alignment = align_center

                        ws2.merge_cells(f"A2:{last_col_letter_t2}2")
                        ws2["A2"] = f"รายงานการใช้เชื้อเพลิงของรถ ประจำเดือน {month_str} {year_buddhist}"
                        ws2["A2"].font = font_title
                        ws2["A2"].alignment = align_center

                        ws2.merge_cells("A3:A5")
                        ws2["A3"] = "วันที่"
                        ws2["A3"].font = font_header
                        ws2["A3"].alignment = align_center
                        ws2["A3"].border = thin_border
                        ws2["A4"].border = thin_border
                        ws2["A5"].border = thin_border

                        col_idx = 2
                        for e in engines_config:
                            start_c = get_column_letter(col_idx)
                            end_c = get_column_letter(col_idx + 3)
                            
                            ws2.merge_cells(f"{start_c}3:{end_c}3")
                            ws2[f"{start_c}3"] = e["title"]
                            ws2[f"{start_c}3"].font = font_header
                            ws2[f"{start_c}3"].alignment = align_center
                            
                            ws2.merge_cells(f"{start_c}4:{end_c}4")
                            ws2[f"{start_c}4"] = e["brand"]
                            ws2[f"{start_c}4"].font = font_header_white if e["hex"] == "FF0000" else font_header
                            ws2[f"{start_c}4"].alignment = align_center
                            fill_color = PatternFill(start_color=e["hex"], end_color=e["hex"], fill_type="solid")
                            ws2[f"{start_c}4"].fill = fill_color

                            for c in range(col_idx, col_idx + 4):
                                ws2[f"{get_column_letter(c)}3"].border = thin_border
                                ws2[f"{get_column_letter(c)}4"].border = thin_border
                                ws2[f"{get_column_letter(c)}4"].fill = fill_color

                            sub_h = ["วันที่มี", "ชม.", "ลิตร", "ล/ชม."]
                            for i, sh in enumerate(sub_h):
                                cell_ref = f"{get_column_letter(col_idx + i)}5"
                                ws2[cell_ref] = sh
                                ws2[cell_ref].font = font_header
                                ws2[cell_ref].alignment = align_center
                                ws2[cell_ref].border = thin_border

                            col_idx += 4

                        # สรุป toyo ท้ายตาราง
                        start_c = get_column_letter(col_idx)
                        end_c = get_column_letter(col_idx + 3)
                        ws2.merge_cells(f"{start_c}3:{end_c}4")
                        ws2[f"{start_c}3"] = "toyo"
                        ws2[f"{start_c}3"].font = font_header_white
                        ws2[f"{start_c}3"].alignment = align_center
                        ws2[f"{start_c}3"].fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
                        for c in range(col_idx, col_idx + 4):
                            for r_h in [3, 4]:
                                ws2[f"{get_column_letter(c)}{r_h}"].border = thin_border
                                ws2[f"{get_column_letter(c)}{r_h}"].fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
                        for i, sh in enumerate(["วันที่มี", "ชม.", "ลิตร", "ล/ชม."]):
                            cell_ref = f"{get_column_letter(col_idx + i)}5"
                            ws2[cell_ref] = sh
                            ws2[cell_ref].font = font_header
                            ws2[cell_ref].alignment = align_center
                            ws2[cell_ref].border = thin_border
                        col_idx += 4

                        # สรุป TCK ท้ายตาราง
                        start_c = get_column_letter(col_idx)
                        end_c = get_column_letter(col_idx + 3)
                        ws2.merge_cells(f"{start_c}3:{end_c}4")
                        ws2[f"{start_c}3"] = "TCK"
                        ws2[f"{start_c}3"].font = font_header
                        ws2[f"{start_c}3"].alignment = align_center
                        ws2[f"{start_c}3"].fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
                        for c in range(col_idx, col_idx + 4):
                            for r_h in [3, 4]:
                                ws2[f"{get_column_letter(c)}{r_h}"].border = thin_border
                                ws2[f"{get_column_letter(c)}{r_h}"].fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
                        for i, sh in enumerate(["วันที่มี", "ชม.", "ลิตร", "ล/ชม."]):
                            cell_ref = f"{get_column_letter(col_idx + i)}5"
                            ws2[cell_ref] = sh
                            ws2[cell_ref].font = font_header
                            ws2[cell_ref].alignment = align_center
                            ws2[cell_ref].border = thin_border
                        col_idx += 4

                        ws2.row_dimensions[3].height = 22
                        ws2.row_dimensions[4].height = 22
                        ws2.row_dimensions[5].height = 20

                        # ข้อมูลวันที่ 1-31
                        current_row = 6
                        for day in range(1, 32):
                            ws2[f"A{current_row}"] = day
                            ws2[f"A{current_row}"].font = font_header
                            ws2[f"A{current_row}"].alignment = align_center
                            ws2[f"A{current_row}"].border = thin_border

                            c_idx = 2
                            for e in engines_config:
                                item = matrix_data_t2[day][e['key']]
                                cell_d = ws2[f"{get_column_letter(c_idx)}{current_row}"]
                                cell_h = ws2[f"{get_column_letter(c_idx+1)}{current_row}"]
                                cell_l = ws2[f"{get_column_letter(c_idx+2)}{current_row}"]
                                cell_r = ws2[f"{get_column_letter(c_idx+3)}{current_row}"]

                                if item['has_data']:
                                    cell_d.value = 1
                                    cell_h.value = item['hours'] if item['hours'] > 0 else "-"
                                    cell_l.value = item['liters'] if item['liters'] > 0 else "-"
                                    cell_r.value = round(item['liters'] / item['hours'], 2) if item['hours'] > 0 else "-"
                                else:
                                    cell_d.value, cell_h.value, cell_l.value, cell_r.value = "", "", "", ""

                                cell_d.font = font_body
                                cell_d.alignment = align_center
                                cell_d.border = thin_border

                                for cell in [cell_h, cell_l, cell_r]:
                                    cell.font = font_body
                                    cell.alignment = align_right if isinstance(cell.value, (int, float)) else align_center
                                    cell.border = thin_border
                                    if isinstance(cell.value, (int, float)):
                                        cell.number_format = '#,##0.00'
                                c_idx += 4

                            # สรุป toyo ท้ายตาราง
                            toyo_item = summary_matrix_t2[day]['toyo']
                            ws2[f"{get_column_letter(c_idx)}{current_row}"] = toyo_item['days'] if toyo_item['has_data'] else ""
                            ws2[f"{get_column_letter(c_idx+1)}{current_row}"] = toyo_item['hours'] if toyo_item['hours'] > 0 else "-"
                            ws2[f"{get_column_letter(c_idx+2)}{current_row}"] = toyo_item['liters'] if toyo_item['liters'] > 0 else "-"
                            ws2[f"{get_column_letter(c_idx+3)}{current_row}"] = round(toyo_item['liters']/toyo_item['hours'], 2) if toyo_item['hours'] > 0 else "-"

                            for offset in range(4):
                                cell = ws2[f"{get_column_letter(c_idx+offset)}{current_row}"]
                                cell.font = font_body
                                cell.alignment = align_right if isinstance(cell.value, (int, float)) else align_center
                                cell.border = thin_border
                                if isinstance(cell.value, (int, float)):
                                    cell.number_format = '#,##0.00'
                            c_idx += 4

                            # สรุป TCK ท้ายตาราง
                            tck_item = summary_matrix_t2[day]['tck']
                            ws2[f"{get_column_letter(c_idx)}{current_row}"] = tck_item['days'] if tck_item['has_data'] else ""
                            ws2[f"{get_column_letter(c_idx+1)}{current_row}"] = tck_item['hours'] if tck_item['hours'] > 0 else "-"
                            ws2[f"{get_column_letter(c_idx+2)}{current_row}"] = tck_item['liters'] if tck_item['liters'] > 0 else "-"
                            ws2[f"{get_column_letter(c_idx+3)}{current_row}"] = round(tck_item['liters']/tck_item['hours'], 2) if tck_item['hours'] > 0 else "-"

                            for offset in range(4):
                                cell = ws2[f"{get_column_letter(c_idx+offset)}{current_row}"]
                                cell.font = font_body
                                cell.alignment = align_right if isinstance(cell.value, (int, float)) else align_center
                                cell.border = thin_border
                                if isinstance(cell.value, (int, float)):
                                    cell.number_format = '#,##0.00'

                            current_row += 1

                        # -------------------------------------------------------------------------
                        # 🎯 ชุด 5 แถวสรุปผลงานตามภาพ (Excel)
                        # -------------------------------------------------------------------------
                        label_target_row = f"ชม.รวม1-{days_in_current_month}"

                        # แถวที่ 1: ชม.รวม 1-XX (เป้าหมายแถบสีชมพู)
                        ws2[f"A{current_row}"] = label_target_row
                        ws2[f"A{current_row}"].font = font_total
                        ws2[f"A{current_row}"].alignment = align_center
                        ws2[f"A{current_row}"].border = thin_border

                        c_idx = 2
                        for e in engines_config:
                            c_key = e['key']
                            for offset in range(4):
                                cell = ws2[f"{get_column_letter(c_idx+offset)}{current_row}"]
                                cell.border = thin_border
                                if offset == 1:
                                    cell.value = std_target_hours[c_key]
                                    cell.font = font_header_white
                                    cell.fill = fill_magenta
                                    cell.alignment = align_center
                            c_idx += 4
                        # toyo & TCK
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"] = tot_target_toyo
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"].font = font_header_white
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"].fill = fill_magenta
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"].alignment = align_center
                        for offset in [0, 2, 3]: ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border
                        c_idx += 4
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"] = tot_target_tck
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"].font = font_header_white
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"].fill = fill_magenta
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"].alignment = align_center
                        for offset in [0, 2, 3]: ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border
                        current_row += 1

                        # แถวที่ 2: ชม.ใช้จริง 1-XX
                        ws2[f"A{current_row}"] = f"ชม.ใช้จริง 1-{days_in_current_month}"
                        ws2[f"A{current_row}"].font = font_total
                        ws2[f"A{current_row}"].alignment = align_center
                        ws2[f"A{current_row}"].border = thin_border

                        c_idx = 2
                        for e in engines_config:
                            c_key = e['key']
                            ws2[f"{get_column_letter(c_idx)}{current_row}"] = totals_days_t2[c_key] if totals_days_t2[c_key]>0 else "-"
                            ws2[f"{get_column_letter(c_idx+1)}{current_row}"] = round(totals_hours_t2[c_key], 0) if totals_hours_t2[c_key]>0 else "-"
                            ws2[f"{get_column_letter(c_idx+2)}{current_row}"] = round(totals_liters_t2[c_key], 0) if totals_liters_t2[c_key]>0 else "-"
                            ws2[f"{get_column_letter(c_idx+3)}{current_row}"] = avg_l_hr_t2[c_key]
                            for offset in range(4):
                                cell = ws2[f"{get_column_letter(c_idx+offset)}{current_row}"]
                                cell.font = font_total
                                cell.alignment = align_right if offset > 0 else align_center
                                cell.border = thin_border
                            c_idx += 4
                        # toyo & TCK
                        ws2[f"{get_column_letter(c_idx)}{current_row}"] = tot_toyo_days
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"] = round(tot_toyo_hours, 0)
                        ws2[f"{get_column_letter(c_idx+2)}{current_row}"] = round(tot_toyo_liters, 0)
                        ws2[f"{get_column_letter(c_idx+3)}{current_row}"] = avg_toyo_rate
                        for offset in range(4): ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].font = font_total; ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border; ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].alignment = align_right
                        c_idx += 4
                        ws2[f"{get_column_letter(c_idx)}{current_row}"] = tot_tck_days
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"] = round(tot_tck_hours, 0)
                        ws2[f"{get_column_letter(c_idx+2)}{current_row}"] = round(tot_tck_liters, 0)
                        ws2[f"{get_column_letter(c_idx+3)}{current_row}"] = avg_tck_rate
                        for offset in range(4): ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].font = font_total; ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border; ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].alignment = align_right
                        current_row += 1

                        # แถวที่ 3: ส่วนต่าง
                        ws2[f"A{current_row}"] = "ส่วนต่าง"
                        ws2[f"A{current_row}"].font = font_total
                        ws2[f"A{current_row}"].alignment = align_center
                        ws2[f"A{current_row}"].border = thin_border

                        c_idx = 2
                        for e in engines_config:
                            c_key = e['key']
                            diff_val = std_target_hours[c_key] - round(totals_hours_t2[c_key], 0)
                            for offset in range(4):
                                cell = ws2[f"{get_column_letter(c_idx+offset)}{current_row}"]
                                cell.border = thin_border
                                if offset == 1:
                                    cell.value = int(diff_val)
                                    cell.font = font_red if diff_val < 0 else font_total
                                    cell.alignment = align_center
                            c_idx += 4
                        # toyo & TCK ส่วนต่าง
                        toyo_diff = tot_target_toyo - round(tot_toyo_hours, 0)
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"] = int(toyo_diff)
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"].font = font_red if toyo_diff < 0 else font_total
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"].alignment = align_center
                        for offset in [0, 2, 3]: ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border
                        c_idx += 4
                        tck_diff = tot_target_tck - round(tot_tck_hours, 0)
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"] = int(tck_diff)
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"].font = font_red if tck_diff < 0 else font_total
                        ws2[f"{get_column_letter(c_idx+1)}{current_row}"].alignment = align_center
                        for offset in [0, 2, 3]: ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border
                        current_row += 1

                        # แถวที่ 4: ชม.รวมทั้งเดือน (แถบสีเขียว + สีฟ้า)
                        ws2[f"A{current_row}"] = "ชม.รวมทั้งเดือน"
                        ws2[f"A{current_row}"].font = font_total
                        ws2[f"A{current_row}"].alignment = align_center
                        ws2[f"A{current_row}"].fill = fill_green_sum
                        ws2[f"A{current_row}"].border = thin_border

                        c_idx = 2
                        for e in engines_config:
                            c_key = e['key']
                            start_c_m = get_column_letter(c_idx)
                            end_c_m = get_column_letter(c_idx + 3)
                            ws2.merge_cells(f"{start_c_m}{current_row}:{end_c_m}{current_row}")
                            cell_m = ws2[f"{start_c_m}{current_row}"]
                            cell_m.value = std_target_hours[c_key]
                            cell_m.font = font_total
                            cell_m.alignment = align_center
                            cell_m.fill = fill_blue_sum
                            for offset in range(4): ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border; ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].fill = fill_blue_sum
                            c_idx += 4
                        # toyo & TCK ชม.รวมทั้งเดือน
                        for target_sum_val in [tot_target_toyo, tot_target_tck]:
                            start_c_m = get_column_letter(c_idx)
                            end_c_m = get_column_letter(c_idx + 3)
                            ws2.merge_cells(f"{start_c_m}{current_row}:{end_c_m}{current_row}")
                            cell_m = ws2[f"{start_c_m}{current_row}"]
                            cell_m.value = target_sum_val
                            cell_m.font = font_total
                            cell_m.alignment = align_center
                            cell_m.fill = fill_blue_sum
                            for offset in range(4): ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border; ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].fill = fill_blue_sum
                            c_idx += 4
                        current_row += 1

                        # แถวที่ 5: ชม.คงเหลือทั้งเดือน (แถบสีส้มอ่อน)
                        ws2[f"A{current_row}"] = "ชม.คงเหลือทั้งเดือน"
                        ws2[f"A{current_row}"].font = font_total
                        ws2[f"A{current_row}"].alignment = align_center
                        ws2[f"A{current_row}"].fill = fill_pink_sum
                        ws2[f"A{current_row}"].border = thin_border

                        c_idx = 2
                        for e in engines_config:
                            c_key = e['key']
                            diff_val = std_target_hours[c_key] - round(totals_hours_t2[c_key], 0)
                            start_c_m = get_column_letter(c_idx)
                            end_c_m = get_column_letter(c_idx + 3)
                            ws2.merge_cells(f"{start_c_m}{current_row}:{end_c_m}{current_row}")
                            cell_m = ws2[f"{start_c_m}{current_row}"]
                            cell_m.value = int(diff_val)
                            cell_m.font = font_red if diff_val < 0 else font_total
                            cell_m.alignment = align_center
                            cell_m.fill = fill_pink_sum
                            for offset in range(4): ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border; ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].fill = fill_pink_sum
                            c_idx += 4
                        # toyo & TCK ชม.คงเหลือทั้งเดือน
                        for diff_sum_val in [toyo_diff, tck_diff]:
                            start_c_m = get_column_letter(c_idx)
                            end_c_m = get_column_letter(c_idx + 3)
                            ws2.merge_cells(f"{start_c_m}{current_row}:{end_c_m}{current_row}")
                            cell_m = ws2[f"{start_c_m}{current_row}"]
                            cell_m.value = int(diff_sum_val)
                            cell_m.font = font_red if diff_sum_val < 0 else font_total
                            cell_m.alignment = align_center
                            cell_m.fill = fill_pink_sum
                            for offset in range(4): ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].border = thin_border; ws2[f"{get_column_letter(c_idx+offset)}{current_row}"].fill = fill_pink_sum
                            c_idx += 4

                        ws2.column_dimensions['A'].width = 16
                        for c in range(2, col_idx):
                            ws2.column_dimensions[get_column_letter(c)].width = 10

                        excel_buffer_t2 = io.BytesIO()
                        wb2.save(excel_buffer_t2)
                        excel_data_t2 = excel_buffer_t2.getvalue()

                        # -------------------------------------------------------------------------
                        # 8. สร้าง HTML สำหรับสั่งปริ้นท์
                        # -------------------------------------------------------------------------
                        header_row1_t2 = "".join([f'<th colspan="4" style="border:1px solid #000;padding:3px;font-size:10px;text-align:center;">{e["title"]}</th>' for e in engines_config])
                        header_row1_t2 += '<th colspan="4" style="background-color:#FF0000;color:#FFF;border:1px solid #000;padding:3px;font-size:10px;text-align:center;" rowspan="2">toyo</th>'
                        header_row1_t2 += '<th colspan="4" style="background-color:#FFC000;border:1px solid #000;padding:3px;font-size:10px;text-align:center;" rowspan="2">TCK</th>'

                        header_row2_t2 = "".join([f'<th colspan="4" style="background-color:#{e["hex"]};color:{"#FFF" if e["hex"]=="FF0000" else "#000"};border:1px solid #000;padding:3px;font-size:10px;text-align:center;">{e["brand"]}</th>' for e in engines_config])
                        
                        sub_cols_html = '<th style="border:1px solid #000;padding:2px;font-size:8px;width:25px;">วันที่มี</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:28px;">ชม.</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:28px;">ลิตร</th><th style="border:1px solid #000;padding:2px;font-size:8px;width:28px;">ล/ชม.</th>'
                        header_row3_t2 = "".join([sub_cols_html for _ in range(len(engines_config) + 2)])

                        body_rows_t2 = ""
                        for day in range(1, 32):
                            body_rows_t2 += f'<tr><td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;font-weight:bold;">{day}</td>'
                            for e in engines_config:
                                item = matrix_data_t2[day][e['key']]
                                if item['has_data']:
                                    d_val = "1"
                                    h_val = f"{item['hours']:,.2f}" if item['hours'] > 0 else "-"
                                    l_val = f"{item['liters']:,.2f}" if item['liters'] > 0 else "-"
                                    r_val = f"{(item['liters']/item['hours']):,.2f}" if item['hours'] > 0 else "-"
                                else:
                                    d_val, h_val, l_val, r_val = "", "", "", ""

                                body_rows_t2 += f'<td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;">{d_val}</td>'
                                body_rows_t2 += f'<td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{h_val}</td>'
                                body_rows_t2 += f'<td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{l_val}</td>'
                                body_rows_t2 += f'<td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{r_val}</td>'

                            # toyo
                            toyo_item = summary_matrix_t2[day]['toyo']
                            td_toyo = "1" if toyo_item['has_data'] else ""
                            th_toyo = f"{toyo_item['hours']:,.2f}" if toyo_item['hours'] > 0 else "-"
                            tl_toyo = f"{toyo_item['liters']:,.2f}" if toyo_item['liters'] > 0 else "-"
                            tr_toyo = f"{(toyo_item['liters']/toyo_item['hours']):,.2f}" if toyo_item['hours'] > 0 else "-"
                            body_rows_t2 += f'<td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;">{td_toyo}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{th_toyo}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{tl_toyo}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{tr_toyo}</td>'

                            # TCK
                            tck_item = summary_matrix_t2[day]['tck']
                            td_tck = "1" if tck_item['has_data'] else ""
                            th_tck = f"{tck_item['hours']:,.2f}" if tck_item['hours'] > 0 else "-"
                            tl_tck = f"{tck_item['liters']:,.2f}" if tck_item['liters'] > 0 else "-"
                            tr_tck = f"{(tck_item['liters']/tck_item['hours']):,.2f}" if tck_item['hours'] > 0 else "-"
                            body_rows_t2 += f'<td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;">{td_tck}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{th_tck}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{tl_tck}</td><td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;">{tr_tck}</td>'

                            body_rows_t2 += '</tr>'

                            # 🎯 ชุด 5 แถวสรุป HTML (Dynamic Days)
                        r1_target_html = f'<tr><td style="border:1px solid #000;padding:3px;font-size:9px;font-weight:bold;text-align:center;">ชม.รวม1-{days_in_current_month}</td>'
                        r2_actual_html = f'<tr><td style="border:1px solid #000;padding:3px;font-size:9px;font-weight:bold;text-align:center;">ชม.ใช้จริง 1-{days_in_current_month}</td>'
                        r3_diff_html = '<tr><td style="border:1px solid #000;padding:3px;font-size:9px;font-weight:bold;text-align:center;">ส่วนต่าง</td>'
                        r4_month_html = '<tr><td style="border:1px solid #000;padding:3px;font-size:9px;font-weight:bold;text-align:center;background-color:#A9D08E;">ชม.รวมทั้งเดือน</td>'
                        r5_remain_html = '<tr><td style="border:1px solid #000;padding:3px;font-size:9px;font-weight:bold;text-align:center;background-color:#FCE4D6;">ชม.คงเหลือทั้งเดือน</td>'

                        for e in engines_config:
                            c_key = e['key']
                            t_tgt = std_target_hours[c_key]
                            t_act_h = round(totals_hours_t2[c_key], 0)
                            t_act_l = round(totals_liters_t2[c_key], 0)
                            t_act_d = totals_days_t2[c_key]
                            diff_h = t_tgt - t_act_h
                            diff_color = "red" if diff_h < 0 else "black"

                            # Row 1
                            r1_target_html += f'<td style="border:1px solid #000;"></td><td style="border:1px solid #000;background-color:#D90082;color:#FFF;text-align:center;font-weight:bold;font-size:9px;">{t_tgt}</td><td style="border:1px solid #000;"></td><td style="border:1px solid #000;"></td>'
                            # Row 2
                            r2_actual_html += f'<td style="border:1px solid #000;text-align:center;font-weight:bold;font-size:9px;">{t_act_d if t_act_d>0 else "-"}</td><td style="border:1px solid #000;text-align:right;font-weight:bold;font-size:9px;">{t_act_h:,.0f}</td><td style="border:1px solid #000;text-align:right;font-weight:bold;font-size:9px;">{t_act_l:,.0f}</td><td style="border:1px solid #000;text-align:right;font-weight:bold;font-size:9px;">{avg_l_hr_t2[c_key]}</td>'
                            # Row 3
                            r3_diff_html += f'<td style="border:1px solid #000;"></td><td style="border:1px solid #000;text-align:center;font-weight:bold;font-size:9px;color:{diff_color};">{diff_h:,.0f}</td><td style="border:1px solid #000;"></td><td style="border:1px solid #000;"></td>'
                            # Row 4
                            r4_month_html += f'<td colspan="4" style="border:1px solid #000;text-align:center;font-weight:bold;font-size:10px;background-color:#BDD7EE;">{t_tgt}</td>'
                            # Row 5
                            r5_remain_html += f'<td colspan="4" style="border:1px solid #000;text-align:center;font-weight:bold;font-size:10px;background-color:#FCE4D6;color:{diff_color};">{diff_h:,.0f}</td>'

                        # toyo & TCK ท้ายตาราง
                        for tgt_s, act_h, act_l, act_d, rate_s, diff_s in [
                            (tot_target_toyo, tot_toyo_hours, tot_toyo_liters, tot_toyo_days, avg_toyo_rate, toyo_diff),
                            (tot_target_tck, tot_tck_hours, tot_tck_liters, tot_tck_days, avg_tck_rate, tck_diff)
                        ]:
                            d_col = "red" if diff_s < 0 else "black"
                            r1_target_html += f'<td style="border:1px solid #000;"></td><td style="border:1px solid #000;background-color:#D90082;color:#FFF;text-align:center;font-weight:bold;font-size:9px;">{tgt_s}</td><td style="border:1px solid #000;"></td><td style="border:1px solid #000;"></td>'
                            r2_actual_html += f'<td style="border:1px solid #000;text-align:center;font-weight:bold;font-size:9px;">{act_d}</td><td style="border:1px solid #000;text-align:right;font-weight:bold;font-size:9px;">{act_h:,.0f}</td><td style="border:1px solid #000;text-align:right;font-weight:bold;font-size:9px;">{act_l:,.0f}</td><td style="border:1px solid #000;text-align:right;font-weight:bold;font-size:9px;">{rate_s}</td>'
                            r3_diff_html += f'<td style="border:1px solid #000;"></td><td style="border:1px solid #000;text-align:center;font-weight:bold;font-size:9px;color:{d_col};">{diff_s:,.0f}</td><td style="border:1px solid #000;"></td><td style="border:1px solid #000;"></td>'
                            r4_month_html += f'<td colspan="4" style="border:1px solid #000;text-align:center;font-weight:bold;font-size:10px;background-color:#BDD7EE;">{tgt_s}</td>'
                            r5_remain_html += f'<td colspan="4" style="border:1px solid #000;text-align:center;font-weight:bold;font-size:10px;background-color:#FCE4D6;color:{d_col};">{diff_s:,.0f}</td>'

                        r1_target_html += '</tr>'
                        r2_actual_html += '</tr>'
                        r3_diff_html += '</tr>'
                        r4_month_html += '</tr>'
                        r5_remain_html += '</tr>'

                        table_full_html_t2 = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Print Fuel Report Matrix</title>
    <style>
        @page {{ size: A4 landscape; margin: 4mm; }}
        body {{ font-family: 'Sarabun', Tahoma, sans-serif; margin: 0; padding: 5px; }}
        .header-title {{ text-align: center; font-size: 16px; font-weight: bold; margin-bottom: 4px; }}
        .banner {{ text-align: center; font-size: 14px; font-weight: bold; padding: 5px; margin-bottom: 4px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ font-family: 'Sarabun', Tahoma, sans-serif; }}
    </style>
</head>
<body>
    <div class="header-title">บริษัท วู้ดเวิร์ค จำกัด สาขา {selected_branch_display}</div>
    <div class="banner">รายงานการใช้เชื้อเพลิงของรถ ประจำเดือน {month_str} {year_buddhist}</div>
    <table>
        <thead>
            <tr>
                <th rowspan="3" style="border:1px solid #000;padding:3px;font-size:10px;width:35px;">วันที่</th>
                {header_row1_t2}
            </tr>
            <tr>
                {header_row2_t2}
            </tr>
            <tr>
                {header_row3_t2}
            </tr>
        </thead>
        <tbody>
            {body_rows_t2}
            {r1_target_html}
            {r2_actual_html}
            {r3_diff_html}
            {r4_month_html}
            {r5_remain_html}
        </tbody>
    </table>
</body>
</html>"""

                        json_print_html_t2 = json.dumps(table_full_html_t2)
                        print_btn_label_t2 = "🖨️ ปริ้นเอกสารรายงาน (Tab 2)" if current_role in ["admin", "manager"] else "🖨️ ปริ้นเอกสารรายงาน"

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.download_button(
                                label="📥 Export เป็น Excel (.xlsx)",
                                data=excel_data_t2,
                                file_name=f"Summary_Fuel_Report_{start_date_t2}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key="dl_t2"
                            )
                        with col_btn2:
                            components.html(f"""
                            <body style="margin:0;padding:0;overflow:hidden;">
                                <button onclick="openPrintPreview2()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">
                                    {print_btn_label_t2}
                                </button>
                            </body>
                            <script>
                            function openPrintPreview2(){{
                                var htmlData = {json_print_html_t2};
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
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 2)", key=f"btn_up_t2_{target_pk_t2}", use_container_width=True):
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
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 2)", type="primary", use_container_width=True, key=f"del_btn_t2_{target_pk_t2}"):
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
        # 💨 TAB 3 REPORT: รายงานสรุปแรงดันไอน้ำ บอยเลอร์ (เพิ่มแถวผลรวมท้ายตาราง)
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
                        selected_branch_display = b_label_t3 if b_label_t3 != "ทั้งหมดทุกสาขา" else "ทุกสาขา"
                    else:
                        st.info(f"📍 สังกัด: {user_branch_name}")
                        b_id_t3 = st.session_state.branch_id
                        selected_branch_display = user_branch_name

                try:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        if b_id_t3 == "ทั้งหมด":
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_pressure_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.record_date BETWEEN %s AND %s ORDER BY r.record_date ASC"""
                            cur.execute(sql, (start_date_t3, end_date_t3))
                        else:
                            sql = """SELECT r.*, b.branch_name 
                                     FROM boiler_pressure_records r 
                                     LEFT JOIN branches b ON r.branch_id = b.id
                                     WHERE r.branch_id = %s AND r.record_date BETWEEN %s AND %s ORDER BY r.record_date ASC"""
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
                            non_pm_d = r.get('non_pm_drop') or 0
                            rem_text = str(r.get('remark') or '')
                            b_text = str(r.get('branch_name') or '')
                            
                            df_display_t3.append({
                                'ID รายการ': r[pk_col_t3],
                                'วันที่': r.get('record_date'),
                                'สาขา': b_text,
                                'จำนวนครั้งทั้งหมด': tot_c,
                                'ตกทั้งหมด (ครั้ง)': tot_d,
                                'ตกตามเงื่อนไข PM': pm_d,
                                'ตกนอกเหนือ PM': non_pm_d,
                                'หมายเหตุ': rem_text,
                                'ตกทั้งหมด (%)': f"{((tot_d / tot_c) * 100):.2f}%" if tot_c > 0 else "0.00%",
                                'ตกตาม PM (%)': f"{((pm_d / tot_c) * 100):.2f}%" if tot_c > 0 else "0.00%"
                            })

                        df_t3 = pd.DataFrame(df_display_t3)
                        st.dataframe(df_t3, use_container_width=True)

                        # 1. คัดแยกรายการสาขาที่ไม่ซ้ำสำหรับสร้าง Matrix
                        seen_b_keys = set()
                        branches_config = []
                        
                        for r in raw_data_t3:
                            b_name = str(r.get('branch_name') or '').strip()
                            try: b_code = b_name.split("สาขา ")[1].split()[0]
                            except: b_code = b_name or "WU"
                            
                            if b_code.lower() not in seen_b_keys:
                                seen_b_keys.add(b_code.lower())
                                branches_config.append({"code": b_code, "full_name": b_name})

                        if not branches_config:
                            branches_config = [{"code": "WU", "full_name": selected_branch_display}]

                        # 2. จัดโครงสร้างข้อมูล วันที่ 1-31
                        matrix_data_t3 = {d: {b['code']: {'total': 0.0, 'drop': 0.0, 'pm': 0.0, 'non_pm': 0.0, 'remark': '', 'has_data': False} for b in branches_config} for d in range(1, 32)}

                        for r in raw_data_t3:
                            d_num = pd.to_datetime(r['record_date']).day
                            b_name = str(r.get('branch_name') or '').strip()
                            try: b_code = b_name.split("สาขา ")[1].split()[0]
                            except: b_code = b_name or "WU"

                            for b in branches_config:
                                if b['code'].lower() == b_code.lower():
                                    matrix_data_t3[d_num][b['code']] = {
                                        'total': float(r.get('total_count') or 0.0),
                                        'drop': float(r.get('total_drop') or 0.0),
                                        'pm': float(r.get('pm_drop') or 0.0),
                                        'non_pm': float(r.get('non_pm_drop') or 0.0),
                                        'remark': str(r.get('remark') or '').strip(),
                                        'has_data': True
                                    }
                                    break

                        # 🎯 3. คำนวณผลรวม Sum และสถิติ % แต่ละสาขา
                        branch_totals_t3 = {}
                        for b in branches_config:
                            b_code = b['code']
                            tot_c = sum([matrix_data_t3[d][b_code]['total'] for d in range(1, 32)])
                            tot_d = sum([matrix_data_t3[d][b_code]['drop'] for d in range(1, 32)])
                            pm_d = sum([matrix_data_t3[d][b_code]['pm'] for d in range(1, 32)])
                            npm_d = sum([matrix_data_t3[d][b_code]['non_pm'] for d in range(1, 32)])

                            p_tot = (tot_d / tot_c * 100) if tot_c > 0 else 0.0
                            p_pm = (pm_d / tot_c * 100) if tot_c > 0 else 0.0
                            p_npm = (npm_d / tot_c * 100) if tot_c > 0 else 0.0

                            branch_totals_t3[b_code] = {
                                'total': tot_c,
                                'drop': tot_d,
                                'pm': pm_d,
                                'non_pm': npm_d,
                                'p_tot': f"{p_tot:.2f}%",
                                'p_pm': f"{p_pm:.2f}%",
                                'p_npm': f"{p_npm:.2f}%"
                            }

                        month_thai = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
                        start_dt = pd.to_datetime(start_date_t3)
                        month_str = month_thai[start_dt.month - 1]
                        year_buddhist = start_dt.year + 543

                        # -------------------------------------------------------------------------
                        # 4. สร้างไฟล์ EXCEL (.xlsx)
                        # -------------------------------------------------------------------------
                        wb3 = Workbook()
                        ws3 = wb3.active
                        ws3.title = "Pressure Report Matrix"
                        ws3.views.sheetView[0].showGridLines = True

                        font_title = Font(name="Sarabun", size=13, bold=True, color="006100")
                        font_banner = Font(name="Sarabun", size=12, bold=True)
                        font_header = Font(name="Sarabun", size=9, bold=True)
                        font_header_purple = Font(name="Sarabun", size=11, bold=True, color="FFFFFF")
                        font_body = Font(name="Sarabun", size=9)
                        font_total = Font(name="Sarabun", size=9, bold=True)
                        font_total_red = Font(name="Sarabun", size=9, bold=True, color="FF0000")
                        font_total_blue = Font(name="Sarabun", size=9, bold=True, color="0000FF")

                        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        align_right = Alignment(horizontal="right", vertical="center")
                        align_left = Alignment(horizontal="left", vertical="center")

                        thin_border = Border(
                            left=Side(style="thin", color="000000"), right=Side(style="thin", color="000000"),
                            top=Side(style="thin", color="000000"), bottom=Side(style="thin", color="000000")
                        )

                        fill_green_banner = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")
                        fill_yellow_banner = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
                        fill_purple = PatternFill(start_color="E000E0", end_color="E000E0", fill_type="solid")
                        fill_yellow_cell = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

                        last_col_idx = 1 + (len(branches_config) * 8)
                        last_col_letter_t3 = get_column_letter(last_col_idx)

                        ws3.merge_cells(f"A1:{last_col_letter_t3}1")
                        ws3["A1"] = "รายงานการตกของ แรงดันไอน้ำปลายทาง ของบอยเลอร์ แบบเปรียบเทียบ"
                        ws3["A1"].font = font_title
                        ws3["A1"].alignment = align_center
                        ws3["A1"].fill = fill_green_banner

                        ws3.merge_cells(f"A2:{last_col_letter_t3}2")
                        ws3["A2"] = f"ประจำเดือน {month_str} {year_buddhist}"
                        ws3["A2"].font = font_banner
                        ws3["A2"].alignment = align_center
                        ws3["A2"].fill = fill_yellow_banner

                        ws3.merge_cells("A3:A5")
                        ws3["A3"] = "วันที่"
                        ws3["A3"].font = font_header_purple
                        ws3["A3"].alignment = align_center
                        ws3["A3"].fill = fill_purple
                        ws3["A3"].border = thin_border
                        ws3["A4"].border = thin_border
                        ws3["A5"].border = thin_border

                        col_idx = 2
                        for b in branches_config:
                            st_c = get_column_letter(col_idx)
                            en_c = get_column_letter(col_idx + 7)

                            ws3.merge_cells(f"{st_c}3:{en_c}3")
                            ws3[f"{st_c}3"] = b["code"]
                            ws3[f"{st_c}3"].font = font_header_purple
                            ws3[f"{st_c}3"].alignment = align_center
                            ws3[f"{st_c}3"].fill = fill_purple

                            c_cnt = get_column_letter(col_idx)
                            c_drp_st = get_column_letter(col_idx + 1)
                            c_drp_en = get_column_letter(col_idx + 3)
                            c_pct_st = get_column_letter(col_idx + 4)
                            c_pct_en = get_column_letter(col_idx + 6)
                            c_rem = get_column_letter(col_idx + 7)

                            ws3[f"{c_cnt}4"] = "นับทั้งหมด"
                            ws3.merge_cells(f"{c_drp_st}4:{c_drp_en}4")
                            ws3[f"{c_drp_st}4"] = "แรงดันตก (ครั้ง)"
                            ws3.merge_cells(f"{c_pct_st}4:{c_pct_en}4")
                            ws3[f"{c_pct_st}4"] = "แรงดันตก (%)"
                            ws3[f"{c_rem}4"] = "หมายเหตุ"

                            for c_i in range(col_idx, col_idx + 8):
                                cell_h = ws3[f"{get_column_letter(c_i)}4"]
                                cell_h.font = font_header_purple
                                cell_h.alignment = align_center
                                cell_h.fill = fill_purple
                                cell_h.border = thin_border

                            sub_cols = [
                                "จำนวน\n(ครั้ง)", "ตกทั้งหมด", "ตกตาม\nเงื่อนไขPM", "เกินนอกเหนือ\nจากการPM",
                                "ตกทั้งหมด", "ตกตาม\nเงื่อนไขPM", "เกินนอกเหนือ\nจากการPM", ""
                            ]
                            for i, sh in enumerate(sub_cols):
                                cell_ref = f"{get_column_letter(col_idx + i)}5"
                                ws3[cell_ref] = sh
                                ws3[cell_ref].font = font_header_purple
                                ws3[cell_ref].alignment = align_center
                                ws3[cell_ref].fill = fill_purple
                                ws3[cell_ref].border = thin_border

                            for c_i in range(col_idx, col_idx + 8):
                                ws3[f"{get_column_letter(c_i)}3"].border = thin_border

                            col_idx += 8

                        ws3.row_dimensions[1].height = 25
                        ws3.row_dimensions[2].height = 22
                        ws3.row_dimensions[3].height = 20
                        ws3.row_dimensions[4].height = 20
                        ws3.row_dimensions[5].height = 25

                        current_row = 6
                        for day in range(1, 32):
                            ws3[f"A{current_row}"] = day
                            ws3[f"A{current_row}"].font = font_header
                            ws3[f"A{current_row}"].alignment = align_center
                            ws3[f"A{current_row}"].border = thin_border

                            c_idx = 2
                            for b in branches_config:
                                item = matrix_data_t3[day][b['code']]
                                c_tot = ws3[f"{get_column_letter(c_idx)}{current_row}"]
                                c_drp = ws3[f"{get_column_letter(c_idx+1)}{current_row}"]
                                c_pm = ws3[f"{get_column_letter(c_idx+2)}{current_row}"]
                                c_npm = ws3[f"{get_column_letter(c_idx+3)}{current_row}"]
                                c_pct_drp = ws3[f"{get_column_letter(c_idx+4)}{current_row}"]
                                c_pct_pm = ws3[f"{get_column_letter(c_idx+5)}{current_row}"]
                                c_pct_npm = ws3[f"{get_column_letter(c_idx+6)}{current_row}"]
                                c_rem = ws3[f"{get_column_letter(c_idx+7)}{current_row}"]

                                if item['has_data']:
                                    tot_v = item['total']
                                    drp_v = item['drop']
                                    pm_v = item['pm']
                                    npm_v = item['non_pm']

                                    c_tot.value = tot_v
                                    c_drp.value = drp_v
                                    c_pm.value = pm_v
                                    c_npm.value = npm_v

                                    c_pct_drp.value = f"{(drp_v / tot_v * 100):.2f}%" if tot_v > 0 else "0.00%"
                                    c_pct_pm.value = f"{(pm_v / tot_v * 100):.2f}%" if tot_v > 0 else "0.00%"
                                    c_pct_npm.value = f"{(npm_v / tot_v * 100):.2f}%" if tot_v > 0 else "0.00%"
                                    c_rem.value = item['remark']
                                else:
                                    c_tot.value, c_drp.value, c_pm.value, c_npm.value = "", "", "", ""
                                    c_pct_drp.value, c_pct_pm.value, c_pct_npm.value, c_rem.value = "", "", "", ""

                                for yellow_c in [c_tot, c_drp, c_pm, c_npm]:
                                    yellow_c.font = font_total
                                    yellow_c.alignment = align_center if yellow_c == c_tot else align_right
                                    yellow_c.fill = fill_yellow_cell
                                    yellow_c.border = thin_border
                                    if isinstance(yellow_c.value, (int, float)):
                                        yellow_c.number_format = '#,##0.00' if yellow_c == c_tot or yellow_c == c_drp else '0'

                                for white_c in [c_pct_drp, c_pct_pm, c_pct_npm]:
                                    white_c.font = font_total
                                    white_c.alignment = align_right
                                    white_c.border = thin_border

                                c_rem.font = font_body
                                c_rem.alignment = align_left
                                c_rem.border = thin_border

                                c_idx += 8
                            current_row += 1

                        # 🎯 แถว รวม (Excel)
                        ws3[f"A{current_row}"] = "รวม"
                        ws3[f"A{current_row}"].font = font_total
                        ws3[f"A{current_row}"].alignment = align_center
                        ws3[f"A{current_row}"].border = thin_border

                        c_idx = 2
                        for b in branches_config:
                            bt = branch_totals_t3[b['code']]
                            c_tot = ws3[f"{get_column_letter(c_idx)}{current_row}"]
                            c_drp = ws3[f"{get_column_letter(c_idx+1)}{current_row}"]
                            c_pm = ws3[f"{get_column_letter(c_idx+2)}{current_row}"]
                            c_npm = ws3[f"{get_column_letter(c_idx+3)}{current_row}"]
                            c_pct_drp = ws3[f"{get_column_letter(c_idx+4)}{current_row}"]
                            c_pct_pm = ws3[f"{get_column_letter(c_idx+5)}{current_row}"]
                            c_pct_npm = ws3[f"{get_column_letter(c_idx+6)}{current_row}"]
                            c_rem = ws3[f"{get_column_letter(c_idx+7)}{current_row}"]

                            c_tot.value = bt['total'] if bt['total'] > 0 else "-"
                            c_drp.value = bt['drop'] if bt['drop'] > 0 else "-"
                            c_pm.value = bt['pm'] if bt['pm'] > 0 else "-"
                            c_npm.value = bt['non_pm'] if bt['non_pm'] > 0 else "-"

                            c_pct_drp.value = bt['p_tot']
                            c_pct_pm.value = bt['p_pm']
                            c_pct_npm.value = bt['p_npm']
                            c_rem.value = ""

                            for yellow_c in [c_tot, c_drp, c_pm, c_npm]:
                                yellow_c.font = font_total
                                yellow_c.alignment = align_center if yellow_c == c_tot else align_right
                                yellow_c.border = thin_border
                                if isinstance(yellow_c.value, (int, float)):
                                    yellow_c.number_format = '#,##0'

                            c_pct_drp.font = font_total_red
                            c_pct_drp.alignment = align_right
                            c_pct_drp.border = thin_border

                            c_pct_pm.font = font_total
                            c_pct_pm.alignment = align_right
                            c_pct_pm.border = thin_border

                            c_pct_npm.font = font_total_blue
                            c_pct_npm.alignment = align_right
                            c_pct_npm.border = thin_border

                            c_rem.border = thin_border

                            c_idx += 8

                        ws3.column_dimensions['A'].width = 8
                        for c in range(2, col_idx):
                            ws3.column_dimensions[get_column_letter(c)].width = 13

                        excel_buffer_t3 = io.BytesIO()
                        wb3.save(excel_buffer_t3)
                        excel_data_t3 = excel_buffer_t3.getvalue()

                        # -------------------------------------------------------------------------
                        # 5. สร้าง HTML สำหรับสั่งปริ้นท์
                        # -------------------------------------------------------------------------
                        header_row1_t3 = "".join([f'<th colspan="8" style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:4px;font-size:11px;text-align:center;">{b["code"]}</th>' for b in branches_config])
                        
                        header_row2_t3 = ""
                        for _ in branches_config:
                            header_row2_t3 += '<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:3px;font-size:9px;">นับทั้งหมด</th>'
                            header_row2_t3 += '<th colspan="3" style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:3px;font-size:9px;">แรงดันตก (ครั้ง)</th>'
                            header_row2_t3 += '<th colspan="3" style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:3px;font-size:9px;">แรงดันตก (%)</th>'
                            header_row2_t3 += '<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:3px;font-size:9px;">หมายเหตุ</th>'

                        header_row3_t3 = ""
                        for _ in branches_config:
                            header_row3_t3 += '<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:35px;">จำนวน<br>(ครั้ง)</th>'
                            header_row3_t3 += '<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:35px;">ตกทั้งหมด</th>'
                            header_row3_t3 += '<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:35px;">ตกตาม<br>เงื่อนไขPM</th>'
                            header_row3_t3 += '<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:40px;">เกินนอกเหนือ<br>จากการPM</th>'
                            header_row3_t3 += '<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:35px;">ตกทั้งหมด</th>'
                            header_row3_t3 += '<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:35px;">ตกตาม<br>เงื่อนไขPM</th>'
                            header_row3_t3 += '<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:40px;">เกินนอกเหนือ<br>จากการPM</th>'
                            header_row3_t3 += '<th style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:2px;font-size:8px;width:90px;"></th>'

                        body_rows_t3 = ""
                        for day in range(1, 32):
                            body_rows_t3 += f'<tr><td style="border:1px solid #000;padding:2px;text-align:center;font-size:9px;font-weight:bold;">{day}</td>'
                            for b in branches_config:
                                item = matrix_data_t3[day][b['code']]
                                if item['has_data']:
                                    tot_v = item['total']
                                    drp_v = item['drop']
                                    pm_v = item['pm']
                                    npm_v = item['non_pm']

                                    c_tot_s = f"{tot_v:,.2f}"
                                    c_drp_s = f"{drp_v:,.2f}"
                                    c_pm_s = f"{int(pm_v)}"
                                    c_npm_s = f"{int(npm_v)}"

                                    p_drp_s = f"{(drp_v / tot_v * 100):.2f}%" if tot_v > 0 else "0.00%"
                                    p_pm_s = f"{(pm_v / tot_v * 100):.2f}%" if tot_v > 0 else "0.00%"
                                    p_npm_s = f"{(npm_v / tot_v * 100):.2f}%" if tot_v > 0 else "0.00%"
                                    rem_s = item['remark']
                                else:
                                    c_tot_s, c_drp_s, c_pm_s, c_npm_s, p_drp_s, p_pm_s, p_npm_s, rem_s = "", "", "", "", "", "", "", ""

                                body_rows_t3 += f'<td style="background-color:#FFFF00;border:1px solid #000;padding:2px;text-align:center;font-size:9px;font-weight:bold;">{c_tot_s}</td>'
                                body_rows_t3 += f'<td style="background-color:#FFFF00;border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{c_drp_s}</td>'
                                body_rows_t3 += f'<td style="background-color:#FFFF00;border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{c_pm_s}</td>'
                                body_rows_t3 += f'<td style="background-color:#FFFF00;border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{c_npm_s}</td>'

                                body_rows_t3 += f'<td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{p_drp_s}</td>'
                                body_rows_t3 += f'<td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{p_pm_s}</td>'
                                body_rows_t3 += f'<td style="border:1px solid #000;padding:2px;text-align:right;font-size:9px;font-weight:bold;">{p_npm_s}</td>'
                                body_rows_t3 += f'<td style="border:1px solid #000;padding:2px;text-align:left;font-size:9px;">{rem_s}</td>'

                            body_rows_t3 += '</tr>'

                        # 🎯 แถว รวม (HTML สั่งปริ้นท์)
                        total_row_html_t3 = '<tr><td style="border:1px solid #000;padding:3px;text-align:center;font-size:10px;font-weight:bold;">รวม</td>'
                        for b in branches_config:
                            bt = branch_totals_t3[b['code']]
                            t_cnt_s = f"{int(bt['total']):,}" if bt['total'] > 0 else "-"
                            t_drp_s = f"{int(bt['drop']):,}" if bt['drop'] > 0 else "-"
                            t_pm_s = f"{int(bt['pm']):,}" if bt['pm'] > 0 else "-"
                            t_npm_s = f"{int(bt['non_pm']):,}" if bt['non_pm'] > 0 else "-"
                            
                            total_row_html_t3 += f'<td style="border:1px solid #000;padding:3px;text-align:center;font-size:9px;font-weight:bold;">{t_cnt_s}</td>'
                            total_row_html_t3 += f'<td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{t_drp_s}</td>'
                            total_row_html_t3 += f'<td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{t_pm_s}</td>'
                            total_row_html_t3 += f'<td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{t_npm_s}</td>'
                            total_row_html_t3 += f'<td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;color:red;">{bt["p_tot"]}</td>'
                            total_row_html_t3 += f'<td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;">{bt["p_pm"]}</td>'
                            total_row_html_t3 += f'<td style="border:1px solid #000;padding:3px;text-align:right;font-size:9px;font-weight:bold;color:blue;">{bt["p_npm"]}</td>'
                            total_row_html_t3 += f'<td style="border:1px solid #000;padding:3px;text-align:left;font-size:9px;"></td>'
                        total_row_html_t3 += '</tr>'

                        table_full_html_t3 = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Print Pressure Report Matrix</title>
    <style>
        @page {{ size: A4 landscape; margin: 4mm; }}
        body {{ font-family: 'Sarabun', Tahoma, sans-serif; margin: 0; padding: 5px; }}
        .header-banner1 {{ background-color: #00FF00; color: #006100; text-align: center; font-size: 16px; font-weight: bold; padding: 6px; border: 1px solid #000; }}
        .header-banner2 {{ background-color: #FFFF00; color: #000; text-align: center; font-size: 14px; font-weight: bold; padding: 5px; border: 1px solid #000; margin-bottom: 4px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ font-family: 'Sarabun', Tahoma, sans-serif; }}
    </style>
</head>
<body>
    <div class="header-banner1">รายงานการตกของ แรงดันไอน้ำปลายทาง ของบอยเลอร์ แบบเปรียบเทียบ</div>
    <div class="header-banner2">ประจำเดือน {month_str} {year_buddhist}</div>
    <table>
        <thead>
            <tr>
                <th rowspan="3" style="background-color:#E000E0;color:#FFF;border:1px solid #000;padding:3px;font-size:10px;width:35px;">วันที่</th>
                {header_row1_t3}
            </tr>
            <tr>
                {header_row2_t3}
            </tr>
            <tr>
                {header_row3_t3}
            </tr>
        </thead>
        <tbody>
            {body_rows_t3}
            {total_row_html_t3}
        </tbody>
    </table>
</body>
</html>"""

                        json_print_html_t3 = json.dumps(table_full_html_t3)
                        print_btn_label_t3 = "🖨️ ปริ้นเอกสารรายงาน (Tab 3)" if current_role in ["admin", "manager"] else "🖨️ ปริ้นเอกสารรายงาน"

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.download_button(
                                label="📥 Export เป็น Excel (.xlsx)",
                                data=excel_data_t3,
                                file_name=f"Summary_Pressure_Report_{start_date_t3}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key="dl_t3"
                            )
                        with col_btn2:
                            components.html(f"""
                            <body style="margin:0;padding:0;overflow:hidden;">
                                <button onclick="openPrintPreview3()" style="width:100%; height:38px; background-color:#F0F2F6; border:1px solid #C4C7D0; border-radius:8px; color:#31333F; font-family:sans-serif; font-size:14px; font-weight:500; cursor:pointer; box-sizing:border-box;">
                                    {print_btn_label_t3}
                                </button>
                            </body>
                            <script>
                            function openPrintPreview3(){{
                                var htmlData = {json_print_html_t3};
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
                            
                            b_name_select = str(r.get('branch_name') or '')
                            record_map_t3 = {f"ID: {r[pk_col_t3]} | วันที่: {r.get('record_date')} | สาขา: {b_name_select}": (r[pk_col_t3], r) for r in raw_data_t3}
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
                                    if st.button("💾 บันทึกการแก้ไข (Update Tab 3)", key=f"btn_up_t3_{target_pk_t3}", use_container_width=True):
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
                                    if st.button("🗑️ ลบรายการนี้ (Delete Tab 3)", type="primary", use_container_width=True, key=f"del_btn_t3_{target_pk_t3}"):
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