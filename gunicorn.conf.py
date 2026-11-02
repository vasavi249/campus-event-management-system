import os

# Render sets the PORT environment variable (default: 10000)
port = os.environ.get("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Concurrency and timeout configurations
workers = int(os.environ.get("WEB_CONCURRENCY", 1))
timeout = 120

# Stream logs directly to stdout/stderr
accesslog = "-"
errorlog = "-"
