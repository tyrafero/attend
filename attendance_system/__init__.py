# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
# Make Celery import optional to allow web service to run without Redis
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except Exception as e:
    print(f"Warning: Celery not available: {e}")
    celery_app = None
    __all__ = ()
