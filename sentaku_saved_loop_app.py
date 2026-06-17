正誤判定をより分かりやすくするための視覚的な工夫（大きなアイコンと背景色の強調）を追加し、さらに「1問につき10秒」の時間制限タイマー機能を組み込みました！

タイマーは画面上でリアルタイムにカウントダウンし、10秒が経過すると自動的に「タイムアップ（不正解）」として処理されます。

プログラムのファイルを書き換えますので、以下の最新コードを sentaku_saved_loop_app.py に上書き保存してください。

📝 アップデート版：メインプログラム (sentaku_saved_loop_app.py)
Python
import streamlit as st
import pandas as pd
import random
import os
import json
import time

# ファイル名の定義
QUIZ_FILE = "sentaku_quiz_data.csv"
SAVE_FILE = "sentaku_user_data.txt"
TIME_LIMIT = 10 # 制限時間（秒）

st.set_page_config(page_title="完全継続・周回型タイムアタッククイズ", layout="centered")

# カスタムCSSで視覚効果を強化
st.markdown("""
<style>
    .correct-box {
        padding: 20px;
        background-color: #d4edda;
        color: #155724;
        border-radius: 10px;
        border: 2px solid #c3e6cb;
        text-align: center;
        margin: 10px 0;
    }
    .wrong-box {
        padding: 20px;
        background-color: #f8d7da;
        color: #721c24;
        border-radius: 10px;
        border: 2px solid #f5c6cb;
        text-align: center;
        margin: 10px 0;
    }
    .time-up-box {
        padding: 20px;
        background-color: #fff3cd;
        color: #856404;
        border-radius: 10px;
        border: 2px solid #ffeeba;
        text-align: center;
        margin: 10px 0;
    }
    .big-icon {
        font-size: 48px;
        font-weight: bold;
        display: block;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# 1. 問題データの読み込み
@st.cache_data
def load_quiz_data():
    if os.path.exists(QUIZ_FILE):
        try:
            df = pd.read_csv(QUIZ_FILE)
            df['choices'] = df['choices'].apply(lambda x: [c.strip() for c in str(x).split(',')])
            return df
        except Exception as e:
            st.error(f"CSVファイルの読み込みに失敗しました。: {e}")
            return pd.DataFrame()
    else:
        st.error(f"エラー: {QUIZ_FILE} が見つかりません。")
        return pd.DataFrame()

df_quiz = load_quiz_data()

# 2. 進捗の読み書き関数
def load_all_user_progress():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user_progress(user_name, history_ids, loop_count, score):
    data = load_all_user_progress()
    data[user_name] = {"history_ids": history_ids, "loop_count": loop_count, "score": score}
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 3. セッション状態の初期化
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "current_question" not in st.session_state: st.session_state.current_question = None
if "history_ids" not in st.session_state: st.session_state.history_ids = []
if "quiz_started" not in st.session_state: st.session_state.quiz_started = False
if "answered" not in st.session_state: st.session_state.answered = False
if "loop_count" not in st.session_state: st.session_state.loop_count = 1
if "score" not in st.session_state: st.session_state.score = 0
if "start_time" not in st.session_state: st.session_state.start_time = 0
if "judge_status" not in st.session_state: st.session_state.judge_status = "" # 正誤判定状態

# 4. 次の問題をセットする関数
def next_question():
    st.session_state.answered = False
    st.session_state.judge_status = ""
    available_quizzes = df_quiz[~df_quiz['question_id'].isin(st.session_state.history_ids)]
    
    if available_quizzes.empty:
        st.session_state.current_question = None
        return

    selected = available_quizzes.sample(n=1).iloc[0]
    choices = selected['choices'].copy()
    random.shuffle(choices)
    
    st.session_state.current_question = {
        "question_id": int(selected['question_id']),
        "question": selected['question'],
        "choices": choices,
        "correct": selected['correct']
    }
    # 出題した瞬間の時間を記録
    st.session_state.start_time = time.time()

# --- 画面表示 ---
st.title("⏱️ タイマー付き・周回ランダムクイズ")

# 5. ログイン画面
if not st.session_state.quiz_started:
    st.subheader("👤 ログイン")
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

# 6. クイズ本編
else:
    st.write(f"挑戦者: **{st.session_state.user_name}** さん （**{st.session_state.loop_count}周目**）")
    total_questions = len(df_quiz)
    cleared_questions = len(st.session_state.history_ids)
    
    st.progress(cleared_questions / total_questions)
    st.write(f"進捗: {cleared_questions} / {total_questions} 問完了 (現在の正解数: {st.session_state.score})")
    
    q = st.session_state.current_question
    
    if q:
        st.markdown("---")
        st.subheader(f"問題")
        st.write(q['question'])
        
        # --- ⏳ タイマー処理の追加 ---
        timer_placeholder = st.empty()
        
        # 未回答、かつタイムアップしていない場合のみカウントダウンを回す
        if not st.session_state.answered and st.session_state.judge_status == "":
            elapsed = time.time() - st.session_state.start_time
            remaining = int(TIME_LIMIT - elapsed)
            
            if remaining <= 0:
                # 10秒が過ぎたらタイムアップ処理
                st.session_state.answered = True
                st.session_state.judge_status = "time_up"
                st.session_state.history_ids.append(q['question_id'])
                save_user_progress(st.session_state.user_name, st.session_state.history_ids, st.session_state.loop_count, st.session_state.score)
                st.rerun()
            else:
                # 画面上の残り秒数表示を更新
                timer_placeholder.markdown(f"⏳ 残り時間: **{remaining}秒**")
                # 少し待って即リロードすることで、リアルタイムに1秒ずつカウントを減らす
                time.sleep(1)
                st.rerun()
        
        # ラジオボタンでの選択肢表示
        # すでに結果が出ている（送信済 or タイムアップ）なら無効化(disabled)にする
        is_disabled = st.session_state.answered
        user_choice = st.radio("選択肢から選んでください:", q['choices'], index=None, key=f"radio_{q['question_id']}", disabled=is_disabled)
        
        # --- 🎨 視覚的な正誤判定エリア ---
        if st.session_state.judge_status == "correct":
            st.markdown(f'<div class="correct-box"><span class="big-icon">⭕ 正解！</span>正解は「{q["correct"]}」です。素晴らしい！</div>', unsafe_allow_html=True)
        elif st.session_state.judge_status == "wrong":
            st.markdown(f'<div class="wrong-box"><span class="big-icon">❌ 不正解...</span>あなたの回答:「{user_choice}」<br>正解は「{q["correct"]}」でした。</div>', unsafe_allow_html=True)
        elif st.session_state.judge_status == "time_up":
            st.markdown(f'<div class="time-up-box"><span class="big-icon">⏰ タイムアップ！</span>10秒以内に回答がありませんでした。<br>正解は「{q["correct"]}」でした。</div>', unsafe_allow_html=True)

        # ボタンの制御
        if not st.session_state.answered:
            if st.button("回答を送信する"):
                if user_choice is None:
                    st.warning("選択肢を選んでください。")
                else:
                    st.session_state.answered = True
                    if user_choice == q['correct']:
                        st.session_state.judge_status = "correct"
                        st.session_state.score += 1
                    else:
                        st.session_state.judge_status = "wrong"
                        
                    st.session_state.history_ids.append(q['question_id'])
                    save_user_progress(st.session_state.user_name, st.session_state.history_ids, st.session_state.loop_count, st.session_state.score)
                    st.rerun()
        else:
            if st.button("次へ進む ➡️"):
                next_question()
                st.rerun()
                
    # 全問クリア画面
    else:
        st.markdown("---")
        st.balloons()
        st.success(f"🎉 おめでとうございます！全 {total_questions} 問を解き終えました！")
        st.metric(label="今回の正解数", value=f"{st.session_state.score} / {total_questions}")
        
        if st.button("🔄 もう一度最初から挑戦する（次の周回へ）"):
            st.session_state.history_ids = []
            st.session_state.score = 0
            st.session_state.loop_count += 1
            save_user_progress(st.session_state.user_name, st.session_state.history_ids, st.session_state.loop_count, st.session_state.score)
            next_question()
            st.rerun()

    # 終了ボタン
    if st.sidebar.button("ユーザーを切り替える / 終了"):
        st.session_state.quiz_started = False
        st.session_state.history_ids = []
        st.session_state.user_name = ""
        st.session_state.current_question = None
        st.session_state.loop_count = 1
        st.session_state.score = 0
        st.session_state.judge_status = ""
        st.rerun()