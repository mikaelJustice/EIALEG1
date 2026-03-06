{% extends "admin/base_admin.html" %}
{% block title %}{{ action }} News – Admin{% endblock %}

{% block admin_content %}
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:28px;">
    <div>
        <h2 style="font-family:'Barlow Condensed',sans-serif; font-weight:900; font-size:2rem; letter-spacing:0.06em; text-transform:uppercase; color:var(--navy); margin:0;">
            {{ action }} <span style="color:var(--lime);">Article</span>
        </h2>
    </div>
    <a href="{{ url_for('admin.news') }}" style="display:inline-flex; align-items:center; gap:8px; font-family:'Barlow Condensed',sans-serif; font-weight:700; font-size:0.82rem; letter-spacing:0.1em; text-transform:uppercase; padding:9px 18px; border:1.5px solid rgba(26,31,94,0.2); border-radius:3px; color:var(--navy); text-decoration:none; background:white;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
        Back
    </a>
</div>

<form method="POST" enctype="multipart/form-data">
    <div class="row g-4">

        <!-- LEFT: Main content -->
        <div class="col-lg-8">
            <div class="card" style="margin-bottom:20px;">
                <div class="card-header"><span style="color:var(--lime); margin-right:8px;">◉</span>Article Content</div>
                <div style="padding:24px;">
                    <div style="margin-bottom:18px;">
                        <label style="font-family:'Barlow Condensed',sans-serif; font-weight:800; font-size:0.78rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--navy); display:block; margin-bottom:8px;">Headline *</label>
                        <input type="text" name="title" class="form-control" value="{{ article.title if article else '' }}" required placeholder="Write a punchy headline...">
                    </div>
                    <div>
                        <label style="font-family:'Barlow Condensed',sans-serif; font-weight:800; font-size:0.78rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--navy); display:block; margin-bottom:8px;">Article Body *</label>
                        <textarea name="content" class="form-control" rows="12" required placeholder="Write your article here...">{{ article.content if article else '' }}</textarea>
                    </div>
                </div>
            </div>

            <!-- IMAGE UPLOAD -->
            <div class="card">
                <div class="card-header"><span style="color:var(--lime); margin-right:8px;">◉</span>Featured Photo</div>
                <div style="padding:24px;">
                    {% if article and article.image_url %}
                    <!-- Current image preview -->
                    <div style="margin-bottom:18px;">
                        <div style="font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:var(--grey); margin-bottom:8px;">Current Photo</div>
                        <div style="position:relative; display:inline-block;">
                            <img src="{{ article.image_url }}" alt="Current" style="max-height:200px; max-width:100%; border-radius:6px; display:block; object-fit:cover;">
                        </div>
                        <div style="margin-top:10px;">
                            <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer; font-size:0.82rem; color:var(--red); font-weight:600;">
                                <input type="checkbox" name="remove_image" style="width:16px; height:16px;">
                                Remove this photo
                            </label>
                        </div>
                    </div>
                    <div style="font-size:0.78rem; color:var(--grey); margin-bottom:10px;">Upload a new photo to replace it:</div>
                    {% endif %}

                    <!-- Upload input -->
                    <div id="dropZone" style="border:2px dashed rgba(26,31,94,0.2); border-radius:6px; padding:32px; text-align:center; cursor:pointer; transition:all 0.2s; background:rgba(26,31,94,0.02);"
                         onclick="document.getElementById('imageInput').click()"
                         ondragover="event.preventDefault(); this.style.borderColor='var(--lime)'; this.style.background='rgba(184,212,0,0.05)'"
                         ondragleave="this.style.borderColor='rgba(26,31,94,0.2)'; this.style.background='rgba(26,31,94,0.02)'"
                         ondrop="handleDrop(event)">
                        <div id="dropContent">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(26,31,94,0.3)" stroke-width="1.5" style="display:block; margin:0 auto 12px;"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                            <div style="font-family:'Barlow Condensed',sans-serif; font-weight:800; font-size:0.9rem; letter-spacing:0.08em; text-transform:uppercase; color:var(--navy); margin-bottom:4px;">Click or drag a photo here</div>
                            <div style="font-size:0.75rem; color:var(--grey);">JPG, PNG, GIF, WebP · Max 5MB</div>
                        </div>
                        <div id="previewContainer" style="display:none;">
                            <img id="previewImg" style="max-height:180px; max-width:100%; border-radius:4px; object-fit:cover;">
                            <div id="previewName" style="font-size:0.78rem; color:var(--grey); margin-top:8px;"></div>
                        </div>
                    </div>
                    <input type="file" name="image" id="imageInput" accept="image/*" style="display:none;" onchange="previewImage(this)">
                </div>
            </div>
        </div>

        <!-- RIGHT: Settings -->
        <div class="col-lg-4">
            <div class="card" style="margin-bottom:20px;">
                <div class="card-header"><span style="color:var(--lime); margin-right:8px;">◉</span>Settings</div>
                <div style="padding:20px;">
                    <div style="margin-bottom:16px;">
                        <label style="font-family:'Barlow Condensed',sans-serif; font-weight:800; font-size:0.78rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--navy); display:block; margin-bottom:8px;">Category</label>
                        <select name="category" class="form-select">
                            {% for cat in ['general','transfer','match','announcement'] %}
                            <option value="{{ cat }}" {% if article and article.category == cat %}selected{% endif %}>{{ cat|capitalize }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div style="margin-bottom:16px;">
                        <label style="font-family:'Barlow Condensed',sans-serif; font-weight:800; font-size:0.78rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--navy); display:block; margin-bottom:8px;">League</label>
                        <select name="league" class="form-select">
                            <option value="both" {% if not article or article.league == 'both' %}selected{% endif %}>Both Leagues</option>
                            <option value="boys" {% if article and article.league == 'boys' %}selected{% endif %}>Boys Only</option>
                            <option value="girls" {% if article and article.league == 'girls' %}selected{% endif %}>Girls Only</option>
                        </select>
                    </div>
                    <label style="display:flex; align-items:center; gap:10px; cursor:pointer; padding:12px; border-radius:4px; border:1.5px solid rgba(26,31,94,0.1);">
                        <input type="checkbox" name="published" id="published" style="width:18px; height:18px; accent-color:var(--lime);" {% if not article or article.published %}checked{% endif %}>
                        <div>
                            <div style="font-size:0.85rem; font-weight:700; color:var(--navy);">Publish immediately</div>
                            <div style="font-size:0.72rem; color:var(--grey);">Visible to all users</div>
                        </div>
                    </label>
                </div>
            </div>

            <button type="submit" class="btn btn-primary" style="width:100%; padding:14px; font-size:0.95rem; letter-spacing:0.08em; display:flex; align-items:center; justify-content:center; gap:10px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                {{ action }} Article
            </button>
        </div>
    </div>
</form>

<script>
function previewImage(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const reader = new FileReader();
        reader.onload = e => {
            document.getElementById('previewImg').src = e.target.result;
            document.getElementById('previewName').textContent = file.name;
            document.getElementById('dropContent').style.display = 'none';
            document.getElementById('previewContainer').style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
}
function handleDrop(e) {
    e.preventDefault();
    const dt = e.dataTransfer;
    if (dt.files.length) {
        const input = document.getElementById('imageInput');
        // Transfer dropped file to file input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(dt.files[0]);
        input.files = dataTransfer.files;
        previewImage(input);
    }
    e.currentTarget.style.borderColor = 'rgba(26,31,94,0.2)';
    e.currentTarget.style.background = 'rgba(26,31,94,0.02)';
}
</script>
{% endblock %}
