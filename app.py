@st.cache_data
def load_and_enrich_data():
    try:
        # تجربة القراءة بترميز utf-8 أولاً، ثم cp1252 (الخاص بـ Excel)
        try:
            df = pd.read_csv("Data.csv", encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv("Data.csv", encoding='cp1252')
            
        df.columns = [c.strip() for c in df.columns]
        df = pd.merge(df, mapping_df, on='Notice Type', how='left')
        df = df[~df['Broadcasting_Category'].isin(['Withdrawal'])]
        return df
    except Exception as e:
        st.error(f"Error loading Data.csv: {e}")
        return pd.DataFrame()
