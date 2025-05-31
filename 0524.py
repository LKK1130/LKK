import streamlit as st
import random
import datetime
import json
import time
import os
from collections import Counter
from datetime import datetime as dt, timedelta
import streamlit.components.v1 as components

# --------------------
# 假資料（用於登入驗證）
# --------------------
FAKE_USERS = {
    "user1": "password1",
    "user2": "password2",
    "admin": "admin123"
}

FAKE_CHECKINS = []  # 模擬打卡紀錄

# --------------------
# 單字永久儲存功能
# --------------------
WORDS_FILE = "words.json"
TODAY_WORDS_FILE = f"today_words_{datetime.date.today().isoformat()}.json"

def load_words():
    if os.path.exists(WORDS_FILE):
        with open(WORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return []

def save_words(words):
    with open(WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

def load_today_words():
    if os.path.exists(TODAY_WORDS_FILE):
        with open(TODAY_WORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return []

def save_today_words(words):
    with open(TODAY_WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

# 在主程式一開始載入
if "words_data" not in st.session_state:
    st.session_state["words_data"] = load_words()

if "words" not in st.session_state:
    st.session_state["words"] = load_today_words()

# --------------------
# 選擇題測驗功能
# --------------------
def generate_choice_questions():
    words = st.session_state["words_data"]
    questions = []
    if len(words) < 2:
        return questions  # 至少要兩個單字才有干擾選項
    for w in words:
        options = [w["meaning"]]
        distractors = [x["meaning"] for x in words if x["word"] != w["word"] and x["meaning"]]
        options += random.sample(distractors, min(3, len(distractors)))
        random.shuffle(options)
        answer_index = options.index(w["meaning"])
        questions.append({
            "word": w["word"],
            "options": options,
            "answer_index": answer_index
        })
    return questions

def quiz_page():
    st.title("📘 學習單字選擇題測驗")
    num_options = [5, 10, 20]
    words_total = len(st.session_state["words_data"])

    # 只在 quiz_started 為 False 時顯示選擇題數與開始測驗
    if "quiz_started" not in st.session_state or not st.session_state.quiz_started:
        num_q = st.radio("請選擇測驗題數：", num_options, horizontal=True, index=0, key="quiz_num_select")
        if words_total == 0:
            st.info("請先在學習頁新增單字。")
            return

        actual_num = min(num_q, words_total)
        if st.button("開始測驗"):
            all_questions = generate_choice_questions()
            if len(all_questions) > actual_num:
                questions = random.sample(all_questions, actual_num)
            else:
                questions = all_questions
            st.session_state.quiz_questions = questions
            st.session_state.current_q = 0
            st.session_state.score = 0
            st.session_state.log = []
            st.session_state.quiz_started = True
        else:
            return  # 還沒按開始測驗就不顯示題目

    questions = st.session_state.get("quiz_questions", [])

    if not questions:
        st.info("請先在學習頁新增至少兩個有意思的單字，才能進行選擇題測驗。")
        return

    if st.session_state.current_q < len(questions):
        q = questions[st.session_state.current_q]
        st.subheader(f"題目 {st.session_state.current_q + 1}: {q['word']}")
        choice = st.radio("請選擇正確意思：", q["options"], index=None, key=f"quiz_choice_{st.session_state.current_q}")

        # 狀態: 是否已提交本題答案
        answered_key = f"quiz_answered_{st.session_state.current_q}"
        if answered_key not in st.session_state:
            st.session_state[answered_key] = False

        if not st.session_state[answered_key]:
            if st.button("提交答案") and choice is not None:
                correct = q["options"].index(choice) == q["answer_index"]
                if correct:
                    st.success("✅ 答對了！")
                    st.session_state.score += 1
                else:
                    st.error(f"❌ 答錯了，正確答案是：{q['options'][q['answer_index']]}")
                # 不論對錯都寫入 log.json
                log_item = {
                    "word": q["word"],
                    "your_answer": choice,
                    "correct_answer": q["options"][q["answer_index"]],
                    "is_correct": correct
                }
                if os.path.exists("log.json"):
                    with open("log.json", "r", encoding="utf-8") as f:
                        old_log = json.load(f)
                else:
                    old_log = []
                old_log.append(log_item)
                with open("log.json", "w", encoding="utf-8") as f:
                    json.dump(old_log, f, ensure_ascii=False, indent=2)
                st.session_state.log.append(log_item)
                st.session_state[answered_key] = True
                # 直接進入下一題
                st.session_state.current_q += 1
                st.session_state.pop(f"quiz_choice_{st.session_state.current_q-1}", None)
                st.session_state.pop(answered_key, None)
    else:
        # 測驗結束只顯示本次測驗結果
        quiz_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        total = len(questions)
        correct = st.session_state.score
        accuracy = round((correct / total) * 100, 2) if total > 0 else 0
        wrong_words = [item["word"] for item in st.session_state.log if not item["is_correct"]]
        wrong_words_str = ", ".join(wrong_words) if wrong_words else "無"
        st.balloons()
        st.markdown(f"### 🎉 測驗結束！")
        st.markdown(f"#### 測驗完成時間：{quiz_time}")
        st.markdown(f"#### 正確率：{accuracy}%")
        st.markdown(f"#### 錯誤單字：{wrong_words_str}")
        # 儲存到 quiz_result.json（避免重複，依 題數+正確率+錯誤單字 判斷）
        result_row = {
            "測驗時間": quiz_time,
            "題數": total,
            "正確率": f"{accuracy}%",
            "錯誤單字": wrong_words_str
        }
        if os.path.exists("quiz_result.json"):
            with open("quiz_result.json", "r", encoding="utf-8") as f:
                quiz_results = json.load(f)
        else:
            quiz_results = []
        is_duplicate = False
        for r in quiz_results:
            if (
                r.get("題數") == total and
                r.get("正確率") == f"{accuracy}%" and
                r.get("錯誤單字") == wrong_words_str
            ):
                # 新增：比對單字內容
                # 取出本次測驗的所有單字
                current_words = set([q["word"] for q in questions])
                # 取出歷史紀錄的所有單字（需額外存一個欄位）
                record_words = set(r.get("單字列表", []))
                if current_words == record_words:
                    is_duplicate = True
                    break
        # 新增：將本次單字列表存入紀錄
        result_row["單字列表"] = [q["word"] for q in questions]
        if not is_duplicate:
            quiz_results.append(result_row)
            with open("quiz_result.json", "w", encoding="utf-8") as f:
                json.dump(quiz_results, f, ensure_ascii=False, indent=2)
        if st.button("重新開始"):
            st.session_state.quiz_questions = []
            st.session_state.current_q = 0
            st.session_state.score = 0
            st.session_state.log = []
            st.session_state.quiz_started = False
            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()

# --------------------
# 各頁面功能
# --------------------
def home_page():
    st.title("歡迎來到背單字習慣追蹤系統")
    st.write("這是一個幫助您追蹤每日學習進度與測驗記憶效果的應用程式。")
    st.write("請使用左側選單進行操作。")
    st.image("https://via.placeholder.com/800x300", caption="學習，測驗，進步！")
    # 將清空所有單字按鈕移到首頁
    if st.button("⚠️ 清空所有單字"):
        st.session_state.show_clear_words_confirm = True
    if st.session_state.get("show_clear_words_confirm", False):
        st.warning("確定要清空所有單字嗎？此動作無法復原！")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("是，清空所有單字"):
                st.session_state["words"] = []
                st.session_state["words_data"] = []
                save_words([])
                st.success("已清空所有單字資料！")
                st.session_state.show_clear_words_confirm = False
        with col2:
            if st.button("否"):
                st.session_state.show_clear_words_confirm = False

def login_page():
    st.title("登入")
    username_input = st.text_input("請輸入帳號", key="login_username")
    password_input = st.text_input("請輸入密碼", type="password", key="login_password")
    if st.button("登入"):
        if username_input in FAKE_USERS and FAKE_USERS[username_input] == password_input:
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = username_input
            st.success(f"歡迎，{username_input}！登入成功！")
        else:
            st.error("帳號或密碼錯誤！")

def study_page():
    st.title("學習頁")
    st.write(f"今天是：{datetime.date.today().isoformat()}")
    col1, col2 = st.columns(2)
    with col1:
        new_word = st.text_input("輸入英文單字").strip().lower()
    with col2:
        new_meaning = st.text_input("輸入中文意思").strip()

    if st.button("新增單字"):
        if new_word and new_meaning:
            exist = next((w for w in st.session_state["words_data"] if w["word"].lower() == new_word), None)
            if exist:
                exist["meaning"] = new_meaning  # 更新意思
            else:
                st.session_state["words_data"].append({
                    "word": new_word,
                    "meaning": new_meaning,
                    "level": 1,
                    "last_review": datetime.date.today().isoformat()
                })
            save_words(st.session_state["words_data"])
            if "words" not in st.session_state:
                st.session_state["words"] = []
            if new_word not in [w.lower() for w in st.session_state["words"]]:
                st.session_state["words"].append(new_word)
                save_today_words(st.session_state["words"])
            st.success(f"已新增：{new_word} - {new_meaning}")
        else:
            st.error("請輸入完整的英文單字與中文意思！")

    if st.button("完成今日學習"):
        user = st.session_state.get("current_user", "")
        today_words = st.session_state.get("words", [])
        if today_words:  # 有新增單字才可打卡
            response = {
                "user": user,
                "date": datetime.date.today().isoformat(),
                "words_learned": today_words
            }
            st.success("今日學習已完成！明天繼續努力！")
            # 新增：寫入一筆學習打卡到 checkin.json
            checkin_record = {
                "user": user,
                "datetime": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "study",  # 標記這是學習打卡
                "words_learned": today_words
            }
            if os.path.exists("checkin.json"):
                with open("checkin.json", "r", encoding="utf-8") as f:
                    checkins = json.load(f)
            else:
                checkins = []
            checkins.append(checkin_record)
            with open("checkin.json", "w", encoding="utf-8") as f:
                json.dump(checkins, f, ensure_ascii=False, indent=2)
        else:
            st.warning("今日還未新增單字，請勿偷懶！")

    st.subheader("已學單字")
    if "words" in st.session_state and st.session_state["words"]:
        for word in st.session_state["words"]:
            meaning = next((w["meaning"] for w in st.session_state["words_data"] if w["word"].lower() == word.lower()), "")
            st.write(f"- {word}（{meaning}）")
    else:
        st.write("尚未記錄任何單字。")

def word_cards_page():
    st.title("單字卡片")
    if "words" in st.session_state and st.session_state["words"]:
        for word in st.session_state["words"]:
            word_key = word.strip().lower()
            meaning = next((w["meaning"] for w in st.session_state["words_data"] if w["word"].strip().lower() == word_key and w["meaning"]), None)
            if meaning:
                with st.expander(f"單字: {word}"):
                    st.write(f"意思: {meaning}")
            else:
                st.write(f"- {word}（尚未輸入意思，請回學習頁補上）")
    else:
        st.info("尚未記錄任何單字，請先到學習頁新增單字。")

def stats_page():
    st.title("單字測驗結果分析報告")
    # 讀取 log.json
    if not os.path.exists("log.json"):
        st.warning("尚未發現測驗紀錄檔 log.json，請先完成測驗並儲存紀錄。")
        return

    with open("log.json", "r", encoding="utf-8") as f:
        log_data = json.load(f)

    # 分析錯誤率與錯誤單字
    total = len(log_data)
    correct = sum(1 for item in log_data if item["is_correct"])
    wrong = total - correct
    accuracy = round((correct / total) * 100, 2) if total > 0 else 0
    error_rate = round(100 - accuracy, 2) if total > 0 else 0

    # 錯誤單字統計
    wrong_words = [item["word"] for item in log_data if not item["is_correct"]]
    wrong_counts = Counter(wrong_words).most_common()

    # 顯示統計資訊
    st.subheader("測驗統計")
    st.write(f"總題數：{total}")
    st.write(f"正確題數：{correct}")
    st.write(f"錯誤題數：{wrong}")
    st.write(f"正確率：{accuracy}%")

    # 遺忘單字單字提示
    if wrong_counts:
        st.subheader("遺忘單字提示")
        st.info("以下單字曾經答錯多次，建議重複複習：")
        # 以表格方式呈現
        import pandas as pd
        df_wrong = pd.DataFrame(wrong_counts, columns=["單字", "錯誤次數"])
        st.table(df_wrong)

    # 歷史測驗分析紀錄表格
    if os.path.exists("quiz_result.json"):
        with open("quiz_result.json", "r", encoding="utf-8") as f:
            quiz_results = json.load(f)
        # 新增：加上編號，從1開始
        for idx, row in enumerate(quiz_results, start=1):
            row["編號"] = idx
        # 讓「編號」顯示在最前面
        if quiz_results:
            cols = ["編號"] + [k for k in quiz_results[0] if k != "編號"]
            st.subheader("📊 歷史測驗分析紀錄")
            st.table([{k: row[k] for k in cols} for row in quiz_results])
        else:
            st.subheader("📊 歷史測驗分析紀錄")
            st.write("尚無紀錄")

    # 歷史測驗分析紀錄管理（刪除按鈕）
    st.subheader("📊 歷史測驗分析紀錄管理")
    if st.button("刪除所有歷史測驗分析紀錄（quiz_result.json）"):
        st.session_state.show_clear_quiz_result_confirm = True
    if st.session_state.get("show_clear_quiz_result_confirm", False):
        st.warning("確定要刪除所有歷史測驗分析紀錄嗎？此動作無法復原！")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("是，刪除所有紀錄"):
                if os.path.exists("quiz_result.json"):
                    with open("quiz_result.json", "w", encoding="utf-8") as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                st.success("已刪除 quiz_result.json！")
                st.session_state.show_clear_quiz_result_confirm = False
        with col2:
            if st.button("否", key="cancel_clear_quiz_result"):
                st.session_state.show_clear_quiz_result_confirm = False
    # 讀取 checkin.json
    if os.path.exists("checkin.json"):
        with open("checkin.json", "r", encoding="utf-8") as f:
            checkins = json.load(f)
        # 計算所有打卡（學習與測驗）
        answer_count = len(checkins)
        # 取出所有打卡日期
        answer_dates = [c["datetime"][:10] for c in checkins]
        unique_dates = sorted(set(answer_dates))
        # 計算最長連續打卡天數
        max_streak = 0
        streak = 0
        last_date = None
        for d in unique_dates:
            d_obj = dt.strptime(d, "%Y-%m-%d")
            if last_date is None or (d_obj - last_date).days == 1:
                streak += 1
            else:
                streak = 1
            if streak > max_streak:
                max_streak = streak
            last_date = d_obj
        st.subheader("打卡分析")
        st.write(f"累積打卡天數：{len(unique_dates)}")
        st.write(f"最長連續打卡天數：{max_streak}")
    else:
        st.subheader("打卡分析")
        st.info("目前沒有打卡紀錄。")

    # 加入清空打卡資料按鈕
    st.subheader("⚠️ 打卡管理")
    if st.button("清空所有打卡資料（checkin.json）"):
        st.session_state.show_clear_checkin_confirm = True
    if st.session_state.get("show_clear_checkin_confirm", False):
        st.warning("確定要清空所有打卡資料嗎？此動作無法復原！")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("是，清空所有打卡資料"):
                for fname in ["checkin.json"]:
                    if os.path.exists(fname):
                        with open(fname, "w", encoding="utf-8") as f:
                            json.dump([], f, ensure_ascii=False, indent=2)
                st.success("已清空 checkin.json！")
                st.session_state.show_clear_checkin_confirm = False
                st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
        with col2:
            if st.button("否", key="cancel_clear_checkin"):
                st.session_state.show_clear_checkin_confirm = False

def word_overview_page():
    st.title("單字總覽")
    words = st.session_state.get("words_data", [])
    if not words:
        st.info("目前沒有單字紀錄。")
        return
    # 依英文單字排序
    sorted_words = sorted(words, key=lambda x: x["word"].lower())
    for idx, w in enumerate(sorted_words):
        row_key = f"word_{idx}_{w['word']}"
        edit_key = f"edit_{row_key}"
        del_key = f"del_{row_key}"
        confirm_del_key = f"confirm_del_{row_key}"
        editing = st.session_state.get(edit_key, False)
        confirming_del = st.session_state.get(confirm_del_key, False)
        col1, col2, col3 = st.columns([4, 4, 2])
        with col1:
            if not editing:
                if st.button(w["word"], key=f"btn_word_{row_key}"):
                    st.session_state[edit_key] = "word"
            else:
                if st.session_state[edit_key] == "word":
                    new_word = st.text_input("編輯英文單字", value=w["word"], key=f"edit_word_input_{row_key}")
                    if st.button("儲存", key=f"save_word_{row_key}"):
                        # 檢查重複
                        if new_word and new_word != w["word"] and any(x["word"] == new_word for x in words):
                            st.error("已有相同英文單字，請重新輸入！")
                        elif new_word:
                            w["word"] = new_word
                            save_words(words)
                            st.session_state[edit_key] = False
                            st.success("已更新！")
                            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
                    if st.button("取消", key=f"cancel_word_{row_key}"):
                        st.session_state[edit_key] = False
        with col2:
            if not editing:
                if st.button(w["meaning"], key=f"btn_meaning_{row_key}"):
                    st.session_state[edit_key] = "meaning"
            else:
                if st.session_state[edit_key] == "meaning":
                    new_meaning = st.text_input("編輯中文意思", value=w["meaning"], key=f"edit_meaning_input_{row_key}")
                    if st.button("儲存", key=f"save_meaning_{row_key}"):
                        if new_meaning:
                            w["meaning"] = new_meaning
                            save_words(words)
                            st.session_state[edit_key] = False
                            st.success("已更新！")
                            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
                    if st.button("取消", key=f"cancel_meaning_{row_key}"):
                        st.session_state[edit_key] = False
        with col3:
            if not confirming_del:
                if st.button("刪除", key=f"del_btn_{row_key}"):
                    st.session_state[confirm_del_key] = True
            else:
                st.warning("確定要刪除這個單字嗎？")
                if st.button("是", key=f"yes_del_{row_key}"):
                    words.remove(w)
                    save_words(words)
                    st.session_state[confirm_del_key] = False
                    st.success("已刪除！")
                    st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
                if st.button("否", key=f"no_del_{row_key}"):
                    st.session_state[confirm_del_key] = False

# --------------------
# 主程式
# --------------------
def main():
    # 初始化 Session State
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "words" not in st.session_state:
        st.session_state["words"] = load_today_words()
    # 側邊欄選單
    st.sidebar.title("背單字習慣追蹤系統")
    # 刪除側邊欄的清空所有單字按鈕
    # if st.sidebar.button("⚠️ 清空所有單字"):
    #     clear_words()
    page = None
    if st.session_state["logged_in"]:
        page = st.sidebar.radio("選擇頁面", ["首頁", "學習", "單字卡片", "單字總覽", "選擇題測驗", "分析報告", "複習"])
    else:
        login_page()
        return
    if page == "首頁":
        home_page()
    elif page == "學習":
        study_page()
    elif page == "單字卡片":
        word_cards_page()
    elif page == "單字總覽":
        word_overview_page()
    elif page == "選擇題測驗":
        quiz_page()
    elif page == "分析報告":
        stats_page()
    elif page == "複習":
        review_page()

def clear_words():
    st.session_state["words"] = []
    st.session_state["words_data"] = []
    save_words([])  # 清空 words.json
    st.success("已清空所有單字資料！")

def get_due_words(words):
    """取得今天需要複習的單字（依level間隔），沒有 last_review 的單字也會出現"""
    today = datetime.date.today()
    level_days = {1: 1, 2: 3, 3: 7, 4: 13, 5: 21}
    due_words = []
    for w in words:
        level = w.get("level", 1)
        last = w.get("last_review")
        if last is None:
            # 沒有複習過的單字直接加入
            due_words.append(w)
            continue
        last_date = datetime.datetime.strptime(last, "%Y-%m-%d").date()
        interval = level_days.get(level, 1)
        if (today - last_date).days >= interval and level < 5:
            due_words.append(w)
    return due_words

def get_permanent_words(words):
    """取得永久記憶區單字（level==5且已答對一次）"""
    today = datetime.date.today()
    level_days = {1: 1, 2: 3, 3: 7, 4: 13, 5: 21}
    permanent = []
    for w in words:
        if w.get("level", 1) == 5:
            last = w.get("last_review", today.isoformat())
            last_date = datetime.datetime.strptime(last, "%Y-%m-%d").date()
            if (today - last_date).days >= level_days[5]:
                permanent.append(w)
    return permanent

def review_page():
    st.title("複習")
    tab = st.radio(
        "請選擇區塊：",
        ["複習單字區", "目前單字記憶狀況", "永久記憶區"],
        horizontal=True
    )
    words = load_words()
    due_words = get_due_words(words)
    permanent = get_permanent_words(words)
    level_words = {i: [] for i in range(1, 6)}
    for w in words:
        level = w.get("level", 1)
        if level <= 5:
            level_words[level].append(w["word"])

    if tab == "複習單字區":
        st.subheader("複習單字區")
        if "review_queue" not in st.session_state or not st.session_state["review_queue"]:
            st.session_state["review_queue"] = random.sample(due_words, len(due_words)) if due_words else []
            st.session_state["review_idx"] = 0
            st.session_state["show_answer"] = False
            st.session_state["level_change_msg"] = ""

        if not st.session_state["review_queue"]:
            st.success("今日沒有需要複習的單字！")
        else:
            idx = st.session_state["review_idx"]
            word_item = st.session_state["review_queue"][idx]
            level_now = word_item.get("level", 1)
            st.markdown(f"**單字：{word_item['word']}  （Level {level_now}）**")

            if not st.session_state.get("show_answer", False):
                colA, colB = st.columns(2)
                with colA:
                    if st.button("記得"):
                        for w in words:
                            if w["word"] == word_item["word"]:
                                old_level = w.get("level", 1)
                                new_level = min(old_level + 1, 5)
                                w["level"] = new_level
                                w["last_review"] = datetime.date.today().isoformat()
                                st.session_state["level_change_msg"] = f"Level {old_level} → Level {new_level}"
                                break
                        save_words(words)
                        st.session_state["show_answer"] = True
                with colB:
                    if st.button("忘記"):
                        for w in words:
                            if w["word"] == word_item["word"]:
                                old_level = w.get("level", 1)
                                new_level = max(old_level - 1, 1)
                                w["level"] = new_level
                                w["last_review"] = datetime.date.today().isoformat()
                                st.session_state["level_change_msg"] = f"Level {old_level} → Level {new_level}"
                                break
                        save_words(words)
                        st.session_state["show_answer"] = True
            else:
                st.info(f"中文意思：{word_item['meaning']}")
                if st.session_state.get("level_change_msg"):
                    st.success(f"等級變化：{st.session_state['level_change_msg']}")
                if st.button("下一題"):
                    st.session_state["review_idx"] += 1
                    st.session_state["show_answer"] = False
                    st.session_state["level_change_msg"] = ""
                    if st.session_state["review_idx"] >= len(st.session_state["review_queue"]):
                        st.session_state["review_queue"] = []
                        st.session_state["review_idx"] = 0
                        st.success("複習結束！")

    elif tab == "目前單字記憶狀況":
        st.subheader("目前單字記憶狀況")
        cols = st.columns(5)
        for i in range(1, 6):
            with cols[i-1]:
                st.markdown(f"**● Level {i}**")
                if level_words[i]:
                    for word in level_words[i]:
                        st.write(word)
                else:
                    st.write("—")

    elif tab == "永久記憶區":
        st.subheader("永久記憶區單字")
        if permanent:
            for w in permanent:
                st.write(f"- {w['word']}：{w['meaning']}")
        else:
            st.info("目前沒有單字進入永久記憶區。")
            st.write("請繼續努力！")

if __name__ == "__main__":
    main()