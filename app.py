import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="英语成绩多维分析", layout="wide")

# --- 核心设置：在这里修改密码 ---
INIT_PASSWORD = "75097509"

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
@st.cache_data 
def process_data(files):
    all_records = []
    found_subjects = set()
    if not files: return None, []

    for file in files:
        exam_name = os.path.splitext(file.name)[0]
        try:
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            df.columns = [str(c).replace('\n', '').strip() for c in df.columns]
            
            # 1. 识别姓名
            name_col = next((c for c in df.columns if '姓名' in c), None)
            
            # 2. 识别总分
            total_score_col = next((c for c in df.columns if '最新得分' in c or '总分' in c or '科目成绩' in c), None)
            
            # 3. 识别特定分析项目
            keywords = ['客观', '主观', '排名', '写作', '填空']
            
            # 筛选列
            current_subjects = [c for c in df.columns if any(k in c for k in keywords)]
            
            if name_col and total_score_col:
                sub_df = df[[name_col, total_score_col] + current_subjects].copy()
                sub_df.rename(columns={name_col: '姓名', total_score_col: '总分'}, inplace=True)
                
                # --- 特殊处理：将 "写作" 重命名为 "写作1" ---
                if '写作' in sub_df.columns:
                    sub_df.rename(columns={'写作': '写作1'}, inplace=True)
                    # 更新列表以匹配新列名
                    current_subjects = [c if c != '写作' else '写作1' for c in current_subjects]
                
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
        student_list = sorted(df_all['姓名'].unique())
        if student_list:
            student = st.selectbox("选择学生姓名", student_list)
            s_data = df_all[df_all['姓名'] == student].sort_values('考试名称')
            
            # --- 数据分离：区分“排名类”和“分数类” ---
            ranking_cols = [s for s in subjects if '排名' in s]
            score_cols = [s for s in subjects if '排名' not in s]

            # 1. 总分趋势 (保持不变)
            st.subheader(f"📈 {student} - 总分变化趋势")
            fig_total = px.line(s_data, x='考试名称', y='总分', markers=True, 
                                text='总分', title="历次考试总分走势")
            fig_total.update_traces(textposition="top center", line_color="#EF553B")
            st.plotly_chart(fig_total, use_container_width=True)

            # 2. 细分题型得分走势 (仅展示分数，不含排名)
            st.subheader("📋 各项细分题型得分走势 (不含排名)")
            if score_cols:
                fig_sub = go.Figure()
                for sub in score_cols:
                    fig_sub.add_trace(go.Scatter(x=s_data['考试名称'], y=s_data[sub], name=sub, mode='lines+markers'))
                fig_sub.update_layout(hovermode="x unified")
                st.plotly_chart(fig_sub, use_container_width=True)
            else:
                st.info("暂无细分分数数据")

            # 3. 排名变动表格 (新增)
            if ranking_cols:
                st.subheader("🏆 排名变动详情")
                # 展示表格，隐藏索引，列宽自适应
                ranking_df = s_data[['考试名称'] + ranking_cols].copy()
                st.dataframe(ranking_df, hide_index=True, use_container_width=True)
            
            # 4. 统计数据
            st.write("#### 个人数据统计")
            # 统计表包含所有项目（分数+排名）
            cols_to_stat = ['总分'] + score_cols + ranking_cols
            valid_cols = [c for c in cols_to_stat if c in s_data.columns]
            
            p_stats = s_data[valid_cols].agg(['mean', 'std']).round(2).T
            p_stats.columns = ['平均值', '波动值(标准差)']
            st.table(p_stats)
        else:
            st.warning("未找到学生数据")

    with tab2:
        st.subheader("全班均分对比")
        if not df_all.empty:
            # 班级分析通常只关注分数均值，排名均值意义不大，但这里保持原样计算
            class_avg = df_all.groupby('考试名称')[['总分'] + subjects].mean().round(1)
            st.line_chart(class_avg['总分'])
            st.dataframe(class_avg)

else:
    st.info("👋 请上传 Excel/CSV 文件开始分析")
