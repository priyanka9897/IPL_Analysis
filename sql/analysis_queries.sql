-- ============================================================
-- IPL Data Analysis: Core SQL Queries
-- Run against ipl.db (SQLite). Each query answers one business
-- question, the kind of framing a data analyst interview expects
-- ("don't just show me a query, tell me what question it answers").
-- ============================================================

-- Q1: Toss impact -- does winning the toss actually help you win the match?
SELECT
    CASE WHEN toss_winner = winner THEN 'Won Toss & Match'
         ELSE 'Won Toss, Lost Match' END AS outcome,
    COUNT(*) AS matches,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM matches WHERE result = 'normal'), 1) AS pct
FROM matches
WHERE result = 'normal'
GROUP BY outcome;


-- Q2: Top 10 run scorers overall (career totals across all seasons)
SELECT batsman, SUM(batsman_runs) AS total_runs, COUNT(DISTINCT match_id) AS innings_played,
       ROUND(SUM(batsman_runs) * 1.0 / COUNT(DISTINCT match_id), 1) AS avg_runs_per_innings
FROM deliveries
GROUP BY batsman
ORDER BY total_runs DESC
LIMIT 10;


-- Q3: Best strike rate among batsmen with a meaningful sample size (200+ balls faced)
SELECT batsman,
       SUM(batsman_runs) AS runs,
       COUNT(*) AS balls_faced,
       ROUND(100.0 * SUM(batsman_runs) / COUNT(*), 1) AS strike_rate
FROM deliveries
WHERE wide_runs = 0  -- wides don't count as a legal ball faced
GROUP BY batsman
HAVING COUNT(*) >= 200
ORDER BY strike_rate DESC
LIMIT 10;


-- Q4: Best bowling economy (runs conceded per over) among bowlers with 300+ balls bowled
SELECT bowler,
       COUNT(*) AS balls_bowled,
       SUM(total_runs) AS runs_conceded,
       ROUND(SUM(total_runs) * 6.0 / COUNT(*), 2) AS economy_rate
FROM deliveries
GROUP BY bowler
HAVING COUNT(*) >= 300
ORDER BY economy_rate ASC
LIMIT 10;


-- Q5: Chasing vs defending -- win rate when batting 2nd (chasing), by season
-- This uses a self-referencing pattern: figure out which team batted 2nd via deliveries,
-- then join back to match result.
WITH batting_first AS (
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
ORDER BY m.season;


-- Q6: Rank each season's top run-scorer (window function -- the "Orange Cap" question)
-- This mirrors the DENSE_RANK / Nth-highest pattern practiced for the SQL interview round.
WITH season_runs AS (
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
ORDER BY season;


-- Q7: Which venues produce the highest-scoring matches on average?
SELECT venue,
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
LIMIT 10;


-- Q8: "Death over" specialists -- bowlers with the best economy in overs 16-20
SELECT bowler,
       COUNT(*) AS balls_bowled,
       ROUND(SUM(total_runs) * 6.0 / COUNT(*), 2) AS death_over_economy
FROM deliveries
WHERE over BETWEEN 16 AND 20
GROUP BY bowler
HAVING COUNT(*) >= 100
ORDER BY death_over_economy ASC
LIMIT 10;
