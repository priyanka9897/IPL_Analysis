/**
 * IPL Analytics Lab — Interactive Frontend Controller
 * Connects to FastAPI Backend, handles Chart.js visualizations,
 * filtering, rivalry simulations, player deep dive, and Live SQL runner.
 */

// Global API Base (relative when hosted on same port)
const API_BASE = window.location.origin;

// State tracking
const state = {
  activeTab: 'overview',
  globalSeason: 'all',
  leaderboardSeason: 'all',
  minBallsBowled: 200,
  teams: [],
  seasons: [],
  lastSqlResult: null,
};

// Chart instances
const charts = {
  toss: null,
  chase: null,
  venues: null,
  batsmen: null,
  bowlers: null,
  playerYearly: null,
};

// ========================================================
// INITIALIZATION
// ========================================================
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initGlobalSeasonFilter();
  loadOverviewMetrics();
  loadOverviewCharts();
  loadSeasonsAndChampions();
  initLeaderboards();
  initRivalrySimulator();
  initPlayerDeepDive();
  initSqlLab();
});

// ========================================================
// TAB NAVIGATION
// ========================================================
function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const targetId = tab.dataset.tab;
      document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
      });
      const activePanel = document.getElementById(`panel-${targetId}`);
      if (activePanel) {
        activePanel.classList.add('active');
      }

      state.activeTab = targetId;

      // Force charts to resize properly when panel opens
      setTimeout(() => {
        Object.values(charts).forEach(c => {
          if (c) c.resize();
        });
      }, 50);

      // Lazy load tab data on first view
      if (targetId === 'leaderboards' && !charts.batsmen) {
        loadLeaderboardData();
      } else if (targetId === 'rivalry' && state.teams.length === 0) {
        loadTeamsForRivalry();
      } else if (targetId === 'player' && !charts.playerYearly) {
        loadPlayerProfile('V Kohli');
      }
    });
  });
}

// ========================================================
// TAB 1: OVERVIEW & MACRO TRENDS
// ========================================================
async function initGlobalSeasonFilter() {
  const select = document.getElementById('global-season-select');
  select.addEventListener('change', (e) => {
    state.globalSeason = e.target.value;
    loadOverviewCharts();
  });
}

async function loadOverviewMetrics() {
  try {
    const res = await fetch(`${API_BASE}/api/overview`);
    const data = await res.json();

    document.getElementById('val-matches').textContent = Number(data.total_matches).toLocaleString();
    document.getElementById('val-deliveries').textContent = Number(data.total_balls).toLocaleString();
    document.getElementById('val-runs').textContent = Number(data.total_runs).toLocaleString();
    document.getElementById('val-boundaries').textContent = `${Number(data.total_fours).toLocaleString()} 4s / ${Number(data.total_sixes).toLocaleString()} 6s`;
    document.getElementById('val-toss').textContent = `${data.toss_win_pct}%`;
    document.getElementById('val-chasing').textContent = `${data.chasing_win_pct}%`;
    document.getElementById('val-topteam').textContent = data.top_team;
    document.getElementById('val-topteam-wins').textContent = `${data.top_team_wins} Wins`;
  } catch (err) {
    console.error('Error loading overview metrics:', err);
  }
}

async function loadSeasonsAndChampions() {
  try {
    const res = await fetch(`${API_BASE}/api/seasons`);
    const seasons = await res.json();
    state.seasons = seasons;

    // Populate global & leaderboard season selects
    const globalSelect = document.getElementById('global-season-select');
    const lbSelect = document.getElementById('leaderboard-season-select');

    seasons.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.season;
      opt.textContent = `Season ${s.season} (${s.match_count} matches)`;
      globalSelect.appendChild(opt);

      const optLb = opt.cloneNode(true);
      lbSelect.appendChild(optLb);
    });

    // Populate Champions Timeline
    const timeline = document.getElementById('champions-timeline');
    timeline.innerHTML = '';
    seasons.forEach(s => {
      const badge = document.createElement('div');
      badge.className = 'champ-badge';
      badge.innerHTML = `
        <span class="champ-year">${s.season}</span>
        <div class="champ-name">${s.champion || 'IPL Winner'}</div>
      `;
      timeline.appendChild(badge);
    });
  } catch (err) {
    console.error('Error loading seasons:', err);
  }
}

async function loadOverviewCharts() {
  loadTossChart();
  loadChaseTrendChart();
  loadVenuesChart();
}

async function loadTossChart() {
  try {
    const res = await fetch(`${API_BASE}/api/charts/toss-impact?season=${state.globalSeason}`);
    const data = await res.json();

    const labels = data.outcomes.map(o => o.outcome);
    const counts = data.outcomes.map(o => o.matches);

    const ctx = document.getElementById('chart-toss').getContext('2d');
    if (charts.toss) charts.toss.destroy();

    charts.toss = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: counts,
          backgroundColor: ['#3b82f6', '#f59e0b'],
          borderColor: '#0a0e17',
          borderWidth: 3,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#e5e7eb', font: { family: 'Inter', size: 12 }, padding: 16 }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const total = counts.reduce((a, b) => a + b, 0);
                const val = ctx.raw;
                const pct = ((val / total) * 100).toFixed(1);
                return ` ${ctx.label}: ${val} matches (${pct}%)`;
              }
            }
          }
        },
        cutout: '68%'
      }
    });
  } catch (err) {
    console.error('Error loading toss chart:', err);
  }
}

async function loadChaseTrendChart() {
  try {
    const res = await fetch(`${API_BASE}/api/charts/chase-trend`);
    const data = await res.json();

    const labels = data.map(d => d.season);
    const chasePcts = data.map(d => d.chasing_win_pct);

    const ctx = document.getElementById('chart-chase').getContext('2d');
    if (charts.chase) charts.chase.destroy();

    charts.chase = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Chasing Team Win %',
            data: chasePcts,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.35,
            borderWidth: 3,
            pointBackgroundColor: '#10b981',
            pointRadius: 5,
            pointHoverRadius: 7,
          },
          {
            label: '50% Baseline (Coin Flip)',
            data: labels.map(() => 50),
            borderColor: '#6b7280',
            borderDash: [6, 6],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            min: 35,
            max: 75,
            grid: { color: 'rgba(255, 255, 255, 0.06)' },
            ticks: { color: '#9ca3af', callback: v => `${v}%` }
          },
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: { color: '#9ca3af' }
          }
        },
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#e5e7eb', font: { family: 'Inter', size: 11 } }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${ctx.raw}%`
            }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error loading chase trend chart:', err);
  }
}

async function loadVenuesChart() {
  try {
    const res = await fetch(`${API_BASE}/api/charts/venues?min_matches=8&limit=10`);
    const data = await res.json();

    const labels = data.map(v => v.venue.length > 28 ? v.venue.substring(0, 26) + '...' : v.venue);
    const avgRuns = data.map(v => v.avg_runs_per_match);

    const ctx = document.getElementById('chart-venues').getContext('2d');
    if (charts.venues) charts.venues.destroy();

    charts.venues = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Avg Total Runs per Match',
          data: avgRuns,
          backgroundColor: 'rgba(139, 92, 246, 0.8)',
          hoverBackgroundColor: 'rgba(167, 139, 250, 0.95)',
          borderRadius: 6,
          borderWidth: 0,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            min: 240,
            grid: { color: 'rgba(255, 255, 255, 0.06)' },
            ticks: { color: '#9ca3af' }
          },
          y: {
            grid: { display: false },
            ticks: { color: '#e5e7eb', font: { size: 11 } }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => ` Avg Match Runs: ${ctx.raw} runs`
            }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error loading venues chart:', err);
  }
}

// ========================================================
// TAB 2: BATTING & BOWLING LEADERBOARDS
// ========================================================
function initLeaderboards() {
  const seasonSelect = document.getElementById('leaderboard-season-select');
  const slider = document.getElementById('bowler-balls-slider');
  const sliderVal = document.getElementById('bowler-balls-val');

  seasonSelect.addEventListener('change', (e) => {
    state.leaderboardSeason = e.target.value;
    loadLeaderboardData();
  });

  slider.addEventListener('input', (e) => {
    sliderVal.textContent = e.target.value;
  });

  slider.addEventListener('change', (e) => {
    state.minBallsBowled = parseInt(e.target.value);
    loadBowlerLeaderboard();
  });
}

async function loadLeaderboardData() {
  await Promise.all([loadBatsmanLeaderboard(), loadBowlerLeaderboard()]);
}

async function loadBatsmanLeaderboard() {
  try {
    const res = await fetch(`${API_BASE}/api/charts/top-batsmen?season=${state.leaderboardSeason}&limit=10`);
    const data = await res.json();

    const labels = data.map(b => b.batsman);
    const runs = data.map(b => b.total_runs);

    const ctx = document.getElementById('chart-batsmen').getContext('2d');
    if (charts.batsmen) charts.batsmen.destroy();

    charts.batsmen = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Total Runs',
          data: runs,
          backgroundColor: 'rgba(245, 158, 11, 0.85)',
          hoverBackgroundColor: '#fbbf24',
          borderRadius: 6,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: 'rgba(255, 255, 255, 0.06)' }, ticks: { color: '#9ca3af' } },
          y: { grid: { display: false }, ticks: { color: '#f3f4f6' } }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel: (ctx) => {
                const item = data[ctx.dataIndex];
                return `Strike Rate: ${item.strike_rate} | 4s: ${item.fours} | 6s: ${item.sixes}`;
              }
            }
          }
        }
      }
    });

    // Populate Table
    const tbody = document.querySelector('#table-batsmen tbody');
    tbody.innerHTML = '';
    data.forEach((b, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>#${idx + 1}</strong></td>
        <td><strong>${b.batsman}</strong></td>
        <td style="color:#fbbf24; font-weight:700;">${b.total_runs.toLocaleString()}</td>
        <td>${b.innings_played}</td>
        <td>${b.strike_rate}</td>
        <td>${b.fours} / ${b.sixes}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading batsman leaderboard:', err);
  }
}

async function loadBowlerLeaderboard() {
  try {
    const res = await fetch(`${API_BASE}/api/charts/bowling-economy?season=${state.leaderboardSeason}&min_balls=${state.minBallsBowled}&limit=10`);
    const data = await res.json();

    const labels = data.map(b => b.bowler);
    const economies = data.map(b => b.economy_rate);

    const ctx = document.getElementById('chart-bowlers').getContext('2d');
    if (charts.bowlers) charts.bowlers.destroy();

    charts.bowlers = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Economy Rate (runs/over)',
          data: economies,
          backgroundColor: 'rgba(6, 182, 212, 0.85)',
          hoverBackgroundColor: '#22d3ee',
          borderRadius: 6,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            min: 5,
            grid: { color: 'rgba(255, 255, 255, 0.06)' },
            ticks: { color: '#9ca3af' }
          },
          y: { grid: { display: false }, ticks: { color: '#f3f4f6' } }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel: (ctx) => {
                const item = data[ctx.dataIndex];
                return `Overs: ${item.overs_bowled} | Wickets: ${item.wickets} | Runs: ${item.runs_conceded}`;
              }
            }
          }
        }
      }
    });

    // Populate Table
    const tbody = document.querySelector('#table-bowlers tbody');
    tbody.innerHTML = '';
    data.forEach((b, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>#${idx + 1}</strong></td>
        <td><strong>${b.bowler}</strong></td>
        <td style="color:#22d3ee; font-weight:700;">${b.economy_rate}</td>
        <td>${b.overs_bowled}</td>
        <td>${b.wickets}</td>
        <td>${b.runs_conceded}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading bowler leaderboard:', err);
  }
}

// ========================================================
// TAB 3: HEAD-TO-HEAD RIVALRY SIMULATOR
// ========================================================
async function initRivalrySimulator() {
  document.getElementById('btn-compare-rivals').addEventListener('click', runRivalryComparison);
}

async function loadTeamsForRivalry() {
  try {
    const res = await fetch(`${API_BASE}/api/teams`);
    const teams = await res.json();
    state.teams = teams;

    const select1 = document.getElementById('rival-team-1');
    const select2 = document.getElementById('rival-team-2');

    select1.innerHTML = '';
    select2.innerHTML = '';

    teams.forEach(t => {
      const opt1 = new Option(`${t.team} (${t.matches_won} wins)`, t.team);
      const opt2 = new Option(`${t.team} (${t.matches_won} wins)`, t.team);
      select1.appendChild(opt1);
      select2.appendChild(opt2);
    });

    // Default select classic rivalry: Mumbai Indians vs Chennai Super Kings
    select1.value = 'Mumbai Indians';
    select2.value = 'Chennai Super Kings';

    runRivalryComparison();
  } catch (err) {
    console.error('Error loading teams for rivalry:', err);
  }
}

async function runRivalryComparison() {
  const team1 = document.getElementById('rival-team-1').value;
  const team2 = document.getElementById('rival-team-2').value;

  if (team1 === team2) {
    alert('Please select two distinct teams to compare their rivalry.');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/head-to-head?team1=${encodeURIComponent(team1)}&team2=${encodeURIComponent(team2)}`);
    const data = await res.json();

    document.getElementById('r-team1-name').textContent = data.team1;
    document.getElementById('r-team2-name').textContent = data.team2;
    document.getElementById('r-team1-wins').textContent = `${data.team1_wins} Wins`;
    document.getElementById('r-team2-wins').textContent = `${data.team2_wins} Wins`;
    document.getElementById('r-team1-pct').textContent = `${data.team1_win_pct}%`;
    document.getElementById('r-team2-pct').textContent = `${data.team2_win_pct}%`;

    document.getElementById('r-total-clashes').textContent = `${data.total_matches} Total Encounters`;
    document.getElementById('r-no-result').textContent = `${data.no_result} Ties or No Results`;

    // Dynamic bar percentage
    const t1Width = data.total_matches > 0 ? (data.team1_wins / data.total_matches) * 100 : 50;
    const t2Width = data.total_matches > 0 ? (data.team2_wins / data.total_matches) * 100 : 50;
    document.getElementById('r-bar-team1').style.width = `${t1Width}%`;
    document.getElementById('r-bar-team2').style.width = `${t2Width}%`;

    document.getElementById('r-team1-avg').textContent = data.team1_avg_score || '--';
    document.getElementById('r-team2-avg').textContent = data.team2_avg_score || '--';
    document.getElementById('r-team1-max').textContent = data.team1_max_score || '--';
    document.getElementById('r-team2-max').textContent = data.team2_max_score || '--';

    // Populate matches table
    const tbody = document.querySelector('#table-rivalry-matches tbody');
    tbody.innerHTML = '';

    if (data.recent_matches.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No matches found between these teams.</td></tr>';
      return;
    }

    data.recent_matches.forEach(m => {
      const margin = m.win_by_runs > 0 ? `${m.win_by_runs} runs` : (m.win_by_wickets > 0 ? `${m.win_by_wickets} wkts` : 'Tie');
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${m.date}</td>
        <td><strong>${m.season}</strong></td>
        <td>${m.venue}</td>
        <td>${m.toss_winner} (${m.toss_decision})</td>
        <td style="color:${m.winner === data.team1 ? '#60a5fa' : '#fbbf24'}; font-weight:700;">${m.winner}</td>
        <td>${margin}</td>
        <td>${m.player_of_match || '--'}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error running rivalry comparison:', err);
  }
}

// ========================================================
// TAB 4: PLAYER DEEP DIVE
// ========================================================
function initPlayerDeepDive() {
  const searchInput = document.getElementById('player-search-input');
  const suggestions = document.getElementById('player-suggestions');
  const searchBtn = document.getElementById('btn-search-player');

  let debounceTimer;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    const query = e.target.value.trim();
    if (query.length < 2) {
      suggestions.classList.add('hidden');
      return;
    }

    debounceTimer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/players/search?q=${encodeURIComponent(query)}`);
        const names = await res.json();

        suggestions.innerHTML = '';
        if (names.length === 0) {
          suggestions.classList.add('hidden');
          return;
        }

        names.forEach(name => {
          const item = document.createElement('div');
          item.className = 'suggestion-item';
          item.textContent = name;
          item.addEventListener('click', () => {
            searchInput.value = name;
            suggestions.classList.add('hidden');
            loadPlayerProfile(name);
          });
          suggestions.appendChild(item);
        });
        suggestions.classList.remove('hidden');
      } catch (err) {
        console.error('Search error:', err);
      }
    }, 200);
  });

  // Search button
  searchBtn.addEventListener('click', () => {
    const name = searchInput.value.trim();
    if (name) loadPlayerProfile(name);
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const name = searchInput.value.trim();
      if (name) loadPlayerProfile(name);
      suggestions.classList.add('hidden');
    }
  });

  // Quick picks chips
  document.querySelectorAll('.quick-picks .chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const player = chip.dataset.player;
      searchInput.value = player;
      loadPlayerProfile(player);
    });
  });

  // Close suggestions if clicked outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-input-wrap')) {
      suggestions.classList.add('hidden');
    }
  });
}

async function loadPlayerProfile(playerName) {
  try {
    const res = await fetch(`${API_BASE}/api/players/${encodeURIComponent(playerName)}`);
    if (!res.ok) {
      alert(`Player "${playerName}" not found.`);
      return;
    }
    const data = await res.json();

    // Identity badge
    document.getElementById('p-name').textContent = data.name;
    const initials = data.name.split(' ').map(n => n[0]).join('').substring(0, 2);
    document.getElementById('p-avatar').textContent = initials;
    document.getElementById('p-potm').textContent = `${data.potm_awards} POTM Awards`;

    const isBatter = data.batting.total_runs > 200;
    const isBowler = data.bowling.balls_bowled > 200;
    const role = (isBatter && isBowler) ? 'All-Rounder' : (isBatter ? 'Top Order / Batsman' : 'Bowler');
    document.getElementById('p-type').textContent = role;

    // Metrics grid
    document.getElementById('p-runs').textContent = data.batting.total_runs.toLocaleString();
    document.getElementById('p-sr').textContent = data.batting.strike_rate || '--';
    document.getElementById('p-hs').textContent = data.batting.highest_score || '0';
    document.getElementById('p-inns').textContent = data.batting.innings || '0';
    document.getElementById('p-fifties').textContent = `${data.batting.fifties} / ${data.batting.hundreds}`;
    document.getElementById('p-boundaries').textContent = `${data.batting.fours} / ${data.batting.sixes}`;
    document.getElementById('p-wickets').textContent = data.bowling.wickets || '0';
    document.getElementById('p-economy').textContent = data.bowling.economy || '--';

    // Trajectory Chart
    const battingHist = data.batting.season_history || [];
    const seasons = battingHist.map(h => h.season);
    const yearlyRuns = battingHist.map(h => h.runs);
    const yearlySR = battingHist.map(h => h.strike_rate);

    const ctx = document.getElementById('chart-player-yearly').getContext('2d');
    if (charts.playerYearly) charts.playerYearly.destroy();

    charts.playerYearly = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: seasons,
        datasets: [
          {
            type: 'bar',
            label: 'Runs Scored',
            data: yearlyRuns,
            backgroundColor: 'rgba(245, 158, 11, 0.8)',
            borderRadius: 6,
            yAxisID: 'y'
          },
          {
            type: 'line',
            label: 'Strike Rate',
            data: yearlySR,
            borderColor: '#3b82f6',
            backgroundColor: '#3b82f6',
            tension: 0.3,
            borderWidth: 2.5,
            pointRadius: 4,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: 'rgba(255, 255, 255, 0.04)' }, ticks: { color: '#9ca3af' } },
          y: {
            type: 'linear',
            position: 'left',
            grid: { color: 'rgba(255, 255, 255, 0.06)' },
            ticks: { color: '#fbbf24' },
            title: { display: true, text: 'Runs Scored', color: '#fbbf24' }
          },
          y1: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#93c5fd' },
            title: { display: true, text: 'Strike Rate', color: '#93c5fd' }
          }
        },
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#e5e7eb', font: { family: 'Inter', size: 12 } }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error loading player profile:', err);
  }
}

// ========================================================
// TAB 5: LIVE SQL LAB
// ========================================================
let presetQueriesList = [];

async function initSqlLab() {
  const select = document.getElementById('sql-preset-select');
  const textarea = document.getElementById('sql-query-input');
  const insightBox = document.getElementById('sql-insight-box');
  const insightText = document.getElementById('sql-insight-text');
  const btnRun = document.getElementById('btn-run-sql');
  const btnReset = document.getElementById('btn-reset-sql');
  const btnExport = document.getElementById('btn-export-csv');

  try {
    const res = await fetch(`${API_BASE}/api/sql-queries`);
    presetQueriesList = await res.json();

    presetQueriesList.forEach(q => {
      const opt = document.createElement('option');
      opt.value = q.id;
      opt.textContent = `${q.id.toUpperCase()}: ${q.title}`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error('Error loading preset queries:', err);
  }

  // Handle Preset Selection
  select.addEventListener('change', (e) => {
    const selected = presetQueriesList.find(q => q.id === e.target.value);
    if (selected) {
      textarea.value = selected.sql;
      insightText.innerHTML = `<strong>${selected.title}</strong><br>${selected.insight}`;
      insightBox.classList.remove('hidden');
    } else {
      insightBox.classList.add('hidden');
    }
  });

  // Run Query
  btnRun.addEventListener('click', runSqlQuery);

  // Reset
  btnReset.addEventListener('click', () => {
    textarea.value = 'SELECT * FROM matches LIMIT 10;';
    select.value = '';
    insightBox.classList.add('hidden');
  });

  // Export CSV
  btnExport.addEventListener('click', exportResultsToCsv);

  // Default query on first load
  textarea.value = `SELECT 
    CASE WHEN toss_winner = winner THEN 'Won Toss & Match'
         ELSE 'Won Toss, Lost Match' END AS outcome,
    COUNT(*) AS matches,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM matches WHERE result = 'normal'), 1) AS pct
FROM matches
WHERE result = 'normal'
GROUP BY outcome;`;
}

async function runSqlQuery() {
  const query = document.getElementById('sql-query-input').value.trim();
  const errorBox = document.getElementById('sql-error-box');
  const thead = document.getElementById('thead-sql-results');
  const tbody = document.getElementById('tbody-sql-results');
  const countTag = document.getElementById('results-count-tag');
  const statRuntime = document.getElementById('stat-runtime');
  const statRows = document.getElementById('stat-rows');
  const btnExport = document.getElementById('btn-export-csv');

  if (!query) {
    alert('Please enter a SQL query.');
    return;
  }

  errorBox.classList.add('hidden');
  statRuntime.textContent = 'Executing...';
  statRows.textContent = '';

  try {
    const res = await fetch(`${API_BASE}/api/sql-runner`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });

    const data = await res.json();

    if (!res.ok) {
      errorBox.textContent = `⚠️ Error: ${data.detail || 'Execution failed'}`;
      errorBox.classList.remove('hidden');
      statRuntime.textContent = 'Failed';
      btnExport.disabled = true;
      return;
    }

    state.lastSqlResult = data;
    btnExport.disabled = data.rowCount === 0;

    statRuntime.textContent = `⏱️ ${data.executionTimeMs} ms`;
    statRows.textContent = `📊 ${data.rowCount} rows returned`;
    countTag.textContent = `${data.rowCount} Rows`;

    // Render Table Header
    thead.innerHTML = '';
    const headerTr = document.createElement('tr');
    data.columns.forEach(col => {
      const th = document.createElement('th');
      th.textContent = col;
      headerTr.appendChild(th);
    });
    thead.appendChild(headerTr);

    // Render Table Rows
    tbody.innerHTML = '';
    if (data.rowCount === 0) {
      tbody.innerHTML = '<tr><td colspan="100%" class="empty-state">Query returned 0 rows.</td></tr>';
      return;
    }

    data.rows.forEach(row => {
      const tr = document.createElement('tr');
      data.columns.forEach(col => {
        const td = document.createElement('td');
        const val = row[col];
        td.textContent = (val !== null && val !== undefined) ? val : 'NULL';
        if (typeof val === 'number') {
          td.style.fontFamily = 'var(--font-mono)';
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

  } catch (err) {
    errorBox.textContent = `Network / Execution Error: ${err.message}`;
    errorBox.classList.remove('hidden');
    statRuntime.textContent = 'Failed';
    btnExport.disabled = true;
  }
}

function exportResultsToCsv() {
  if (!state.lastSqlResult || !state.lastSqlResult.rows.length) return;

  const { columns, rows } = state.lastSqlResult;
  const csvRows = [];

  // Header row
  csvRows.push(columns.join(','));

  // Data rows
  rows.forEach(row => {
    const values = columns.map(col => {
      const val = row[col] === null || row[col] === undefined ? '' : String(row[col]);
      return `"${val.replace(/"/g, '""')}"`;
    });
    csvRows.push(values.join(','));
  });

  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.setAttribute('hidden', '');
  a.setAttribute('href', url);
  a.setAttribute('download', `ipl_query_export_${Date.now()}.csv`);
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
