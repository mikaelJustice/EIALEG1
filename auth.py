"""
Captain Portal Routes - team management for captains
Captains can only manage their own team
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db
from auth_helpers import captain_required
from upload_helpers import save_image, delete_image

captain_bp = Blueprint('captain', __name__)


def get_captain_team():
    """Helper: get current captain's team from DB"""
    db = get_db()
    team_id = session.get('team_id')
    if not team_id:
        return None
    return db.execute('SELECT * FROM teams WHERE id=?', (team_id,)).fetchone()


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@captain_bp.route('/dashboard')
@captain_required
def dashboard():
    db = get_db()
    team = get_captain_team()
    if not team:
        flash('Your account is not linked to a team. Contact admin.', 'warning')
        return redirect(url_for('public.home'))

    team_id = team['id']

    # Squad info
    players = db.execute(
        'SELECT * FROM players WHERE team_id=? ORDER BY position, name',
        (team_id,)
    ).fetchall()

    # Upcoming fixtures
    upcoming = db.execute('''
        SELECT m.*,
               ht.name as home_name, at.name as away_name
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE (m.home_team_id=? OR m.away_team_id=?) AND m.status='scheduled'
        ORDER BY m.match_date ASC LIMIT 3
    ''', (team_id, team_id)).fetchall()

    # Pending transfers
    pending_transfers = db.execute('''
        SELECT t.*, p.name as player_name, tt.name as to_team, ft.name as from_team
        FROM transfers t
        JOIN players p ON t.player_id = p.id
        JOIN teams tt ON t.to_team_id = tt.id
        LEFT JOIN teams ft ON t.from_team_id = ft.id
        WHERE t.requested_by=? AND t.status='pending'
    ''', (session['user_id'],)).fetchall()

    # Recent transactions
    transactions = db.execute('''
        SELECT * FROM transactions WHERE team_id=?
        ORDER BY created_at DESC LIMIT 10
    ''', (team_id,)).fetchall()

    return render_template('captain/dashboard.html',
                           team=team, players=players,
                           upcoming=upcoming,
                           pending_transfers=pending_transfers,
                           transactions=transactions,
                           league=team['league'])


# ─────────────────────────────────────────────────────────────────────────────
# SQUAD MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@captain_bp.route('/squad')
@captain_required
def squad():
    db = get_db()
    team = get_captain_team()
    players = db.execute(
        'SELECT * FROM players WHERE team_id=? ORDER BY position, name',
        (team['id'],)
    ).fetchall()
    return render_template('captain/squad.html', team=team, players=players)


@captain_bp.route('/squad/<int:player_id>/set_price', methods=['POST'])
@captain_required
def set_price(player_id):
    """Captain can set transfer price for their own players"""
    db = get_db()
    team = get_captain_team()

    # Security: ensure player belongs to this team
    player = db.execute(
        'SELECT * FROM players WHERE id=? AND team_id=?',
        (player_id, team['id'])
    ).fetchone()

    if not player:
        flash('Player not found in your squad.', 'danger')
        return redirect(url_for('captain.squad'))

    price = float(request.form.get('price', 0))
    db.execute('UPDATE players SET price=? WHERE id=?', (price, player_id))
    db.execute('COMMIT')
    flash(f'{player["name"]} price set to £{price:,.0f}!', 'success')
    return redirect(url_for('captain.squad'))


@captain_bp.route('/squad/<int:player_id>/upload_photo', methods=['POST'])
@captain_required
def upload_player_photo(player_id):
    """Captain can upload/change photo for their own players"""
    db = get_db()
    team = get_captain_team()

    player = db.execute(
        'SELECT * FROM players WHERE id=? AND team_id=?',
        (player_id, team['id'])
    ).fetchone()

    if not player:
        flash('Player not found in your squad.', 'danger')
        return redirect(url_for('captain.squad'))

    if request.form.get('remove_photo'):
        delete_image(player['photo_url'])
        db.execute('UPDATE players SET photo_url=NULL WHERE id=?', (player_id,))
        db.execute('COMMIT')
        flash(f'Photo removed for {player["name"]}.', 'success')
        return redirect(url_for('captain.squad'))

    photo_url = save_image(request.files.get('photo'), 'players')
    if photo_url:
        if player['photo_url']:
            delete_image(player['photo_url'])
        db.execute('UPDATE players SET photo_url=? WHERE id=?', (photo_url, player_id))
        db.execute('COMMIT')
        flash(f'Photo updated for {player["name"]}!', 'success')
    else:
        flash('No valid image file was uploaded.', 'warning')

    return redirect(url_for('captain.squad'))


# ─────────────────────────────────────────────────────────────────────────────
# TRANSFER REQUESTS
# ─────────────────────────────────────────────────────────────────────────────

@captain_bp.route('/transfers')
@captain_required
def transfers():
    db = get_db()
    team = get_captain_team()

    # All transfer requests made by this captain
    my_requests = db.execute('''
        SELECT t.*, p.name as player_name, p.position as player_pos,
               ft.name as from_team, tt.name as to_team
        FROM transfers t
        JOIN players p ON t.player_id = p.id
        LEFT JOIN teams ft ON t.from_team_id = ft.id
        JOIN teams tt ON t.to_team_id = tt.id
        WHERE t.requested_by=?
        ORDER BY t.requested_at DESC
    ''', (session['user_id'],)).fetchall()

    # Available players (free agents or for sale from other teams)
    available_players = db.execute('''
        SELECT p.*, t.name as team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE (p.team_id IS NULL OR p.team_id != ?) AND p.price > 0
        ORDER BY p.position, p.name
    ''', (team['id'],)).fetchall()

    return render_template('captain/transfers.html',
                           team=team,
                           my_requests=my_requests,
                           available_players=available_players)


@captain_bp.route('/transfers/request/<int:player_id>', methods=['POST'])
@captain_required
def request_transfer(player_id):
    """Submit a transfer request to buy a player"""
    db = get_db()
    team = get_captain_team()

    player = db.execute('SELECT * FROM players WHERE id=?', (player_id,)).fetchone()
    if not player:
        flash('Player not found.', 'danger')
        return redirect(url_for('captain.transfers'))

    # Cannot buy your own player
    if player['team_id'] == team['id']:
        flash('This player is already in your squad!', 'danger')
        return redirect(url_for('captain.transfers'))

    # Check for duplicate pending request
    existing = db.execute('''
        SELECT id FROM transfers
        WHERE player_id=? AND to_team_id=? AND status='pending'
    ''', (player_id, team['id'])).fetchone()
    if existing:
        flash('You already have a pending request for this player.', 'warning')
        return redirect(url_for('captain.transfers'))

    fee = player['price']
    if fee <= 0:
        flash('This player is not available for transfer.', 'danger')
        return redirect(url_for('captain.transfers'))

    db.execute('''
        INSERT INTO transfers (player_id, from_team_id, to_team_id, fee, requested_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (player_id, player['team_id'], team['id'], fee, session['user_id']))
    db.execute('COMMIT')

    flash(f'Transfer request for {player["name"]} submitted! Awaiting admin approval.', 'success')
    return redirect(url_for('captain.transfers'))


@captain_bp.route('/transfers/sell/<int:player_id>', methods=['POST'])
@captain_required
def list_for_sale(player_id):
    """List a player for sale by setting their price"""
    db = get_db()
    team = get_captain_team()

    player = db.execute(
        'SELECT * FROM players WHERE id=? AND team_id=?',
        (player_id, team['id'])
    ).fetchone()
    if not player:
        flash('Player not in your squad.', 'danger')
        return redirect(url_for('captain.squad'))

    price = float(request.form.get('price', 0))
    db.execute('UPDATE players SET price=? WHERE id=?', (price, player_id))
    db.execute('COMMIT')
    flash(f'{player["name"]} listed for £{price:,.0f}', 'success')
    return redirect(url_for('captain.squad'))


# ─────────────────────────────────────────────────────────────────────────────
# LINEUPS
# ─────────────────────────────────────────────────────────────────────────────

@captain_bp.route('/lineups')
@captain_required
def lineups():
    """View upcoming matches and submit lineups"""
    db = get_db()
    team = get_captain_team()
    team_id = team['id']

    upcoming = db.execute('''
        SELECT m.*,
               ht.name as home_name, at.name as away_name
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE (m.home_team_id=? OR m.away_team_id=?) AND m.status='scheduled'
        ORDER BY m.match_date ASC
    ''', (team_id, team_id)).fetchall()

    return render_template('captain/lineups.html', team=team, upcoming=upcoming)


@captain_bp.route('/lineups/<int:match_id>', methods=['GET', 'POST'])
@captain_required
def submit_lineup(match_id):
    """Submit lineup for a specific match"""
    db = get_db()
    team = get_captain_team()
    team_id = team['id']

    match = db.execute('SELECT * FROM matches WHERE id=?', (match_id,)).fetchone()
    if not match:
        flash('Match not found.', 'danger')
        return redirect(url_for('captain.lineups'))

    # Verify this team is in this match
    if match['home_team_id'] != team_id and match['away_team_id'] != team_id:
        flash('Your team is not in this match.', 'danger')
        return redirect(url_for('captain.lineups'))

    if request.method == 'POST':
        formation   = request.form.get('formation', '4-3-3')
        starter_ids = request.form.getlist('starters')
        sub_ids     = request.form.getlist('subs')

        # pitch positions: starter_pos_<player_id> = "row,col,slot"
        # Clear previous lineup
        db.execute('DELETE FROM lineups WHERE match_id=? AND team_id=?', (match_id, team_id))

        for pid in starter_ids:
            pos_key = f'starter_pos_{pid}'
            pos_val = request.form.get(pos_key, '0,0,0')
            parts   = pos_val.split(',')
            row = int(parts[0]) if len(parts) > 0 else 0
            col = int(parts[1]) if len(parts) > 1 else 0
            slot= int(parts[2]) if len(parts) > 2 else 0
            db.execute('''
                INSERT INTO lineups (match_id, team_id, player_id, is_starter, formation, pitch_row, pitch_col, shirt_slot)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?)
            ''', (match_id, team_id, int(pid), formation, row, col, slot))

        for pid in sub_ids:
            db.execute('''
                INSERT INTO lineups (match_id, team_id, player_id, is_starter, formation, pitch_row, pitch_col, shirt_slot)
                VALUES (?, ?, ?, 0, ?, 0, 0, 0)
            ''', (match_id, team_id, int(pid), formation))

        db.execute('COMMIT')
        flash('Lineup submitted successfully!', 'success')
        return redirect(url_for('captain.lineups'))

    # Load squad and existing lineup
    players = db.execute(
        'SELECT * FROM players WHERE team_id=? ORDER BY position, name',
        (team_id,)
    ).fetchall()

    existing_lineup = db.execute(
        'SELECT * FROM lineups WHERE match_id=? AND team_id=?',
        (match_id, team_id)
    ).fetchall()

    starter_ids = {l['player_id'] for l in existing_lineup if l['is_starter']}
    sub_ids     = {l['player_id'] for l in existing_lineup if not l['is_starter']}
    saved_formation = existing_lineup[0]['formation'] if existing_lineup else '4-3-3'
    positions = {l['player_id']: f"{l['pitch_row']},{l['pitch_col']},{l['shirt_slot']}"
                 for l in existing_lineup if l['is_starter']}

    return render_template('captain/lineup_form.html',
                           team=team, match=match, players=players,
                           starter_ids=starter_ids, sub_ids=sub_ids,
                           saved_formation=saved_formation, positions=positions)
