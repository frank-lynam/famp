import time, threading, sys, os, random
import http.server, json, urllib.parse

mp = "/mount/files/Music"
state = {"running": True, "playing": True, 
  "lr": False, "dr": False, "out": False, "index": 0, 
  "vol": 75, "file": "", "pos": 0, "path": "",
  "playlist":[], "updated": time.time()}

class famp(http.server.BaseHTTPRequestHandler):

  def ww(s, txt, code=200, content="application/json"):
    # A simple little wrapper to make responses easier

    s.send_response(code)
    s.send_header("Content-type", content)
    s.end_headers()
    s.wfile.write(bytes(txt, "utf-8"))

  def do_GET(s):
    # Handle all the get endpoints
    global state

    # Parse incoming data
    parts = s.path.split("?")
    ep = parts[0]
    qp = {}
    if len(parts) > 1:
      qp = {x.split("=")[0]:x.split("=")[-1] for x in parts[1].split("&")}
    log = ""    

    if ep=="/":
      # I like to load it fresh for easy development
      log = "Index hit"
      with open("index.html") as fl:
        s.ww(fl.read(), content="text/html")
    
    elif ep=="/favicon.svg":
      # My totally sweet logo

      s.ww('<svg xmlns="http://www.w3.org/2000/svg"><text>'
        + '</text>&#127926;</svg>', content="image/svg+xml")

    elif ep=="/pause":
      # mplayer's pause call doesn't work, so this is the workaround...
      if state["playing"]:
        log = "Pausing"
        os.system("killall -9 mplayer 2>/dev/null")
        state["playing"] = False
        state["updated"] = 0
      else:
        log = "Unpausing"
        play(state["playlist"][state["index"]], state["pos"])
      s.ww("True")

    elif ep=="/next":
      # Using the playlist makes this easy!
      log = "Playing next playlist item"
      if len(state["playlist"]) > 0:
        state["index"] = (state["index"] + 1) % len(state["playlist"])
      state["file"] = state["playlist"][state["index"]].split("/")[-1]
      play()
      s.ww("True")

    elif ep=="/shuffle":
      # Random sort ftw!
      log = "Every day I'm shufflin'..."
      random.shuffle(state["playlist"])
      play()

    elif ep=="/volume":
      # Volume control works great!
      log = "Setting volume to " + urllib.parse.unquote(qp["to"])
      state["vol"] = qp["to"]
      set_volume()
      s.ww("True")

    elif ep=="/play":
      # Every play call is a playlist, even if it's a playlist of one
      log = "Playing " + urllib.parse.unquote(qp["path"])
      state["path"] = urllib.parse.unquote(qp["path"])
      os.system(f'find "{mp + urllib.parse.unquote(qp["path"])}" | egrep -i "opus|mp3|wma|ogg|flac" | tac > famp.playlist')
      with open("famp.playlist") as fl:
        state["playlist"] = [x.strip() for x in fl.readlines() if x.strip()!=""]
      state["index"] = 0
      play()
      s.ww("True")

    elif ep=="/list":
      # Returns the folder contents if a folder, and play if a file
      log = "Listed " + urllib.parse.unquote(qp["path"])
      if os.path.isfile(mp + urllib.parse.unquote(qp["path"])[:-1]):
        s.ww('"play"')
      else:
        s.ww(json.dumps(os.listdir(mp + urllib.parse.unquote(qp["path"]))))

    elif ep=="/skip":
      # Jumps to a specific playlist item
      state["index"] = int(qp["index"])
      play()
      s.ww("True")

    elif ep=="/mute":
      # Stateful mute on the hardware controller side
      state[qp["side"]] = not state[qp["side"]]
      log = ("Unmuted " if state[qp["side"]] else "Muted ") + qp["side"]
      if qp["side"] == "lr":
        os.system(f"amixer -c 1 set LFE {255 if state['lr'] else 0} >/dev/null")
      elif qp["side"] == "dr":
        os.system(f"amixer -c 1 set Center {255 if state['dr'] else 0} >/dev/null")
      else:
        os.system(f"amixer -c 1 set Front {255 if state['out'] else 0} >/dev/null")
      s.ww(json.dumps(state[qp["side"]]))

    elif ep=="/state":
      # I store state serverside because that's where it is!
      if state["playing"] and float(state["updated"]) > 0:
        dt = time.time() - float(state["updated"])
        state["updated"] = float(state["updated"]) + dt
        state["pos"] = float(state["pos"]) + dt
      s.ww(json.dumps(state))
    
    else:
      s.ww("False")

    if log!="":
      print(f"[{s.log_date_time_string()}] {s.request.getpeername()[0]} - {log}")

  def log_request(s, *args):
    # Shush you!
    pass

def send(m):
  os.system(f"echo {m} > /tmp/famp-control &\necho $! > famp.pid")
  time.sleep(0.2)
  os.system("kill -9 $(cat famp.pid) 2>/dev/null")

def play(path=None, pos=0):
  # A fresh mplayer instance was the most reliable way to start a song
  global state
  if path==None:
    if len(state["playlist"]) == 0:
      return
    path = state["playlist"][state["index"]]

  state["pos"] = pos
  with open("famp.playlist", "w") as fl:
    fl.write(path)
  os.system("killall -9 mplayer 2>/dev/null")
  if "famp-control" in os.listdir("/tmp"):
    os.system("unlink /tmp/famp-control")
  os.system("mkfifo /tmp/famp-control")
  os.system(f'mplayer -slave -input file=/tmp/famp-control -msglevel all=4 -playlist famp.playlist > famp.log &')
  send(f'volume 100 1')
  send(f'seek {pos}')
  state["playing"] = True

def get_file(state):
  # This just regularly polls mplayer for state info
  while state["running"]:
    os.system("ps aux | grep mplayer > famp.log")
    with open("famp.log") as fl:
      running = len(fl.readlines()) > 2
    if not running:
      # Plays the next song when one ends
      if state["playing"] and len(state["playlist"]) > 0:
        state["index"] = (state["index"] + 1) % len(state["playlist"])
        play()
      time.sleep(1)
      continue
    send("get_property filename")
    #send("get_property volume")
    send("get_property time_pos")
    time.sleep(0.05)
    with open("famp.log", errors='ignore') as fl:
      d = fl.readlines()
    got = 0
    for x in d[::-1]:
      if "ANS_filename=" in x:
        state["file"] = x.split("ANS_filename=")[1].strip()
        got = got + 1
      #if "ANS_volume=" in x:
      #  state["vol"] = x.split("ANS_volume=")[1].strip()
      #  got = got + 1
      if "ANS_time_pos=" in x:
        state["pos"] = x.split("ANS_time_pos=")[1].strip()
        got = got + 1
      if got == 2:
        break
    state["updated"] = time.time()
    time.sleep(0.5)

def set_volume():
  global state
  os.system(f"amixer -c 1 set PCM {state['vol']} >/dev/null")

if __name__=="__main__":
  # Prep environment
  if "famp-control" in os.listdir("/tmp"):
    os.system("unlink /tmp/famp-control")
  os.system("mkfifo /tmp/famp-control")
  os.system("amixer -c 1 set PCM 75 >/dev/null")
  os.system("amixer -c 1 set Master 255 >/dev/null")
  os.system("amixer -c 1 set LFE 0 >/dev/null")
  os.system("amixer -c 1 set Center 0 >/dev/null")
  os.system("amixer -c 1 set Front 0 >/dev/null")

  get_file_thread = threading.Thread(target=get_file, args=(state,))
  get_file_thread.start()

  print("\nPrepped for mplayer and set system volume to max")

  try:
    # Start server
    print ("Frank's Awesome Media Player started! Hit port 8000 for controls =]\n")
    http.server.HTTPServer(('', 8000), famp).serve_forever()
  except:
    # Clean up
    print("\nBuh-bye!")
    os.system("killall -9 mplayer 2>/dev/null")
    os.system("amixer -c 1 set PCM 0 >/dev/null")
    state["running"] = False
    get_file_thread.join()
    os.system("rm -f /tmp/famp-control")
    os.system("rm -f famp.playlist")
    os.system("rm -f famp.log")
    os.system("rm -f famp.pid")
    print("Quit mplayer and set system volume to zero\n")
