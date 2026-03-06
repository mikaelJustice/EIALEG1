"""
Admin Routes - full control panel
NEW v2: league filtering, match events (scorers/cards), prize money on results
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from database import get_db
from auth_helpers import admin_required

admin_bp = Blueprint('admin', __name__)

# Prize money constants (euros)
PRIZE_WIN  =  1000   # winner receives €1000
PRIZE_LOSS =  -200   # loser loses €200
# Draw: no money changes hands

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    db = get_db()
    stats = {
        'teams':            db.execute('SELECT COUNT(*) FROM teams').fetchone()[0],
        'players':          db.execute('SELECT COUNT(*) FROM players').fetchone()[0],
        'matches_played':   db.execute("SELECT COUNT(*) FROM matches WHERE status='played'").fetchone()[0],
        'pending_transfers':db.execute("SELECT COUNT(*) FROM transfers WHERE status='pending'").fetchone()[0],
        'boys_teams':       db.execute("SELECT COUNT(*) FROM teams WHERE league='boys'").fetchone()[0],
        'girls_teams':      db.execute("SELECT COUNT(*) FROM teams WHERE league='girls'").fetchone()[0],
    }
    recent_transfers = db.execute('''
        SELECT t.*, p.name as player_name,
               ft.name as from_team, tt.name as to_team,
               u.username as captain
        FROM transfers t
        JOIN players p ON t.player_id = p.id
        LEFT JOIN teams ft ON t.from_team_id = ft.id
        JOIN teams tt ON t.to_team_id = tt.id
        JOIN users u ON t.requested_by = u.id
        WHERE t.status = 'pending'
        ORDER BY t.requested_at DESC LIMIT 10
    ''').fetchall()
    return render_template('admin/dashboard.html', stats=stats, recent_transfers=recent_transfers)


# ─────────────────────────────────────────────────────────────────────────────
# TEAM MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/teams')
@admin_required
def teams():
    db = get_db()
    league = request.args.get('league', 'boys')
    teams = db.execute('''
        SELECT t.*, COUNT(p.id) as player_count,
               u.username as captain_name
        FROM teams t
        LEFT JOIN players p ON p.team_id = t.id
        LEFT JOIN users u ON u.team_id = t.id AND u.role = 'captain'
        WHERE t.league = ?
        GROUP BY t.id ORDER BY t.name
    ''', (league,)).fetchall()
    return render_template('admin/teams.html', teams=teams, league=league)


@admin_bp.route('/teams/add', methods=['GET', 'POST'])
@admin_required
def add_team():
    league = request.args.get('league', request.form.get('league', 'boys'))
    if request.method == 'POST':
        name        = request.form['name'].strip()
        short_name  = request.form['short_name'].strip().upper()
        badge_color = request.form.get('badge_color', '#e74c3c')
        balance     = float(request.form.get('balance', 0))
        home_ground = request.form.get('home_ground', '').strip()
        founded_year= request.form.get('founded_year') or None
        league      = request.form.get('league', 'boys')
        cap_user    = request.form.get('captain_username', '').strip()
        cap_pass    = request.form.get('captain_password', '').strip()

        db = get_db()
        try:
            db.execute('''
                INSERT INTO teams (name, short_name, badge_color, balance, home_ground, founded_year, league)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, short_name, badge_color, balance, home_ground, founded_year, league))
            team_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
            if cap_user and cap_pass:
                db.execute('''
                    INSERT INTO users (username, password_hash, role, team_id)
                    VALUES (?, ?, 'captain', ?)
                ''', (cap_user, generate_password_hash(cap_pass), team_id))
            db.execute('COMMIT')
            flash(f'Team "{name}" created!', 'success')
            return redirect(url_for('admin.teams', league=league))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

    return render_template('admin/team_form.html', team=None, action='Add', league=league)


@admin_bp.route('/teams/<int:team_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_team(team_id):
    db = get_db()
    team = db.execute('SELECT * FROM teams WHERE id=?', (team_id,)).fetchone()
    if not team:
        flash('Team not found.', 'danger')
        return redirect(url_for('admin.teams'))

    if request.method == 'POST':
        name         = request.form['name'].strip()
        short_name   = request.form['short_name'].strip().upper()
        badge_color  = request.form.get('badge_color', '#e74c3c')
        home_ground  = request.form.get('home_ground', '').strip()
        founded_year = request.form.get('founded_year') or None
        league       = request.form.get('league', team['league'])
        db.execute('''
            UPDATE teams SET name=?, short_name=?, badge_color=?, home_ground=?, founded_year=?, league=?
            WHERE id=?
        ''', (name, short_name, badge_color, home_ground, founded_year, league, team_id))
        db.execute('COMMIT')
        flash(f'Team "{name}" updated!', 'success')
        return redirect(url_for('admin.teams', league=league))

    return render_template('admin/team_form.html', team=team, action='Edit', league=team['league'])


@admin_bp.route('/teams/<int:team_id>/delete', methods=['POST'])
@admin_required
def delete_team(team_id):
    db = get_db()
    t = db.execute('SELECT league FROM teams WHERE id=?', (team_id,)).fetchone()
    league = t['league'] if t else 'boys'
    db.execute('DELETE FROM teams WHERE id=?', (team_id,))
    db.execute('COMMIT')
    flash('Team deleted.', 'success')
    return redirect(url_for('admin.teams', league=league))


@admin_bp.route('/teams/<int:team_id>/add_money', methods=['POST'])
@admin_required
def add_money(team_id):
    amount      = float(request.form.get('amount', 0))
    description = request.form.get('description', 'Admin top-up')
    if amount <= 0:
        flash('Amount must be positive.', 'danger')
        return redirect(url_for('admin.teams'))
    db = get_db()
    t = db.execute('SELECT league FROM teams WHERE id=?', (team_id,)).fetchone()
    db.execute('UPDATE teams SET balance = balance + ? WHERE id=?', (amount, team_id))
    db.execute('''
        INSERT INTO transactions (team_id, amount, description, transaction_type)
        VALUES (?, ?, ?, 'top_up')
    ''', (team_id, amount, description))
    db.execute('COMMIT')
    flash(f'€{amount:,.0f} added to team balance!', 'success')
    return redirect(url_for('admin.teams', league=t['league'] if t else 'boys'))


# ─────────────────────────────────────────────────────────────────────────────
# PLAYER MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/players')
@admin_required
def players():
    db  = get_db()
    league = request.args.get('league', 'boys')
    players = db.execute('''
        SELECT p.*, t.name as team_name, t.badge_color as team_color
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.league = ?
        ORDER BY t.name, p.position, p.name
    ''', (league,)).fetchall()
    return render_template('admin/players.html', players=players, league=league)


@admin_bp.route('/players/add', methods=['GET', 'POST'])
@admin_required
def add_player():
    league = request.args.get('league', 'boys')
    db = get_db()
    if request.method == 'POST':
        name         = request.form['name'].strip()
        position     = request.form['position']
        team_id      = request.form.get('team_id') or None
        price        = float(request.form.get('price', 0))
        age          = request.form.get('age') or None
        shirt_number = request.form.get('shirt_number') or None
        league       = request.form.get('league', 'boys')
        photo_url = save_image(request.files.get('photo'), 'players')
        db.execute('''
            INSERT INTO players (name, position, team_id, price, age, shirt_number, league, photo_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, position, team_id, price, age, shirt_number, league, photo_url))
        db.execute('COMMIT')
        flash(f'Player "{name}" added!', 'success')
        return redirect(url_for('admin.players', league=league))
    teams = db.execute('SELECT * FROM teams WHERE league=? ORDER BY name', (league,)).fetchall()
    return render_template('admin/player_form.html', player=None, teams=teams, action='Add', league=league)


@admin_bp.route('/players/<int:player_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_player(player_id):
    db = get_db()
    player = db.execute('SELECT * FROM players WHERE id=?', (player_id,)).fetchone()
    if not player:
        flash('Player not found.', 'danger')
        return redirect(url_for('admin.players'))
    league = player['league']

    if request.method == 'POST':
        name         = request.form['name'].strip()
        position     = request.form['position']
        team_id      = request.form.get('team_id') or None
        price        = float(request.form.get('price', 0))
        age          = request.form.get('age') or None
        shirt_number = request.form.get('shirt_number') or None
        goals        = int(request.form.get('goals', 0))
        assists      = int(request.form.get('assists', 0))
        yellow_cards = int(request.form.get('yellow_cards', 0))
        red_cards    = int(request.form.get('red_cards', 0))
        league       = request.form.get('league', league)
        new_photo = save_image(request.files.get('photo'), 'players')
        photo_url = new_photo if new_photo else player['photo_url']
        if request.form.get('remove_photo'):
            delete_image(player['photo_url'])
            photo_url = None
        db.execute('''
            UPDATE players SET name=?, position=?, team_id=?, price=?, age=?,
            shirt_number=?, goals=?, assists=?, yellow_cards=?, red_cards=?, league=?, photo_url=?
            WHERE id=?
        ''', (name, position, team_id, price, age, shirt_number,
              goals, assists, yellow_cards, red_cards, league, photo_url, player_id))
        db.execute('COMMIT')
        flash(f'Player "{name}" updated!', 'success')
        return redirect(url_for('admin.players', league=league))

    teams = db.execute('SELECT * FROM teams WHERE league=? ORDER BY name', (league,)).fetchall()
    return render_template('admin/player_form.html', player=player, teams=teams, action='Edit', league=league)


@admin_bp.route('/players/<int:player_id>/delete', methods=['POST'])
@admin_required
def delete_player(player_id):
    db = get_db()
    p = db.execute('SELECT league FROM players WHERE id=?', (player_id,)).fetchone()
    league = p['league'] if p else 'boys'
    db.execute('DELETE FROM players WHERE id=?', (player_id,))
    db.execute('COMMIT')
    flash('Player deleted.', 'success')
    return redirect(url_for('admin.players', league=league))


# ─────────────────────────────────────────────────────────────────────────────
# TRANSFER MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/transfers')
@admin_required
def transfers():
    db = get_db()
    transfers = db.execute('''
        SELECT t.*, p.name as player_name, p.position as player_position,
               p.league as player_league,
               ft.name as from_team, tt.name as to_team,
               u.username as captain
        FROM transfers t
        JOIN players p ON t.player_id = p.id
        LEFT JOIN teams ft ON t.from_team_id = ft.id
        JOIN teams tt ON t.to_team_id = tt.id
        JOIN users u ON t.requested_by = u.id
        ORDER BY t.status ASC, t.requested_at DESC
    ''').fetchall()
    return render_template('admin/transfers.html', transfers=transfers)


@admin_bp.route('/transfers/<int:transfer_id>/approve', methods=['POST'])
@admin_required
def approve_transfer(transfer_id):
    db = get_db()
    transfer = db.execute('SELECT * FROM transfers WHERE id=?', (transfer_id,)).fetchone()
    if not transfer or transfer['status'] != 'pending':
        flash('Transfer not found or already processed.', 'danger')
        return redirect(url_for('admin.transfers'))

    admin_note   = request.form.get('admin_note', '')
    fee          = transfer['fee']
    player_id    = transfer['player_id']
    to_team_id   = transfer['to_team_id']
    from_team_id = transfer['from_team_id']

    to_team = db.execute('SELECT * FROM teams WHERE id=?', (to_team_id,)).fetchone()
    if to_team['balance'] < fee:
        flash(f'Rejected: {to_team["name"]} cannot afford €{fee:,.0f}!', 'danger')
        db.execute('''
            UPDATE transfers SET status='rejected', admin_note=?, resolved_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', ('Insufficient funds - ' + admin_note, transfer_id))
        db.execute('COMMIT')
        return redirect(url_for('admin.transfers'))

    player = db.execute('SELECT * FROM players WHERE id=?', (player_id,)).fetchone()
    db.execute('UPDATE players SET team_id=? WHERE id=?', (to_team_id, player_id))
    db.execute('UPDATE teams SET balance = balance - ? WHERE id=?', (fee, to_team_id))
    db.execute('''
        INSERT INTO transactions (team_id, amount, description, transaction_type)
        VALUES (?, ?, ?, 'transfer_out')
    ''', (to_team_id, -fee, f'Transfer: bought {player["name"]}'))
    if from_team_id:
        db.execute('UPDATE teams SET balance = balance + ? WHERE id=?', (fee, from_team_id))
        db.execute('''
            INSERT INTO transactions (team_id, amount, description, transaction_type)
            VALUES (?, ?, ?, 'transfer_in')
        ''', (from_team_id, fee, f'Transfer: sold {player["name"]}'))
    db.execute('''
        UPDATE transfers SET status='approved', admin_note=?, resolved_at=CURRENT_TIMESTAMP
        WHERE id=?
    ''', (admin_note, transfer_id))
    db.execute('COMMIT')
    flash(f'Transfer approved! {player["name"]} has moved teams.', 'success')
    return redirect(url_for('admin.transfers'))


@admin_bp.route('/transfers/<int:transfer_id>/reject', methods=['POST'])
@admin_required
def reject_transfer(transfer_id):
    db = get_db()
    admin_note = request.form.get('admin_note', 'Rejected by admin')
    db.execute('''
        UPDATE transfers SET status='rejected', admin_note=?, resolved_at=CURRENT_TIMESTAMP
        WHERE id=?
    ''', (admin_note, transfer_id))
    db.execute('COMMIT')
    flash('Transfer rejected.', 'warning')
    return redirect(url_for('admin.transfers'))


# ─────────────────────────────────────────────────────────────────────────────
# MATCH MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/matches')
@admin_required
def matches():
    db = get_db()
    league = request.args.get('league', 'boys')
    matches = db.execute('''
        SELECT m.*,
               ht.name as home_name, ht.badge_color as home_color,
               at.name as away_name, at.badge_color as away_color
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.league = ?
        ORDER BY m.match_date DESC
    ''', (league,)).fetchall()
    return render_template('admin/matches.html', matches=matches, league=league)


@admin_bp.route('/matches/add', methods=['GET', 'POST'])
@admin_required
def add_match():
    league = request.args.get('league', 'boys')
    db = get_db()
    if request.method == 'POST':
        home_team_id = int(request.form['home_team_id'])
        away_team_id = int(request.form['away_team_id'])
        match_date   = request.form['match_date']
        venue        = request.form.get('venue', '').strip()
        matchday     = int(request.form.get('matchday', 1))
        league       = request.form.get('league', 'boys')
        if home_team_id == away_team_id:
            flash('Home and away teams cannot be the same!', 'danger')
        else:
            db.execute('''
                INSERT INTO matches (home_team_id, away_team_id, match_date, venue, matchday, league)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (home_team_id, away_team_id, match_date, venue, matchday, league))
            db.execute('COMMIT')
            flash('Fixture created!', 'success')
            return redirect(url_for('admin.matches', league=league))
    teams = db.execute('SELECT * FROM teams WHERE league=? ORDER BY name', (league,)).fetchall()
    return render_template('admin/match_form.html', match=None, teams=teams, action='Create', league=league)


@admin_bp.route('/matches/<int:match_id>/result', methods=['GET', 'POST'])
@admin_required
def enter_result(match_id):
    """
    Dedicated result-entry page:
    - Enter home/away goals
    - Record goal scorers per team (with optional minute)
    - Record yellow cards per team (with optional minute)
    - On save: auto-apply prize money (win +€1000, lose -€200, draw nothing)
    - Player stats (goals, yellow_cards) auto-update
    """
    db = get_db()
    match = db.execute('''
        SELECT m.*,
               ht.name as home_name, ht.badge_color as home_color,
               at.name as away_name, at.badge_color as away_color
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.id=?
    ''', (match_id,)).fetchone()
    if not match:
        flash('Match not found.', 'danger')
        return redirect(url_for('admin.matches'))

    if request.method == 'POST':
        home_goals = int(request.form.get('home_goals', 0))
        away_goals = int(request.form.get('away_goals', 0))

        # ── Clear previous events so re-entry is clean ─────────────────────
        db.execute('DELETE FROM match_events WHERE match_id=?', (match_id,))

        # ── Parse goal scorers ─────────────────────────────────────────────
        # Form sends: goal_player_<n>, goal_team_<n>, goal_minute_<n>
        goal_players  = request.form.getlist('goal_player')
        goal_teams    = request.form.getlist('goal_team')
        goal_minutes  = request.form.getlist('goal_minute')
        for i, pid in enumerate(goal_players):
            if pid:
                tid = goal_teams[i] if i < len(goal_teams) else None
                min_ = goal_minutes[i] if i < len(goal_minutes) and goal_minutes[i] else None
                db.execute('''
                    INSERT INTO match_events (match_id, player_id, team_id, event_type, minute)
                    VALUES (?, ?, ?, 'goal', ?)
                ''', (match_id, int(pid), int(tid), min_))
                # Update player goals tally
                db.execute('UPDATE players SET goals = goals + 1 WHERE id=?', (int(pid),))

        # ── Parse yellow cards ─────────────────────────────────────────────
        yc_players = request.form.getlist('yc_player')
        yc_teams   = request.form.getlist('yc_team')
        yc_minutes = request.form.getlist('yc_minute')
        for i, pid in enumerate(yc_players):
            if pid:
                tid  = yc_teams[i] if i < len(yc_teams) else None
                min_ = yc_minutes[i] if i < len(yc_minutes) and yc_minutes[i] else None
                db.execute('''
                    INSERT INTO match_events (match_id, player_id, team_id, event_type, minute)
                    VALUES (?, ?, ?, 'yellow_card', ?)
                ''', (match_id, int(pid), int(tid), min_))
                db.execute('UPDATE players SET yellow_cards = yellow_cards + 1 WHERE id=?', (int(pid),))

        # ── Parse red cards ────────────────────────────────────────────────
        rc_players = request.form.getlist('rc_player')
        rc_teams   = request.form.getlist('rc_team')
        for i, pid in enumerate(rc_players):
            if pid:
                tid = rc_teams[i] if i < len(rc_teams) else None
                db.execute('''
                    INSERT INTO match_events (match_id, player_id, team_id, event_type, minute)
                    VALUES (?, ?, ?, 'red_card', NULL)
                ''', (match_id, int(pid), int(tid)))
                db.execute('UPDATE players SET red_cards = red_cards + 1 WHERE id=?', (int(pid),))

        # ── Save result ────────────────────────────────────────────────────
        was_played = match['status'] == 'played'
        db.execute('''
            UPDATE matches SET home_goals=?, away_goals=?, status='played', prize_applied=0
            WHERE id=?
        ''', (home_goals, away_goals, match_id))

        # ── Apply prize money (only once per match result) ─────────────────
        _apply_prize_money(db, match_id, match['home_team_id'], match['away_team_id'],
                           home_goals, away_goals)

        db.execute('COMMIT')
        flash(f'Result saved! Score: {match["home_name"]} {home_goals}–{away_goals} {match["away_name"]}', 'success')
        return redirect(url_for('admin.matches', league=match['league']))

    # GET: load both squads for the dropdowns
    home_players = db.execute(
        'SELECT * FROM players WHERE team_id=? ORDER BY position, name',
        (match['home_team_id'],)
    ).fetchall()
    away_players = db.execute(
        'SELECT * FROM players WHERE team_id=? ORDER BY position, name',
        (match['away_team_id'],)
    ).fetchall()
    # Existing events
    existing_events = db.execute('''
        SELECT me.*, p.name as player_name
        FROM match_events me
        JOIN players p ON me.player_id = p.id
        WHERE me.match_id = ?
        ORDER BY me.event_type, me.minute
    ''', (match_id,)).fetchall()

    return render_template('admin/enter_result.html',
                           match=match,
                           home_players=home_players,
                           away_players=away_players,
                           existing_events=existing_events,
                           league=match['league'])


def _apply_prize_money(db, match_id, home_team_id, away_team_id, home_goals, away_goals):
    """
    Apply win/loss prize money.
    Win  = +€1000 for winner
    Loss = -€200  for loser
    Draw = no change
    """
    if home_goals > away_goals:
        winner_id, loser_id = home_team_id, away_team_id
        result_label = 'won'
    elif away_goals > home_goals:
        winner_id, loser_id = away_team_id, home_team_id
        result_label = 'won'
    else:
        # Draw - no money changes
        return

    # Winner gets €1000
    db.execute('UPDATE teams SET balance = balance + ? WHERE id=?', (PRIZE_WIN, winner_id))
    db.execute('''
        INSERT INTO transactions (team_id, amount, description, transaction_type)
        VALUES (?, ?, ?, 'match_bonus')
    ''', (winner_id, PRIZE_WIN, f'Match prize: victory bonus (Match #{match_id})'))

    # Loser loses €200
    db.execute('UPDATE teams SET balance = balance + ? WHERE id=?', (PRIZE_LOSS, loser_id))
    db.execute('''
        INSERT INTO transactions (team_id, amount, description, transaction_type)
        VALUES (?, ?, ?, 'match_penalty')
    ''', (loser_id, PRIZE_LOSS, f'Match deduction: loss penalty (Match #{match_id})'))

    db.execute('UPDATE matches SET prize_applied=1 WHERE id=?', (match_id,))


@admin_bp.route('/matches/<int:match_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_match(match_id):
    db = get_db()
    match = db.execute('SELECT * FROM matches WHERE id=?', (match_id,)).fetchone()
    if not match:
        flash('Match not found.', 'danger')
        return redirect(url_for('admin.matches'))

    if request.method == 'POST':
        match_date = request.form['match_date']
        venue      = request.form.get('venue', '').strip()
        matchday   = int(request.form.get('matchday', 1))
        status     = request.form.get('status', 'scheduled')
        db.execute('''
            UPDATE matches SET match_date=?, venue=?, matchday=?, status=?
            WHERE id=?
        ''', (match_date, venue, matchday, status, match_id))
        db.execute('COMMIT')
        flash('Match updated!', 'success')
        return redirect(url_for('admin.matches', league=match['league']))

    teams = db.execute('SELECT * FROM teams WHERE league=? ORDER BY name', (match['league'],)).fetchall()
    return render_template('admin/match_form.html', match=match, teams=teams, action='Edit', league=match['league'])


@admin_bp.route('/matches/<int:match_id>/delete', methods=['POST'])
@admin_required
def delete_match(match_id):
    db = get_db()
    m = db.execute('SELECT league FROM matches WHERE id=?', (match_id,)).fetchone()
    league = m['league'] if m else 'boys'
    db.execute('DELETE FROM matches WHERE id=?', (match_id,))
    db.execute('COMMIT')
    flash('Match deleted.', 'success')
    return redirect(url_for('admin.matches', league=league))


# ─────────────────────────────────────────────────────────────────────────────
# NEWS MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/news')
@admin_required
def news():
    db = get_db()
    articles = db.execute('''
        SELECT n.*, u.username as author FROM news n
        JOIN users u ON n.posted_by = u.id
        ORDER BY n.created_at DESC
    ''').fetchall()
    return render_template('admin/news.html', articles=articles)


@admin_bp.route('/news/add', methods=['GET', 'POST'])
@admin_required
def add_news():
    if request.method == 'POST':
        title     = request.form['title'].strip()
        content   = request.form['content'].strip()
        category  = request.form.get('category', 'general')
        league    = request.form.get('league', 'both')
        published = 1 if request.form.get('published') else 0
        image_url = save_image(request.files.get('image'), 'news')
        db = get_db()
        db.execute('''
            INSERT INTO news (title, content, category, posted_by, published, league, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, content, category, session['user_id'], published, league, image_url))
        db.execute('COMMIT')
        flash('News article posted!', 'success')
        return redirect(url_for('admin.news'))
    return render_template('admin/news_form.html', article=None, action='Post')


@admin_bp.route('/news/<int:news_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_news(news_id):
    db = get_db()
    article = db.execute('SELECT * FROM news WHERE id=?', (news_id,)).fetchone()
    if request.method == 'POST':
        title     = request.form['title'].strip()
        content   = request.form['content'].strip()
        category  = request.form.get('category', 'general')
        league    = request.form.get('league', 'both')
        published = 1 if request.form.get('published') else 0
        new_image = save_image(request.files.get('image'), 'news')
        image_url = new_image if new_image else article['image_url']
        if request.form.get('remove_image'):
            delete_image(article['image_url'])
            image_url = None
        db.execute('''
            UPDATE news SET title=?, content=?, category=?, published=?, league=?, image_url=? WHERE id=?
        ''', (title, content, category, published, league, image_url, news_id))
        db.execute('COMMIT')
        flash('Article updated!', 'success')
        return redirect(url_for('admin.news'))
    return render_template('admin/news_form.html', article=article, action='Edit')


@admin_bp.route('/news/<int:news_id>/delete', methods=['POST'])
@admin_required
def delete_news(news_id):
    db = get_db()
    db.execute('DELETE FROM news WHERE id=?', (news_id,))
    db.execute('COMMIT')
    flash('Article deleted.', 'success')
    return redirect(url_for('admin.news'))


# ─────────────────────────────────────────────────────────────────────────────
# USER MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/users')
@admin_required
def users():
    db = get_db()
    users = db.execute('''
        SELECT u.*, t.name as team_name, t.league as team_league FROM users u
        LEFT JOIN teams t ON u.team_id = t.id
        ORDER BY u.role, u.username
    ''').fetchall()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    db = get_db()
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role     = request.form['role']
        team_id  = request.form.get('team_id') or None
        try:
            db.execute('''
                INSERT INTO users (username, password_hash, role, team_id)
                VALUES (?, ?, ?, ?)
            ''', (username, generate_password_hash(password), role, team_id))
            db.execute('COMMIT')
            flash(f'User "{username}" created!', 'success')
            return redirect(url_for('admin.users'))
        except Exception:
            flash('Error: Username already exists.', 'danger')
    teams = db.execute('SELECT * FROM teams ORDER BY league, name').fetchall()
    return render_template('admin/user_form.html', user=None, teams=teams)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == session['user_id']:
        flash('Cannot delete your own account!', 'danger')
        return redirect(url_for('admin.users'))
    db = get_db()
    db.execute('DELETE FROM users WHERE id=?', (user_id,))
    db.execute('COMMIT')
    flash('User deleted.', 'success')
    return redirect(url_for('admin.users'))
