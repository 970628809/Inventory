import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "inventory_app"))

from inventory_app.app import app


if __name__ == "__main__":
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "5001"))
    debug = os.getenv("FLASK_ENV", "development") != "production"
    app.run(host=host, port=port, debug=debug)
