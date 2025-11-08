import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time 

# --- Gemini AI ---
import google.generativeai as genai

# --- Streamlit ページの基本設定 ---
st.set_page_config(layout="wide") 
st.title("ドル円 AI経済指標カレンダー 🗓️")
st.write("Investing.comから「USD」「JPY」の「星3つ」の指標を自動取得します。")

# --- 1. Gemini AIのセットアップ ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    
    # (★ 診断結果に基づき 'models/gemini-2.5-flash' に変更 ★)
    model = genai.GenerativeModel(
        'models/gemini-2.5-flash',
        generation_config={"temperature": 0.1} 
    )
    gemini_ready = True
except Exception as e:
    st.error(f"❌ Geminiの初期化に失敗しました。APIキーが正しく設定されているか（.streamlit/secrets.toml）確認してください。 {e}")
    gemini_ready = False

# --- 2. スクレイピング関数 (Step 2) ---
# (変更なし)
def fetch_indicators():
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    url = "https://www.investing.com/economic-calendar/"
    
    indicator_list = [] 

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'economicCalendarData'})
        
        if table:
            rows = table.find_all('tr', {'class': 'js-event-item'})
            
            for row in rows:
                currency_tag = row.find('td', {'class': 'left flagCur'})
                currency = currency_tag.text.strip() if currency_tag else ""
                
                sentiment_tag = row.find('td', {'class': 'sentiment'})
                importance = sentiment_tag['data_img_key'] if sentiment_tag and 'data_img_key' in sentiment_tag.attrs else ""
                
                if (currency == "USD" or currency == "JPY") and (importance == "bull3"):
                    
                    time_tag = row.find('td', {'class': 'time'})
                    time_val = time_tag.text.strip() if time_tag else "N/A"
                    
                    event_tag = row.find('td', {'class': 'event'})
                    event_name = event_tag.text.strip() if event_tag else "N/A"
                    
                    forecast_tag = row.find('td', {'class': 'forecast'})
                    forecast_val = forecast_tag.text.strip() if forecast_tag else "N/A"
                    
                    actual_tag = row.find('td', {'class': 'actual'})
                    actual_val = actual_tag.text.strip() if actual_tag else "N/A"
                    
                    indicator_list.append({
                        "時刻": time_val,
                        "通貨": currency,
                        "指標名": event_name,
                        "予想": forecast_val,
                        "結果": actual_val
                    })
        
        return indicator_list 

    except requests.exceptions.RequestException as e:
        st.error(f"エラー: サイトにアクセスできませんでした。{e}") 
        return None

# --- 3. Gemini AI解説関数 (Step 3 & 4) ---
# (変更なし)
def get_gemini_analysis(indicator_name, forecast):
    prompt = f"""
    あなたはFXの専門アナリストです。
    以下の経済指標について、FX初心者にも分かりやすく「発表前の解説」をしてください。

    【ルール】
    * この指標が「何を示すか」を簡潔に説明してください。
    * 「予想」に対して「結果」が強い（良い）場合、ドル円相場（USD/JPY）にどのような影響（上昇/下落）が一般的か説明してください。
    * 「予想」に対して「結果」が弱い（悪い）場合、ドル円相場（USD/JPY）にどのような影響（上昇/下落）が一般的か説明してください。
    * 必ず簡潔に、箇条書きで3～4行程度でまとめてください。

    【経済指標】
    * 指標名: {indicator_name}
    * 予想値: {forecast}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI解説の生成に失敗しました: {e}"

# (変更なし)
def get_gemini_analysis_after(indicator_name, forecast, actual):
    prompt = f"""
    あなたは敏腕FXアナリストです。
    経済指標の結果が発表されたので、「速報解説」をしてください。

    【ルール】
    * 「予想」と「結果」を比較し、それが市場にとって「ポジティブ・サプライズ」「ネガティブ・サプライズ」「予想通り」のどれにあたるか判定してください。
    * その結果が、ドル円相場（USD/JPY）にどのような「瞬発的な影響」（上昇/下落圧力）を与えるかを、簡潔に断定的に解説してください。
    * 全体を2〜3行でまとめてください。

    【発表された指標】
    * 指標名: {indicator_name}
    * 予想値: {forecast}
    * 結果値: {actual}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI速報の生成に失敗しました: {e}"


# --- 4. Streamlit アプリ本体 ---
# (★ ここが正しいコード ★)
if st.button("最新の指標データを取得 ＆ AI解説"):
    
    with st.spinner('Investing.comからデータを取得中...'):
        time.sleep(1) 
        indicators = fetch_indicators()

    if indicators is not None:
        
        if len(indicators) > 0:
            st.success(f"{len(indicators)}件の重要指標が見つかりました！")
            
            df = pd.DataFrame(indicators)
            st.dataframe(df, use_container_width=True) 
            
            st.subheader("🤖 Geminiによる AI解説")
            
            if gemini_ready: 
                
                for index, row in df.iterrows():
                    indicator_name = row['指標名']
                    forecast = row['予想']
                    actual = row['結果']
                    
                    st.divider() 
                    st.markdown(f"**【{row['時刻']}】 {indicator_name}**")
                    
                    if actual == "N/A" or actual == "" or actual == " ":
                        st.markdown(f"**(発表前)** 予想: {forecast}")
                        with st.spinner(f"「発表前」AI解説を生成中..."):
                            analysis = get_gemini_analysis(indicator_name, forecast)
                            st.markdown(analysis) 
                    
                    else:
                        st.markdown(f"**(発表済)** 予想: {forecast} / **結果: {actual}**")
                        with st.spinner(f"「発表後」AI速報を生成中..."):
                            # ★ 正しくは _after() を呼び、結果をst.markdown()する ★
                            analysis = get_gemini_analysis_after(indicator_name, forecast, actual)
                            st.markdown(f"**【速報】 {analysis}**")
                        
            else:
                st.error("Gemini AIが準備できていないため、解説を生成できません。")
            
        else:
            st.warning("今日はUSD/JPYの星3指標は見つかりませんでした。")
            
    else:
        st.error("データの取得に失敗しました。")

# --- 5. AI強制テスト用 ---
# (★ このブロックが丸ごと必要です ★)
st.divider() 
st.subheader("🤖 AI機能の強制テスト")
if st.button("「発表前」AI解説を強制テスト実行"):
    if gemini_ready:
        with st.spinner("Geminiにダミーデータで解説を生成させています..."):
            
            test_analysis = get_gemini_analysis(
                indicator_name="米国 非農業部門雇用者数 (テスト)",
                forecast="20.0万人 (テスト)"
            )
            st.success("AI解説の生成テスト完了！")
            st.markdown(test_analysis)
            
if st.button("「発表後」AI速報を強制テスト実行"):
    if gemini_ready:
        with st.spinner("Geminiにダミーデータで「速報」を生成させています..."):

            test_analysis = get_gemini_analysis_after(
                indicator_name="米国 雇用統計 (テスト)",
                forecast="18.0万人 (テスト)",
                actual="27.2万人 (テスト)"
            )
            st.success("AI速報の生成テスト完了！")
            st.markdown(f"**【速報】 {test_analysis}**")
