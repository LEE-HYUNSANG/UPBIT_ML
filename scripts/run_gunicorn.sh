#!/bin/bash
# Run gunicorn with eventlet worker
exec gunicorn -k eventlet -w 1 -b 0.0.0.0:8000 app:app
