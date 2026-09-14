import streamlit as st
from database import get_db_connection
from datetime import date

def render_home_dashboard(branch_name, branch_id, role):
    st.markdown("## 🏠 แดชบอร์ดสรุปข้อมูลประจำวัน (Daily Dashboard)")
    st.write(f"ยินดีต้อนรับคุณ **{st.session_state.full_name}** | ประจำสาขา: **{branch_name}**")
    st.markdown("---")

    # ---------------------------------------------------------
    # 📊 ส่วนที่ 1: Metric Cards (ตัวเลขสรุปผล)
    # ---------------------------------------------------------
    st.markdown("#### 📈 ภาพรวมข้อมูลวันนี้")
    
    # ตัวอย่างการจำลองตัวเลข (ดึงจริงจาก DB ได้ในอนาคต)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="⚙️ เครื่องจักรเบรกดาวน์", value="2 เครื่อง", delta="-1 เครื่องจากเมื่อวาน")
    with col2:
        st.metric(label="🚚 การใช้น้ำมัน (ลิตร)", value="145 L", delta="ปกติ", delta_color="off")
    with col3:
        st.metric(label="💨 แรงดันไอน้ำบอยเลอร์", value="7.5 Bar", delta="+0.2 Bar")
    with col4:
        st.metric(label="🔥 เชื้อเพลิงบอยเลอร์", value="3,200 kg", delta="-150 kg")

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 🚀 ส่วนที่ 2: Quick Access (ทางลัด)
    # ---------------------------------------------------------
    st.markdown("#### 🚀 ทางลัดเข้าสู่ระบบ")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        with st.container(border=True):
            st.markdown("### 📝 บันทึกข้อมูล")
            st.write("เข้าสู่หน้าต่างบันทึกข้อมูลประจำวันของเครื่องจักรและเชื้อเพลิง")
            if st.button("ไปที่หน้าบันทึกข้อมูล ➔", use_container_width=True, type="primary"):
                st.session_state['sidebar_main'] = "📝 บันทึกข้อมูลประจำวัน"
                st.rerun()

    with c2:
        with st.container(border=True):
            st.markdown("### 📑 รายงานรวม")
            st.write("ดูรายงานสรุปผล ย้อนหลัง และตรวจสอบข้อมูลย้อนหลังทั้งหมด")
            if st.button("ไปที่หน้ารายงาน ➔", use_container_width=True):
                st.session_state['sidebar_main'] = "📑 รายงานรวม (All Report)" if role == 'admin' else "📑 รายงานประจำสาขา"
                st.rerun()

    if role in ['admin', 'manager']:
        with c3:
            with st.container(border=True):
                st.markdown("### 🛠️ จัดการอุปกรณ์")
                st.write("เพิ่ม แก้ไข หรือระงับการใช้งานเครื่องจักรและรถยนต์ในระบบ")
                if st.button("จัดการอุปกรณ์ ➔", use_container_width=True):
                    st.session_state['sidebar_main'] = "🛠️ จัดการข้อมูลอุปกรณ์"
                    st.rerun()