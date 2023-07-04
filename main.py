from flask import Flask, redirect, request
from google_auth_oauthlib.flow import Flow

# Replace with your Railway.app domain and redirect URI
RAILWAY_DOMAIN = "https://flask-production-d5a3.up.railway.app"
REDIRECT_URI = f"{RAILWAY_DOMAIN}/callback"

# Replace with your client ID and secret from the Google Cloud Console
CLIENT_ID = "21876034997-mjfsr5ojhnrmspao3ud5er3babhtvn0s.apps.googleusercontent.com"
CLIENT_SECRET = "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"
SCOPES = ['openid', 'email', 'profile']

app = Flask(__name__)

@app.route('/')
def index():
    authorization_url, state = create_authorization_url()
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    flow = create_flow()
    flow.fetch_token(authorization_response=request.url)

    # Retrieve the user's email and profile information
    credentials = flow.credentials
    userinfo = credentials.id_token['email']
    profile = credentials.id_token['sub']

    # Perform further actions with the user's email and profile
    # ...

    return f"Authenticated successfully! Email: {userinfo}, Profile: {profile}"

def create_authorization_url():
    flow = create_flow()
    authorization_url, state = flow.authorization_url()
    return authorization_url, state

def create_flow():
    flow = Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.client_type = 'web'
    flow.redirect_uri = REDIRECT_URI
    return flow
