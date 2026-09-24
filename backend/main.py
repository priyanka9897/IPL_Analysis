"""
backend/main.py
FastAPI backend for IPL Analytics Dashboard.
Connects to SQLite ipl.db and exposes endpoints for metrics,
charts, head-to-head simulations, player stats, and a live SQL runner.
"""

import os
import sqlite3
import time
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ipl.db")

app = FastAPI(
    title="IPL Analytics API",
    description="Interactive API for 10 seasons of IPL Cricket Data Analysis (2008-2017)",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------------------------------------
# 1. OVERVIEW & METRICS
# -------------------------------------------------------------
@app.get("/api/overview")
def get_overview():
    with get_db() as conn:
        cur = conn.cursor()

        # Matches summary
        cur.execute("""
            SELECT 
                COUNT(*) as total_matches,
                COUNT(DISTINCT season) as total_seasons,
                COUNT(DISTINCT city) as total_cities,
                COUNT(DISTINCT venue) as total_venues
            FROM matches
        """)
        m_row = dict(cur.fetchone())

        # Deliveries summary
        cur.execute("""
            SELECT 
                COUNT(*) as total_balls,
                SUM(total_runs) as total_runs,
                SUM(CASE WHEN batsman_runs = 4 THEN 1 ELSE 0 END) as total_fours,
                SUM(CASE WHEN batsman_runs = 6 THEN 1 ELSE 0 END) as total_sixes,
                COUNT(DISTINCT batsman) as total_batsmen,
                COUNT(DISTINCT bowler) as total_bowlers
            FROM deliveries
        """)
        d_row = dict(cur.fetchone())

        # Toss impact overall
        cur.execute("""
            SELECT 
                ROUND(100.0 * SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END) / COUNT(*), 1) as toss_win_pct
            FROM matches
            WHERE result = 'normal'
        """)
        toss_pct = cur.fetchone()[0]

        # Chasing win % overall
        cur.execute("""
            WITH batting_first AS (
                SELECT match_id, batting_team AS team1_bat
                FROM deliveries WHERE inning = 1 GROUP BY match_id
            )
            SELECT 
                ROUND(100.0 * SUM(CASE WHEN m.winner != bf.team1_bat AND m.winner != 'No Result' THEN 1 ELSE 0 END) / COUNT(*), 1) AS chasing_win_pct
            FROM matches m 
            JOIN batting_first bf ON m.id = bf.match_id
        """)
        chase_pct = cur.fetchone()[0]

        # Top winning team
        cur.execute("""
            SELECT winner, COUNT(*) as wins
            FROM matches
            WHERE winner != 'No Result'
            GROUP BY winner
            ORDER BY wins DESC LIMIT 1
        """)
        top_team = dict(cur.fetchone())

        return {
            **m_row,
            **d_row,
            "toss_win_pct": toss_pct,
            "chasing_win_pct": chase_pct,
            "top_team": top_team["winner"],
            "top_team_wins": top_team["wins"],
        }


# -------------------------------------------------------------
# 2. SEASONS & TEAMS METADATA
# -------------------------------------------------------------
@app.get("/api/seasons")
def get_seasons():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                m1.season,
                COUNT(m1.id) as match_count,
                (
                    SELECT winner FROM matches m2 
                    WHERE m2.season = m1.season 
                    ORDER BY id DESC LIMIT 1
                ) as champion
            FROM matches m1
            GROUP BY m1.season
            ORDER BY m1.season ASC
        """)
        return [dict(row) for row in cur.fetchall()]


@app.get("/api/teams")
def get_teams():
    with get_db() as conn:
        cur = conn.cursor()
        # Get team win totals and match totals
        cur.execute("""
            WITH all_teams AS (
                SELECT team1 as team FROM matches
                UNION
                SELECT team2 as team FROM matches
            ),
            team_matches AS (
                SELECT team, COUNT(*) as total_matches
                FROM (
                    SELECT team1 as team FROM matches
                    UNION ALL
                    SELECT team2 as team FROM matches
                )
                GROUP BY team
            ),
            team_wins AS (
                SELECT winner as team, COUNT(*) as wins
                FROM matches
                WHERE winner != 'No Result'
                GROUP BY winner
            )
            SELECT 
                t.team, 
                COALESCE(tm.total_matches, 0) as matches_played,
                COALESCE(tw.wins, 0) as matches_won,
                ROUND(100.0 * COALESCE(tw.wins, 0) / COALESCE(tm.total_matches, 1), 1) as win_pct
            FROM all_teams t
            LEFT JOIN team_matches tm ON t.team = tm.team
            LEFT JOIN team_wins tw ON t.team = tw.team
            ORDER BY matches_won DESC
        """)
        return [dict(row) for row in cur.fetchall()]


# -------------------------------------------------------------
# 3. ANALYTICAL CHARTS DATA
# -------------------------------------------------------------
@app.get("/api/charts/toss-impact")
def get_toss_impact(season: str = Query("all")):
    with get_db() as conn:
        cur = conn.cursor()
        where_clause = "WHERE result = 'normal'"
        params = []
        if season != "all":
            where_clause += " AND season = ?"
            params.append(int(season))

        # Outcome summary
        cur.execute(f"""
            SELECT 
                CASE WHEN toss_winner = winner THEN 'Won Toss & Match'
                     ELSE 'Won Toss, Lost Match' END AS outcome,
                COUNT(*) AS matches
            FROM matches
            {where_clause}
            GROUP BY outcome
        """, params)
        outcome_data = [dict(row) for row in cur.fetchall()]

        # Toss decision breakdown
        cur.execute(f"""
            SELECT 
                toss_decision,
                COUNT(*) as total,
                SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END) as toss_winner_won,
                ROUND(100.0 * SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
            FROM matches
            {where_clause}
            GROUP BY toss_decision
        """, params)
        decision_data = [dict(row) for row in cur.fetchall()]

        return {
            "outcomes": outcome_data,
            "decisions": decision_data
        }


@app.get("/api/charts/chase-trend")
def get_chase_trend():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH batting_first AS (
                SELECT match_id, batting_team AS team1_bat
                FROM deliveries WHERE inning = 1 GROUP BY match_id
            )
            SELECT 
                m.season,
                COUNT(*) AS total_matches,
                SUM(CASE WHEN m.winner = bf.team1_bat THEN 1 ELSE 0 END) AS defending_wins,
                SUM(CASE WHEN m.winner != bf.team1_bat AND m.winner != 'No Result' THEN 1 ELSE 0 END) AS chasing_wins,
                ROUND(100.0 * SUM(CASE WHEN m.winner != bf.team1_bat AND m.winner != 'No Result' THEN 1 ELSE 0 END) / COUNT(*), 1) AS chasing_win_pct
            FROM matches m 
            JOIN batting_first bf ON m.id = bf.match_id
            GROUP BY m.season 
            ORDER BY m.season ASC
        """)
        return [dict(row) for row in cur.fetchall()]


@app.get("/api/charts/top-batsmen")
def get_top_batsmen(season: str = Query("all"), limit: int = Query(10, le=50)):
    with get_db() as conn:
        cur = conn.cursor()
        if season == "all":
            cur.execute("""
                SELECT 
                    batsman,
                    SUM(batsman_runs) AS total_runs,
                    COUNT(DISTINCT match_id) AS innings_played,
                    COUNT(CASE WHEN wide_runs = 0 THEN 1 END) AS balls_faced,
                    ROUND(100.0 * SUM(batsman_runs) / MAX(COUNT(CASE WHEN wide_runs = 0 THEN 1 END), 1), 1) AS strike_rate,
                    SUM(CASE WHEN batsman_runs = 4 THEN 1 ELSE 0 END) AS fours,
                    SUM(CASE WHEN batsman_runs = 6 THEN 1 ELSE 0 END) AS sixes
                FROM deliveries
                GROUP BY batsman
                ORDER BY total_runs DESC
                LIMIT ?
            """, (limit,))
        else:
            cur.execute("""
                SELECT 
                    d.batsman,
                    SUM(d.batsman_runs) AS total_runs,
                    COUNT(DISTINCT d.match_id) AS innings_played,
                    COUNT(CASE WHEN d.wide_runs = 0 THEN 1 END) AS balls_faced,
                    ROUND(100.0 * SUM(d.batsman_runs) / MAX(COUNT(CASE WHEN d.wide_runs = 0 THEN 1 END), 1), 1) AS strike_rate,
                    SUM(CASE WHEN d.batsman_runs = 4 THEN 1 ELSE 0 END) AS fours,
                    SUM(CASE WHEN d.batsman_runs = 6 THEN 1 ELSE 0 END) AS sixes
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE m.season = ?
                GROUP BY d.batsman
                ORDER BY total_runs DESC
                LIMIT ?
            """, (int(season), limit))
        return [dict(row) for row in cur.fetchall()]


@app.get("/api/charts/bowling-economy")
def get_bowling_economy(season: str = Query("all"), min_balls: int = Query(200), limit: int = Query(10, le=50)):
    with get_db() as conn:
        cur = conn.cursor()
        if season == "all":
            cur.execute("""
                SELECT 
                    bowler,
                    COUNT(*) AS balls_bowled,
                    ROUND(COUNT(*) / 6.0, 1) AS overs_bowled,
                    SUM(total_runs) AS runs_conceded,
                    SUM(CASE WHEN dismissal_kind IS NOT NULL AND dismissal_kind NOT IN ('run out', 'retired hurt') THEN 1 ELSE 0 END) as wickets,
                    ROUND(SUM(total_runs) * 6.0 / COUNT(*), 2) AS economy_rate
                FROM deliveries
                GROUP BY bowler
                HAVING balls_bowled >= ?
                ORDER BY economy_rate ASC
                LIMIT ?
            """, (min_balls, limit))
        else:
            # Adjust min balls for single season if too high
            season_min_balls = min(min_balls, 60)
            cur.execute("""
                SELECT 
                    d.bowler,
                    COUNT(*) AS balls_bowled,
                    ROUND(COUNT(*) / 6.0, 1) AS overs_bowled,
                    SUM(d.total_runs) AS runs_conceded,
                    SUM(CASE WHEN d.dismissal_kind IS NOT NULL AND d.dismissal_kind NOT IN ('run out', 'retired hurt') THEN 1 ELSE 0 END) as wickets,
                    ROUND(SUM(d.total_runs) * 6.0 / COUNT(*), 2) AS economy_rate
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE m.season = ?
                GROUP BY d.bowler
                HAVING balls_bowled >= ?
                ORDER BY economy_rate ASC
                LIMIT ?
            """, (int(season), season_min_balls, limit))
        return [dict(row) for row in cur.fetchall()]


@app.get("/api/charts/venues")
def get_venues(min_matches: int = Query(10), limit: int = Query(10, le=30)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH match_scores AS (
                SELECT 
                    m.id, 
                    m.venue,
                    SUM(d.total_runs) AS match_total_runs
                FROM matches m
                JOIN deliveries d ON m.id = d.match_id
                GROUP BY m.id
            )
            SELECT 
                venue,
                COUNT(*) AS matches_hosted,
                ROUND(AVG(match_total_runs), 1) AS avg_runs_per_match,
                MAX(match_total_runs) AS highest_match_score,
                MIN(match_total_runs) AS lowest_match_score
            FROM match_scores
            GROUP BY venue
            HAVING matches_hosted >= ?
            ORDER BY avg_runs_per_match DESC
            LIMIT ?
        """, (min_matches, limit))
        return [dict(row) for row in cur.fetchall()]


# -------------------------------------------------------------
# 4. HEAD-TO-HEAD RIVALRY SIMULATOR
# -------------------------------------------------------------
@app.get("/api/head-to-head")
def get_head_to_head(team1: str = Query(...), team2: str = Query(...)):
    if team1 == team2:
        raise HTTPException(status_code=400, detail="Please choose two different teams.")

    with get_db() as conn:
        cur = conn.cursor()
        # Head-to-head matches
        cur.execute("""
            SELECT 
                id, season, city, date, team1, team2, toss_winner, toss_decision, winner,
                win_by_runs, win_by_wickets, player_of_match, venue
            FROM matches
            WHERE (team1 = ? AND team2 = ?) OR (team1 = ? AND team2 = ?)
            ORDER BY date DESC
        """, (team1, team2, team2, team1))
        matches = [dict(row) for row in cur.fetchall()]

        total_matches = len(matches)
        if total_matches == 0:
            return {
                "team1": team1,
                "team2": team2,
                "total_matches": 0,
                "team1_wins": 0,
                "team2_wins": 0,
                "no_result": 0,
                "team1_win_pct": 0,
                "team2_win_pct": 0,
                "matches": []
            }

        team1_wins = sum(1 for m in matches if m["winner"] == team1)
        team2_wins = sum(1 for m in matches if m["winner"] == team2)
        no_result = total_matches - (team1_wins + team2_wins)

        # Average innings score in their encounters
        cur.execute("""
            SELECT 
                d.batting_team,
                ROUND(AVG(inning_runs), 1) as avg_inning_score,
                MAX(inning_runs) as max_inning_score
            FROM (
                SELECT 
                    match_id, batting_team, inning, SUM(total_runs) as inning_runs
                FROM deliveries
                WHERE match_id IN (
                    SELECT id FROM matches 
                    WHERE (team1 = ? AND team2 = ?) OR (team1 = ? AND team2 = ?)
                )
                GROUP BY match_id, batting_team, inning
            ) d
            WHERE d.batting_team IN (?, ?)
            GROUP BY d.batting_team
        """, (team1, team2, team2, team1, team1, team2))
        avg_scores = {row["batting_team"]: dict(row) for row in cur.fetchall()}

        return {
            "team1": team1,
            "team2": team2,
            "total_matches": total_matches,
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "no_result": no_result,
            "team1_win_pct": round(100.0 * team1_wins / total_matches, 1),
            "team2_win_pct": round(100.0 * team2_wins / total_matches, 1),
            "team1_avg_score": avg_scores.get(team1, {}).get("avg_inning_score", 0),
            "team2_avg_score": avg_scores.get(team2, {}).get("avg_inning_score", 0),
            "team1_max_score": avg_scores.get(team1, {}).get("max_inning_score", 0),
            "team2_max_score": avg_scores.get(team2, {}).get("max_inning_score", 0),
            "recent_matches": matches[:10]
        }


# -------------------------------------------------------------
# 5. PLAYER DEEP DIVE & SEARCH
# -------------------------------------------------------------
@app.get("/api/players/search")
def search_players(q: str = Query("", min_length=1)):
    with get_db() as conn:
        cur = conn.cursor()
        search_term = f"%{q}%"
        cur.execute("""
            SELECT DISTINCT name FROM (
                SELECT batsman AS name FROM deliveries WHERE batsman LIKE ?
                UNION
                SELECT bowler AS name FROM deliveries WHERE bowler LIKE ?
            )
            ORDER BY name ASC
            LIMIT 15
        """, (search_term, search_term))
        return [row["name"] for row in cur.fetchall()]


@app.get("/api/players/{name}")
def get_player_profile(name: str):
    with get_db() as conn:
        cur = conn.cursor()

        # Batting overall stats
        cur.execute("""
            SELECT 
                COALESCE(SUM(batsman_runs), 0) AS total_runs,
                COUNT(DISTINCT match_id) AS innings,
                COUNT(CASE WHEN wide_runs = 0 THEN 1 END) AS balls_faced,
                ROUND(100.0 * COALESCE(SUM(batsman_runs), 0) / MAX(COUNT(CASE WHEN wide_runs = 0 THEN 1 END), 1), 2) AS strike_rate,
                SUM(CASE WHEN batsman_runs = 4 THEN 1 ELSE 0 END) AS fours,
                SUM(CASE WHEN batsman_runs = 6 THEN 1 ELSE 0 END) AS sixes
            FROM deliveries
            WHERE batsman = ?
        """, (name,))
        batting_overall = dict(cur.fetchone())

        # Innings breakdown for 50s, 100s, highest score
        cur.execute("""
            SELECT 
                MAX(match_runs) as highest_score,
                SUM(CASE WHEN match_runs >= 100 THEN 1 ELSE 0 END) as hundreds,
                SUM(CASE WHEN match_runs >= 50 AND match_runs < 100 THEN 1 ELSE 0 END) as fifties
            FROM (
                SELECT match_id, SUM(batsman_runs) as match_runs
                FROM deliveries
                WHERE batsman = ?
                GROUP BY match_id
            )
        """, (name,))
        milestones = dict(cur.fetchone())

        # Bowling overall stats
        cur.execute("""
            SELECT 
                COUNT(*) AS balls_bowled,
                ROUND(COUNT(*) / 6.0, 1) AS overs,
                COALESCE(SUM(total_runs), 0) AS runs_conceded,
                SUM(CASE WHEN dismissal_kind IS NOT NULL AND dismissal_kind NOT IN ('run out', 'retired hurt') THEN 1 ELSE 0 END) as wickets,
                ROUND(COALESCE(SUM(total_runs), 0) * 6.0 / MAX(COUNT(*), 1), 2) AS economy
            FROM deliveries
            WHERE bowler = ?
        """, (name,))
        bowling_overall = dict(cur.fetchone())

        # Player of the match awards
        cur.execute("""
            SELECT COUNT(*) FROM matches WHERE player_of_match = ?
        """, (name,))
        potm_count = cur.fetchone()[0]

        # Year-by-year batting progression
        cur.execute("""
            SELECT 
                m.season,
                SUM(d.batsman_runs) as runs,
                COUNT(DISTINCT d.match_id) as matches,
                ROUND(100.0 * SUM(d.batsman_runs) / MAX(COUNT(CASE WHEN d.wide_runs = 0 THEN 1 END), 1), 1) as strike_rate
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE d.batsman = ?
            GROUP BY m.season
            ORDER BY m.season ASC
        """, (name,))
        season_batting = [dict(row) for row in cur.fetchall()]

        # Year-by-year bowling progression
        cur.execute("""
            SELECT 
                m.season,
                SUM(CASE WHEN d.dismissal_kind IS NOT NULL AND d.dismissal_kind NOT IN ('run out', 'retired hurt') THEN 1 ELSE 0 END) as wickets,
                ROUND(SUM(d.total_runs) * 6.0 / MAX(COUNT(*), 1), 2) as economy
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE d.bowler = ?
            GROUP BY m.season
            ORDER BY m.season ASC
        """, (name,))
        season_bowling = [dict(row) for row in cur.fetchall()]

        if batting_overall["innings"] == 0 and bowling_overall["balls_bowled"] == 0:
            raise HTTPException(status_code=404, detail="Player not found")

        return {
            "name": name,
            "potm_awards": potm_count,
            "batting": {
                **batting_overall,
                "highest_score": milestones.get("highest_score") or 0,
                "hundreds": milestones.get("hundreds") or 0,
                "fifties": milestones.get("fifties") or 0,
                "season_history": season_batting
            },
            "bowling": {
                **bowling_overall,
                "season_history": season_bowling
            }
        }


# -------------------------------------------------------------
# 6. LIVE SQL RUNNER & PRESET QUERIES
# -------------------------------------------------------------
PRESET_QUERIES = [
    {
        "id": "q1",
        "title": "Toss Impact: Does winning toss predict match victory?",
        "description": "Quantifies whether winning the toss translates to a statistical winning advantage.",
        "sql": """SELECT
    CASE WHEN toss_winner = winner THEN 'Won Toss & Match'
         ELSE 'Won Toss, Lost Match' END AS outcome,
    COUNT(*) AS matches,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM matches WHERE result = 'normal'), 1) AS pct
FROM matches
WHERE result = 'normal'
GROUP BY outcome;""",
        "insight": "Winning the toss gives only a 51.4% win rate — virtually indistinguishable from a 50/50 coin flip."
    },
    {
        "id": "q2",
        "title": "Top 10 Run Scorers Overall (Career Totals)",
        "description": "Calculates career aggregate runs and average runs scored per match played.",
        "sql": """SELECT batsman, 
       SUM(batsman_runs) AS total_runs, 
       COUNT(DISTINCT match_id) AS innings_played,
       ROUND(SUM(batsman_runs) * 1.0 / COUNT(DISTINCT match_id), 1) AS avg_runs_per_innings
FROM deliveries
GROUP BY batsman
ORDER BY total_runs DESC
LIMIT 10;""",
        "insight": "Suresh Raina (4,548 runs) narrowly edged Virat Kohli (4,423) and Rohit Sharma (4,207) over 2008-2017."
    },
    {
        "id": "q3",
        "title": "Highest Batting Strike Rates (Min 200 balls)",
        "description": "Filters out wides as non-faced legal balls and enforces a sample size threshold.",
        "sql": """SELECT batsman,
       SUM(batsman_runs) AS runs,
       COUNT(*) AS balls_faced,
       ROUND(100.0 * SUM(batsman_runs) / COUNT(*), 1) AS strike_rate
FROM deliveries
WHERE wide_runs = 0
GROUP BY batsman
HAVING COUNT(*) >= 200
ORDER BY strike_rate DESC
LIMIT 10;""",
        "insight": "Enforcing HAVING COUNT(*) >= 200 avoids small-sample anomalies like tailenders with a 300 SR on 3 balls."
    },
    {
        "id": "q4",
        "title": "Best Bowling Economy Rates (Min 300 balls)",
        "description": "Computes runs conceded per 6 balls bowled for regular bowlers.",
        "sql": """SELECT bowler,
       COUNT(*) AS balls_bowled,
       SUM(total_runs) AS runs_conceded,
       ROUND(SUM(total_runs) * 6.0 / COUNT(*), 2) AS economy_rate
FROM deliveries
GROUP BY bowler
HAVING COUNT(*) >= 300
ORDER BY economy_rate ASC
LIMIT 10;""",
        "insight": "Spinners and disciplined pacers dominating the top 10 economy rates below 6.6 runs/over."
    },
    {
        "id": "q5",
        "title": "Chasing vs Defending Win % by Season",
        "description": "Uses a CTE to determine first-innings batting team, then computes chasing win rates.",
        "sql": """WITH batting_first AS (
    SELECT match_id, batting_team AS team1_bat
    FROM deliveries
    WHERE inning = 1
    GROUP BY match_id
)
SELECT m.season,
       COUNT(*) AS total_matches,
       SUM(CASE WHEN m.winner != bf.team1_bat AND m.winner != 'No Result' THEN 1 ELSE 0 END) AS chasing_team_wins,
       ROUND(100.0 * SUM(CASE WHEN m.winner != bf.team1_bat AND m.winner != 'No Result' THEN 1 ELSE 0 END)
             / COUNT(*), 1) AS chasing_win_pct
FROM matches m
JOIN batting_first bf ON m.id = bf.match_id
GROUP BY m.season
ORDER BY m.season;""",
        "insight": "Chasing success surged from ~42% in 2009 to a peak 68% in 2016 as T20 target tactics matured."
    },
    {
        "id": "q6",
        "title": "Orange Cap Winners (Window Function: DENSE_RANK)",
        "description": "Finds the #1 run scorer per season partitioned by year.",
        "sql": """WITH season_runs AS (
    SELECT m.season, d.batsman, SUM(d.batsman_runs) AS runs
    FROM deliveries d
    JOIN matches m ON d.match_id = m.id
    GROUP BY m.season, d.batsman
),
ranked AS (
    SELECT season, batsman, runs,
           DENSE_RANK() OVER (PARTITION BY season ORDER BY runs DESC) AS rnk
    FROM season_runs
)
SELECT season, batsman, runs
FROM ranked
WHERE rnk = 1
ORDER BY season;""",
        "insight": "Demonstrates DENSE_RANK() OVER (PARTITION BY ...), the classic Nth-highest interview query."
    },
    {
        "id": "q7",
        "title": "Highest Scoring Stadium Venues",
        "description": "Aggregates total match runs per venue for stadiums hosting at least 10 matches.",
        "sql": """SELECT venue,
       COUNT(DISTINCT match_id) AS matches_hosted,
       ROUND(AVG(total_runs), 1) AS avg_runs_per_match
FROM (
    SELECT match_id, venue, SUM(total_runs) AS total_runs
    FROM deliveries d
    JOIN matches m ON d.match_id = m.id
    GROUP BY match_id
)
GROUP BY venue
HAVING matches_hosted >= 10
ORDER BY avg_runs_per_match DESC
LIMIT 10;""",
        "insight": "Chinnaswamy Stadium (Bengaluru) leads in run production, making it a dream venue for batters."
    },
    {
        "id": "q8",
        "title": "Death Over Specialists (Overs 16-20, Min 100 balls)",
        "description": "Analyzes the high-pressure death overs where run rates typically explode.",
        "sql": """SELECT bowler,
       COUNT(*) AS balls_bowled,
       ROUND(SUM(total_runs) * 6.0 / COUNT(*), 2) AS death_over_economy
FROM deliveries
WHERE over BETWEEN 16 AND 20
GROUP BY bowler
HAVING COUNT(*) >= 100
ORDER BY death_over_economy ASC
LIMIT 10;""",
        "insight": "Bowlers like Lasith Malinga and Sunil Narine maintain sub-8.0 economy even in the death overs."
    }
]


@app.get("/api/sql-queries")
def get_preset_queries():
    return PRESET_QUERIES


class QueryRequest(BaseModel):
    query: str


@app.post("/api/sql-runner")
def run_custom_query(req: QueryRequest):
    sql = req.query.strip()
    if not sql:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Security check: Read-only queries only
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA", "VACUUM"]
    normalized = sql.upper()
    for word in forbidden:
        # Check as isolated keyword
        if f" {word} " in f" {normalized} " or normalized.startswith(f"{word} "):
            raise HTTPException(status_code=403, detail=f"Destructive or mutating command '{word}' is not permitted. Read-only queries only.")

    start_time = time.perf_counter()
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = [dict(zip(columns, row)) for row in cur.fetchmany(500)]
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return {
                "columns": columns,
                "rows": rows,
                "rowCount": len(rows),
                "executionTimeMs": execution_time_ms
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------
# 7. STATIC FRONTEND MOUNT
# -------------------------------------------------------------
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
