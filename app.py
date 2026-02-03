import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="英语成绩多维分析", layout="wide")

# --- 核心设置 ---
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

st.title("🎯🤏⌚ 英语全题型多维成绩分析系统")

# --- 数据处理逻辑 ---
@st.cache_data 
def process_data(files):
    all_records = []
    found_subjects = set()
    if not files: return None, []

    for file in files:
        exam_name = os.path.splitext(file.name)[0]
        try:
            # 1. 智能读取：先不指定表头，全部读进来
            if file.name.endswith('.csv'):
                df_raw = pd.read_csv(file, header=None)
            else:
                df_raw = pd.read_excel(file, header=None)
            
            # 2. 寻找表头行：扫描前10行，寻找包含"姓名"的行
            header_row_idx = -1
            for i in range(min(10, len(df_raw))):
                # 将这一行转为字符串，检查是否包含关键字
                row_values = [str(x) for x in df_raw.iloc[i].values]
                if "姓名" in row_values or "Name" in row_values:
                    header_row_idx = i
                    break
            
            if header_row_idx == -1:
                st.warning(f"⚠️ 文件 {file.name} 中未找到'姓名'列，跳过。")
                continue

            # 3. 重置表头：将找到的那一行设为列名
            df = df_raw.iloc[header_row_idx + 1:].copy()
            df.columns = df_raw.iloc[header_row_idx].values
            
            # 4. 常规清洗
            df.columns = [str(c).replace('\n', '').strip() for c in df.columns]
            
            # 定位关键列
            name_col = next((c for c in df.columns if '姓名' in c), None)
            
            # 扩充总分关键词：增加了 '科目成绩', '成绩'
            total_score_col = next((c for c in df.columns if any(k in c for k in ['最新得分', '总分', '科目成绩', 'Score'])), None)
            
            # 扩充题型关键词：增加了 '单词', '写作'
            keywords = ['听力', '阅读', '五', '完形', '语法', '文', '续写', '填空', '单词', '写作']
            current_subjects = [c for c in df.columns if any(k in c for k in keywords) and '排名' not in c and '总' not in c]
            
            # 如果没找到总分列，尝试用“客观题+主观题”计算（针对你的新表结构）
            if not total_score_col and '客观题成绩' in df.columns and '主观题成绩' in df.columns:
                df['计算总分'] = pd.to_numeric(df['客观题成绩'], errors='coerce') + pd.to_numeric(df['主观题成绩'], errors='coerce')
                total_score_col = '计算总分'

            if name_col and total_score_col:
                # 提取数据
                cols_to_keep = [name_col, total_score_col] + current_subjects
                sub_df = df[cols_to_keep].copy()
                
                # 重命名以便统一合并
                sub_df.rename(columns={name_col: '姓名', total_score_col: '总分'}, inplace=True)
                sub_df['考试名称'] = exam_name
                
                # 确保是有效数据行（排除下面的空行）
                sub_df.dropna(subset=['姓名'], inplace=True)
                
                all_records.append(sub_df)
                for s in current_subjects: found_subjects.add(s)
            else:
                st.warning(f"⚠️ 文件 {file.name} 缺少关键列（姓名或总分），已跳过。")

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
st.sidebar.header("📁 数据上传")
uploaded_files = st.sidebar.file_uploader("上传成绩单 (支持期中/期末等任意命名)", type=['xlsx', 'csv'], accept_multiple_files=True)

df_all, subjects = process_data(uploaded_files)

if df_all is not None:
    # --- 新增：考试顺序手动调整 ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 调整考试先后顺序")
    all_exams = list(df_all['考试名称'].unique())
    # 让用户自己选择排序顺序
    sorted_exams = st.sidebar.multiselect(
        "请按考试先后顺序点击选择（先选的排在前面）", 
        options=all_exams, 
        default=all_exams
    )

    if not sorted_exams:
        st.warning("请在左侧侧边栏选择考试顺序以显示图表。")
        st.stop()

    tab1, tab2 = st.tabs(["👤 个人追踪分析", "📊 班级整体分析"])

    with tab1:
        student_list = sorted(df_all['姓名'].unique())
        student = st.selectbox("选择学生姓名", student_list)
        
        # 根据用户定义的顺序筛选和排序数据
        s_data = df_all[df_all['姓名'] == student].copy()
        # 将考试名称转为分类类型，并按照 sorted_exams 的顺序排序
        s_data['考试名称'] = pd.Categorical(s_data['考试名称'], categories=sorted_exams, ordered=True)
        s_data = s_data.sort_values('考试名称')
        
        ranking_cols = [s for s in subjects if '排名' in s]
        score_cols = [s for s in subjects if '排名' not in s]

        # 1. 总分趋势
        st.subheader(f"📈 {student} - 总分变化趋势")
        fig_total = px.line(s_data, x='考试名称', y='总分', markers=True, text='总分')
        fig_total.update_traces(textposition="top center", line_color="#EF553B")
        st.plotly_chart(fig_total, use_container_width=True)

        # 2. 细分得分走势
        st.subheader("📋 各项细分题型得分走势")
        if score_cols:
            fig_sub = go.Figure()
            for sub in score_cols:
                fig_sub.add_trace(go.Scatter(x=s_data['考试名称'], y=s_data[sub], name=sub, mode='lines+markers'))
            fig_sub.update_layout(hovermode="x unified")
            st.plotly_chart(fig_sub, use_container_width=True)

        # 3. 排名变动详情
        if ranking_cols:
            st.subheader("🏆 排名变动详情")
            st.dataframe(s_data[['考试名称'] + ranking_cols], hide_index=True, use_container_width=True)
            
        # 4. 统计数据
        st.write("#### 个人数据统计")
        valid_cols = [c for c in ['总分'] + score_cols + ranking_cols if c in s_data.columns]
        st.table(s_data[valid_cols].agg(['mean', 'std']).round(2).T.rename(columns={'mean':'平均值', 'std':'波动值'}))

    with tab2:
        st.subheader("全班均分对比")
        class_avg = df_all.groupby('考试名称')[['总分'] + score_cols].mean().reindex(sorted_exams).round(1)
        st.line_chart(class_avg['总分'])
        st.dataframe(class_avg)

else:
    st.info("👋 请在左侧上传 Excel/CSV 文件。文件名可以叫'期中考试'、'第一次月考'等任意名称。")


