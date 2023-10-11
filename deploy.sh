#!/usr/bin/env sh

echo "Starting up web server in daemon mode..."
gunicorn conf.wsgi --capture-output --log-level info --workers 4 --enable-stdio-inheritance --daemon


echo "Starting up Huey..."
python manage.py run_huey