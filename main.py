import rq
from rq import Queue
from rq_scheduler import Scheduler
import redis
from datetime import datetime, timedelta
from flask import Flask, Blueprint, session, request, jsonify
from upload_to_drive import upload_blueprint
from zoom_authorize import zoom_blueprint

# Create Flask app
app = Flask(__name__)
app.secret_key = '@unblinded2018'
q = Queue(connection=redis.from_url('redis://default:XqJamtL8Koq8Vvo3VdZj@containers-us-west-91.railway.app:6664'))
scheduler = Scheduler(queue=q)

# Register blueprints
app.register_blueprint(zoom_blueprint)
app.register_blueprint(upload_blueprint)
