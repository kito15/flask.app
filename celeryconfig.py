# celeryconfig.py

broker_url = 'redis://default:2QDSdWu0b2py954gMfcJ@containers-us-west-82.railway.app:6096'
result_backend = 'redis://default:2QDSdWu0b2py954gMfcJ@containers-us-west-82.railway.app:6096'
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
