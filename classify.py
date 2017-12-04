from flask import Flask, request, redirect, g, render_template, url_for, make_response
from flask_bootstrap import Bootstrap
from flask_mongoengine import MongoEngine
from bson.objectid import ObjectId
from spotify_api import *
from math import ceil
from pymongo import MongoClient
from pymongo.collection import ReturnDocument
import pymongo

app = Flask(__name__)
Bootstrap(app)

client = MongoClient('mongodb://localhost:27017')
db = client['classify']

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

    auth_header = {"Authorization": "Bearer {}".format(access_token)}
    profile_data = get_profile(auth_header)

    if 'error' in profile_data:
        return api_error_handler(profile_data)

    if profile_data['images']:
        avatar = profile_data['images'][0]
    else:
        avatar = None

    profile = {
        "id": profile_data['id'],
        "token": access_token,
        "followers": profile_data['followers']['total'],
        "avatar": avatar,
    }

    entry = db.profiles.find_one_and_update(
        {'id': profile_data['id']}, 
        {'$set': profile}, 
        upsert = True,
        return_document=ReturnDocument.AFTER
    )

    resp = make_response(redirect(url_for("playlists") + "?id=" + str(entry['_id']), 302))
    resp.set_cookie('token', access_token)
    return resp


@app.route("/playlists")
def playlists():
    # Get profile data from database
    user_id = request.args['id']
    if not ObjectId.is_valid(user_id):
        return api_error_handler({
            "error": "invalid id",
            "error_description": "oops. it looks like the url's id is invalid. try restarting"
        })

    profile_data = db.profiles.find_one({ '_id': ObjectId(user_id) })
    if profile_data is None:
        return api_error_handler({
            "error": "unknown user",
            "error_description": "uh oh. it looks like you might not be logged in. try logging in again"
        })

    # Verify that the client side token is equal to the database's token
    client_token = request.cookies.get('token')
    access_token = profile_data['token']
    if client_token != access_token:
        return api_error_handler({
            "error": "unauthorized access",
            "error_description": "we were unable to authenticate the account properly"
        })

    authorization_header = {"Authorization": "Bearer {}".format(access_token)}

    # Get user playlist data
    playlist_data = get_playlists(authorization_header)
 
    if 'error' in playlist_data:
        return api_error_handler(playlist_data)
   
    # Display playlist data
    resp = make_response(render_template("playlists.html",
                                         user_id=user_id,
                                         profile=profile_data,
                                         playlists=playlist_data["items"]))
    resp.set_cookie('token', access_token)
    return resp


@app.route("/tracks")
def tracks():
    # Get profile data from database
    user_id = request.args['id']
    if not ObjectId.is_valid(user_id):
        return api_error_handler({
            "error": "invalid id",
            "error_description": "oops. it looks like the url's id is invalid. try restarting"
        })

    profile_data = db.profiles.find_one({ '_id': ObjectId(user_id) })
    if profile_data is None:
        return api_error_handler({
            "error": "unknown user",
            "error_description": "uh oh. it looks like you might not be logged in. try logging in again"
        })

    # Verify that the client side token is equal to the database's token
    client_token = request.cookies.get('token')
    access_token = profile_data['token']
    if client_token != access_token:
        return api_error_handler({
            "error": "unauthorized access",
            "error_description": "we were unable to authenticate the account properly"
        })

    authorization_header = {"Authorization": "Bearer {}".format(access_token)}

    # Get playlist data
    playlist_id = request.args['playlist']
    owner_id = request.args['owner']
    playlist_data = get_playlist(authorization_header, owner_id, playlist_id)

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
        stats[feat]['values'].append(track['track']['popularity'] / 100.0)
        stats[feat]['measures']['avg'] += track['track']['popularity']

        if first or track['track']['popularity'] > stats[feat]['measures']['max']:
            stats[feat]['measures']['max'] = track['track']['popularity']

        if first or track['track']['popularity'] < stats[feat]['measures']['min']:
            stats[feat]['measures']['min'] = track['track']['popularity']

        if first:
            first = False

    stats[feat]['measures']['avg'] /= stats['num_tracks']['val']
    stats[feat]['measures']['avg'] = round_float(stats[feat]['measures']['avg'])
    for measure in stats[feat]['measures']:
        stats[feat]['measures'][measure] /= 100.0

    resp = make_response(render_template("tracks.html",
                                         profile=profile_data,
                                         playlist=playlist_data,
                                         stats=stats))
    resp.set_cookie('token', access_token)
    return resp


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
