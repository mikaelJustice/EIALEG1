"""
Public Routes - accessible by everyone without login.
All routes accept ?league=boys|girls  (default: boys)
"""

from flask import Blueprint, render_template, request
from database import get_db

public_bp = Blueprint('public', __name__)


def get_league():
    return request.args.get('league', 'boys')


def calculate_league_table(db, league='boys'):
    teams = db.execute('SELECT * FROM teams WHERE league=? ORDER BY name', (league,)).fetchall()
    table = []
    for team in teams:
        tid = team['id']
        home = db.execute('''
            SELECT home_goals, away_goals FROM matches
            WHERE home_team_id=? AND status='played' AND league=?
        ''', (tid, league)).fetchall()
        away = db.execute('''
            SELECT home_goals, away_goals FROM matches
            WHERE away_team_id=? AND status='played' AND league=?
        ''', (tid, league)).fetchall()
        played = len(home) + len(away)
        wins = draws = losses = gf = ga = 0
        for m in home:
            gf += m['home_goals']; ga += m['away_goals']
            if   m['home_goals'] > m['away_goals']:  wins += 1
            elif m['home_goals'] == m['away_goals']: draws += 1
            else:                                    losses += 1
        for m in away:
            gf += m['away_goals']; ga += m['home_goals']
            if   m['away_goals'] > m['home_goals']:  wins += 1
            elif m['away_goals'] == m['home_goals']: draws += 1
            else:                                    losses += 1
        table.append({
            'team': team, 'played': played, 'wins': wins, 'draws': draws,
            'losses': losses, 'gf': gf, 'ga': ga,
            'gd': gf - ga, 'points': wins * 3 + draws
        })
    table.sort(key=lambda x: (-x['points'], -x['gd'], -x['gf']))
    return table


def get_top_scorers(db, league='boys', limit=10):
    return db.execute('''
        SELECT p.*, t.name as team_name, t.badge_color as team_color
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.league = ? AND p.goals > 0
        ORDER BY p.goals DESC, p.assists DESC
        LIMIT ?
    ''', (league, limit)).fetchall()


def get_match_events(db, match_id):
    return db.execute('''
        SELECT me.*, p.name as player_name, t.name as team_name, t.badge_color as team_color
        FROM match_events me
        JOIN players p ON me.player_id = p.id
        JOIN teams t ON me.team_id = t.id
        WHERE me.match_id = ?
        ORDER BY me.event_type, me.minute
    ''', (match_id,)).fetchall()


def get_lineup_for_match(db, match_id, team_id):
    """Return starters with their pitch positions for a match/team."""
    return db.execute('''
        SELECT l.*, p.name as player_name, p.position as player_pos,
               p.shirt_number, l.formation, l.pitch_row, l.pitch_col, l.shirt_slot
        FROM lineups l
        JOIN players p ON l.player_id = p.id
        WHERE l.match_id=? AND l.team_id=? AND l.is_starter=1
        ORDER BY l.pitch_row, l.pitch_col
    ''', (match_id, team_id)).fetchall()


@public_bp.route('/home')
def home():
    db     = get_db()
    league = get_league()

    # Check both leagues have teams (for switcher)
    boys_count  = db.execute("SELECT COUNT(*) FROM teams WHERE league='boys'").fetchone()[0]
    girls_count = db.execute("SELECT COUNT(*) FROM teams WHERE league='girls'").fetchone()[0]

    news = db.execute('''
        SELECT n.*, u.username as author FROM news n
        JOIN users u ON n.posted_by = u.id
        WHERE n.published = 1 AND (n.league = ? OR n.league = 'both')
        ORDER BY n.created_at DESC LIMIT 5
    ''', (league,)).fetchall()

    recent_results = db.execute('''
        SELECT m.*,
               ht.name as home_name, ht.badge_color as home_color,
               at.name as away_name, at.badge_color as away_color
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.status = 'played' AND m.league = ?
        ORDER BY m.match_date DESC LIMIT 5
    ''', (league,)).fetchall()

    upcoming = db.execute('''
        SELECT m.*,
               ht.name as home_name, ht.badge_color as home_color,
               at.name as away_name, at.badge_color as away_color
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.status = 'scheduled' AND m.league = ?
        ORDER BY m.match_date ASC LIMIT 5
    ''', (league,)).fetchall()

    table       = calculate_league_table(db, league)[:5]
    top_scorers = get_top_scorers(db, league, limit=5)

    return render_template('public/home.html',
                           news=news, recent_results=recent_results,
                           upcoming=upcoming, table=table,
                           top_scorers=top_scorers, league=league,
                           boys_count=boys_count, girls_count=girls_count)


@public_bp.route('/table')
def league_table():
    db     = get_db()
    league = get_league()
    table  = calculate_league_table(db, league)
    top_scorers = get_top_scorers(db, league, limit=10)
    return render_template('public/table.html', table=table,
                           top_scorers=top_scorers, league=league)


@public_bp.route('/fixtures')
def fixtures():
    db     = get_db()
    league = get_league()
    fixtures_raw = db.execute('''
        SELECT m.*,
               ht.name as home_name, ht.short_name as home_short, ht.badge_color as home_color,
               at.name as away_name, at.short_name as away_short, at.badge_color as away_color
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.status = 'scheduled' AND m.league = ?
        ORDER BY m.match_date ASC
    ''', (league,)).fetchall()

    # Attach lineups to each fixture
    fixtures_with_lineups = []
    for m in fixtures_raw:
        home_lineup = get_lineup_for_match(db, m['id'], m['home_team_id'])
        away_lineup = get_lineup_for_match(db, m['id'], m['away_team_id'])
        formation_home = home_lineup[0]['formation'] if home_lineup else None
        formation_away = away_lineup[0]['formation'] if away_lineup else None
        fixtures_with_lineups.append({
            'match': m,
            'home_lineup': home_lineup,
            'away_lineup': away_lineup,
            'formation_home': formation_home,
            'formation_away': formation_away,
            'has_lineups': len(home_lineup) > 0 or len(away_lineup) > 0
        })

    return render_template('public/fixtures.html',
                           fixtures=fixtures_with_lineups, league=league)


@public_bp.route('/results')
def results():
    db     = get_db()
    league = get_league()
    matches = db.execute('''
        SELECT m.*,
               ht.name as home_name, ht.short_name as home_short, ht.badge_color as home_color, ht.id as ht_id,
               at.name as away_name, at.short_name as away_short, at.badge_color as away_color, at.id as at_id
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.status = 'played' AND m.league = ?
        ORDER BY m.match_date DESC
    ''', (league,)).fetchall()

    results_with_events = []
    for m in matches:
        events = get_match_events(db, m['id'])
        goals        = [e for e in events if e['event_type'] == 'goal']
        yellow_cards = [e for e in events if e['event_type'] == 'yellow_card']
        red_cards    = [e for e in events if e['event_type'] == 'red_card']
        results_with_events.append({
            'match': m, 'goals': goals,
            'yellow_cards': yellow_cards, 'red_cards': red_cards,
        })

    return render_template('public/results.html',
                           results=results_with_events, league=league)


@public_bp.route('/news')
def news():
    db     = get_db()
    league = get_league()
    articles = db.execute('''
        SELECT n.*, u.username as author FROM news n
        JOIN users u ON n.posted_by = u.id
        WHERE n.published = 1 AND (n.league = ? OR n.league = 'both')
        ORDER BY n.created_at DESC
    ''', (league,)).fetchall()
    return render_template('public/news.html', articles=articles, league=league)


@public_bp.route('/news/<int:news_id>')
def news_detail(news_id):
    db     = get_db()
    league = get_league()
    article = db.execute('''
        SELECT n.*, u.username as author FROM news n
        JOIN users u ON n.posted_by = u.id
        WHERE n.id = ? AND n.published = 1
    ''', (news_id,)).fetchone()
    if not article:
        return render_template('public/404.html'), 404
    return render_template('public/news_detail.html', article=article, league=league)


@public_bp.route('/teams')
def teams():
    db     = get_db()
    league = get_league()
    teams_raw = db.execute('''
        SELECT t.*, COUNT(p.id) as player_count
        FROM teams t
        LEFT JOIN players p ON p.team_id = t.id
        WHERE t.league = ?
        GROUP BY t.id ORDER BY t.name
    ''', (league,)).fetchall()

    teams_data = []
    for team in teams_raw:
        # Get captain
        captain = db.execute('''
            SELECT u.username FROM users u
            WHERE u.team_id=? AND u.role='captain'
            LIMIT 1
        ''', (team['id'],)).fetchone()

        # Get transfer history (approved)
        transfers = db.execute('''
            SELECT t.*, p.name as player_name, p.position as player_pos,
                   ft.name as from_team, tt.name as to_team
            FROM transfers t
            JOIN players p ON t.player_id = p.id
            LEFT JOIN teams ft ON t.from_team_id = ft.id
            JOIN teams tt ON t.to_team_id = tt.id
            WHERE (t.to_team_id=? OR t.from_team_id=?) AND t.status='approved'
            ORDER BY t.resolved_at DESC LIMIT 5
        ''', (team['id'], team['id'])).fetchall()

        teams_data.append({
            'team': team,
            'captain': captain['username'] if captain else None,
            'transfers': transfers,
        })

    return render_template('public/teams.html', teams=teams_data, league=league)


@public_bp.route('/teams/<int:team_id>')
def team_detail(team_id):
    db     = get_db()
    league = get_league()
    team = db.execute('SELECT * FROM teams WHERE id=?', (team_id,)).fetchone()
    if not team:
        return render_template('public/404.html'), 404

    players = db.execute(
        'SELECT * FROM players WHERE team_id=? ORDER BY position, name',
        (team_id,)
    ).fetchall()

    captain = db.execute(
        "SELECT username FROM users WHERE team_id=? AND role='captain' LIMIT 1",
        (team_id,)
    ).fetchone()

    # Transfer history
    transfers = db.execute('''
        SELECT t.*, p.name as player_name, p.position as player_pos,
               ft.name as from_team, tt.name as to_team
        FROM transfers t
        JOIN players p ON t.player_id = p.id
        LEFT JOIN teams ft ON t.from_team_id = ft.id
        JOIN teams tt ON t.to_team_id = tt.id
        WHERE (t.to_team_id=? OR t.from_team_id=?) AND t.status='approved'
        ORDER BY t.resolved_at DESC
    ''', (team_id, team_id)).fetchall()

    recent_raw = db.execute('''
        SELECT m.*,
               ht.name as home_name, ht.badge_color as home_color,
               at.name as away_name, at.badge_color as away_color
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE (m.home_team_id=? OR m.away_team_id=?) AND m.status='played'
        ORDER BY m.match_date DESC LIMIT 5
    ''', (team_id, team_id)).fetchall()

    recent = []
    for m in recent_raw:
        events = get_match_events(db, m['id'])
        recent.append({'match': m, 'events': events})

    # Latest submitted lineup (most recent fixture)
    latest_match = db.execute('''
        SELECT m.* FROM matches m
        WHERE (m.home_team_id=? OR m.away_team_id=?) AND m.status='scheduled'
        ORDER BY m.match_date ASC LIMIT 1
    ''', (team_id, team_id)).fetchone()

    latest_lineup = []
    lineup_formation = None
    lineup_match = None
    if latest_match:
        latest_lineup = get_lineup_for_match(db, latest_match['id'], team_id)
        if latest_lineup:
            lineup_formation = latest_lineup[0]['formation']
            lineup_match = latest_match

    return render_template('public/team_detail.html',
                           team=team, players=players, recent=recent,
                           captain=captain['username'] if captain else None,
                           transfers=transfers,
                           latest_lineup=latest_lineup,
                           lineup_formation=lineup_formation,
                           lineup_match=lineup_match,
                           league=league)


@public_bp.route('/scorers')
def scorers():
    db     = get_db()
    league = get_league()
    top_scorers  = get_top_scorers(db, league, limit=50)
    most_yellows = db.execute('''
        SELECT p.*, t.name as team_name, t.badge_color as team_color
        FROM players p LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.league = ? AND p.yellow_cards > 0
        ORDER BY p.yellow_cards DESC LIMIT 20
    ''', (league,)).fetchall()
    return render_template('public/scorers.html',
                           top_scorers=top_scorers,
                           most_yellows=most_yellows,
                           league=league)
