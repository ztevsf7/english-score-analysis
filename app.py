import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="英语成绩多维分析", layout="wide")

# --- 核心设置：在这里修改密码 ---
INIT_PASSWORD = "75097509"  # <--- 在这里直接修改引号内的内容

def check_password():
    if "password_correct" not in st.session_state:
        st.sidebar.markdown("### 🔒 安全验证")
        pwd = st.sidebar.text_input("请输入访问口令", type="password")
        if st.sidebar.button("登录"):
            if pwd == INIT_PASSWORD:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.sidebar.error("密码错误")
        return False
    return True

if not check_password():
    st.info("请在左侧侧边栏输入密码以开始分析。")
    st.stop()

st.title("🎯  🤏🕖 英语全题型多维成绩分析系统")

# --- 数据处理逻辑 ---
@st.cache_data # 增加缓存，提高大数据量时的运行速度
def process_data(files):
    all_records = []
    found_subjects = set()
    if not files: return None, []

    for file in files:
        exam_name = os.path.splitext(file.name)[0]
        try:
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            df.columns = [str(c).replace('\n', '').strip() for c in df.columns]
            
            name_col = next((c for c in df.columns if '姓名' in c), None)
            total_score_col = next((c for c in df.columns if '最新得分' in c or '总分' in c), None)
            
            keywords = ['听力', '阅读', '五', '完形', '语法', '文', '续写', '填空']
            current_subjects = [c for c in df.columns if any(k in c for k in keywords) and '排名' not in c]
            
            if name_col and total_score_col:
                sub_df = df[[name_col, total_score_col] + current_subjects].copy()
                sub_df.rename(columns={name_col: '姓名', total_score_col: '总分'}, inplace=True)
                sub_df['考试名称'] = exam_name
                all_records.append(sub_df)
                for s in current_subjects: found_subjects.add(s)
        except Exception as e:
            st.error(f"解析 {file.name} 失败: {e}")
            
    if all_records:
        full_df = pd.concat(all_records, ignore_index=True)
        # 确保数值化
        for col in list(found_subjects) + ['总分']:
            full_df[col] = pd.to_numeric(full_df[col], errors='coerce')
        return full_df, list(found_subjects)
    return None, []

# --- 侧边栏 ---
uploaded_files = st.sidebar.file_uploader("上传成绩单", type=['xlsx', 'csv'], accept_multiple_files=True)

df_all, subjects = process_data(uploaded_files)

if df_all is not None:
    tab1, tab2 = st.tabs(["👤 个人追踪分析", "📊 班级整体分析"])

    with tab1:
        student = st.selectbox("选择学生姓名", sorted(df_all['姓名'].unique()))
        s_data = df_all[df_all['姓名'] == student].sort_values('考试名称')
        
        # 1. 总分趋势折线图 (新增)
        st.subheader(f"📈 {student} - 总分变化趋势")
        fig_total = px.line(s_data, x='考试名称', y='总分', markers=True, 
                            text='总分', title="历次考试总分走势")
        fig_total.update_traces(textposition="top center", line_color="#EF553B")
        st.plotly_chart(fig_total, use_container_width=True)

        # 2. 细分题型对比趋势图
        st.subheader("📋 各项细分题型得分走势")
        fig_sub = go.Figure()
        for sub in subjects:
            fig_sub.add_trace(go.Scatter(x=s_data['考试名称'], y=s_data[sub], name=sub, mode='lines+markers'))
        fig_sub.update_layout(hovermode="x unified")
        st.plotly_chart(fig_sub, use_container_width=True)

        # 3. 统计数据
        st.write("#### 个人均分与稳定性 (标准差越小越稳定)")
        p_stats = s_data[['总分'] + subjects].agg(['mean', 'std']).round(2).T
        p_stats.columns = ['平均分', '波动值(标准差)']
        st.table(p_stats)

    with tab2:
        st.subheader("全班均分对比")
        class_avg = df_all.groupby('考试名称')[['总分'] + subjects].mean().round(1)
        st.line_chart(class_avg['总分'])
        st.dataframe(class_avg)

else:

    st.info("👋 请上传 Excel/CSV 文件开始分析")
