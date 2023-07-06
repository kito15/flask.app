from flask import Flask, Blueprint, session, request, jsonify
from upload_to_drive import upload_blueprint, store_parameters, retrieve_parameters
from zoom_authorize import zoom_blueprint
from celery import app
from your_app_name import test_task

# Create Flask app
app = Flask(__name__)
app.secret_key = '@unblinded2018'

# Register blueprints
app.register_blueprint(upload_blueprint)
app.register_blueprint(zoom_blueprint)

@app.route('/test', methods=['GET', 'POST'])
def test():
    if request.method == "GET":
        return jsonify({"response": "GET"})
    elif request.method == "POST":
        try:
            data = request.get_json(force=True)
            accountName = data.get('accountName')
            email=data.get('email')

            results=store_parameters(accountName,email)
            print(retrieve_parameters())

            print(request.args.get('share_url'))

            result = test_task.delay()
            print(result.get())
            
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)})
