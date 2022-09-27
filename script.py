#export SPOTIFYTOKEN={spotify web api}, SPOTIFYID in os;

import os
import json
import requests
import youtube_dl
import urllib.parse
import googleapiclient.errors
import googleapiclient.discovery
import google_auth_oauthlib.flow

class Playlist(object):

    def __init__(self, id, title):
        self.id = id
        self.title = title

class PlaylistData(object):
    
    def __init__(self, artist, track):
        self.artist = artist
        self.track = track

class YoutubeClientAccess(object):

    def __init__(self, credentialsLocation):
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = credentialsLocation
        
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        credentials = flow.run_console()
        youtube = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)

        self.youtube = youtube

    def getPlaylist(self):
        request = self.youtube.playlists().list(part = "id, snippet", maxResults = 20, mine = True)
        get = request.execute()

        playlists = [Playlist(item["id"], item["snippet"]["title"]) for item in get["items"]]

        return playlists

    def getPlaylistMusic(self, PlaylistId):
        music = []
        request = self.youtube.playlistItems().list(playlistId = PlaylistId, part = "id, snippet", maxResults = 20)
        get = request.execute()
        
        for item in get["items"]:
            videoId = item["snippet"]["resourceId"]["videoId"]
            artist, track =  self.getPlaylistMusicData(videoId)
            if artist and track:
                music.append(PlaylistData(artist, track))

        return music

    def getPlaylistMusicData(self, videoId):
        url = f"https://www.youtube.com/watch?v={videoId}"
        video = youtube_dl.YoutubeDL({}).extract_info(url, download = False)
        artist = video["uploader"]
        track = video["title"]

        return artist, track

class SpotifyClientAccess(object):

    def __init__(self, token):
        self.token = token

    def createPlaylist(self):
        request = json.dumps({"name": "Youtube Music", "description": "Music imported from Youtube", "public": True})
        get = f"https://api.spotify.com/v1/users/{os.getenv('SPOTIFYID')}/playlists"
        response = requests.post(get, data = request, headers = {"Content-Type":  "application/json", "Authorization": f"Bearer {self.token}"})
        playlistJSON = response.json()

        return playlistJSON["id"]

    def searchMusic(self, artist, track):
        request = urllib.parse.quote(f"{artist} {track}")
        url = f"https://api.spotify.com/v1/search?q={request}&type=track"
        get = requests.get(url, headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"})
        responseJSON = get.json()
        music = responseJSON["tracks"]["items"]

        if music:
            return music[0]["id"]

    def addMusic(self, create, uri):
        id = "".join(uri)
        url = f"https://api.spotify.com/v1/playlists/{create}/tracks?uris={id}"
        response = requests.put(url, headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"})
        
        return response.ok

def main():
    youtubeClient = YoutubeClientAccess("clientCredentials.json")
    spotifyClient = SpotifyClientAccess(os.getenv('SPOTIFYTOKEN'))
    playlists = youtubeClient.getPlaylist()

    for i, playlist in enumerate(playlists):
        print(f"{i}: {playlist.title}")

    userInput = int(input("enter playlist: "))
    selectedPlaylist = playlists[userInput]
    print(f"loading {selectedPlaylist.title}...")

    songs = youtubeClient.getPlaylistMusic(selectedPlaylist.id)
    print(f"searching for songs in {selectedPlaylist.title}...")

    uri = []
    create = spotifyClient.createPlaylist()
    for song in songs:
        spotifyId = spotifyClient.searchMusic(song.artist, song.track)
        if spotifyId:
            uri = uri + ["spotify%3Atrack%3A"+spotifyId+"%2C"]

    uri[-1] = uri[-1][:-3]
    print(f"adding songs to playlist...")
    spotifyClient.addMusic(create, uri)
    print("success!")

main()
