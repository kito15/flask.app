from your_app_name.tasks import upload_task

# Create an instance of the upload task
task = upload_task.apply_async()

# Get the task ID
task_id = task.id

# You can use the task ID to track the status or retrieve the result later

# Check the task status
status = task.status
print(f"Task ID: {task_id}, Status: {status}")

# Retrieve the task result (if applicable)
result = task.get()
print(f"Task Result: {result}")
