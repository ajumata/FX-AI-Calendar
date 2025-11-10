import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# --- Gemini AI ---
import google.generativeai as genai

# --- App 2 (News) ---
import feedparser # ニュース取得用ライブラリ

# --- (日付・時刻ライブラリ) ---
from datetime import datetime, timezone, timedelta
import calendar # UTCタイムスタンプ変換用

# --- Streamlit ページの基本設定 ---
st.set_page_config(layout="wide")
st.title("ドル円 総合AIダッシュボード 📈")
st.write("経済指標（アプリ1）と最新ニュース（アプリ2）をAIで分析します。")


# --- 「経過時間」を計算するヘルパー関数 ---
def format_time_ago(delta):
    """datetime.timedelta を「○時間○分前」の文字列に変換する"""
    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return "1分未満前"

    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}分前"

    hours = minutes // 60
    if hours < 24:
        minutes_remaining = minutes % 60
        if minutes_remaining == 0:
            return f"{hours}時間前"
        else:
            return f"{hours}時間{minutes_remaining}分前"

    days = hours // 24
    return f"{days}日前"


# --- 1. Gemini AIのセットアップ ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel(
        'models/gemini-2.5-flash', # 診断結果で確認したモデル名
        generation_config={"temperature": 0.1}
    )
    gemini_ready = True
except Exception as e:
    st.error(f"❌ Geminiの初期化に失敗しました。APIキーが正しく設定されているか確認してください。 {e}")
    gemini_ready = False

# --- 2. 関数定義 (App 1: 指標カレンダー) ---
# (変更なし)
def fetch_indicators():
    """App 1: Investing.comから指標を取得"""
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
                    time_val = row.find('td', {'class': 'time'}).text.strip() or "N/A"
                    event_name = row.find('td', {'class': 'event'}).text.strip() or "N/A"
                    forecast_val = row.find('td', {'class': 'forecast'}).text.strip() or "N/A"
                    actual_val = row.find('td', {'class': 'actual'}).text.strip() or "N/A"
                    indicator_list.append({"時刻": time_val, "通貨": currency, "指標名": event_name, "予想": forecast_val, "結果": actual_val})
        return indicator_list
    except Exception as e:
        st.error(f"App1 エラー: 指標サイトにアクセスできませんでした。{e}")
        return None

# (変更なし)
def get_gemini_analysis(indicator_name, forecast):
    """App 1 (Step 3): 発表「前」の解説"""
    prompt = f"..." # (省略)
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI解説(前) 失敗: {e}"

# (変更なし)
def get_gemini_analysis_after(indicator_name, forecast, actual):
    """App 1 (Step 4): 発表「後」の速報"""
    prompt = f"..." # (省略)
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI速報(後) 失敗: {e}"

# --- 3. 関数定義 (App 2: ニュース) ---
# (変更なし)
def fetch_nhk_news():
    """App 2: NHK経済ニュースRSSを取得 (日付・経過時間も計算)"""
    rss_url = "https://www.nhk.or.jp/rss/news/cat5.xml"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    news_list = []

    try:
        response = requests.get(rss_url, headers=headers)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        jst_tz = timezone(timedelta(hours=9))
        current_time_dt_utc = datetime.now(timezone.utc)

        if feed.entries:
            for entry in feed.entries[:40]: # 最新40件

                formatted_date = "（日時不明）"
                time_ago = "（-）"

                if hasattr(entry, 'published_parsed'):
                    try:
                        publish_time_utc_timestamp = calendar.timegm(entry.published_parsed)
                        publish_time_dt_utc = datetime.fromtimestamp(publish_time_utc_timestamp, timezone.utc)

                        delta = current_time_dt_utc - publish_time_dt_utc
                        time_ago = format_time_ago(delta)

                        publish_time_dt_jst = publish_time_dt_utc.astimezone(jst_tz)
                        formatted_date = publish_time_dt_jst.strftime('%m月%d日 %H:%M')

                    except Exception as e:
                        formatted_date = f"（日付変換エラー: {e}）"

                news_list.append({
                    "見出し": entry.title,
                    "URL": entry.link,
                    "要約": entry.get("description", "（要約なし）"),
                    "公開日時": formatted_date,
                    "経過時間": time_ago
                })
        return news_list
    except Exception as e:
        st.error(f"App2 エラー: ニュースRSSにアクセスできませんでした。{e}")
        return None

# (★ App 2 のAI分析関数を「ドル円サマリー」対応に更新 ★)
def get_gemini_news_analysis(news_items_list):
    """App 2 (AI Filter): ニュースリストをまとめて渡し、関連ニュースだけ分析させる"""

    prompt_news_list = ""
    if not news_items_list:
        return "分析対象のニュースがありません。"

    for i, item in enumerate(news_items_list):
        prompt_news_list += f"--- ニュース {i+1} ---\n"
        prompt_news_list += f"見出し: {item['見出し']}\n"
        prompt_news_list += f"要約: {item['要約']}\n"
        prompt_news_list += f"公開日時: {item['公開日時']} ({item['経過時間']})\n\n"

    # (★ AIへの指示（プロンプト）を更新 ★)
    prompt = f"""
    あなたは、24時間市場を監視するAIアナリストです。
    以下の「NHK経済ニュースリスト（{len(news_items_list)}件）」を読んで、**「ドル円相場（USD/JPY）に関連する可能性のあるニュース」だけを厳選**してください。

    【ルール】
    * もし関連するニュースが**1件もなければ**、「ドル円関連ニュースなし」とだけ回答してください。
    * もし関連するニュースが**あれば**、そのニュースだけを以下の形式で抜き出してまとめてください。
    * 回答はマークダウン形式（`###`や`*`）で、読みやすくしてください。
    * 「公開日時」と「経過時間」も必ず回答に含めてください。
    * (★ 新ルール ★) **最後に、抽出したすべてのニュースが「ドル円相場（USD/JPY）」に与える影響を総合的に判断し、「ドル円の短期的な方向性」として3行でコメントしてください。**

    ---
    ### 1. [抜き出したニュースの見出し]
    **（公開日時: [AIが抜き出した日時] / [AIが抜き出した経過時間]）**
    * **AI要約:** （ドル円にどう関係するか、2行で要約）
    * **AI感情分析:** （ドル円に対し ポジティブ / ネガティブ / 中立）
    * **AIトピック:** （例：米金利、日銀、要人発言、米経済指標、地政学リスク）

    ### 2. [抜き出した次のニュースの見出し]
    ... (以下、関連ニュースが続く) ...
    ---

    **【ドル円サマリー】**
    (ここに、抽出した全ニュースがドル円相場に与える影響と、短期的な方向性について3行コメントを記述)

    ---

    **【NHK経済ニュースリスト】**
    {prompt_news_list}
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AIニュース分析 失敗: {e}"


# --- 4. Streamlit アプリ本体 (タブ機能) ---
# (変更なし)
tab1, tab2 = st.tabs(["🗓️ 経済指標カレンダー (App 1)", "📰 最新ニュース (App 2)"])

# --- タブ1 (App 1) の中身 ---
# (変更なし)
with tab1:
    st.header("経済指標カレンダー")

    if st.button("最新の指標データを取得 ＆ AI解説"):
        with st.spinner('Investing.comからデータを取得中...'):
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
                                analysis = get_gemini_analysis_after(indicator_name, forecast, actual)
                                st.markdown(f"**【速報】 {analysis}**")
                else:
                    st.error("Gemini AIが準備できていません。")
            else:
                st.warning("今日はUSD/JPYの星3指標は見つかりませんでした。")
        else:
            st.error("データの取得に失敗しました。")

# --- タブ2 (App 2) の中身 ---
# (変更なし)
with tab2:
    st.header("最新ニュース（NHK経済）")
    st.write("最新40件のニュースをAIが分析し、「ドル円」関連のニュースだけを抽出します。")

    if st.button("最新ニュースを取得 ＆ AI分析"):

        with st.spinner('NHK RSSから最新ニュースを取得中...'):
            news_items = fetch_nhk_news()

        if news_items and gemini_ready:
            st.success(f"{len(news_items)}件のニュースを取得しました。AIが分析・フィルタリングします...")

            with st.spinner('🤖 AIがドル円関連ニュースを分析・抽出中...'):
                ai_filtered_news = get_gemini_news_analysis(news_items)

            st.markdown(ai_filtered_news)

        elif not news_items:
            st.error("ニュースの取得に失敗しました。")
        else:
            st.error("Gemini AIが準備できていないため、分析できません。")
