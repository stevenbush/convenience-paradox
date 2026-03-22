"""run.py — Flask Development Server Entry Point

Usage:
    conda activate convenience-paradox
    python run.py

Or with Flask CLI:
    export FLASK_APP=run.py
    flask run --port=5000

The Flask app is created by the factory in api/app.py.
All routes are registered in api/routes.py.
The dashboard is then accessible at http://127.0.0.1:5000
"""

from api.app import create_app

app = create_app()

if __name__ == "__main__":
    # Debug mode enables auto-reloading on code changes.
    # Set host="0.0.0.0" to allow LAN access from another device.
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=True,
    )
