# gunicorn --worker-class eventlet --workers 3 -b :$PORT main:app

import multiprocessing

worker_class = 'eventlet'
workers = 1  # multiprocessing.cpu_count() * 2 + 1
