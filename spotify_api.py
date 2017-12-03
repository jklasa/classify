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
        return ceil(val * 10000.00) / 10000.00

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
                stats[feature]['avg'] += track[feature]

                if first or track[feature] > stats[feature]['max']:
                    stats[feature]['max'] = track[feature]

                if first or track[feature] < stats[feature]['min']:
                    stats[feature]['min'] = track[feature]

            addStat(first)
        first = False

    # Special duration handling
    feat = 'duration_ms'
    stats[feat]['avg'] /= 1000
    stats[feat]['min'] = floor(stats[feat]['min'] / 1000.0)
    stats[feat]['max'] = ceil(stats[feat]['max'] / 1000.0)

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

    stats['duration_ms']['avg'] = avg(stats['duration_ms']['avg'])
    stats['key']['avg'] = avg(stats['key']['avg'])
    stats['loudness']['avg'] = avg(stats['loudness']['avg'])
    stats['time_signature']['avg'] = stats['time_signature']['avg'] / stats['num_tracks']['val']
    stats['tempo']['avg'] = avg(stats['tempo']['avg'])

    for measure in stats['key']:
        if measure != 'type':
            stats['key'][measure] = format_key(stats['key'][measure], stats['mode'][measure])
            stats['loudness'][measure] = round_float(stats['loudness'][measure])
            stats['time_signature'][measure] = stats['time_signature'][measure]
            stats['tempo'][measure] = round_float(stats['tempo'][measure])

    # Round proportions
    for feature in stats:
        if stats[feature]['type'] == 'prop':
            stats[feature]['avg'] /= stats['num_tracks']['val']
            stats[feature]['avg'] = round_float(stats[feature]['avg'])

    return stats
