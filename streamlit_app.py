
import os
import sqlite3
import datetime as dt
from contextlib import closing
from typing import Dict, Any, List, Tuple

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# -----------------------------
# App Config
# -----------------------------
st.set_page_config(page_title="CoreSync AI", page_icon="💪", layout="wide")

DB_PATH = "coresync.db"

# -----------------------------
# Utilities
# -----------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    with closing(get_conn()) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                exercise TEXT NOT NULL,
                muscle_group TEXT NOT NULL,
                sets INTEGER,
                reps INTEGER,
                weight REAL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nutrition (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                food TEXT NOT NULL,
                calories REAL NOT NULL,
                protein REAL NOT NULL,
                fat REAL,
                carbs REAL,
                fiber REAL,
                sugar REAL,
                sodium REAL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        # Seed test user if not exists
        cur = conn.execute("SELECT id FROM users WHERE username = ?", ("testuser",))
        if cur.fetchone() is None:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("testuser", "test123"))

def get_user_id(username: str) -> int:
    with closing(get_conn()) as conn, conn:
        cur = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
    return row[0] if row else None

def validate_login(username: str, password: str) -> bool:
    with closing(get_conn()) as conn:
        cur = conn.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if not row:
            return False
        return row[0] == password  # NOTE: For demo only. Use hashing in production.

def ensure_logged_in():
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
    if st.session_state.auth_user is None:
        with st.form("login_form", clear_on_submit=False):
            st.subheader("Login to CoreSync AI")
            username = st.text_input("Username", value="testuser")
            password = st.text_input("Password", value="test123", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            if validate_login(username, password):
                st.session_state.auth_user = username
                st.toast("Logged in successfully.", icon="✅")
                st.rerun()
            else:
                st.error("Invalid credentials. Try testuser / test123 for demo.")
        st.stop()

# -----------------------------
# Workout Logic
# -----------------------------
MUSCLE_GROUPS = [
    "Chest", "Back", "Shoulders", "Biceps", "Triceps",
    "Core", "Quads", "Hamstrings", "Glutes", "Calves"
]

def add_workout(user_id: int, date: str, exercise: str, muscle_group: str, sets: int, reps: int, weight: float):
    with closing(get_conn()) as conn, conn:
        conn.execute("""
            INSERT INTO workouts (user_id, date, exercise, muscle_group, sets, reps, weight)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, date, exercise, muscle_group, sets, reps, weight))

def get_workouts(user_id: int, month: int, year: int) -> pd.DataFrame:
    with closing(get_conn()) as conn:
        cur = conn.execute("""
            SELECT date, exercise, muscle_group, sets, reps, weight
            FROM workouts
            WHERE user_id = ? AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
            ORDER BY date ASC
        """, (user_id, f"{month:02d}", str(year)))
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["date", "exercise", "muscle_group", "sets", "reps", "weight"])
    return df

def muscle_heat_counts(user_id: int, start_date: str = None, end_date: str = None) -> Dict[str, int]:
    q = "SELECT muscle_group, COUNT(*) FROM workouts WHERE user_id = ?"
    params = [user_id]
    if start_date:
        q += " AND date >= ?"
        params.append(start_date)
    if end_date:
        q += " AND date <= ?"
        params.append(end_date)
    q += " GROUP BY muscle_group"
    with closing(get_conn()) as conn:
        cur = conn.execute(q, tuple(params))
        rows = cur.fetchall()
    counts = {mg: 0 for mg in MUSCLE_GROUPS}
    for mg, c in rows:
        if mg in counts:
            counts[mg] = c
    return counts

def render_body_heatmap(counts: Dict[str, int]):
    # Simple schematic body silhouette using rectangles for key muscle groups.
    # Intensity mapped to alpha; not setting specific colors per tool guidance, using default facecolor.
    fig, ax = plt.subplots(figsize=(4, 8))
    ax.set_xlim(0, 10); ax.set_ylim(0, 20)
    ax.axis('off')

    def draw_block(x, y, w, h, value, label):
        alpha = 0.2 + min(value, 10) * 0.08  # clamp for visibility
        rect = Rectangle((x, y), w, h, alpha=alpha)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=8)

    # Torso / core regions
    draw_block(3, 12, 4, 3, counts.get("Chest", 0), "Chest")
    draw_block(3, 9, 4, 3, counts.get("Back", 0), "Back")
    draw_block(3, 6, 4, 3, counts.get("Core", 0), "Core")
    # Shoulders
    draw_block(2.2, 15, 2, 1.5, counts.get("Shoulders", 0), "Shoulders")
    draw_block(5.8, 15, 2, 1.5, counts.get("Shoulders", 0), "")
    # Arms
    draw_block(1, 13, 1.5, 2, counts.get("Biceps", 0), "Bi")
    draw_block(0, 13, 1, 2, counts.get("Triceps", 0), "Tri")
    draw_block(7.5, 13, 1.5, 2, counts.get("Biceps", 0), "")
    draw_block(9, 13, 1, 2, counts.get("Triceps", 0), "")
    # Legs / lower body
    draw_block(3, 3, 2, 3, counts.get("Quads", 0), "Quads")
    draw_block(5, 3, 2, 3, counts.get("Quads", 0), "")
    draw_block(3, 0, 2, 3, counts.get("Hamstrings", 0), "Hams")
    draw_block(5, 0, 2, 3, counts.get("Hamstrings", 0), "")
    # Glutes
    draw_block(3, 6, 4, 1.2, counts.get("Glutes", 0), "Glutes")
    # Calves
    draw_block(3, -1.5, 2, 1.5, counts.get("Calves", 0), "Calves")
    draw_block(5, -1.5, 2, 1.5, counts.get("Calves", 0), "")

    st.pyplot(fig)

# -----------------------------
# Nutrition Logic
# -----------------------------
def add_food(user_id: int, date: str, food: str, calories: float, protein: float,
             fat: float = None, carbs: float = None, fiber: float = None,
             sugar: float = None, sodium: float = None):
    with closing(get_conn()) as conn, conn:
        conn.execute("""
            INSERT INTO nutrition (user_id, date, food, calories, protein, fat, carbs, fiber, sugar, sodium)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, date, food, calories, protein, fat, carbs, fiber, sugar, sodium))

def get_nutrition(user_id: int, month: int, year: int) -> pd.DataFrame:
    with closing(get_conn()) as conn:
        cur = conn.execute("""
            SELECT date, food, calories, protein, fat, carbs, fiber, sugar, sodium
            FROM nutrition
            WHERE user_id = ? AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
            ORDER BY date ASC
        """, (user_id, f"{month:02d}", str(year)))
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["date", "food", "calories", "protein", "fat", "carbs", "fiber", "sugar", "sodium"])
    return df

def daily_averages(df: pd.DataFrame) -> Tuple[pd.DataFrame, float, float]:
    if df.empty:
        return pd.DataFrame(columns=["date", "avg_calories", "avg_protein"]), 0.0, 0.0
    agg = df.groupby("date").agg(avg_calories=("calories", "mean"), avg_protein=("protein", "mean")).reset_index()
    return agg, agg["avg_calories"].mean(), agg["avg_protein"].mean()

def plot_daily_series(agg: pd.DataFrame, y_col: str, title: str):
    fig, ax = plt.subplots()
    if not agg.empty:
        ax.plot(pd.to_datetime(agg["date"]), agg[y_col], marker="o")
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel(y_col.replace("_", " ").title())
    st.pyplot(fig)

# -----------------------------
# Chatbot Logic
# -----------------------------
def chat_with_model(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", None)
    if not api_key:
        # Fallback simple response (demo mode without API key)
        if "calorie" in prompt.lower():
            return "Approximate calorie counts vary; try logging food name, serving size, and brand for better estimates."
        if "protein" in prompt.lower():
            return "A common target is ~0.7–1.0 g protein per lb of goal bodyweight, depending on training intensity."
        if "workout" in prompt.lower() or "plan" in prompt.lower():
            return "Consider a push/pull/legs split 3–6x/week. Balance volume per muscle group and track progressive overload."
        return "I'm in demo mode without an API key. Add OPENAI_API_KEY to enable full responses."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        # Use a small, cost-effective model; adjust as needed
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a helpful fitness and nutrition assistant."},
                      {"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error calling model: {e}"

# -----------------------------
# UI Sections
# -----------------------------
def section_workouts(user_id: int):
    st.header("🏋️ Workouts")
    colA, colB = st.columns([1, 2])

    with colA:
        st.subheader("Log Workout")
        today = dt.date.today()
        date = st.date_input("Date", value=today)
        exercise = st.text_input("Exercise (e.g., Bench Press)")
        muscle = st.selectbox("Muscle Group", MUSCLE_GROUPS, index=0)
        c1, c2, c3 = st.columns(3)
        with c1:
            sets = st.number_input("Sets", min_value=1, max_value=20, value=3, step=1)
        with c2:
            reps = st.number_input("Reps", min_value=1, max_value=50, value=8, step=1)
        with c3:
            weight = st.number_input("Weight", min_value=0.0, max_value=2000.0, value=135.0, step=5.0)
        if st.button("Add Workout"):
            if exercise.strip():
                add_workout(user_id, str(date), exercise.strip(), muscle, int(sets), int(reps), float(weight))
                st.success("Workout added.")
            else:
                st.warning("Please enter an exercise name.")

    with colB:
        st.subheader("Calendar View")
        month = st.selectbox("Month", list(range(1, 13)), index=dt.date.today().month - 1)
        year = st.number_input("Year", min_value=2000, max_value=2100, value=dt.date.today().year, step=1)
        df = get_workouts(user_id, month, year)
        if df.empty:
            st.info("No workouts logged for this month yet.")
        else:
            st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.subheader("Muscle Group Heatmap")
        # Allow date range selection for heatmap
        cstart, cend = st.columns(2)
        with cstart:
            start_date = st.date_input("Start Date", value=dt.date(year, month, 1))
        with cend:
            # Get last day of the month
            last_day = dt.date(year, month, 28)
            while True:
                try:
                    last_day = dt.date(year, month, last_day.day + 1)
                except ValueError:
                    break
            last_day = last_day - dt.timedelta(days=1)
            end_date = st.date_input("End Date", value=last_day)
        counts = muscle_heat_counts(user_id, str(start_date), str(end_date))
        render_body_heatmap(counts)

def section_nutrition(user_id: int):
    st.header("🍽️ Calories & Nutrition")
    colA, colB = st.columns([1, 2])

    with colA:
        st.subheader("Log Food")
        today = dt.date.today()
        date = st.date_input("Date ", value=today, key="food_date")
        food = st.text_input("Food name (required)")
        calories = st.number_input("Calories (required)", min_value=0.0, value=300.0, step=10.0)
        protein = st.number_input("Protein grams (required)", min_value=0.0, value=20.0, step=1.0)
        with st.expander("Optional nutrition fields"):
            fat = st.number_input("Fat (g)", min_value=0.0, value=0.0, step=1.0)
            carbs = st.number_input("Carbs (g)", min_value=0.0, value=0.0, step=1.0)
            fiber = st.number_input("Fiber (g)", min_value=0.0, value=0.0, step=1.0)
            sugar = st.number_input("Sugar (g)", min_value=0.0, value=0.0, step=1.0)
            sodium = st.number_input("Sodium (mg)", min_value=0.0, value=0.0, step=10.0)

        if st.button("Add Food Entry"):
            if food.strip() and calories >= 0 and protein >= 0:
                add_food(user_id, str(date), food.strip(), float(calories), float(protein),
                         float(fat), float(carbs), float(fiber), float(sugar), float(sodium))
                st.success("Food entry added.")
            else:
                st.warning("Food, calories, and protein are required.")

    with colB:
        st.subheader("Calendar View")
        month = st.selectbox("Month ", list(range(1, 13)), index=dt.date.today().month - 1, key="nutri_month")
        year = st.number_input("Year ", min_value=2000, max_value=2100, value=dt.date.today().year, step=1, key="nutri_year")
        df = get_nutrition(user_id, month, year)
        if df.empty:
            st.info("No nutrition data for this month yet.")
        else:
            st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.subheader("Real-Time Analytics")
        agg, avg_cal, avg_pro = daily_averages(df)
        st.caption(f"Overall average calories/day: {avg_cal:.1f} | average protein/day: {avg_pro:.1f} g")

        # Line charts using matplotlib (no specific colors/styles)
        plot_daily_series(agg, "avg_calories", "Average Calories per Day")
        plot_daily_series(agg, "avg_protein", "Average Protein per Day")

def section_chatbot(_user_id: int):
    st.header("🤖 Chatbot")
    st.caption("Ask about calorie counts, workout plans, and general fitness questions. "
               "Set OPENAI_API_KEY env var to enable full model responses.")
    prompt = st.text_area("Your question")
    if st.button("Ask"):
        if prompt.strip():
            with st.spinner("Thinking..."):
                ans = chat_with_model(prompt.strip())
            st.markdown("**Answer:**")
            st.write(ans)
        else:
            st.warning("Please enter a question.")

# -----------------------------
# Main App
# -----------------------------
def main():
    init_db()
    ensure_logged_in()
    username = st.session_state.auth_user
    user_id = get_user_id(username)

    st.sidebar.success(f"Logged in as: {username}")
    page = st.sidebar.radio("Navigate", ["Workouts", "Calories", "Chatbot"])

    if page == "Workouts":
        section_workouts(user_id)
    elif page == "Calories":
        section_nutrition(user_id)
    else:
        section_chatbot(user_id)

if __name__ == "__main__":
    main()
