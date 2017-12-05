import base64
import json
import requests
import urllib
from math import ceil, floor

# Client keys: must be stored in separate json file
with open('spotify_secret.json') as json_data:
    client = json.load(json_data)
    CLIENT_ID = client['client_id']
    CLIENT_SECRET = client['client_secret']

# Spotify Parameters
SCOPE = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"
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
PLAYLIST_ENDPOINT = SPOTIFY_API_ENDPOINT + "/users/{uid}/playlists/{pid}"
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

def get_playlist(auth_header, user_id, playlist_id):
    url = PLAYLIST_ENDPOINT.format(uid=user_id, pid=playlist_id)
    return get_authorized(auth_header, url)

def get_audio_features(auth_header, tracks_data):
    tids = []
    for track in tracks_data['items']:
        tids.append(track['track']['id'])
    csv_tids = ','.join(tids)

    url = AUDIO_FEATURES_ENDPOINT.format(csv_tids)
    return get_authorized(auth_header, url)

def round_float(val):
        return ceil(val * 10000.0) / 10000.0

def get_audio_stats(audio_feats):
    with open('audio_features.json') as json_data:
        stats = json.load(json_data)

    non_stats = ['type',
                 'id',
                 'uri',
                 'track_href',
                 'analysis_url']

    first = True
    for track in audio_feats:
        stats['num_tracks']['val'] += 1
        for feature in track:
            def addStat(first):
                for non_stat in non_stats:
                    if feature == non_stat:
                        return

                stats[feature]['values'].append(track[feature])
                stats[feature]['measures']['avg'] += track[feature]

                if first or track[feature] > stats[feature]['measures']['max']:
                    stats[feature]['measures']['max'] = track[feature]

                if first or track[feature] < stats[feature]['measures']['min']:
                    stats[feature]['measures']['min'] = track[feature]

            addStat(first)
        first = False

    if stats['num_tracks']['val'] == 0:
        for feat in stats:
            stats[feat]['val'] = 0
        return stats

    # Special duration handling
    feat = 'duration_ms'
    stats[feat]['measures']['avg'] /= 1000
    stats[feat]['measures']['min'] = floor(stats[feat]['measures']['min'] / 1000.0)
    stats[feat]['measures']['max'] = ceil(stats[feat]['measures']['max'] / 1000.0)

    # Special key/mode handling
    pitches = ['C',
               u'C# or D\u266D',
               'D',
               u'D# or E\u266D',
               'E',
               'F',
               u'F# or G\u266D',
               'G',
               u'G# or A\u266D',
               'A',
               u'A# or B\u266D',
               'B']

    def format_key(key, mode):
        pitch_idx = int(key)
        
        if mode < 0.5:
            return pitches[pitch_idx] + " minor"
        else:
            return pitches[pitch_idx] + " major"

    # Combine handling for loudness, key, beats, tempo
    def avg(value):
        return round_float(value / stats['num_tracks']['val'])

    stats['duration_ms']['measures']['avg'] = avg(stats['duration_ms']['measures']['avg'])
    stats['key']['measures']['avg'] = avg(stats['key']['measures']['avg'])
    stats['loudness']['measures']['avg'] = avg(stats['loudness']['measures']['avg'])
    stats['time_signature']['measures']['avg'] = stats['time_signature']['measures']['avg'] / stats['num_tracks']['val']
    stats['tempo']['measures']['avg'] = avg(stats['tempo']['measures']['avg'])

    # Round down and up for mins and maxs
    for feature in stats:
        if (feature != 'num_tracks' and stats[feature]['type'] == 'prop'):
            stats[feature]['measures']['min'] = floor(stats[feature]['measures']['min'] * 100.0) / 100.0
            stats[feature]['measures']['max'] = ceil(stats[feature]['measures']['max'] * 100.0) / 100.0

    stats['tempo']['measures']['min'] = floor(stats['tempo']['measures']['min'])
    stats['tempo']['measures']['max'] = ceil(stats['tempo']['measures']['max'])
    stats['loudness']['measures']['min'] = floor(stats['loudness']['measures']['min'])
    stats['loudness']['measures']['max'] = ceil(stats['loudness']['measures']['max'])

    for measure in stats['key']['measures']:
        stats['key']['measures'][measure] = format_key(stats['key']['measures'][measure], stats['mode']['measures'][measure])

    # Round proportions
    for feature in stats:
        if stats[feature]['type'] == 'prop':
            stats[feature]['measures']['avg'] /= stats['num_tracks']['val']
            stats[feature]['measures']['avg'] = round_float(stats[feature]['measures']['avg'])    

    return stats
