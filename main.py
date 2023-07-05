from flask import Flask, Blueprint, session, request, jsonify
from upload_to_drive import upload_blueprint, upload_callback
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
            topic = data.get('topic')
            email=data.get('email')

            response=upload_callback(email,topic)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)})
