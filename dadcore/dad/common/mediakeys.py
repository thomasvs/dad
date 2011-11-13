# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Handling pressing of media keys.


See http://git.gnome.org/browse/gnome-settings-daemon/tree/plugins/media-keys/README.media-keys-API
"""

class GNOMEMediaKeysListener(object):

    def __init__(self, app=None):
        """
        @param app: the name of the application.
        @type  app: C{unicode}
        """

        self._callbacks = []
        self._app = app

        self._register()

    def add(self, callback):
        """
        Add a callback to be called when a key is pressed.

        @type  callback: a callable taking two unicode strings.
        """
        self._callbacks.append(callback)

    def _get_obj_iface(self):
        import dbus

        # this import has the side effect of setting the main loop on dbus
        from dbus import glib
        bus = dbus.SessionBus()
        mediakeys = bus.get_object('org.gnome.SettingsDaemon',
            '/org/gnome/SettingsDaemon/MediaKeys')
        iface = dbus.Interface(mediakeys,
            'org.gnome.SettingsDaemon.MediaKeys')

        return mediakeys, iface

    def _signal_handler(self, app, key):
        exception = None

        if self._app and self._app != app:
            return

        for c in self._callbacks:
            try:
                c(app, key)
            except Exception, e:
                exception = e

        if exception:
            raise exception


    def _register(self):
        mediakeys, iface = self._get_obj_iface()
        try:
            mediakeys, iface = self._get_obj_iface()

            mediakeys.connect_to_signal("MediaPlayerKeyPressed",
                self._signal_handler,
                dbus_interface='org.gnome.SettingsDaemon.MediaKeys')

        except Exception, e:
            print 'Cannot listen to multimedia keys', e

    def grab(self):
        mediakeys, iface = self._get_obj_iface()
        # 0L is GDK_CURRENT_TIME or gtk.gdk.CURRENT_TIME, which is 0L
        iface.GrabMediaPlayerKeys(self._app, 0L)

    def release(self):
        mediakeys, iface = self._get_obj_iface()
        # 0L is GDK_CURRENT_TIME or gtk.gdk.CURRENT_TIME, which is 0L
        iface.ReleaseMediaPlayerKeys(self._app)


if __name__ == '__main__':
    def cb(app, key):
        print "callback:", app, key

    l = GNOMEMediaKeysListener(app='mediakeys')
    l.grab()
    l.add(cb)

    import gobject

    loop = gobject.MainLoop()

    loop.run()
