import streamlit as st
import pandas as pd
import random
import os
import json
import time

# ファイル名の定義
QUIZ_FILE = "sentaku_quiz_data.csv"
SAVE_FILE = "sentaku_user_data.txt"
TIME_LIMIT = 10  # 制限時間（秒）
MAX_LIFE = 3     # 最大ライフ数

st.set_page_config(page_title="CHALLENGER - 究極の選択クイズ", layout="centered")

# --- 🎮 圧倒的ゲームグラフィックを実現するカスタムCSS ---
st.markdown("""
<style>
    /* 全体の背景を黒（ゲーム風）に */
    .stApp {
        background-color: #0d0f12;
        color: #e2e8f0;
    }
    
    /* タイトルロゴデザイン */
    .game-title {
        font-family: 'Courier New', Courier, monospace;
        font-size: 42px;
        font-weight: bold;
        text-align: center;
        color: #00ffcc;
        text-shadow: 0 0 10px #00ffcc, 0 0 20px #00ffcc;
        margin-bottom: 20px;
    }
    
    /* ステータスバー（プレイヤー情報・ライフ） */
    .status-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid #38bdf8;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.2);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 25px;
    }
    
    /* ライフ（ハート）の点滅風演出 */
    .life-heart {
        color: #ff2a6d;
        font-size: 24px;
        text-shadow: 0 0 8px #ff2a6d;
    }
    .life-empty {
        color: #475569;
        font-size: 24px;
    }
    
    /* 正解・不正解・タイムアップの特大演出ボックス */
    .result-box {
        padding: 30px;
        border-radius: 15px;
        text-align: center;
        margin: 20px 0;
        font-weight: bold;
        animation: pulse 1s infinite alternate;
    }
    .correct-style {
        background: rgba(16, 185, 129, 0.15);
        border: 3px solid #10b981;
        color: #10b981;
        box-shadow: 0 0 25px rgba(16, 185, 129, 0.4);
    }
    .wrong-style {
        background: rgba(239, 68, 68, 0.15);
        border: 3px solid #ef4444;
        color: #ef4444;
        box-shadow: 0 0 25px rgba(239, 68, 68, 0.4);
    }
    .timeup-style {
        background: rgba(245, 158, 11, 0.15);
        border: 3px solid #f59e0b;
        color: #f59e0b;
        box-shadow: 0 0 25px rgba(245, 158, 11, 0.4);
    }
    .gameover-style {
        background: rgba(0, 0, 0, 0.8);
        border: 3px solid #ff0055;
        color: #ff0055;
        box-shadow: 0 0 30px rgba(255, 0, 85, 0.6);
    }
    
    /* 特大アイコン */
    .huge-icon {
        font-size: 64px;
        display: block;
        margin-bottom: 10px;
    }
    
    /* ランク表示用 */
    .rank-text {
        font-size: 72px;
        font-weight: bold;
        color: #ff007f;
        text-shadow: 0 0 20px #ff007f;
        text-align: center;
        margin: 20px 0;
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
            st.error(f"CSV読み込み失敗: {e}")
            return pd.DataFrame()
    else:
        st.error(f"{QUIZ_FILE} が見つかりません。")
        return pd.DataFrame()

df_quiz = load_quiz_data()

# 2. 進捗データの読み書き
def load_all_user_progress():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_user_progress(user_name, history_ids, loop_count, score, life, current_combo, max_combo):
    data = load_all_user_progress()
    data[user_name] = {
        "history_ids": history_ids, "loop_count": loop_count, "score": score,
        "life": life, "current_combo": current_combo, "max_combo": max_combo
    }
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
if "life" not in st.session_state: st.session_state.life = MAX_LIFE
if "current_combo" not in st.session_state: st.session_state.current_combo = 0
if "max_combo" not in st.session_state: st.session_state.max_combo = 0
if "start_time" not in st.session_state: st.session_state.start_time = 0.0
if "judge_status" not in st.session_state: st.session_state.judge_status = "" 

# 4. 次の問題をセットする関数
def next_question():
    st.session_state.answered = False
    st.session_state.judge_status = ""
    
    # ゲームオーバー、または全クリア時は問題を抽出しない
    if st.session_state.life <= 0:
        return
        
    available_quizzes = df_quiz[~df_quiz['question_id'].isin(st.session_state.history_ids)]
    if available_quizzes.empty:
        st.session_state.current_question = None
        return

    selected = available_quizzes.sample(n=1).iloc[0]
    choices = selected['choices'].copy()
    random.shuffle(choices)
    
    st.session_state.current_question = {
        "question_id": int(selected['question_id']), "question": selected['question'],
        "choices": choices, "correct": selected['correct']
    }
    st.session_state.start_time = time.time()

# 5. 称号（ランク）を判定するロジック
def get_rank(score, total, max_combo, life):
    rate = (score / total) * 100 if total > 0 else 0
    if rate == 100 and life == MAX_LIFE: return "👑 SSS級: 不死鳥マスター"
    elif rate == 100: return "🏆 SS級: 完全無欠の覇者"
    elif rate >= 80: return "🎓 S級: 大賢者"
    elif rate >= 60: return "⚔️ A級: 上級戦士"
    elif max_combo >= 3: return "🏹 B級: 連撃の狩人"
    else: return "🪵 C級: 新米冒険者"

# --- ⚙️ 画面描画 ---
st.markdown('<div class="game-title">⚡ QUIZ CHALLENGER ⚡</div>', unsafe_allow_html=True)

# 6. ログイン画面
if not st.session_state.quiz_started:
    st.subheader("🎮 プレイヤーエントリー")
    name_input = st.text_input("プレイヤー名（ID）を入力してください:")
    
    if st.button("GAME START"):
        if name_input.strip() == "":
            st.warning("プレイヤー名を入力してください。")
        elif df_quiz.empty:
            st.error("問題データが空です。")
        else:
            user = name_input.strip()
            st.session_state.user_name = user
            all_progress = load_all_user_progress()
            
            if user in all_progress:
                st.session_state.history_ids = all_progress[user].get("history_ids", [])
                st.session_state.loop_count = all_progress[user].get("loop_count", 1)
                st.session_state.score = all_progress[user].get("score", 0)
                st.session_state.life = all_progress[user].get("life", MAX_LIFE)
                st.session_state.current_combo = all_progress[user].get("current_combo", 0)
                st.session_state.max_combo = all_progress[user].get("max_combo", 0)
                st.toast("💾 セーブデータをロードしました！")
            else:
                st.session_state.history_ids = []
                st.session_state.loop_count = 1
                st.session_state.score = 0
                st.session_state.life = MAX_LIFE
                st.session_state.current_combo = 0
                st.session_state.max_combo = 0
                st.toast("🌱 新規プレイヤーを作成しました！")
                
            st.session_state.quiz_started = True
            next_question()
            st.rerun()

# 7. ゲーム本編
else:
    # ── 📊 ゲームUI：ステータスバー ──
    hearts = "❤️" * st.session_state.life + "🖤" * (MAX_LIFE - st.session_state.life)
    combo_flash = f"🔥 {st.session_state.current_combo} COMBO!" if st.session_state.current_combo > 0 else "ーー"
    
    st.markdown(f"""
    <div class="status-container">
        <table style="width:100%; border:none; font-family:monospace; color:#38bdf8;">
            <tr>
                <td>👤 PLAYER: <b>{st.session_state.user_name}</b> ({st.session_state.loop_count}周目)</td>
                <td style="text-align:right;">❤️ HP: <span class="life-heart">{hearts}</span></td>
            </tr>
            <tr>
                <td>🎯 SCORE: <b>{st.session_state.score}</b> P</td>
                <td style="text-align:right; color:#ff9f43; font-weight:bold;">{combo_flash}</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)
    
    total_questions = len(df_quiz)
    cleared_questions = len(st.session_state.history_ids)
    q = st.session_state.current_question
    
    # ── 💀 ライフゼロ（ゲームオーバー判定） ──
    if st.session_state.life <= 0:
        st.markdown('<div class="result-box wrong-style"><span class="huge-icon">💀</span>❌ GAME OVER ❌<br><br>ライフが尽きました。修業し直してきてください。</div>', unsafe_allow_html=True)
        if st.button("🔄 もう一度1周目から挑戦（リトライ）"):
            st.session_state.history_ids = []
            st.session_state.score = 0
            st.session_state.life = MAX_LIFE
            st.session_state.current_combo = 0
            st.session_state.loop_count = 1
            save_user_progress(st.session_state.user_name, st.session_state.history_ids, st.session_state.loop_count, st.session_state.score, st.session_state.life, st.session_state.current_combo, st.session_state.max_combo)
            next_question()
            st.rerun()
            
    # ── ⚔️ クイズ解答中 ──
    elif q:
        st.subheader(f"STAGE {cleared_questions + 1} / {total_questions}")
        st.info(q['question'])
        
        # タイマー部
        @st.fragment(run_every=1.0)
        def show_timer_and_check():
            if not st.session_state.answered and st.session_state.judge_status == "":
                elapsed = time.time() - st.session_state.start_time
                remaining = int(TIME_LIMIT - elapsed)
                if remaining <= 0:
                    st.session_state.answered = True
                    st.session_state.judge_status = "time_up"
                    st.session_state.life -= 1  # タイムアップでダメージ
                    st.session_state.current_combo = 0  # コンボストップ
                    st.session_state.history_ids.append(q['question_id'])
                    save_user_progress(st.session_state.user_name, st.session_state.history_ids, st.session_state.loop_count, st.session_state.score, st.session_state.life, st.session_state.current_combo, st.session_state.max_combo)
                    st.rerun()
                else:
                    st.markdown(f"⏳ 残り時間: <b style='color:#ff0055;'>{remaining}秒</b>", unsafe_allow_html=True)
        show_timer_and_check()
        
        user_choice = st.radio("選択肢をロックオンせよ:", q['choices'], index=None, key=f"radio_{q['question_id']}", disabled=st.session_state.answered)
        
        # 演出表示
        if st.session_state.judge_status == "correct":
            st.markdown(f'<div class="result-box correct-style"><span class="huge-icon">✨ ⭕ CRITICAL HIT! ✨</span>正解！コンボ継続中！</div>', unsafe_allow_html=True)
        elif st.session_state.judge_status == "wrong":
            st.markdown(f'<div class="result-box wrong-style"><span class="huge-icon">💥 ❌ DAMAGE! 💥</span>不正解！ 正解は「{q["correct"]}」だった！</div>', unsafe_allow_html=True)
        elif st.session_state.judge_status == "time_up":
            st.markdown(f'<div class="result-box timeup-style"><span class="huge-icon">⌛ ⏰ TIME UP! ⏳</span>時間切れ！ライフが1減少した。</div>', unsafe_allow_html=True)

        if not st.session_state.answered:
            if st.button("回答を送信（LOCK ON）"):
                if user_choice is None:
                    st.warning("選択肢を選んでください。")
                else:
                    st.session_state.answered = True
                    if user_choice == q['correct']:
                        st.session_state.judge_status = "correct"
                        st.session_state.score += 1
                        st.session_state.current_combo += 1
                        # 最高コンボの更新
                        if st.session_state.current_combo > st.session_state.max_combo:
                            st.session_state.max_combo = st.session_state.current_combo
                    else:
                        st.session_state.judge_status = "wrong"
                        st.session_state.life -= 1  # 不正解でダメージ
                        st.session_state.current_combo = 0  # コンボリセット
                        
                    st.session_state.history_ids.append(q['question_id'])
                    save_user_progress(st.session_state.user_name, st.session_state.history_ids, st.session_state.loop_count, st.session_state.score, st.session_state.life, st.session_state.current_combo, st.session_state.max_combo)
                    st.rerun()
        else:
            if st.button("次のステージへ ➡️"):
                next_question()
                st.rerun()
                
    # ── 🏆 全問クリア画面 ──
    else:
        st.markdown("---")
        st.balloons()
        
        rank = get_rank(st.session_state.score, total_questions, st.session_state.max_combo, st.session_state.life)
        
        st.markdown(f"""
        <div style="text-align:center;">
            <h2 style="color:#00ffcc;">🎉 MISSION CLEAR 🎉</h2>
            <p>全ステージを突破しました！あなたの最終ランクを発表します。</p>
            <div class="rank-text">{rank.split(":")[0]}</div>
            <h3>称号: {rank.split(":")[1]}</h3>
            <p style="color:#a855f7;">👑 最高コンボ記録: <b>{st.session_state.max_combo}</b> 連続正解</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.metric(label="獲得スコア", value=f"{st.session_state.score} / {total_questions} 問正解")
        
        if st.button("🔄 次の周回（難関）へ進む"):
            st.session_state.history_ids = []
            st.session_state.score = 0
            st.session_state.life = MAX_LIFE  # 次の周でライフ全回復
            st.session_state.current_combo = 0
            st.session_state.loop_count += 1
            save_user_progress(st.session_state.user_name, st.session_state.history_ids, st.session_state.loop_count, st.session_state.score, st.session_state.life, st.session_state.current_combo, st.session_state.max_combo)
            next_question()
            st.rerun()

    # ギブアップ（終了）
    if st.sidebar.button("プレイヤー交代 / 終了"):
        st.session_state.quiz_started = False
        st.session_state.history_ids = []
        st.session_state.user_name = ""
        st.session_state.current_question = None
        st.session_state.loop_count = 1
        st.session_state.score = 0
        st.session_state.life = MAX_LIFE
        st.session_state.current_combo = 0
        st.session_state.max_combo = 0
        st.session_state.judge_status = ""
        st.rerun()