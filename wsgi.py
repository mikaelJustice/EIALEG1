from app import create_app

app = create_app()
```

Then update your **Start Command** in Render to:
```
gunicorn wsgi:app
