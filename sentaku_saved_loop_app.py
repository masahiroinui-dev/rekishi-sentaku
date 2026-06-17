import streamlit as st
import pandas as pd
import random
import os
import json

# ファイル名の定義
QUIZ_FILE = "sentaku_quiz_data.csv"
SAVE_FILE = "sentaku_user_data.txt"  # ユーザー進捗を保存するテキストファイル

st.set_page_config(page_title="完全継続・周回型クイズ", layout="centered")

# 1. 問題データの読み込み
@st.cache_data
def load_quiz_data():
    if os.path.exists(QUIZ_FILE):
        try:
            df = pd.read_csv(QUIZ_FILE)
            df['choices'] = df['choices'].apply(lambda x: [c.strip() for c in str(x).split(',')])
            return df
        except Exception as e:
            st.error(f"CSVファイルの読み込みに失敗しました。形式を確認してください。: {e}")
            return pd.DataFrame()
    else:
        st.error(f"エラー: {QUIZ_FILE} が見つかりません。")
        return pd.DataFrame()

df_quiz = load_quiz_data()

# 2. テキストファイルから全ユーザーの進捗を読み込む関数
def load_all_user_progress():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

# 3. テキストファイルに特定のユーザーの進捗を保存する関数
def save_user_progress(user_name, history_ids, loop_count, score):
    data = load_all_user_progress()
    data[user_name] = {
        "history_ids": history_ids,
        "loop_count": loop_count,
        "score": score
    }
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 4. セッション状態（State）の初期化
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "history_ids" not in st.session_state:
    st.session_state.history_ids = []
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
if "answered" not in st.session_state:
    st.session_state.answered = False
if "loop_count" not in st.session_state:
    st.session_state.loop_count = 1
if "score" not in st.session_state:
    st.session_state.score = 0

# 5. 次の問題をセットする関数
def next_question():
    st.session_state.answered = False
    
    # まだ解いていない問題を抽出
    available_quizzes = df_quiz[~df_quiz['question_id'].isin(st.session_state.history_ids)]
    
    # すべての問題を解き終わった場合
    if available_quizzes.empty:
        st.session_state.current_question = None
        return

    # ランダムに1問を抽出
    selected = available_quizzes.sample(n=1).iloc[0]
    choices = selected['choices'].copy()
    random.shuffle(choices)
    
    st.session_state.current_question = {
        "question_id": int(selected['question_id']),
        "question": selected['question'],
        "choices": choices,
        "correct": selected['correct']
    }

# --- 画面表示 ---
st.title("🔁 データ保存型・周回ランダムクイズ")

# 6. ユーザーログイン画面（ここでテキストファイルからデータを復元）
if not st.session_state.quiz_started:
    st.subheader("👤 ログイン（進捗を自動で引き継ぎます）")
    name_input = st.text_input("あなたの名前（またはID）を入力してください:")
    
    if st.button("クイズを開始する"):
        if name_input.strip() == "":
            st.warning("名前を入力してください。")
        elif df_quiz.empty:
            st.error("問題データ（CSV）が読み込めていません。")
        else:
            user = name_input.strip()
            st.session_state.user_name = user
            
            all_progress = load_all_user_progress()
            
            if user in all_progress:
                st.session_state.history_ids = all_progress[user].get("history_ids", [])
                st.session_state.loop_count = all_progress[user].get("loop_count", 1)
                st.session_state.score = all_progress[user].get("score", 0)
                st.toast(f"📢 前回の続き（{st.session_state.loop_count}周目）から再開しました！")
            else:
                st.session_state.history_ids = []
                st.session_state.loop_count = 1
                st.session_state.score = 0
                st.toast("🌱 新しい進捗データを作成しました！")
                
            st.session_state.quiz_started = True
            next_question()
            st.rerun()

# 7. クイズ本編画面
else:
    st.write(f"挑戦者: **{st.session_state.user_name}** さん （**{st.session_state.loop_count}周目**）")
    
    total_questions = len(df_quiz)
    cleared_questions = len(st.session_state.history_ids)
    
    st.progress(cleared_questions / total_questions)
    st.write(f"進捗: {cleared_questions} / {total_questions} 問完了 (現在の正解数: {st.session_state.score})")
    
    q = st.session_state.current_question
    
    # まだ現在の周回で未解答の問題がある場合
    if q:
        st.markdown("---")
        st.subheader(f"問題")
        st.write(q['question'])
        
        user_choice = st.radio("選択肢から選んでください:", q['choices'], index=None, key=f"radio_{q['question_id']}")
        
        if not st.session_state.answered:
            if st.button("回答を送信する"):
                if user_choice is None:
                    st.warning("選択肢を選んでください。")
                else:
                    st.session_state.answered = True
                    is_correct = (user_choice == q['correct'])
                    
                    if is_correct:
                        st.success("⭕ 正解です！")
                        st.session_state.score += 1
                    else:
                        st.error(f"❌ 不正解... 正解は「{q['correct']}」でした。")
                        
                    st.session_state.history_ids.append(q['question_id'])
                    
                    # 解いた瞬間にテキストファイルへ保存
                    save_user_progress(
                        st.session_state.user_name,
                        st.session_state.history_ids,
                        st.session_state.loop_count,
                        st.session_state.score
                    )
                    st.rerun()
                    
        else:
            if st.button("次へ進む ➡️"):
                next_question()
                st.rerun()
                
    # 全問クリアした場合（再挑戦へリループする画面）
    else:
        st.markdown("---")
        st.balloons()
        st.success(f"🎉 おめでとうございます！全 {total_questions} 問を解き終えました！")
        st.metric(label="今回の正解数", value=f"{st.session_state.score} / {total_questions}")
        
        if st.button("🔄 もう一度最初から挑戦する（次の周回へ）"):
            st.session_state.history_ids = []
            st.session_state.score = 0
            st.session_state.loop_count += 1
            
            save_user_progress(
                st.session_state.user_name,
                st.session_state.history_ids,
                st.session_state.loop_count,
                st.session_state.score
            )
            next_question()
            st.rerun()

    # 終了・ユーザー切り替えボタン
    if st.sidebar.button("ユーザーを切り替える / 終了"):
        st.session_state.quiz_started = False
        st.session_state.history_ids = []
        st.session_state.user_name = ""
        st.session_state.current_question = None
        st.session_state.loop_count = 1
        st.session_state.score = 0
        st.rerun()