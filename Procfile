{% extends "admin/base_admin.html" %}
{% block title %}{{ action }} Team – Admin{% endblock %}

{% block admin_content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 style="font-family:'Barlow Condensed',sans-serif;color:var(--lime);letter-spacing:2px">
        <i class="bi bi-shield me-2"></i>{{ action }} Team
    </h2>
    <a href="{{ url_for('admin.teams', league=league) }}" class="btn btn-outline-secondary btn-sm">
        <i class="bi bi-arrow-left me-1"></i>Back
    </a>
</div>
<div class="card">
    <div class="card-body p-4">
        <form method="POST">
            <input type="hidden" name="league" value="{{ league }}">
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label">Team Name *</label>
                    <input type="text" name="name" class="form-control"
                           value="{{ team.name if team else '' }}" required placeholder="e.g. Red Dragons FC">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Short Name *</label>
                    <input type="text" name="short_name" class="form-control" maxlength="5"
                           value="{{ team.short_name if team else '' }}" required placeholder="e.g. RDR">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Badge Color</label>
                    <input type="color" name="badge_color" class="form-control form-control-color w-100"
                           value="{{ team.badge_color if team else '#e74c3c' }}">
                </div>
                <div class="col-md-4">
                    <label class="form-label">League *</label>
                    <select name="league" class="form-select">
                        <option value="boys" {% if league == 'boys' %}selected{% endif %}>👦 Boys League</option>
                        <option value="girls" {% if league == 'girls' %}selected{% endif %}>👧 Girls League</option>
                    </select>
                </div>
                <div class="col-md-5">
                    <label class="form-label">Home Ground</label>
                    <input type="text" name="home_ground" class="form-control"
                           value="{{ team.home_ground if team else '' }}" placeholder="e.g. School Sports Field A">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Founded Year</label>
                    <input type="number" name="founded_year" class="form-control"
                           value="{{ team.founded_year if team else '' }}" placeholder="e.g. 2020">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Starting Balance (€)</label>
                    <input type="number" name="balance" class="form-control"
                           value="{{ team.balance if team else 0 }}" min="0" step="100">
                </div>
                {% if not team %}
                <div class="col-12">
                    <hr style="border-color:rgba(0,212,170,0.2)">
                    <h6 style="color:var(--lime)"><i class="bi bi-person-badge me-2"></i>Create Captain Account (Optional)</h6>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Captain Username</label>
                    <input type="text" name="captain_username" class="form-control" placeholder="e.g. captain_dragons">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Captain Password</label>
                    <input type="password" name="captain_password" class="form-control" placeholder="Minimum 6 characters">
                </div>
                {% endif %}
                <div class="col-12 mt-3">
                    <button type="submit" class="btn btn-primary px-5">
                        <i class="bi bi-check-circle me-2"></i>{{ action }} Team
                    </button>
                    <a href="{{ url_for('admin.teams', league=league) }}" class="btn btn-outline-secondary ms-2">Cancel</a>
                </div>
            </div>
        </form>
    </div>
</div>
{% endblock %}
