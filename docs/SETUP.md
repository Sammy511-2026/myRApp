# Local Django and MySQL setup

## Requirements

- Python 3.11 (64-bit)
- MySQL Server 8.0.13 or newer
- MySQL Workbench (optional client; it does not include the MySQL Server)

## Create the environment

Run these commands from the `RPNGC` project directory in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Generate a local Django secret and replace the placeholder in `.env`:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Create the MySQL database

Start MySQL Server and create the application database, for example by running
this in a Workbench SQL tab:

```sql
CREATE DATABASE RPNGC CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` in `.env` to
match the MySQL server and account. For anything beyond local development, use
a dedicated database account instead of `root`.

Create the schema from the Django migrations, then create a staff account:

```powershell
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The migrations also seed the PNG province and district reference list. Applicant
province selectors are grouped by region, and the residence district selector
loads districts for the selected province. The reference names are adapted from
the [Open Admin Data PNG administrative divisions dataset](https://github.com/open-admin-data/papua-new-guinea-administrative-divisions)
under CC BY 4.0; the four region assignments are maintained by this project.

The admin workspace separates **Applications** from **Admin settings**.
Submitted applications are reviewed from the Applications list; applicant
details, documents, eligibility, screening history, interviews, test attempts,
and final selection are linked to the application. Use Admin settings to
manage users, recruitment cycles, tests, questions, and location reference data.

## Applicant REST API

The versioned Django REST Framework API is available under `/api/v1/`. It uses
the existing Django session login; API requests must come from an authenticated
applicant. Session-authenticated `POST`, `PUT`, and `PATCH` requests must include
a valid CSRF token. Staff accounts and anonymous requests cannot access these
applicant endpoints.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/cycles/` | List active recruitment cycles |
| `GET`, `PATCH` | `/api/v1/me/profile/` | Read or update the signed-in applicant's profile |
| `GET` | `/api/v1/me/applications/` | List the signed-in applicant's applications |
| `GET` | `/api/v1/me/applications/<id>/` | Read one of the signed-in applicant's applications |
| `GET` | `/api/v1/me/notifications/` | List the signed-in applicant's notifications |
| `GET`, `PATCH` | `/api/v1/me/notifications/<id>/` | Read a notification or update its `is_read` field |
| `POST` | `/api/v1/me/notifications/read-all/` | Mark the signed-in applicant's unread notifications as read |

Applications and recruitment cycles are read-only through this API. Application
creation and submission remain in the existing web form workflow. The API does
not expose document file uploads or staff screening/selection operations.

MySQL Workbench can connect to this same server and inspect the `RPNGC` schema.
Keep Django migrations as the schema source of truth; do not separately edit
application tables in Workbench. Use Workbench's reverse-engineering/export
features if you need a SQL snapshot of the migrated schema.

The existing case-insensitive NID constraint is conditional (it excludes
blank values), which MySQL does not enforce as a partial unique index. Resolve
that constraint for the chosen MySQL version before relying on database-level
NID uniqueness.

## Existing database archive

`database/legacy_postgres.dump` is a PostgreSQL custom-format backup, not a
MySQL-compatible `.sql` script. MySQL Workbench cannot import it. The new
MySQL schema should be created with `manage.py migrate`. To carry old records
across, first restore the archive into a PostgreSQL server with `pg_restore`,
then perform a separately planned data migration into MySQL.

## Rebuilding generated files

Applicant uploads in `media/` and collected static files in `static_root/` are
runtime/generated data and are excluded from version control. Static source
assets remain in `static/` and `recruitment/static/`. Recreate collected static
files when needed with:

```powershell
python manage.py collectstatic
```
