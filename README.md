# plex-scripts

Collection of Plex administration scripts.

## import-itunes-playlists

Intelligent iTunes playlist importer for Plex. Reads `iTunes Library.xml` file into memory and attempts to match each track from the specified list of iTunes playlists.

### Configuration / Deployment

You'll need to add your local Plex information to the `config.py` file. (Note that this file is explicitly ignored to prevent you from exposing local credentials.)

You'll also need your iTunes Library XML file.

There is a `Dockerfile` and `docker-compose` configuration in development; it has not been tested. See the [Known Issues](#known-issues) section for more information.

### Import Strategy

For each playlist specified and found in the iTunes library file:

First, check to see if a `.pickle` file exists. The match data for each playlist is stashed during execution to allow efficient restarts. Otherwise, proceed to matching algorithm to build Plex playlist.

For each track in the current iTunes playlist:

1. Try straight match for track. If Plex returns a single hit, assume match is good and continue.
1. Try scoped match for artist.
    1. Try straight match against artist. If Plex returns a single hit, assume match is good; otherwise, use fuzzy matching for artist name. Match must be >95% to be valid; take best match.
    1. If a valid artist match is found, get all tracks by that artist and build a list of track names. Use fuzzy matching for track name. Match must be >95% to be valid; take best match.
1. Try "brute-force" fuzzy string match. If iTunes track includes album name, use {<Artist> <Track> <Album>} string to match; otherwise, just use {<Artist> <Track>}. No threshold, so best match wins.

If a match is found, add the Plex track to the Plex playlist; otherwise, skip iTunes track and print a warning message to the console. Once the iTunes playlist is complete, create the playlist in Plex based on the matched tracks.

For each specified user, check to see if a playlist already exists with the same name; if so, delete it. Create a new playlist with the matched tracks. Print status message and continue to next specified iTunes playlist.

### Known Issues

#### Docker

Docker configuration is untested. It was developed to solve performance issues that were resolved through the caching of match data (via `pickle`).

#### Multicore / Multiprocessing

The multi-thread processing caused issues during development with minimal speed-up. It was developed to solve performance issues that were resolved through the caching of match data (via `pickle`).
