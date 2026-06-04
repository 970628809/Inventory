import runpy
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENTRY = os.path.join(BASE_DIR, "inventory_app", "init_db.py")
runpy.run_path(ENTRY, run_name="__main__")
