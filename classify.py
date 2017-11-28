from flask import Flask, request, redirect, g, render_template, url_for
from flask_bootstrap import Bootstrap
from spotify_api import *
from math import ceil

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
 
    if 'error' in playlist_data:
        return api_error_handler(playlist_data)
   
    # Display playlist data
    return render_template("playlists.html", playlists=playlist_data["items"])


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

    def round_float(val):
        return ceil(val * 10000.00) / 10000.00

    # Format duration
    def format_duration(millis):
        seconds = (millis / 1000) % 60
        seconds = int(seconds)
        seconds = str(seconds).zfill(2)
        minutes = (millis / (1000 * 60)) % 60
        minutes = int(minutes)
        return "{}:{}".format(minutes, seconds)

    duration = {
        "min": {
            "value": 0,
            "formatted": ""
        },
        "avg": {
            "value": 0,
            "formatted": ""
        },
        "max": {
            "value": 0,
            "formatted": ""
        }
    }

    for measure in duration:
        duration[measure]['value'] = round_float(stats['duration_ms'][measure] / 1000)
        duration[measure]['formatted'] = format_duration(stats['duration_ms'][measure])

    # Pitch notation
    pitches = ['C',
               'C# or D\xe2',
               'D',
               'D# or E\xe2',
               'E',
               'F',
               'F# or G\xe2',
               'G',
               'G# or A\xe2',
               'A',
               'A# or B\xe2',
               'B']

    def format_key(key, mode):
        pitch_idx = int(key)
        
        if mode < 0.5:
            return pitches[pitch_idx] + " minor"
        else:
            return pitches[pitch_idx] + " major"

    key = {
        "min": 0,
        "avg": 0,
        "max": 0
    }

    for measure in key:
        key[measure] = format_key(stats['key'][measure], stats['mode'][measure])

    # Loudness
    loudness = {
        "min": 0,
        "avg": 0,
        "max": 0
    }

    for measure in loudness:
        loudness[measure] = round_float(stats['loudness'][measure])

    # Time signature and tempo
    beats = {
        "min": 0,
        "avg": 0,
        "max": 0
    }

    tempo = {
        "min": 0,
        "avg": 0,
        "max": 0
    }

    for measure in beats:
        beats[measure] = stats['time_signature'][measure]
        tempo[measure] = round_float(stats['tempo'][measure])

    # Number of tracks
    num_tracks = stats['num_tracks']

    # Filter proportions out of stats
    non_proportions = ['duration_ms', 'key', 'loudness', 'mode', 'tempo', 'time_signature', 'num_tracks']
    for non_prop in non_proportions:
        stats.pop(non_prop, None)

    # Popularity
    popularity = {
        "min": 0,
        "avg": 0,
        "max": 0
    }

    first = True
    for track in playlist_data['tracks']['items']:
        popularity['avg'] += track['track']['popularity']

        if first or track['track']['popularity'] > popularity['max']:
            popularity['max'] = track['track']['popularity']

        if first or track['track']['popularity'] < popularity['min']:
            popularity['min'] = track['track']['popularity']

        if first:
            first = False

    popularity['avg'] /= num_tracks
    popularity['avg'] = round_float(popularity['avg'])
    for measure in popularity:
        popularity[measure] /= 100.0
    stats['popularity'] = popularity

    return render_template("tracks.html",
                           playlist=playlist_data,
                           props=stats,
                           duration=duration,
                           key=key,
                           loudness=loudness,
                           beats=beats,
                           tempo=tempo,
                           num_tracks=num_tracks)


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
