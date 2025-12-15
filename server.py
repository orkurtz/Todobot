"""
Unified entry point to run the Flask web server and the background scheduler
in a single process. We create the app with process_role='worker' so the
scheduler initializes while all blueprints/routes remain available.
"""

import os
from src.app import create_app

# Create Flask application with scheduler enabled
app = create_app(process_role='worker')


if __name__ == "__main__":
    # Development-only: production should run via gunicorn
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

