import base64
import json
import requests
import urllib

# Client keys: must be stored in separate json file
with open('spotify_secret.json') as json_data:
    client = json.load(json_data)
    CLIENT_ID = client['client_id']
    CLIENT_SECRET = client['client_secret']

# Spotify Parameters
SCOPE = "user-library-read playlist-read-private playlist-read-collaborative"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

# Spotify URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
SPOTIFY_API_VERSION = "v1"

# Spotify Endpoints
SPOTIFY_API_ENDPOINT = "{}/{}".format(SPOTIFY_API_BASE_URL, SPOTIFY_API_VERSION)
PROFILE_ENDPOINT = SPOTIFY_API_ENDPOINT + "/me"
PLAYLISTS_ENDPOINT = SPOTIFY_API_ENDPOINT + "/me/playlists"
TRACKS_ENDPOINT = SPOTIFY_API_ENDPOINT + "/users/{uid}/playlists/{pid}/tracks"
AUDIO_FEATURES_ENDPOINT = SPOTIFY_API_ENDPOINT + "/audio-features?ids={}"

def get_auth_url(redirect_uri):
    auth_query_parameters = {
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPE,
        # "state": STATE,
        "show_dialog": SHOW_DIALOG_str,
        "client_id": CLIENT_ID
    }

    url_args = "&".join(["{}={}".format(key,urllib.quote(val)) for key,val in auth_query_parameters.iteritems()])
    return "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)

def get_access_tokens(auth_token, redirect_uri):
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": redirect_uri
    }

    b64enc = base64.b64encode("{}:{}".format(CLIENT_ID, CLIENT_SECRET))
    headers = {"Authorization": "basic {}".format(b64enc)}
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)
    return json.loads(post_request.text)

def get_authorized(auth_header, url):
    resp = requests.get(url, headers=auth_header)
    return json.loads(resp.text)

def get_unauthorized(url):
    resp = requests.get(url)
    return json.loads(resp.text)

def get_profile(auth_header):
    url = PROFILE_ENDPOINT
    return get_authorized(auth_header, url)

def get_playlists(auth_header):
    url = PLAYLISTS_ENDPOINT
    return get_authorized(auth_header, url)

def get_tracks(auth_header, user_id, playlist_id):
    url = TRACKS_ENDPOINT.format(uid=user_id, pid=playlist_id)
    return get_authorized(auth_header, url)

def get_audio_features(auth_header, tracks_data):
    tids = []
    for track in tracks_data['items']:
        tids.append(track['track']['id'])
    csv_tids = ','.join(tids)

    url = AUDIO_FEATURES_ENDPOINT.format(csv_tids)
    return get_authorized(auth_header, url)

def get_audio_stats(audio_feats):
    stats = {
        "acousticness": 0,
        "danceability": 0,
        "duration_ms": 0,
        "energy": 0,
        "key": 0,
        "instrumentalness": 0,
        "liveness": 0,
        "loudness": 0,
        "mode": 0,
        "speechiness": 0,
        "tempo": 0,
        "time_signature": 0,
        "valence": 0,
        "num_tracks": 0
    }

    non_stats = ['type',
                 'id',
                 'uri',
                 'track_href',
                 'analysis_url']

    for track in audio_feats:
        stats['num_tracks'] += 1
        for feature in track:
            def addStat():
                for non_stat in non_stats:
                    if feature == non_stat:
                        return
                stats[feature] += track[feature]
            addStat()

    for feature in stats:
        if feature != 'num_tracks':
            stats[feature] /= stats['num_tracks']

    return stats
