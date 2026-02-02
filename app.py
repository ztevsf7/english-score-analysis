import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="英语成绩细分分析", layout="wide")

# --- 密码保护 (可选) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.text_input("请输入访问口令", type="password", on_change=lambda: st.session_state.update({"password_correct": st.session_state.password == "123456"}), key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()

st.title("🎯 英语全题型多维成绩分析系统")

# --- 侧边栏 ---
st.sidebar.header("📂 数据上传")
uploaded_files = st.sidebar.file_uploader("支持一次性拖入多个 Excel/CSV", type=['xlsx', 'csv'], accept_multiple_files=True)

def process_data(files):
    all_records = []
    found_subjects = set()
    
    if not files:
        return None, []

    for file in files:
        exam_name = os.path.splitext(file.name)[0]
        try:
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            
            # 清洗列名
            df.columns = [str(c).replace('\n', '').strip() for c in df.columns]
            
            name_col = next((c for c in df.columns if '姓名' in c), None)
            total_score_col = next((c for c in df.columns if '最新得分' in c or '总分' in c), None)
            
            # 定义题型关键词
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
        return pd.concat(all_records, ignore_index=True), list(found_subjects)
    return None, []

# --- 运行逻辑 ---
df_all, subjects = process_data(uploaded_files)

if df_all is not None:
    # 强制转换数值
    for col in subjects + ['总分']:
        df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

    tab1, tab2 = st.tabs(["👤 个人追踪", "📊 班级分析"])

    with tab1:
        student = st.selectbox("选择学生", sorted(df_all['姓名'].unique()))
        s_data = df_all[df_all['姓名'] == student].sort_values('考试名称')
        
        # 指标展示
        st.subheader(f"{student} 的各题型均分")
        m_cols = st.columns(len(subjects) + 1)
        m_cols[0].metric("总分均值", round(s_data['总分'].mean(), 1))
        for i, sub in enumerate(subjects):
            m_cols[i+1].metric(sub.split('（')[0], round(s_data[sub].mean(), 1))

        # 趋势图
        fig = go.Figure()
        for sub in subjects:
            fig.add_trace(go.Scatter(x=s_data['考试名称'], y=s_data[sub], name=sub, mode='lines+markers'))
        fig.update_layout(title="各题型得分走势", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("各题型全班平均水平 (雷达图)")
        avg_values = df_all[subjects].mean().tolist()
        fig_radar = go.Figure(data=go.Scatterpolar(r=avg_values, theta=subjects, fill='toself'))
        st.plotly_chart(fig_radar, use_container_width=True)
        
        st.write("### 全班统计明细 (均分与方差)")
        # 增加方差分析
        stats_df = df_all.groupby('姓名')[['总分'] + subjects].agg(['mean', 'std']).round(2)
        st.dataframe(stats_df)
else:
    st.info("请先在左侧上传学生成绩单文件。")