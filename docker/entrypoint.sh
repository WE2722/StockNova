#!/bin/sh
set -e

python -c "import os,time,psycopg; host=os.getenv('POSTGRES_HOST','db'); port=int(os.getenv('POSTGRES_PORT','5432')); db=os.getenv('POSTGRES_DB','stocknova_db'); user=os.getenv('POSTGRES_USER','stocknova_user'); password=os.getenv('POSTGRES_PASSWORD','stocknova_pass');
for i in range(30):
    try:
        psycopg.connect(host=host, port=port, dbname=db, user=user, password=password, connect_timeout=5).close();
        print('PostgreSQL is ready');
        break
    except Exception as exc:
        print(f'Waiting for PostgreSQL ({i+1}/30): {exc}');
        time.sleep(2)
else:
    raise SystemExit('PostgreSQL is not reachable')"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
