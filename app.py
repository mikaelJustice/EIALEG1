from flask import Flask, redirect, url_for, send_from_directory
from config import Config
from database import init_db
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.captain import captain_bp
from routes.public import public_bp
import os

app = Flask(__name__)
app.config.from_object(Config)

# Ensure folders exist
os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'news'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'players'), exist_ok=True)

# Serve uploaded files
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Initialize database
with app.app_context():
    init_db(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(captain_bp, url_prefix='/captain')
app.register_blueprint(public_bp)

# Jinja2 helpers
app.jinja_env.filters['enumerate'] = enumerate
app.jinja_env.globals['enumerate'] = enumerate

def format_dt(value):
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d %H:%M')
    return str(value)[:16]

app.jinja_env.filters['fmtdt'] = format_dt

@app.route('/')
def index():
    return redirect(url_for('public.home'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
