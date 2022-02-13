# Recommended by Flask-SocketIO:
# gunicorn --worker-class eventlet -w 1 module:app
# gunicorn -w 1 --threads 100 module:app

# Recommended by Flask-Sock:
# gunicorn -b :5000 --threads 100 module:app
# gunicorn -b :5000 --worker-class eventlet module:app

# Also see:
# https://stackoverflow.com/questions/56157266/how-can-i-use-websocket-transport-and-async-mode-threading-in-flask-socketio-at
# "Here is the long answer. A WebSocket server based on standard threads is in general a bad idea, that is why I have
# never implemented it myself. WebSocket servers are very demanding, because they require a permanent connection with
# each client. If you have 100 connected clients, then you need 100 active connections. In a threaded server, that means
# you need 100 threads all running concurrently, and for a potentially long time. Unfortunately the number of threads
# you can have in a Python process is somewhat limited. You can probably have 100, but 1000 might be a challenge. Pretty
# much all WebSocket implementations use asynchronous servers, because this type of server can easily maintain a high
# number of active connections."

# https://stackoverflow.com/questions/48160535/how-can-i-run-long-tasks-on-google-app-engine-which-uses-gunicorn
# "You can use async worker-class and then you won't need to set the timeout to 20 minutes. The default worker class is
# sync."
# "Use the eventlet async worker (gevent not recommended if using google client libraries)"

# import multiprocessing

# See https://cloud.google.com/appengine/docs/standard/python3/runtime for recommended number of workers by instance
# class
workers = 1  # multiprocessing.cpu_count() * 2 + 1

worker_class = 'eventlet'

# This setting only affects the Gthread worker type, see https://docs.gunicorn.org/en/latest/settings.html#threads
# Also note in the doc: "If you try to use the sync worker type and set the threads setting to more than 1, the gthread
# worker type will be used instead."
# threads = 100
