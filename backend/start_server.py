"""Start uvicorn with file-based logging (avoids 'I/O operation on closed file' in background mode)."""
import logging
import sys
import uvicorn

logging.basicConfig(
    filename='/tmp/vitalis_backend.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    filemode='w',
)

# Also capture uvicorn logs
uvicorn_logger = logging.getLogger('uvicorn')
uvicorn_logger.handlers.clear()
file_handler = logging.FileHandler('/tmp/vitalis_backend.log', mode='a')
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
uvicorn_logger.addHandler(file_handler)
uvicorn_logger.propagate = False

if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host='0.0.0.0',
        port=8005,
        reload=False,
        log_config=None,
        access_log=True,
    )
