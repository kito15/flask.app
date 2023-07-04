from flask import Flask, Blueprint, session, request, jsonify
from zoom_authorize import zoom_blueprint
from upload_to_drive import upload_blueprint

# Create Flask app
app = Flask(__name__)
app.secret_key = '@unblinded2018'

# Register blueprints
app.register_blueprint(zoom_blueprint)
app.register_blueprint(upload_blueprint)
