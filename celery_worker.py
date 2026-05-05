from app import create_app
from app.tasks.celery_app import make_celery
from app.tasks import jobs  # noqa: F401

flask_app = create_app()
celery = make_celery(flask_app)
