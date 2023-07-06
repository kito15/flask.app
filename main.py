from flask import Flask, Blueprint, session, request, jsonify
from upload_to_drive import upload_blueprint, store_parameters,retrieve_parameters
from zoom_authorize import zoom_blueprint

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

            results=store_parameters(accountName,email)
            share_url = uploadFiles(drive_service)  # Get the share_url from uploadFiles function
            if share_url:
                return jsonify({"share_url": share_url})
            else:
                return jsonify({"error": "Share URL not found"})
        except Exception as e:
            return jsonify({"error": str(e)})
