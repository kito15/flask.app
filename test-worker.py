from your_app_name.tasks import upload_task

# Create an instance of the upload task
task = upload_task.apply_async()

result = test_task.delay()
print(result.get())
