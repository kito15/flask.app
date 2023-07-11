from flask import Flask, Blueprint, session, request, jsonify
from upload_to_drive import upload_blueprint, store_parameters, retrieve_parameters
from zoom_authorize import zoom_blueprint
import requests
import redis
import json

redis_url = "redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759"
redis_client = redis.from_url(redis_url)

# Create Flask app
app = Flask(__name__)
app.secret_key = '@unblinded2018'

# Register blueprints
app.register_blueprint(zoom_blueprint)
app.register_blueprint(upload_blueprint)
    
@app.route('/test', methods=['GET', 'POST'])
def test():
    if request.method == "GET":
        return jsonify({"response": "GET"})
    elif request.method == "POST":
        try:
            data = request.get_json(force=True)
            accountName = data.get('accountName')
            email=data.get('email')

            store_parameters(accountName,email)
            
            stored_folder_urls = redis_client.get("folder_urls")
            if stored_folder_urls is not None:
                folder_urls={}
                folder_urls = json.loads(stored_folder_urls)
                share_url = folder_urls.get(accountName)
                print(share_url)
                
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)})
