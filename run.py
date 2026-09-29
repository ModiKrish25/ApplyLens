import os

from app import create_app, db

app = create_app()


@app.cli.command("init-db")
def init_db():
    """Create all database tables."""
    db.create_all()
    print("Database initialized.")


if __name__ == "__main__":
    # Bind to 0.0.0.0:$PORT so the app is reachable when deployed; $PORT is
    # provided by the hosting platform. Defaults keep local dev unchanged.
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
