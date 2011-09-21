# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.common import player

class GTKPlayerView(player.PlayerView):
    def __init__(self, player):

        self._player = player

        self._playing = None

        import gtk

        self._window = gtk.Window()
        from dadgtk.views import scheduler as sch, seek
        sui = sch.SchedulerUI()

        def jukebox_started_cb(jukebox, scheduled):
            sui.started(scheduled)
            import gst
            self._seekui.set_track_length(
                float(scheduled.duration) / gst.SECOND)
            self._seekui.set_track_offset(
                float(scheduled.start) / gst.SECOND)
            self._seekui.set_schedule_length(
                float(self._player.scheduler.duration) / gst.SECOND)
            self._playing = scheduled
            self._window.set_title('dad: %s - %s' % (
                " & ".join(scheduled.artists), scheduled.title))

        # FIXME: poking into private bits
        self._player._jukebox.connect('started', jukebox_started_cb)

        def scheduler_clicked_cb(scheduler, scheduled):
            print 'seeking to %r' % scheduled
            where = scheduled.start
            self._player.seek(where)
        sui.connect('clicked', scheduler_clicked_cb)

        sui.set_scheduler(player.scheduler)

        box = gtk.VBox()
        box.set_homogeneous(False)
        box.add(sui)

        self._seekui = seek.SeekUI()
        box.pack_end(self._seekui, expand=False, fill=False)

        def _seeked_schedule_cb(seekui, position):
            import gst
            self._player.seek(position * gst.SECOND)
        self._seekui.connect('seeked-schedule', _seeked_schedule_cb)
            

        self._window.add(box)

        self._window.set_default_size(640, 480)
        self._window.show_all()

    def set_schedule_position(self, position):
        import gst
        if position is not None:
            self._seekui.set_schedule_position(float(position) / gst.SECOND)
            if self._playing is not None:
                self._seekui.set_track_position(
                    float(position - self._playing.start) / gst.SECOND)

    def set_title(self, title):
        self._window.set_title(title)
