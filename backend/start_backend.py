"""
Start the backend with file-based logging.
Uses logging.FileHandler instead of replacing sys.stdout/sys.stderr
to avoid 'I/O operation on closed file' errors when Uvicorn reloader
spawns/kills child processes.
"""
import logging
import sys
import os

# --- Configure root logger with file + console handlers ---
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'vitalis.log')

# Capture the ORIGINAL stdout/stderr BEFORE any redirection
_original_stdout = sys.stdout
_original_stderr = sys.stderr

# Remove any pre-existing handlers
root_logger = logging.getLogger()
root_logger.handlers.clear()

# File handler – write all logs here
file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
file_handler.setLevel(logging.INFO)
root_logger.addHandler(file_handler)

# Console handler – keep terminal output working
console_handler = logging.StreamHandler(_original_stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%H:%M:%S'))
console_handler.setLevel(logging.INFO)
root_logger.addHandler(console_handler)
root_logger.setLevel(logging.INFO)

logger = logging.getLogger('startup')
logger.info('Starting ATLAS backend server...')
logger.info(f'Logs also written to: {log_file}')

# Ensure backend dir is in path
sys.path.insert(0, log_dir)

import uvicorn
from app.main import app

if __name__ == '__main__':
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8005,
        log_level='info',
        reload=False,
    )
