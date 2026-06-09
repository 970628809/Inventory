# Inventory App Package

This directory contains the Flask application code for the inventory management tool.

## Purpose

- Support inventory work that was previously handled with Excel files
- Run locally with SQLite during development
- Run in the cloud with PostgreSQL in production
- Protect inventory pages with login
- Separate admin users from regular users
- Keep the app simple, without complex charts or multi-store features

## Structure

- `app.py` - Main Flask application
- `db.py` - Database connection helper for SQLite and PostgreSQL
- `init_db.py` - Database table and user initialization script
- `requirements.txt` - Python package list for this package
- `templates/` - HTML templates
- `static/` - CSS and frontend assets
- `data/sample_products.csv` - Sample CSV data for local development only

## Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Database

For local development, leave `DATABASE_URL` unset and the app will use SQLite:

```bash
python inventory_app/init_db.py
```

To reset local development data only:

```bash
python inventory_app/init_db.py --reset
```

For cloud deployment, set `DATABASE_URL` to a PostgreSQL connection string.

## Start The App

Local development:

```bash
python app.py
```

Production:

```bash
gunicorn app:app
```

## Browser

- Dashboard: `http://127.0.0.1:5001/`
- Inventory: `http://127.0.0.1:5001/inventory`

If port `5001` is already in use, start with another port:

```bash
APP_PORT=5002 python app.py
```

## Notes

- The dashboard shows zero-stock, low-stock, and inactive-stock reminders
- Inventory search supports product name, SKU, category, and location
- Admin users can import Excel files, edit inventory, and export data
- Regular users can view inventory, search, and view reminders
