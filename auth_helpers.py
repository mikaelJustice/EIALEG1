{% extends "admin/base_admin.html" %}
{% block title %}Players – Admin{% endblock %}

{% block admin_content %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <h2 style="font-family:'Barlow Condensed',sans-serif;color:var(--lime);letter-spacing:2px">
        <i class="bi bi-person-fill me-2"></i>Players
    </h2>
    <a href="{{ url_for('admin.add_player', league=league) }}" class="btn btn-primary btn-sm">
        <i class="bi bi-plus-circle me-1"></i>Add Player
    </a>
</div>

<ul class="nav nav-tabs mb-4" style="border-color:rgba(0,212,170,0.2)">
    <li class="nav-item">
        <a class="nav-link {% if league=='boys' %}active{% endif %}"
           href="{{ url_for('admin.players', league='boys') }}"
           style="{% if league=='boys' %}color:var(--lime);border-color:var(--lime);background:rgba(59,130,246,0.1){% else %}color:rgba(255,255,255,0.6){% endif %}">
            <i class="bi bi-person-fill me-1"></i>Boys League
        </a>
    </li>
    <li class="nav-item">
        <a class="nav-link {% if league=='girls' %}active{% endif %}"
           href="{{ url_for('admin.players', league='girls') }}"
           style="{% if league=='girls' %}color:#f472b6;border-color:#f472b6;background:rgba(236,72,153,0.1){% else %}color:rgba(255,255,255,0.6){% endif %}">
            <i class="bi bi-person-fill me-1"></i>Girls League
        </a>
    </li>
</ul>

<div class="card">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table mb-0">
                <thead>
                    <tr>
                        <th>Player</th><th>Pos</th><th>Team</th>
                        <th class="text-center">Age</th>
                        <th class="text-center">Price</th>
                        <th class="text-center">⚽</th>
                        <th class="text-center">🟨</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in players %}
                    <tr>
                        <td class="fw-semibold text-white">{{ p.name }}</td>
                        <td><span class="badge-position pos-{{ p.position }}">{{ p.position }}</span></td>
                        <td>
                            {% if p.team_name %}
                            <span class="team-badge me-1" style="background:{{ p.team_color }};width:20px;height:20px;font-size:0.6rem">{{ p.team_name[:2] }}</span>
                            <small>{{ p.team_name }}</small>
                            {% else %}<small class="text-muted">Free Agent</small>{% endif %}
                        </td>
                        <td class="text-center text-muted">{{ p.age or '–' }}</td>
                        <td class="text-center" style="color:var(--gold)">
                            {% if p.price > 0 %}€{{ '{:,.0f}'.format(p.price) }}{% else %}–{% endif %}
                        </td>
                        <td class="text-center">{{ p.goals }}</td>
                        <td class="text-center" style="color:var(--gold)">{{ p.yellow_cards }}</td>
                        <td>
                            <a href="{{ url_for('admin.edit_player', player_id=p.id) }}"
                               class="btn btn-sm btn-outline-secondary py-0 px-2 me-1"><i class="bi bi-pencil"></i></a>
                            <form method="POST" action="{{ url_for('admin.delete_player', player_id=p.id) }}"
                                  class="d-inline" onsubmit="return confirm('Delete {{ p.name }}?')">
                                <button class="btn btn-sm btn-outline-danger py-0 px-2"><i class="bi bi-trash"></i></button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="8" class="text-center py-5 text-muted">
                        No {{ league }} league players yet.
                        <a href="{{ url_for('admin.add_player', league=league) }}">Add one</a>.
                    </td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
