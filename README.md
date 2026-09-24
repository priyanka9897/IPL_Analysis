# IPL Match & Player Performance Analytics Platform

**An end-to-end Full-Stack Python + SQL Data Analytics Platform on 10 seasons of IPL cricket (2008–2017).**  
Analyzes 636 matches and 150,000+ ball-by-ball deliveries through an interactive web dashboard powered by FastAPI, SQLite, Chart.js, and modern Vanilla web technologies.

---

## 🌟 Features & Highlights

- **📊 Overview & Macro Trends:** Real-time KPI summaries, interactive Toss Impact donut chart, season-by-season Chasing Win % line progression, and stadium run-scoring rankings.
- **⚡ Batting & Bowling Leaderboards:** Dynamic Orange Cap and bowling economy rankings filterable by season (2008–2017) with custom minimum overs/balls sliders.
- **⚔️ Franchise Head-to-Head Simulator:** Select any two IPL teams (e.g., Mumbai Indians vs Chennai Super Kings) to simulate rivalry win splits, average scores, and encounter histories.
- **🔍 Player Deep Dive:** Autocomplete search and quick-picks for any player (Virat Kohli, MS Dhoni, Suresh Raina, Lasith Malinga) with career milestones and dual-axis yearly performance charts.
- **💻 Live SQL Lab:** Built-in interactive SQL console allowing users and interviewers to run read-only `SELECT` queries live against `ipl.db` with execution runtime metrics and CSV export.
- **📖 Auto-Generated API Docs:** Interactive Swagger UI available at `/docs`.

---

## 📂 Project Structure

```
ipl_project/
├── backend/
│   ├── __init__.py
│   └── main.py                # FastAPI REST API & static file server
├── frontend/
│   ├── index.html             # Single-page interactive dashboard
│   ├── style.css              # Custom Vanilla CSS design system (Dark mode & Glassmorphism)
│   └── app.js                 # Frontend state, API integration, and Chart.js controllers
├── data/
│   ├── matches.csv            # 636 matches: teams, toss, result, venue
│   └── deliveries.csv         # 150,460 ball-by-ball records
├── sql/
│   └── analysis_queries.sql   # 8 canonical SQL queries (joins, CTEs, window functions)
├── charts/                    # Static Matplotlib/Seaborn output visualizations
├── 01_build_database.py       # Ingests CSVs into indexed SQLite database
├── 02_analysis_and_charts.py  # Generates static PNG charts
├── run.py                     # One-command fullstack launcher
├── requirements.txt           # Python dependencies
├── ipl.db                     # Generated indexed SQLite database
└── README.md
```

---

## 🚀 How to Run Locally

### 1. Setup Virtual Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Build Database (if not already generated)
```bash
python3 01_build_database.py
```

### 3. Launch the Interactive Platform
```bash
python run.py
```
- **Web Dashboard:** Open [http://localhost:8000](http://localhost:8000) in your browser.
- **API Swagger Documentation:** Open [http://localhost:8000/docs](http://localhost:8000/docs).

*(Optional) Generate static chart images to `charts/`:*
```bash
python3 02_analysis_and_charts.py
```

---

## 📊 Key Analytics & Insights

1. **The toss barely matters:** Toss winners went on to win only **51.4%** of matches (322 of 626), proving that winning the toss is practically a 50/50 coin flip.
2. **Chasing advantage has grown:** Chasing (batting second) win rates rose from **42.4%** in 2009 to a peak of **68.3%** in 2016 as teams mastered target pacing.
3. **Leading career scorer (2008–2017):** **Suresh Raina** led with 4,548 runs, narrowly ahead of Virat Kohli (4,423) and Rohit Sharma (4,207).
4. **Venue dynamics:** M. Chinnaswamy Stadium (Bengaluru) leads in run production, averaging over 320 runs per match.

---

## 🛠️ Tech Stack & Methods

- **Backend:** Python, FastAPI, Uvicorn, SQLite3.
- **Frontend:** HTML5, Modern Vanilla CSS (Glassmorphism & CSS Grid), Vanilla JavaScript, Chart.js.
- **Data & Analytics:** Pandas, Matplotlib, Seaborn.
- **SQL Techniques:** Multi-table `JOIN`s, Common Table Expressions (`WITH`), Window functions (`DENSE_RANK() OVER (PARTITION BY ...)`), conditional aggregation (`CASE WHEN`), and `HAVING` sample-size filters.

---

## 📄 License & Source
Data sourced from Kaggle/Cricsheet (2008–2017). Project created for sports performance analytics and data science demonstration.
