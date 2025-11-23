import os

# Only import Celery if we're running Celery workers, not the web service
if os.environ.get('CELERY_WORKER', 'false').lower() == 'true':
    try:
        from .celery import app as celery_app
        __all__ = ('celery_app',)
    except Exception as e:
        print(f"Warning: Celery not available: {e}")
        celery_app = None
        __all__ = ()
else:
    # Skip Celery for web service
    celery_app = None
    __all__ = ()