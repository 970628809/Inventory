import runpy
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "inventory_app"))
ENTRY = os.path.join(BASE_DIR, "inventory_app", "init_db.py")
runpy.run_path(ENTRY, run_name="__main__")
