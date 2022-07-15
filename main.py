from pubsub.pubsub import PubSub

from SLclient import SLclient
from RollingStream import RollingStream
from DetectSpike import DetectSpike
from Conversion import Conversion
from helpers import alarm, change_colon
from threading import Thread, Event

from obspy.core import read
import os

def main():
    # TODO: get configs from configs file
    IP = "rs.local"#"192.168.1.21" # rshake IP
    DUR = 30 # duration in sec (for plotting and other processes)
    STA_SEC = 2 # length of data in seconds to get short-term-ave
    LTA_SEC = 15 # length of data in seconds to get long-term-ave
    ON_THRESH = 3.0 # sta/lta threshold to trigger an on-pick
    OFF_THRESH = 1.5 # sta/lta threshold to trigger an off-pick / reset
    MAX_EVT_DUR = 20 # max duration of on-thresh to off-thresh in sta/lta
    BASIS_CHANNEL = "EHZ" # picks on this channel trigger conversion for all traces
    PADDING_DUR = 3 # duration of padding on the left of event onset
    INTENSITY_THRESHOLD = 2 # intensity greater than this triggers an alarm
    INV_DIR = "inventories" # folder to store station inventory files
    CAP_DIR = "captures" # folder to captured event mseed and png data

    # create communication link between threads
    message_board = PubSub(max_queue_in_a_channel=100)

    # create link to rshake
    SL_client = SLclient(message_board, IP)

    # create spike detector
    Picker = DetectSpike(
        message_board,
        SL_client.station, SL_client.channels, SL_client.sps,
        STA_SEC, LTA_SEC, ON_THRESH, OFF_THRESH, MAX_EVT_DUR,
        DUR
    )

    # create traces converter
    Converter = Conversion(
        message_board,
        SL_client.network, SL_client.station, SL_client.channels, SL_client.sps,
        BASIS_CHANNEL, PADDING_DUR, INTENSITY_THRESHOLD,
        DUR,
        INV_DIR, CAP_DIR
    )

    # subscribe message queues
    picks_queue = message_board.subscribe(Picker.dst_topic)
    event_summary_queue = message_board.subscribe(Converter.dst_event_summary_topic)
    event_data_queue = message_board.subscribe(Converter.dst_event_data_topic)
    
    while True:
        for pick in picks_queue.listen():
            print("MAIN: ", "RECEIVED PICK: id=", pick['id'], " data=", pick['data'], " qsize=", picks_queue.qsize(), sep='')
            if picks_queue.qsize() == 0:
                break

        for summary in event_summary_queue.listen():
            print("MAIN: ", "RECEIVED EVT: id=", summary['id'], " data=", summary['data'], " qsize=", event_summary_queue.qsize(), sep='')
            intensity = summary['data']['intensity']
            PGA = summary['data']['PGA']
            PGA_channel = summary['data']['PGA_channel']
            PGD = summary['data']['PGD']
            PGD_channel = summary['data']['PGD_channel']

            alarm(intensity, PGD*100, PGD_channel, PGA*100, PGA_channel) # convert to cm

            if event_summary_queue.qsize() == 0:
                break

        for dirpath in event_data_queue.listen():
            print("MAIN: ", "RECEIVED EVT-DATA: id=", dirpath['id'], " data=", dirpath['data'], " qsize=", event_data_queue.qsize(), sep='')
            directory = dirpath['data']['path']
            # pass
            if os.name == 'nt':
                directory = change_colon(directory)
            for unit in ["acc", "dis", "counts", "metric", "vel"]:
                st = read(os.path.join(directory,unit + ".mseed"))
                st.plot(outfile = os.path.join(directory,unit + ".png"))

            if event_data_queue.qsize() == 0:
                break
        

    # wait for all threads to exit gracefully
    #SL_client.join()
    #Picker.join()


if __name__ == "__main__":
    main()




