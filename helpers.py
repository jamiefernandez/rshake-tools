from obspy import read_inventory
from obspy.clients.fdsn import Client as RS_Client
from obspy.core.inventory import Inventory, Network
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from tkinter import *
from tkinter import messagebox as mb
from pathlib import Path
import threading
import json
import time
import os

def get_inventory(inv_dir, network, station, client_name="RASPISHAKE"):
    # create copy of latest inv, remove date so it can be used in remove_response
    inv_path = os.path.join(os.getcwd(), inv_dir, network+"_"+station+".xml")
    if os.path.exists(inv_path):
        #print("reading inv")
        inv = read_inventory(inv_path)
    else:
        #print("downloading inv")
        rs_client = RS_Client(client_name)
        inv = rs_client.get_stations(network=network, station=station, level="RESP")
        latest_station_response = (inv[-1][-1]).copy()
        latest_station_response.start_date = None
        latest_station_response.end_date = None
        for cha in latest_station_response:
            cha.start_date=None
            cha.end_date=None
        inv = Inventory(networks=[ \
                Network(code=network, stations=[latest_station_response])])
        Path(os.path.dirname(inv_path)).mkdir(parents=True, exist_ok=True)
        inv.write(inv_path, format="STATIONXML")
    return inv

def g_to_intensity(g): # Gets intensity from PGA
    intensity_scale = {
        (0,0.00170): 'I',
        (0.00170,0.01400): 'II-III',
        (0.01400,0.03900): 'IV',
        (0.03900,0.09200): 'V',
        (0.09200,0.18000): 'VI',
        (0.18000,0.34000): 'VII',
        (0.34000,0.65000): 'VIII',
        (0.65000,1.24000): 'IX',
        (1.24000,5): 'X+'
    }
    for i in intensity_scale:
        if i[0] < g < i[1]:
            intensity = intensity_scale[i]
    return intensity

def change_colon(target_dir):
    dirSplit = target_dir.split("\\")
    dirSplit[-1] = dirSplit[-1].replace(':','\ua789')
    target_new = '\\'.join(dirSplit)
    return target_new

def save_mseed(st, title, target_dir):
    if os.name == 'nt':
        target_dir = change_colon(target_dir)
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    mseed_path = os.path.join(target_dir, title +".mseed")
    for i in range(len(st)):
        st[i].data = st[i].data.astype('float32')
    st.write(mseed_path, format="MSEED", reclen=512)
    # try:
    #     st.write(mseed_path, format="MSEED", reclen=512)
    # except:
    #     pass

    return mseed_path

def save_json(dic, title, target_dir):
    if os.name == 'nt':
        target_dir = change_colon(target_dir)
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    json_path = os.path.join(target_dir, title +".json")
    with open(json_path, 'w') as fp:
        json.dump(dic, fp)

    return json_path

def intensity_to_int(intensity): # Convert string to number for text-to-voice
    if intensity == "I":
        intensityNum = 1
    elif intensity == "II-III":
        intensityNum = 2
    elif intensity == "IV":
        intensityNum = 4
    elif intensity == "V":
        intensityNum = 5
    elif intensity == "VI":
        intensityNum = 6
    elif intensity == "VII":
        intensityNum = 7
    elif intensity == "VIII":
        intensityNum = 8
    elif intensity == "IX":
        intensityNum = 9
    elif intensity == "X+":
        intensityNum = 10
    else:
        intensityNum = 0

    return intensityNum

def channel_to_axis(channel):
    if "HZ" in channel:
        return "Vertical axis" # geophone, should we indicate?
    elif "NZ" in channel:
        return "Vertical axis" # MEMS.
    elif "NN" in channel:
        return "North-South axis"# MEMS.
    elif "NE" in channel:
        return "East-West axis"# MEMS.

def threadSound(): #thread for playing alert sound
    for _ in range(1):
        play(AudioSegment.from_mp3("alarm.mp3"))
        play(AudioSegment.from_mp3("eq_intensity.mp3"))
        play(AudioSegment.from_mp3("eq_displacement.mp3"))
        time.sleep(1)

def threadDialog(intensity,displacement,channel, PGA, PGA_channel): # thread for displaying alert box
    root = Tk()
    root.withdraw()
    mb.showwarning('! EARTHQUAKE ALERT !',
                   ('Intensity: %s\nDisplacement: %.2f cm, '+channel+'\nAcceleration: %.2f cm/s2, '+PGA_channel) % (intensity,displacement,PGA),
                   parent=root)
    root.destroy()

def alarm(intensity, disp, channel, PGA, PGA_channel):
    # Convert intensity string into number
    intensityNum = intensity_to_int(intensity)
    # create audio file for intensity
    if intensity=="II-III":
        myobj = gTTS(text="Attention! Earthquake detected at intensity two or three", lang="en", slow=False)
    else:
        myobj = gTTS(text="Attention! Earthquake detected at intensity %.0f" % intensityNum, lang="en", slow=False)
    myobj.save("./eq_intensity.mp3")
    # create audio file for displacement
    myobj = gTTS(text=("Peak displacement is %.2f centimeters along "+channel_to_axis(channel) \
                        +", and peak acceleration is %.2f centimeters-per-second-squared along "+channel_to_axis(PGA_channel)) % (disp, PGA), lang="en", slow=False)
    myobj.save("./eq_displacement.mp3")

    # Create separate threads for alert sounds and dialog box
    alertThread1 = threading.Thread(target=threadSound)
    alertThread1.start()
    #root = Tk()
    #root.withdraw()
    #mb.showwarning('! EARTHQUAKE ALERT !',
    #               ('Intensity: %s\nDisplacement: %.2f cm, '+channel) % (intensity,displacement),
    #               parent=root)
    #root.destroy()
    alertThread2 = threading.Thread(target=threadDialog, args=(intensity,disp,channel, PGA, PGA_channel))
    alertThread2.start()

    # alertThread1.join()
    # alertThread2.join()


