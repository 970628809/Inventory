# Inventory App

A Flask inventory management tool designed for both local use and cloud deployment.

## Local SQLite

```bash
cd /Users/wangyilin/Desktop/Inventory
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="local-dev-secret"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="change-this-password"
python inventory_app/init_db.py

python app.py
```

Open `http://127.0.0.1:5001/` in your browser and log in with the admin account.

If `DATABASE_URL` is not set, the app uses the local SQLite database at `inventory_app/inventory.db`.

## Cloud PostgreSQL

Set these environment variables in your cloud service:

```bash
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
SECRET_KEY=long-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong-admin-password
```

Production start command:

```bash
gunicorn app:app
```

On first startup with an empty PostgreSQL database, the app automatically creates the required tables.
If `ADMIN_USERNAME` and `ADMIN_PASSWORD` are set, it also creates the initial admin user.
For normal deployment, you do not need to run `init_db.py` manually.

If a cloud provider gives a `postgres://...` URL, the app converts it to `postgresql://...` for SQLAlchemy.

## Users

Users are stored in the `users` table. Passwords are hashed and are never stored as plain text.

To create the initial admin locally:

```bash
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong-admin-password
python inventory_app/init_db.py
```

To create an optional regular user for testing:

```bash
USER_USERNAME=staff
USER_PASSWORD=staff-password
python inventory_app/init_db.py
```

## Roles

Admin users can:

- Import Excel files
- Export Excel files
- Manage users
- Add and delete reminders

All logged-in users can:

- Edit inventory
- Add new products
- Receive and ship stock
- Start stocktaking, check stock, and apply stock corrections
- Edit and delete recent inventory activity

Regular users can:

- View the dashboard
- View and search inventory
- View stocktaking lists
- View reminders

Users who are not logged in cannot access inventory pages.

## Files Not To Commit

The following files are ignored by `.gitignore`:

- `.env`
- `inventory_app/inventory.db`
- `*.xlsx`, `*.xls`, `*.xlsm`
- `uploads/`
- `exports/`

Do not commit real company data or production Excel files to the repository.
