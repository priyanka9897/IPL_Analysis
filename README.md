# IPL Match & Player Performance Analysis

**A Python + SQL data analysis project on 10 seasons of IPL cricket (2008–2017).**
636 matches, 150,000+ ball-by-ball deliveries.

## Why this project

Sports data is messy, real, and has enough volume to require actual
query design (not just `df.describe()`) — every claim below is answered
with a SQL query first, then visualized in Python. That mirrors how a
data analyst role actually works: SQL to pull and shape the data,
Python to communicate it.

## Project structure

```
ipl_project/
├── data/
│   ├── matches.csv         # 636 matches: teams, toss, result, venue
│   └── deliveries.csv      # 150,460 ball-by-ball records
├── sql/
│   └── analysis_queries.sql  # 8 standalone SQL queries (joins, CTEs, window functions)
├── 01_build_database.py    # Loads CSVs into an indexed SQLite database
├── 02_analysis_and_charts.py  # Runs the SQL queries, generates 5 charts
├── charts/                 # Output visualizations
└── ipl.db                  # Generated SQLite database
```

## How to run it

```bash
pip install pandas matplotlib seaborn
python 01_build_database.py       # builds ipl.db from the CSVs
python 02_analysis_and_charts.py  # runs queries, saves charts/
```

## Key findings

1. **The toss barely matters.** Toss winners went on to win only
   51.4% of matches (322 of 626) — statistically close to a coin
   flip. This contradicts the common cricket-commentary narrative
   that winning the toss is a major advantage.

2. **Chasing (batting second) is a real edge, and it's grown over
   time.** Win rate for the chasing team ranged from 42% to 68%
   across seasons, with a general upward trend — consistent with
   T20 strategy evolving toward chasing being favored due to
   knowing the target.

3. **Top run-scorer across the full dataset: SK Raina (4,548 runs)**,
   narrowly ahead of V Kohli (4,423) and RG Sharma (4,207) —
   interesting because Raina isn't the player most casual fans would
   guess first, which is exactly the kind of "data corrects intuition"
   insight worth highlighting in an interview.

4. **Venue matters more than people assume for total runs scored** —
   the highest-scoring venues average meaningfully more runs per
   match than the lowest, useful context for e.g. broadcast planning
   or fantasy-sports pricing models in a real commercial setting.

## SQL techniques demonstrated

- Multi-table joins (`matches` ↔ `deliveries`)
- CTEs (`WITH` clauses) for multi-step logic
- Window functions (`DENSE_RANK() OVER (PARTITION BY ...)`) to find
  each season's top scorer — the same pattern as the classic
  "Nth highest salary" interview question
- Conditional aggregation (`CASE WHEN` inside `SUM`)
- `HAVING` clauses to filter on aggregated minimums (avoiding
  small-sample noise, e.g. excluding bowlers with under 300 balls
  bowled from an economy-rate ranking)

## How to talk about this in an interview

- **"Walk me through a project you've worked on"**: lead with the
  toss finding — it's counterintuitive, which makes for a better
  story than a predictable result.
- **If asked about data quality**: mention that `winner` had nulls for
  no-result matches (handled via `fillna`), and that wides were
  excluded from strike-rate balls-faced calculations since they
  aren't legal deliveries faced by the batsman.
- **If asked "what would you do with more time"**: extend to
  post-2017 seasons, add player-vs-player matchup analysis, or build
  a simple win-probability model using match-state features (a
  natural next step that shows you think beyond the current scope).

## Data source

Cricsheet ball-by-ball data via a public IPL dataset (Kaggle:
manasgarg/ipl), 2008–2017 seasons.
