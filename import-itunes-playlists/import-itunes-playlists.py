#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Description:  Sync Plex playlists to shared users.
# Author:       /u/SwiftPanda16
# Requires:     plexapi, requests, xmltodict

import pickle
import string
import requests
import xmltodict
from plexapi.server import PlexServer
from libpytunes import Library
from difflib import SequenceMatcher
from joblib import Parallel, delayed
import multiprocessing

# Import config. variables
from config import *

## CODE BELOW ##
def similar(a: string, b: string) -> float:
    return SequenceMatcher(None, a, b).ratio()


def fetch_plex_api(path='', method='GET', plextv=False, **kwargs):
    """Fetches data from the Plex API"""

    url = 'https://plex.tv' if plextv else PLEX_URL.rstrip('/')

    headers = {'X-Plex-Token': PLEX_TOKEN,
               'Accept': 'application/json'}

    params = {}
    if kwargs:
        params.update(kwargs)

    try:
        if method.upper() == 'GET':
            r = requests.get(url + path,
                             headers=headers, params=params, verify=False)
        elif method.upper() == 'POST':
            r = requests.post(url + path,
                              headers=headers, params=params, verify=False)
        elif method.upper() == 'PUT':
            r = requests.put(url + path,
                             headers=headers, params=params, verify=False)
        elif method.upper() == 'DELETE':
            r = requests.delete(url + path,
                                headers=headers, params=params, verify=False)
        else:
            print("Invalid request method provided: {method}".format(method=method))
            return

        if r and len(r.content):
            if 'application/json' in r.headers['Content-Type']:
                return r.json()
            elif 'application/xml' in r.headers['Content-Type']:
                return xmltodict.parse(r.content)
            else:
                return r.content
        else:
            return r.content

    except Exception as e:
        print("Error fetching from Plex API: {err}".format(err=e))


def get_user_tokens(server_id):
    api_users = fetch_plex_api('/api/users', plextv=True)
    api_shared_servers = fetch_plex_api('/api/servers/{server_id}/shared_servers'.format(server_id=server_id),
                                        plextv=True)
    user_ids = {user['@id']: user.get('@username', user.get('@title')) for user in api_users['MediaContainer']['User']}
    users = {user_ids[user['@userID']]: user['@accessToken'] for user in
             api_shared_servers['MediaContainer']['SharedServer']}
    return users


def find_best_match(target_str, source_list):
    best_ratio = 0.0
    for source_str in source_list:
        match_ratio = similar(target_str, source_str)
        if match_ratio > best_ratio:
            best_match_str = source_str
            best_ratio = match_ratio
    return best_ratio, source_list.index(best_match_str)


def build_plex_track_str_list(TRACKS, ALBUM):
    TRACK_STR_LIST = []
    for track in TRACKS:
        track_str = track.grandparentTitle + ' ' + track.title
        if ALBUM:
            track_str = track_str + ' ' + track.parentTitle
        TRACK_STR_LIST.append(track_str)
    return TRACK_STR_LIST


def match_track(PLAYLIST_TRACK, PLEX_MUSIC, PLEX_ARTIST_LIST, PLEX_TRACK_LIST):
    match_ratio = 0.0
    track_match = []

    try:
        track_matches = PLEX_MUSIC.search(PLAYLIST_TRACK.name)

        if len(track_matches) == 1:
            if track_matches[0].type == 'track':
                # Easy-peasy -- collect $200
                track_match = track_matches[0]
        if not track_match:
            # Build search string
            PLAYLIST_STR = PLAYLIST_TRACK.artist + ' ' + PLAYLIST_TRACK.name
            if PLAYLIST_TRACK.album:
                PLAYLIST_STR = PLAYLIST_STR + ' ' + PLAYLIST_TRACK.album

            # First, try to match against artist
            artist_match = []
            artist_matches = PLEX_MUSIC.search(PLAYLIST_TRACK.artist)

            if len(artist_matches) == 1:
                # Artist match!
                artist_match = artist_matches[0]
            else:
                # No match -- try text search through artists
                artist_matches = []
                for artist in PLEX_ARTIST_LIST:
                    artist_matches.append(artist.title)
                match_ratio, match_idx = find_best_match(PLAYLIST_TRACK.artist, artist_matches)
                if match_ratio > 0.95:
                    artist_match = PLEX_ARTIST_LIST[match_idx]
            # ENDIF

            if artist_match:
                # If you got an artist match, get all tracks by that artist
                albums = PLEX_MUSIC.fetchItems(artist_match._data.attrib.get('key'))
                track_matches = []
                for album in albums:
                    tracks = PLEX_MUSIC.fetchItems(album._data.attrib.get('key'))
                    for track in tracks:
                        track_matches.append(track)

                # Evaluate artist track matches
                MATCH_STR_LIST = build_plex_track_str_list(track_matches, PLAYLIST_TRACK.album)
                match_ratio, match_idx = find_best_match(PLAYLIST_STR, MATCH_STR_LIST)

                if match_ratio > 0.95:
                    track_match = track_matches[match_idx]

            if not track_match:
                # Default to brute-force search (slow but relatively-sure)
                MATCH_STR_LIST = build_plex_track_str_list(PLEX_TRACK_LIST, PLAYLIST_TRACK.album)
                match_ratio, match_idx = find_best_match(PLAYLIST_STR, MATCH_STR_LIST)
                track_match = PLEX_TRACK_LIST[match_idx]
            # ENDIF

        # ENDIF
        print('\tMatched: {iArtist} - {iTrack} <==> {pArtist} - {pTrack} [{pAlbum}]'.format(
            iArtist=PLAYLIST_TRACK.artist, iTrack=PLAYLIST_TRACK.name, pArtist=track_match.grandparentTitle,
            pTrack=track_match.title, pAlbum=track_match.parentTitle))
    except:
        print('\t!!! Match failure @ {iArtist} - {iTrack}'.format(
            iArtist=PLAYLIST_TRACK.artist, iTrack=PLAYLIST_TRACK.name))
        pass

    return track_match


def main():
    """Main script"""
    num_cores = multiprocessing.cpu_count()

    l = Library(FILEPATH)
    playlists = l.getPlaylistNames()

    PLEX = PlexServer(PLEX_URL, PLEX_TOKEN)
    PLEX_USERS = get_user_tokens(PLEX.machineIdentifier)
    PLEX_MUSIC = PLEX.library.section('Music')
    PLEX_TRACK_LIST = PLEX_MUSIC.searchTracks()
    PLEX_ARTIST_LIST = PLEX_MUSIC.searchArtists()

    for playlist in playlists:
        playlist_items = []
        DATA_FILE = playlist + '.pickle'

        if playlist not in PLAYLISTS:
            continue

        # Check if .pickle exists
        try:
            print("Loading the '{title}' playlist from disk...".format(title=playlist))

            with open(DATA_FILE, 'rb') as fp:
                playlist_items = pickle.load(fp)
                fp.close()

            # HACK
            playlist_items = [playlist_item for playlist_item in playlist_items if playlist_item]

        except FileNotFoundError:
            print("Building the '{title}' playlist...".format(title=playlist))

            PLAYLIST_TRACKS = l.getPlaylist(playlist).tracks

            # Multiprocessing implementation
            # playlist_items = Parallel(n_jobs=num_cores, prefer='processes')(
            #     delayed(match_track)(PLAYLIST_TRACK, PLEX_MUSIC, PLEX_ARTIST_LIST, PLEX_TRACK_LIST) for PLAYLIST_TRACK in PLAYLIST_TRACKS)

            # Standard implementation
            for PLAYLIST_TRACK in PLAYLIST_TRACKS:
                track_match = match_track(PLAYLIST_TRACK, PLEX_MUSIC, PLEX_ARTIST_LIST, PLEX_TRACK_LIST)
                if track_match:
                    playlist_items.append(track_match)

            # Save data (just in case)
            with open(DATA_FILE, 'wb') as fp:
                pickle.dump(playlist_items, fp)
                fp.close()

        # Create playlist (per user)
        for user in USERS:
            user_token = PLEX_USERS.get(user)
            if not user_token:
                print("...User '{user}' not found in shared users. Skipping.".format(user=user))
                continue

            user_plex = PlexServer(PLEX_URL, user_token)

            # Delete the old playlist
            try:
                user_playlist = user_plex.playlist(playlist)
                user_playlist.delete()
            except:
                pass

            # Create a new playlist
            user_plex.createPlaylist(playlist, playlist_items)
            print("...Created playlist for '{user}'.".format(user=user))
    return


if __name__ == "__main__":
    main()
    print("Done.")
