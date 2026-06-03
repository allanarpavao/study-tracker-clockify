from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import csv
import io
from datetime import datetime, date, timedelta
import calendar
import os

app = Flask(__name__, static_folder='static')
DB_PATH = os.path.join(os.path.dirname(__file__), 'study_tracker.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        project TEXT,
        task TEXT,
        description TEXT,
        duration_hours REAL NOT NULL,
        start_time TEXT,
        end_time TEXT
    )''')
    # Legacy global goals (used as default fallback)
    conn.execute('''CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY,
        daily_hours REAL DEFAULT 3.0,
        weekly_hours REAL DEFAULT 20.0,
        monthly_hours REAL DEFAULT 80.0
    )''')
    conn.execute('INSERT OR IGNORE INTO goals (id, daily_hours, weekly_hours, monthly_hours) VALUES (1, 3.0, 20.0, 80.0)')
    # Per-month goals
    conn.execute('''CREATE TABLE IF NOT EXISTS monthly_goals (
        year_month TEXT PRIMARY KEY,
        daily_hours REAL NOT NULL,
        weekly_hours REAL NOT NULL,
        monthly_hours REAL NOT NULL
    )''')
    # Project filter
    conn.execute('''CREATE TABLE IF NOT EXISTS project_filters (
        project TEXT PRIMARY KEY,
        included INTEGER DEFAULT 1
    )''')
    conn.commit()
    conn.close()


def get_goals_for_month(conn, year_month):
    row = conn.execute('SELECT * FROM monthly_goals WHERE year_month=?', (year_month,)).fetchone()
    if row:
        return dict(row)
    default = conn.execute('SELECT * FROM goals WHERE id=1').fetchone()
    return {'year_month': year_month, 'daily_hours': default['daily_hours'],
            'weekly_hours': default['weekly_hours'], 'monthly_hours': default['monthly_hours']}


def get_project_filter(conn):
    """Returns (filter_sql_fragment, params) to append to WHERE clauses."""
    rows = conn.execute('SELECT project FROM project_filters WHERE included=1').fetchall()
    selected = [r['project'] for r in rows]
    total = conn.execute('SELECT COUNT(*) as c FROM project_filters').fetchone()['c']
    # If no filter configured at all → no restriction
    if total == 0 or not selected:
        return '', []
    placeholders = ','.join('?' * len(selected))
    return f' AND project IN ({placeholders})', selected


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


# ── IMPORT ──
@app.route('/api/import', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    file = request.files['file']
    try:
        content = file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        content = file.read().decode('latin-1')

    reader = csv.DictReader(io.StringIO(content))
    conn = get_db()
    inserted = 0
    skipped = 0
    new_projects = set()

    for row in reader:
        try:
            date_str = row.get('Start Date', '').strip()
            if not date_str:
                continue
            date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
            date_iso = date_obj.isoformat()
            duration = float(row.get('Duration (decimal)', 0) or 0)
            project = row.get('Project', '').strip()
            task = row.get('Task', '').strip()
            description = row.get('Description', '').strip()
            start_time = row.get('Start Time', '').strip()
            end_time = row.get('End Time', '').strip()

            existing = conn.execute(
                'SELECT id FROM sessions WHERE date=? AND start_time=? AND end_time=? AND project=?',
                (date_iso, start_time, end_time, project)
            ).fetchone()
            if existing:
                skipped += 1
                continue

            conn.execute(
                'INSERT INTO sessions (date, project, task, description, duration_hours, start_time, end_time) VALUES (?,?,?,?,?,?,?)',
                (date_iso, project, task, description, duration, start_time, end_time)
            )
            if project:
                new_projects.add(project)
            inserted += 1
        except Exception:
            continue

    # Register new projects in filter table (default: not included until user picks)
    for p in new_projects:
        existing_filter = conn.execute('SELECT project FROM project_filters WHERE project=?', (p,)).fetchone()
        if not existing_filter:
            # First import: include all by default
            conn.execute('INSERT OR IGNORE INTO project_filters (project, included) VALUES (?, 1)', (p,))

    conn.commit()
    conn.close()
    return jsonify({'inserted': inserted, 'skipped': skipped})


# ── MONTHS ──
@app.route('/api/months', methods=['GET'])
def get_months():
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT substr(date,1,7) as ym FROM sessions ORDER BY ym DESC"
    ).fetchall()
    conn.close()
    months = [r['ym'] for r in rows]
    return jsonify({'months': months})


# ── PROJECTS ──
@app.route('/api/projects', methods=['GET'])
def get_projects():
    conn = get_db()
    # All projects seen in sessions
    all_proj = conn.execute(
        "SELECT DISTINCT project FROM sessions WHERE project != '' ORDER BY project"
    ).fetchall()
    # Their filter status
    filter_rows = conn.execute('SELECT project, included FROM project_filters').fetchall()
    filter_map = {r['project']: r['included'] for r in filter_rows}
    conn.close()

    result = []
    for r in all_proj:
        p = r['project']
        result.append({'name': p, 'included': filter_map.get(p, 1)})
    return jsonify({'projects': result})


@app.route('/api/filters', methods=['PUT'])
def update_filters():
    data = request.json
    included = data.get('included', [])
    all_projects = data.get('all_projects', [])
    conn = get_db()
    for p in all_projects:
        inc = 1 if p in included else 0
        conn.execute(
            'INSERT INTO project_filters (project, included) VALUES (?,?) ON CONFLICT(project) DO UPDATE SET included=?',
            (p, inc, inc)
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ── GOALS ──
@app.route('/api/goals', methods=['GET'])
def get_goals():
    month = request.args.get('month')
    conn = get_db()
    if month:
        goals = get_goals_for_month(conn, month)
    else:
        row = conn.execute('SELECT * FROM goals WHERE id=1').fetchone()
        goals = dict(row)
    conn.close()
    return jsonify(goals)


@app.route('/api/goals', methods=['PUT'])
def update_goals():
    data = request.json
    month = request.args.get('month')
    conn = get_db()
    if month:
        conn.execute(
            'INSERT INTO monthly_goals (year_month, daily_hours, weekly_hours, monthly_hours) VALUES (?,?,?,?) '
            'ON CONFLICT(year_month) DO UPDATE SET daily_hours=?, weekly_hours=?, monthly_hours=?',
            (month, data['daily_hours'], data['weekly_hours'], data['monthly_hours'],
             data['daily_hours'], data['weekly_hours'], data['monthly_hours'])
        )
    else:
        conn.execute(
            'UPDATE goals SET daily_hours=?, weekly_hours=?, monthly_hours=? WHERE id=1',
            (data['daily_hours'], data['weekly_hours'], data['monthly_hours'])
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ── STATS ──
@app.route('/api/stats', methods=['GET'])
def get_stats():
    month_param = request.args.get('month')
    week_start_param = request.args.get('week_start')  # YYYY-MM-DD (Monday)
    today = date.today()
    current_ym = today.strftime('%Y-%m')
    viewing_ym = month_param or current_ym
    is_current = viewing_ym == current_ym

    year, month = map(int, viewing_ym.split('-'))
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    # Determine selected week
    current_week_monday = today - timedelta(days=today.weekday())
    if week_start_param:
        sel_week_start = date.fromisoformat(week_start_param)
    else:
        sel_week_start = current_week_monday
    sel_week_end = sel_week_start + timedelta(days=6)
    is_current_week = (sel_week_start == current_week_monday)

    conn = get_db()
    pf, pp = get_project_filter(conn)
    goals = get_goals_for_month(conn, viewing_ym)
    daily_goal = goals['daily_hours']
    weekly_goal = goals['weekly_hours']
    monthly_goal = goals['monthly_hours']

    # ── Month total ──
    month_hours = conn.execute(
        f'SELECT COALESCE(SUM(duration_hours),0) as h FROM sessions WHERE date>=? AND date<=?{pf}',
        [month_start.isoformat(), month_end.isoformat()] + pp
    ).fetchone()['h']

    # ── Today (current month only) ──
    if is_current:
        today_hours = conn.execute(
            f'SELECT COALESCE(SUM(duration_hours),0) as h FROM sessions WHERE date=?{pf}',
            [today.isoformat()] + pp
        ).fetchone()['h']
    else:
        today_hours = None

    # ── Week: always the selected week from the navigator ──
    week_hours = conn.execute(
        f'SELECT COALESCE(SUM(duration_hours),0) as h FROM sessions WHERE date>=? AND date<=?{pf}',
        [sel_week_start.isoformat(), sel_week_end.isoformat()] + pp
    ).fetchone()['h']

    # ── Total all-time (unfiltered) ──
    total_hours = conn.execute('SELECT COALESCE(SUM(duration_hours),0) as h FROM sessions').fetchone()['h']

    # ── Streak (always current, with project filter) ──
    streak = 0
    check_date = today
    for _ in range(365):
        dh = conn.execute(
            f'SELECT COALESCE(SUM(duration_hours),0) as h FROM sessions WHERE date=?{pf}',
            [check_date.isoformat()] + pp
        ).fetchone()['h']
        if dh >= daily_goal * 0.5:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    # ── Daily data for selected month ──
    days_in_month = calendar.monthrange(year, month)[1]
    daily_rows = conn.execute(
        f'SELECT date, SUM(duration_hours) as hours FROM sessions WHERE date>=? AND date<=?{pf} GROUP BY date',
        [month_start.isoformat(), month_end.isoformat()] + pp
    ).fetchall()
    daily_map = {r['date']: round(r['hours'], 2) for r in daily_rows}
    daily_data = []
    for i in range(days_in_month):
        d = (month_start + timedelta(days=i)).isoformat()
        daily_data.append({'date': d, 'hours': daily_map.get(d, 0)})

    # ── Weekly trend: 8 weeks ending in the viewed month ──
    # Find the last week of viewed month, go back 7 more
    last_day = month_end
    week_of_last = last_day - timedelta(days=last_day.weekday())
    weekly_trend = []
    for i in range(7, -1, -1):
        ws = week_of_last - timedelta(weeks=i)
        we = ws + timedelta(days=6)
        wh = conn.execute(
            f'SELECT COALESCE(SUM(duration_hours),0) as h FROM sessions WHERE date>=? AND date<=?{pf}',
            [ws.isoformat(), we.isoformat()] + pp
        ).fetchone()['h']
        weekly_trend.append({'week': ws.strftime('%d/%m'), 'hours': round(wh, 2)})

    # ── Projects breakdown for viewed month ──
    projects = conn.execute(
        f'SELECT project, SUM(duration_hours) as hours FROM sessions WHERE date>=? AND date<=? GROUP BY project ORDER BY hours DESC LIMIT 8',
        [month_start.isoformat(), month_end.isoformat()]
    ).fetchall()

    # ── Days studied + best day ──
    days_studied = conn.execute(
        f'SELECT COUNT(DISTINCT date) as cnt FROM sessions WHERE date>=? AND date<=?{pf} AND duration_hours>0',
        [month_start.isoformat(), month_end.isoformat()] + pp
    ).fetchone()['cnt']
    best_day = conn.execute(
        f'SELECT date, SUM(duration_hours) as hours FROM sessions WHERE date>=? AND date<=?{pf} GROUP BY date ORDER BY hours DESC LIMIT 1',
        [month_start.isoformat(), month_end.isoformat()] + pp
    ).fetchone()

    conn.close()

    return jsonify({
        'is_current': is_current,
        'is_current_week': is_current_week,
        'viewing_month': viewing_ym,
        'sel_week_start': sel_week_start.isoformat(),
        'sel_week_end': sel_week_end.isoformat(),
        'today': round(today_hours, 2) if today_hours is not None else None,
        'week': round(week_hours, 2),
        'month': round(month_hours, 2),
        'total': round(total_hours, 2),
        'streak': streak,
        'days_studied_month': days_studied,
        'best_day': {'date': best_day['date'], 'hours': round(best_day['hours'], 2)} if best_day else None,
        'goals': {'daily': daily_goal, 'weekly': weekly_goal, 'monthly': monthly_goal},
        'daily_data': daily_data,
        'weekly_trend': weekly_trend,
        'projects': [{'name': r['project'] or 'Sem projeto', 'hours': round(r['hours'], 2)} for r in projects],
    })


if __name__ == '__main__':
    init_db()
    print('\n🎓 Study Tracker iniciado!')
    print('📊 Acesse: http://localhost:5000\n')
    app.run(debug=True, port=5000)
