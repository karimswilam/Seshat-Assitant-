# --- محرك التحليل الذكي المحدث ---
if query and not df.empty:
    q = query.lower()
    st.info(f"🔍 جاري تحليل الطلب: {query}")
    
    # 1. تنظيف الداتا لضمان دقة الفلترة
    f_df = df.copy()
    
    # 2. منطق استخراج الدولة (Adm) - بيدعم الفرانكو والعربي والإنجليزي
    if any(w in q for w in ['ars', 'سعودية', 'saudi']): 
        f_df = f_df[f_df['Adm'] == 'ARS']
    elif any(w in q for w in ['egy', 'مصر', 'egypt']): 
        f_df = f_df[f_df['Adm'] == 'EGY']
    
    # 3. منطق استخراج نوع الإشعار (Notice Type)
    if 'gs1' in q: f_df = f_df[f_df['Notice Type'] == 'GS1']
    if 'gs2' in q: f_df = f_df[f_df['Notice Type'] == 'GS2']
    if 'ds1' in q: f_df = f_df[f_df['Notice Type'] == 'DS1']
    if 'ds2' in q: f_df = f_df[f_df['Notice Type'] == 'DS2']

    # 4. الفرق الجوهري: هل المستخدم عايز "عدد" ولا "عرض بيانات"؟
    statistical_keywords = ['kam', '3dd', 'count', 'total', 'كم', 'عدد', 'إجمالي']
    
    if any(w in q for w in statistical_keywords):
        # لو السؤال عن العدد (Analytical Response)
        result_count = len(f_df)
        st.success(f"📊 الإجابة: العدد الإجمالي هو **{result_count}** سجل.")
        
        # رد صوتي بالأرقام
        tts_msg = f"العدد الإجمالي هو {result_count}"
        tts = gTTS(text=tts_msg, lang='ar')
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        st.audio(audio_io.getvalue(), format="audio/mp3")
    else:
        # لو السؤال عرض بيانات (Display Response)
        st.success(f"🤖 لقيتلك {len(f_df)} سجل هندسي:")
        st.dataframe(f_df.head(100)) # عرض أول 100 سجل بدلاً من سطر واحد

    # 5. الرسوم البيانية للتأكيد البصري
    if not f_df.empty:
        st.subheader("📈 توزيع البيانات المفلترة")
        st.bar_chart(f_df['Notice Type'].value_counts())
