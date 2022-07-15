from obspy.realtime import RtTrace
from obspy import UTCDateTime

class RollingStream:
    """ Class for a local copy of real-time traces from STATION_TRACES"""

    def __init__(self, channels, channel_length):
        """
            Parameters:
            - channels: list of channel names
            - channel_length: max length per channel
        """
        self.traces = []
        for channel in channels:
            self.traces.append(RtTrace(max_length=channel_length))
            self.traces[-1].stats.channel = channel

    def update_trace(self, tr):
        """ Update a single trace and return a copy """

        for rt_tr in self.traces:
            if rt_tr.stats.channel == tr.stats.channel:
                rt_tr.append(tr)
                return rt_tr.copy()

    def get_traces_from(self, starttime):
        """ Get all traces from starttime to latest """

        starttime = UTCDateTime(starttime, precision=6) # revert to default precision

        # get earliest endtime
        earliest_endtime = self.traces[0].stats.endtime
        for tr in self.traces:
            endtime = tr.stats.endtime
            if endtime < earliest_endtime:
                earliest_endtime = endtime

        latest_traces = []
        for tr in self.traces:
            latest_traces.append( \
                tr.slice(starttime=starttime, endtime=endtime).copy())

        return latest_traces


    def latest_traces(self, duration):
        """ Get a duration of the latest values of all traces """

        # get earliest endtime
        earliest_endtime = self.traces[0].stats.endtime
        for tr in self.traces:
            endtime = tr.stats.endtime
            if endtime < earliest_endtime:
                earliest_endtime = endtime

        latest_traces = []
        for tr in self.traces:
            latest_traces.append( \
                tr.slice(starttime=endtime-duration, endtime=endtime).copy())


        return latest_traces
