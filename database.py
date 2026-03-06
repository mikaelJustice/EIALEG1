{% extends "admin/base_admin.html" %}
{% block title %}Users – Admin{% endblock %}

{% block admin_content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 style="font-family:'Barlow Condensed',sans-serif;color:var(--lime);letter-spacing:2px">
        <i class="bi bi-people-fill me-3"></i>Users
    </h2>
    <a href="{{ url_for('admin.add_user') }}" class="btn btn-primary">
        <i class="bi bi-person-plus me-2"></i>Add User
    </a>
</div>

<div class="card">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table mb-0">
                <thead>
                    <tr>
                        <th>Username</th><th>Role</th><th>Team</th><th>Created</th><th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for user in users %}
                    <tr>
                        <td class="fw-semibold text-white">
                            <i class="bi bi-person-circle me-2 text-muted"></i>{{ user.username }}
                        </td>
                        <td>
                            <span class="badge {% if user.role == 'admin' %}bg-danger{% else %}bg-primary{% endif %}">
                                {{ user.role }}
                            </span>
                        </td>
                        <td class="text-muted">{{ user.team_name or '–' }}</td>
                        <td class="text-muted small">{{ user.created_at|fmtdt|truncate(10,True,"") }}</td>
                        <td>
                            {% if user.id != session.user_id %}
                            <form method="POST" action="{{ url_for('admin.delete_user', user_id=user.id) }}"
                                  class="d-inline"
                                  onsubmit="return confirm('Delete user {{ user.username }}?')">
                                <button class="btn btn-sm btn-outline-danger py-0 px-2">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </form>
                            {% else %}
                            <span class="text-muted small">(you)</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
