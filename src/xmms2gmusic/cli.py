#!/usr/bin/env python

import os, sys

import gobject
import xmmsclient
import xmmsclient.glib
import gmusicapi

TRACK_URL = "googlemusic://{0}"
PROPERTY_SOURCE = "googlemusic"
PLAYLIST_FORMAT = "GMusic: {0}"
LAST_MODIFIED_KEY = ("plugin/googlemusic", "lastmodified")

def wait_for_value(r):
    r.wait()
    return r.value()

class XMMS2GMusicSync:
    def __init__(self):
        self.xmms = xmmsclient.XMMS("xmms2-googlemusic-sync")
        self.gmusic = gmusicapi.api.Api()
        self.ml = gobject.MainLoop(None, False)
        self.numsyncs = 0

    def log(self, prefix, msg, *args):
        msg = msg.format(*args)

        print(("[{0}] {1}").format(prefix, msg))

    def connect(self):
        self.xmms.connect(os.getenv("XMMS_PATH"), self.on_disconnect)
        xmmsclient.glib.GLibConnector(self.xmms)

    def authenticate(self):
        try:
            username = wait_for_value(self.xmms.config_get_value("googlemusic.username"))
            password = wait_for_value(self.xmms.config_get_value("googlemusic.password"))
        except xmmsclient.XMMSError:
            self.log("xmms", "Failed to get username/password from server. Make sure config options googlemusic.username/googlemusic.password are set!")
            sys.exit()

        return self.gmusic.login(username, password)

    def on_disconnect(self, loop):
        self.quit()

    def sync_existing_song(self, id, song, cb):
        if "deleted" in song and song["deleted"]:
            self.log("xmms", "Removing entry from medialib ({0})", id)
            return self.xmms.medialib_remove_entry(id, cb=cb)

        def on_get_info(val):
            info = val.value()

            if LAST_MODIFIED_KEY in info:
                lastmodified = int(info[LAST_MODIFIED_KEY])

                if int(song["lastPlayed"]) > lastmodified:
                    self.log("xmms", "Rehashing entry in medialib ({0})", id)
                    return self.xmms.medialib_rehash(id, cb=cb)

            return cb()

        self.xmms.medialib_get_info(id, cb=on_get_info)

    def sync_song(self, song, cb):
        url = TRACK_URL.format(song["id"])
        self.numsyncs += 1

        def on_get_id(val):
            id = val.value()

            if id > 0:
                self.sync_existing_song(id, song, cb)
            else:
                self.log("xmms", "Adding song to medialib ({0})", song["id"])
                self.xmms.medialib_add_entry(url, cb)

        self.xmms.medialib_get_id(url, cb=on_get_id)

    def sync_songs(self):
        self.log("gmusic", "Fetching song library")

        songs = self.gmusic.get_all_songs()

        for song in songs:
            self.sync_song(song, cb=self.on_sync)

    def sync_playlist(self, name, songs, cb):
        self.numsyncs += 1

        plname = PLAYLIST_FORMAT.format(name)

        def on_clear(val):
            self.log("xmms", "Syncing playlist ({0})", name)

            for song in songs:
                url = TRACK_URL.format(song["id"])
                self.numsyncs += 1
                self.xmms.playlist_add_url(url, plname, cb=cb)

            cb()

        def on_create(val):
            self.xmms.playlist_clear(plname, cb=on_clear)


        self.xmms.playlist_create(plname, cb=on_create)

    def sync_playlists(self):
        self.log("gmusic", "Fetching playlists")

        playlists = self.gmusic.get_all_playlist_ids()

        for pltype, playlists in playlists.items():
            for name, plid in playlists.items():
                songs = self.gmusic.get_playlist_songs(plid)
                self.sync_playlist(name, songs, self.on_sync)

    def on_sync(self, val=None):
        self.numsyncs -= 1

        if self.numsyncs == 0:
            self.log("app", "Sync complete")
            self.quit()

    def run(self):
        self.sync_songs()
        self.sync_playlists()
        self.ml.run()

    def quit(self):
        self.ml.quit()

def main():
    app = XMMS2GMusicSync()

    app.log("xmms", "Connecting to daemon")

    try:
        app.connect()
    except IOError, err:
        app.log("xmms", "Failed to connect to daemon: {0}", str(err))
        sys.exit()

    app.log("xmms", "Successfully connected")
    app.log("gmusic", "Authenticating to Google")

    if not app.authenticate():
        app.log("gmusic", "Failed to authenticate to Google")
        sys.exit()

    app.log("gmusic", "Successfully authenticated")
    app.run()
