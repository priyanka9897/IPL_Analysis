"""
02_analysis_and_charts.py
Runs the SQL queries from sql/analysis_queries.sql against ipl.db,
and produces a set of charts summarizing the findings.

This is the "Python + SQL combined" half of the project: SQL does the
heavy aggregation, pandas/matplotlib turn the results into visuals a
non-technical stakeholder could actually read.
"""
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 110

conn = sqlite3.connect("ipl.db")


def q(sql):
    return pd.read_sql_query(sql, conn)


# ---------------------------------------------------------------
# 1. Toss impact
# ---------------------------------------------------------------
toss = q("""
    SELECT CASE WHEN toss_winner = winner THEN 'Won Toss & Match'
                ELSE 'Won Toss, Lost Match' END AS outcome,
           COUNT(*) AS matches
    FROM matches WHERE result = 'normal'
    GROUP BY outcome
""")
plt.figure(figsize=(5, 5))
plt.pie(toss["matches"], labels=toss["outcome"], autopct="%1.1f%%",
        colors=["#4C72B0", "#DD8452"], startangle=90)
plt.title("Does Winning the Toss Predict Winning the Match?")
plt.tight_layout()
plt.savefig("charts/01_toss_impact.png")
plt.close()

# ---------------------------------------------------------------
# 2. Top run scorers
# ---------------------------------------------------------------
top_scorers = q("""
    SELECT batsman, SUM(batsman_runs) AS total_runs
    FROM deliveries GROUP BY batsman
    ORDER BY total_runs DESC LIMIT 10
""")
plt.figure(figsize=(8, 5))
sns.barplot(data=top_scorers, y="batsman", x="total_runs", palette="viridis")
plt.title("Top 10 Run Scorers (2008-2017)")
plt.xlabel("Total Runs")
plt.ylabel("")
plt.tight_layout()
plt.savefig("charts/02_top_scorers.png")
plt.close()

# ---------------------------------------------------------------
# 3. Chasing win % trend by season
# ---------------------------------------------------------------
chase = q("""
    WITH batting_first AS (
        SELECT match_id, batting_team AS team1_bat
        FROM deliveries WHERE inning = 1 GROUP BY match_id
    )
    SELECT m.season,
           ROUND(100.0 * SUM(CASE WHEN m.winner != bf.team1_bat AND m.winner != 'No Result' THEN 1 ELSE 0 END)
                 / COUNT(*), 1) AS chasing_win_pct
    FROM matches m JOIN batting_first bf ON m.id = bf.match_id
    GROUP BY m.season ORDER BY m.season
""")
plt.figure(figsize=(8, 5))
sns.lineplot(data=chase, x="season", y="chasing_win_pct", marker="o", linewidth=2.5, color="#55A868")
plt.axhline(50, color="grey", linestyle="--", alpha=0.6, label="50% (coin flip)")
plt.title("Chasing Team Win % by Season")
plt.ylabel("Win % When Batting Second")
plt.xlabel("Season")
plt.legend()
plt.tight_layout()
plt.savefig("charts/03_chase_win_trend.png")
plt.close()

# ---------------------------------------------------------------
# 4. Best economy bowlers (min 300 balls)
# ---------------------------------------------------------------
econ = q("""
    SELECT bowler, ROUND(SUM(total_runs) * 6.0 / COUNT(*), 2) AS economy_rate
    FROM deliveries GROUP BY bowler
    HAVING COUNT(*) >= 300
    ORDER BY economy_rate ASC LIMIT 10
""")
plt.figure(figsize=(8, 5))
sns.barplot(data=econ, y="bowler", x="economy_rate", palette="mako")
plt.title("Best Economy Rate — Bowlers with 300+ Balls Bowled")
plt.xlabel("Economy Rate (runs/over)")
plt.ylabel("")
plt.tight_layout()
plt.savefig("charts/04_best_economy.png")
plt.close()

# ---------------------------------------------------------------
# 5. Highest scoring venues
# ---------------------------------------------------------------
venues = q("""
    SELECT venue, ROUND(AVG(total_runs), 1) AS avg_runs_per_match
    FROM (
        SELECT match_id, venue, SUM(total_runs) AS total_runs
        FROM deliveries d JOIN matches m ON d.match_id = m.id
        GROUP BY match_id
    ) GROUP BY venue
    HAVING COUNT(*) >= 10
    ORDER BY avg_runs_per_match DESC LIMIT 10
""")
plt.figure(figsize=(9, 5))
sns.barplot(data=venues, y="venue", x="avg_runs_per_match", palette="rocket")
plt.title("Highest-Scoring Venues (10+ Matches Hosted)")
plt.xlabel("Avg Total Runs per Match")
plt.ylabel("")
plt.tight_layout()
plt.savefig("charts/05_highscoring_venues.png")
plt.close()

print("All 5 charts saved to charts/")
print("\n--- Key numbers for your writeup ---")
print(toss.to_string(index=False))
print()
print(top_scorers.head(3).to_string(index=False))
print()
print("Chase win % range:", chase["chasing_win_pct"].min(), "-", chase["chasing_win_pct"].max())

conn.close()
