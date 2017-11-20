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
        return api_error_handler(response_data)

    access_token = response_data["access_token"]
    #refresh_token = response_data["refresh_token"]
    #token_type = response_data["token_type"]
    #expires_in = response_data["expires_in"]

    return redirect(url_for("playlists") + "?token=" + access_token, 302)


@app.route("/playlists")
def playlists():
    # Auth Step 6: Use the access token to access Spotify API
    access_token = request.args['token']
    authorization_header = {"Authorization": "Bearer {}".format(access_token)}

    # Get profile data
    profile_data = get_profile(authorization_header)

    if 'error' in profile_data:
        return api_error_handler(profile_data)

    # Get user playlist data
    playlist_data = get_playlists(authorization_header)
    
    # Display playlist data
    return render_template("playlists.html", playlists=playlist_data["items"])


@app.route("/tracks")
def tracks():
    # Auth Step 6: Use the access token to access Spotify API
    access_token = request.args['token']
    authorization_header = {"Authorization": "Bearer {}".format(access_token)}

    # Get tracks from playlist
    user_id = request.args['uid']
    playlist_id = request.args['pid']
    tracks_data = get_tracks(authorization_header, user_id, playlist_id)

    if 'error' in tracks_data:
        return api_error_handler(tracks_data)

    # Get audio features
    audio_feats = get_audio_features(authorization_header, tracks_data)['audio_features']

    if 'error' in audio_feats:
        return api_error_handler(audio_feats)

    # Get statistics
    stats = get_audio_stats(audio_feats)

    return render_template("tracks.html", tracks=tracks_data['items'], stats=stats);

@app.route("/error")
def error():
    error = request.args['error']
    desc = request.args['desc']

    return render_template("error.html", error=error, description=desc)

def api_error_handler(data):
    error = data['error']

    # Authentication error object
    if 'error_description' in data:
        desc = data['error_description']
        err_args = "?error={}&desc={}".format(error, desc)
    else:
        desc = "{}: {}".format(error['status'], error['message'])
        error = "uh oh. we received an error code from spotify"

    err_args = "?error={}&desc={}".format(error, desc)
    return redirect(url_for("error") + err_args)


if __name__ == "__main__":
    app.run(debug=True,port=PORT)
