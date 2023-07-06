from celery import Celery
import os

# Configure Celery
celery = Celery('celery_test', broker=os.getenv('REDIS_URL'), backend=os.getenv('REDIS_URL'))
celery.conf.update(
    broker_user=os.getenv('REDISUSER'),
    broker_password=os.getenv('REDISPASSWORD')
)

# Define a test task
@celery.task
def test_task():
    return 'Celery test task executed successfully!'
