from flask import Flask, request, redirect, g, render_template, url_for
from flask_bootstrap import Bootstrap
from flask_mongoengine import MongoEngine
from spotify_api import *
from math import ceil

app = Flask(__name__)
Bootstrap(app)

app.config['MONGODB_SETTINGS'] = {
    'db': 'classify'
}
db = MongoEngine(app)

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
 
    if 'error' in playlist_data:
        return api_error_handler(playlist_data)
   
    # Display playlist data
    return render_template("playlists.html", profile=profile_data, playlists=playlist_data["items"])


@app.route("/tracks")
def tracks():
    # Auth Step 6: Use the access token to access Spotify API
    access_token = request.args['token']
    authorization_header = {"Authorization": "Bearer {}".format(access_token)}

    # Get playlist data
    user_id = request.args['uid']
    playlist_id = request.args['pid']
    playlist_data = get_playlist(authorization_header, user_id, playlist_id)

    if 'error' in playlist_data:
        return api_error_handler(playlist_data)

    # Get audio features
    audio_feats = get_audio_features(authorization_header, playlist_data['tracks'])['audio_features']

    if 'error' in audio_feats:
        return api_error_handler(audio_feats)

    # Get statistics
    stats = get_audio_stats(audio_feats)

    # Popularity comes from track data instead of audio features
    first = True
    feat = 'popularity'
    for track in playlist_data['tracks']['items']:
        stats[feat]['avg'] += track['track']['popularity']

        if first or track['track']['popularity'] > stats[feat]['max']:
            stats[feat]['max'] = track['track']['popularity']

        if first or track['track']['popularity'] < stats[feat]['min']:
            stats[feat]['min'] = track['track']['popularity']

        if first:
            first = False

    stats[feat]['avg'] /= stats['num_tracks']['val']
    stats[feat]['avg'] = round_float(stats[feat]['avg'])
    for measure in stats[feat]:
        if measure != 'type':
            stats[feat][measure] /= 100.0

    return render_template("tracks.html",
                           playlist=playlist_data,
                           stats=stats)


def api_error_handler(data):
    error = data['error']

    # Authentication error object
    if 'error_description' in data:
        desc = data['error_description']
    else:
        desc = "{}: {}".format(error['status'], error['message'])
        error = "uh oh. we received an error code from spotify"

    return render_template("error.html", error=error, description=desc)


@app.errorhandler(404)
def page_not_found(e):
    error = "uh oh. we've encountered an error"
    desc = "404 not found: the requested URL was not found on this server" 
    return render_template('error.html', error=error, description=desc)

if __name__ == "__main__":
    app.run(debug=True,port=PORT)
