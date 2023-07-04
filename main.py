from flask import Flask, Blueprint, session, request, jsonify
from upload_to_drive import upload_blueprint
from zoom_authorize import zoom_blueprint

# Create Flask app
app = Flask(__name__)
app.secret_key = '@unblinded2018'

# Register blueprints
app.register_blueprint(zoom_blueprint)

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
