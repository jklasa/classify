import flask
from flask import Flask, request, redirect, g, render_template, url_for, make_response
from flask_bootstrap import Bootstrap
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
CLIENT_SIDE_URL = "http://18.216.149.158"
PORT = 80
#REDIRECT_URI = "{}:{}".format(CLIENT_SIDE_URL, PORT)
REDIRECT_URI = CLIENT_SIDE_URL


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

    if profile_data['display_name'] != 'null':
        username = profile_data['display_name']
    else:
	username = profile_data['id']

    profile = {
        "profile": {
	    "name": username,
            "followers": profile_data['followers']['total'],
            "avatar": avatar
        },
        "token": access_token
    }

    entry = db.users.find_one_and_update(
        {'id': profile_data['id']}, 
        {'$set': profile}, 
        upsert = True,
        return_document=ReturnDocument.AFTER
    )

    resp = make_response(redirect(url_for("playlists") + "?id=" + str(entry['_id']), 303))
    resp.set_cookie('token', access_token)
    return resp


@app.route("/playlists")
def playlists():
    # Get user data from database
    user_id = request.args['id']
    if not ObjectId.is_valid(user_id):
        return api_error_handler({
            "error": "invalid id",
            "error_description": "oops. it looks like the url's id is invalid. try restarting"
        })

    user = db.users.find_one({ '_id': ObjectId(user_id) })
    if user is None:
        return api_error_handler({
            "error": "unknown user",
            "error_description": "uh oh. it looks like you might not be logged in. try logging in again"
        })

    # Verify that the client side token is equal to the database's token
    client_token = request.cookies.get('token')
    access_token = user['token']
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
                                         profile=user['profile'],
                                         playlists=playlist_data["items"]))
    resp.set_cookie('token', access_token)
    return resp


@app.route('/tracks', methods=['POST', 'GET'])
def tracks():
    # Get user data from database
    user_id = request.args['id']
    if not ObjectId.is_valid(user_id):
        return api_error_handler({
            "error": "invalid id",
            "error_description": "oops. it looks like the url's id is invalid. try restarting"
        })

    user = db.users.find_one({ '_id': ObjectId(user_id) })
    if user is None:
        return api_error_handler({
            "error": "unknown user",
            "error_description": "uh oh. it looks like you might not be logged in. try logging in again"
        })

    # Verify that the client side token is equal to the database's token
    client_token = request.cookies.get('token')
    access_token = user['token']
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
    unfiltered_audio_feats = get_audio_features(authorization_header, playlist_data['tracks'])['audio_features']

    if 'error' in unfiltered_audio_feats:
        return api_error_handler(unfiltered_audio_feats)
 
    # Filter if necessary
    tracks = playlist_data['tracks']['items']
    if flask.request.method == 'POST':
        filter = request.form

        audio_feats = []
        for track in unfiltered_audio_feats:
            for entry in filter:
                if entry != "popularity":
                    add = True
                    
                    vals = filter[entry].split(",")
                    min = float(vals[0])
                    max = float(vals[1])

                    if entry == "duration_ms":
                        min *= 1000
                        max *= 1000

                    if (track[entry] < min or track[entry] > max):
                        add = False
                       
                        for to_remove in tracks:
                            if to_remove['track']['id'] == track['id']:
                                tracks.remove(to_remove)

                        break
    
            if add:
                audio_feats.append(track)
    else:
        audio_feats = unfiltered_audio_feats
 
    # Get statistics from tracks
    stats = get_audio_stats(audio_feats)

    # Popularity comes from track data instead of audio features
    first = True
    feat = 'popularity'
    for track in tracks:
        if flask.request.method == 'POST':
            vals = request.form['popularity'].split(",")
            if (track['track']['popularity'] < float(vals[0]) * 100 or 
                track['track']['popularity'] > float(vals[1]) * 100):

                tracks.remove(track)
                continue

        stats[feat]['values'].append(track['track']['popularity'] / 100.0)
        stats[feat]['measures']['avg'] += track['track']['popularity']

        if first or track['track']['popularity'] > stats[feat]['measures']['max']:
            stats[feat]['measures']['max'] = track['track']['popularity']

        if first or track['track']['popularity'] < stats[feat]['measures']['min']:
            stats[feat]['measures']['min'] = track['track']['popularity']

        if first:
            first = False

    if stats['num_tracks']['val'] != 0:
        stats[feat]['measures']['avg'] /= stats['num_tracks']['val']
        stats[feat]['measures']['avg'] = round_float(stats[feat]['measures']['avg'])
        for measure in stats[feat]['measures']:
            stats[feat]['measures'][measure] /= 100.0
    
    # Save filtered tracks to database
    if flask.request.method == 'POST':
        uris = []
        for track in tracks:
            uris.append("spotify:track:" + track['track']['id'])

        filtered = {
            "uris": uris
        }

        db.users.update_one(
            { '_id': ObjectId(user_id) },
            {'$set': filtered }, 
            upsert = True,
        )

    tracks_url = "/tracks?id={}&playlist={}&owner={}".format(user_id, playlist_id, owner_id)
    playlists_url = "/playlists?id={}".format(user_id)
    save_url = "/save?id={}".format(user_id)

    resp = make_response(render_template("tracks.html",
                                         profile=user['profile'],
                                         playlist=playlist_data,
                                         tracks=tracks,
                                         stats=stats,
                                         tracks_url=tracks_url,
                                         playlists_url=playlists_url,
                                         save_url=save_url,
                                         filtered=(flask.request.method == 'POST')))
    resp.set_cookie('token', access_token)
    return resp


@app.route('/save', methods=['POST'])
def save_user_playlist():
    # Responses
    def create_response(status, info):
        resp = make_response('{"status": "' + status + ', "info: "' + info + '"}')
        resp.headers['Content-Type'] = "application/json"
        return resp

    # Get user data from database
    user_key = request.args['id']
    if not ObjectId.is_valid(user_key):
        return create_response('failure', 'invalid id')

    user = db.users.find_one({ '_id': ObjectId(user_key) })
    if user is None:
        return create_response('failure', 'no user')

    # Verify that the client side token is equal to the database's token
    client_token = request.cookies.get('token')
    access_token = user['token']
    if client_token != access_token:
        return create_response('failure', 'invalid token')

    authorization_header = {"Authorization": "Bearer {}".format(access_token)}
    user_id = user['id']

    # Create new playlist
    data = {
        "name": request.form['name'],
        "description": request.form['description'],
        "public": "false"
    }
    create_resp = create_playlist(authorization_header, user_id, data)

    if 'error' in create_resp:
        print create_resp
        return create_response('failure', 'error creating')

    # Get the tracks from database if available
    if not 'uris' in user:
        return create_response('failure', 'no uris')
    uris = user['uris']

    # Add the tracks to the playlist
    playlist_id = create_resp['id']
    add_resp = add_tracks_to_playlist(authorization_header, user_id, playlist_id, uris)

    if 'error' in add_resp:
        print add_resp
        return create_response('failure', 'error adding')

    return create_response('success', 'created new playlist')

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
    app.run(host='0.0.0.0', debug=False, threaded=True, port=PORT)
