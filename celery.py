import Celery
import os

app = Celery('your_app_name', broker=os.getenv('REDIS_URL'), backend=os.getenv('REDIS_URL'))
app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    task_routes={
        'your_app_name.tasks.upload_task': {'queue': 'video_queue'}
    },
    worker_prefetch_multiplier=1
)

@shared_task
def test_task():
    return 'Celery worker is working!'
