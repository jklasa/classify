from flask import Flask, request, redirect, g, render_template, url_for
from flask_bootstrap import Bootstrap
from spotify_api import *

app = Flask(__name__)
Bootstrap(app)

# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 8080
REDIRECT_URI = "{}:{}".format(CLIENT_SIDE_URL, PORT)


@app.route("/")
def login():
    # Auth Step 1: Authorization using the login.html page
    auth_url = get_auth_url(REDIRECT_URI + "/tokenrecv")
    return render_template("login.html", login_url=auth_url)

@app.route("/tokenrecv")
def tokenrecv():
    # Auth Step 4 and 5: Requests refresh and access tokens
    auth_token = request.args['code']
    response_data = get_access_tokens(auth_token, REDIRECT_URI + "/tokenrecv")
    
    if 'error' in response_data:
        return redirect(url_for("error") + "?error={}&desc={}".format(response_data['error'], response_data['error_description']))

    access_token = response_data["access_token"]
    #refresh_token = response_data["refresh_token"]
    #token_type = response_data["token_type"]
    #expires_in = response_data["expires_in"]

    return redirect(url_for("playlists") + "?token=" + access_token, 302)


@app.route("/playlists")
def playlists():
    # Auth Step 6: Use the access token to access Spotify API
    access_token = request.args['token']
    authorization_header = {"Authorization":"Bearer {}".format(access_token)}

    # Get profile data
    profile_data = get_profile(authorization_header)
    
    # Get user playlist data
    playlist_data = get_playlists(authorization_header)
    
    # Display playlist data
    return render_template("playlists.html", playlists=playlist_data["items"])


@app.route("/tracks")
def tracks():
    print(request.args['id'])

@app.route("/error")
def error():
    error = request.args['error']
    desc = request.args['desc']

    return render_template("error.html", error=error, description=desc)

if __name__ == "__main__":
    app.run(debug=True,port=PORT)
