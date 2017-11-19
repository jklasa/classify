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
GET_PROFILE_ENDPOINT = SPOTIFY_API_ENDPOINT + "/me"
GET_PLAYLISTS_ENDPOINT = SPOTIFY_API_ENDPOINT + "/me/playlists"

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
    url = GET_PROFILE_ENDPOINT
    return get_authorized(auth_header, url)

def get_playlists(auth_header):
    url = GET_PLAYLISTS_ENDPOINT
    resp = requests.get(url, headers=auth_header)
    return json.loads(resp.text)

# https://developer.spotify.com/web-api/get-artist/
def get_artist(artist_id):
    url = GET_ARTIST_ENDPOINT.format(id=artist_id)
    resp = requests.get(url)
    return resp.json()


# https://developer.spotify.com/web-api/search-item/
def search_by_artist_name(name):
    myparams = {'type': 'artist'}
    myparams['q'] = name
    resp = requests.get(SEARCH_ENDPOINT, params=myparams)
    return resp.json()


# https://developer.spotify.com/web-api/get-related-artists/
def get_related_artists(artist_id):
    url = RELATED_ARTISTS_ENDPOINT.format(id=artist_id)
    resp = requests.get(url)
    return resp.json()

# https://developer.spotify.com/web-api/get-artists-top-tracks/
def get_artist_top_tracks(artist_id, country='US'):
    url = TOP_TRACKS_ENDPOINT.format(id=artist_id)
    myparams = {'country': country}
    resp = requests.get(url, params=myparams)
    return resp.json()
