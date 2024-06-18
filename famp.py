import time, threading, sys, os, http.server, json, urllib.parse

mp = "/mount/files/Music"
state = {"running": True, "playing": True, 
  "lr": False, "dr": False, "out": False, "index": 0, 
  "vol": 30, "file": "", "pos": 0,
  "playlist":[], "updated": time.time()}

class famp(http.server.BaseHTTPRequestHandler):

  def ww(s, txt, code=200, content="application/json"):
    # A simple little wrapper to make responses easier

    s.send_response(code)
    s.send_header("Content-type", content)
    s.end_headers()
    s.wfile.write(bytes(txt, "utf-8"))

  def do_GET(s):
    global state

    parts = s.path.split("?")
    ep = parts[0]
    qp = {}
    if len(parts) > 1:
      qp = {x.split("=")[0]:x.split("=")[-1] for x in parts[1].split("&")}
    
    if ep=="/":
      with open("index.html") as fl:
        s.ww(fl.read(), content="text/html")
    
    elif ep=="/pause":
      if state["playing"]:
        os.system("killall -9 mplayer")
        state["playing"] = False
        state["updated"] = 0
      else:
        play(state["playlist"][state["index"]], state["pos"])
      s.ww("True")

    elif ep=="/next":
      if len(state["playlist"]) > 0:
        state["index"] = (state["index"] + 1) % len(state["playlist"])
      state["file"] = state["playlist"][state["index"]].split("/")[-1]
      play()
      s.ww("True")

    elif ep=="/volume":
      os.system(f'echo "volume {qp["to"]} 1" > /tmp/famp-control')
      state["vol"] = qp["to"]
      s.ww("True")

    elif ep=="/play":
      os.system(f'find "{mp + urllib.parse.unquote(qp["path"])}" | egrep -i "opus|mp3|wma|ogg|flac" | tac > famp.playlist')
      with open("famp.playlist") as fl:
        state["playlist"] = [x.strip() for x in fl.readlines() if x.strip()!=""]
      state["index"] = 0
      play()
      s.ww("True")

    elif ep=="/list":
      if os.path.isfile(mp + urllib.parse.unquote(qp["path"])[:-1]):
        s.ww('"play"')
      else:
        s.ww(json.dumps(os.listdir(mp + urllib.parse.unquote(qp["path"]))))

    elif ep=="/skip":
      state["index"] = int(qp["index"])
      play()
      s.ww("True")

    elif ep=="/mute":
      state[qp["side"]] = not state[qp["side"]]
      if qp["side"] == "lr":
        os.system(f"amixer -c 1 set LFE {255 if state['lr'] else 0}")
      elif qp["side"] == "dr":
        os.system(f"amixer -c 1 set Center {255 if state['dr'] else 0}")
      else:
        os.system(f"amixer -c 1 set Front {255 if state['out'] else 0}")
      s.ww(json.dumps(state[qp["side"]]))

    elif ep=="/state":
      if state["playing"] and float(state["updated"]) > 0:
        dt = time.time() - float(state["updated"])
        state["updated"] = float(state["updated"]) + dt
        state["pos"] = float(state["pos"]) + dt
      s.ww(json.dumps(state))
    
    else:
      s.ww("False")

def play(path=None, pos=0):
  global state
  if path==None:
    if len(state["playlist"]) == 0:
      return
    path = state["playlist"][state["index"]]

  state["pos"] = pos
  with open("famp.playlist", "w") as fl:
    fl.write(path)
  os.system("killall -9 mplayer")
  if "famp-control" in os.listdir("/tmp"):
    os.system("unlink /tmp/famp-control")
  os.system("mkfifo /tmp/famp-control")
  os.system(f'mplayer -slave -input file=/tmp/famp-control -msglevel all=4 -loop 0 silence.mp3 > famp.log &')
  time.sleep(0.05)
  os.system(f'echo "volume {state["vol"]} 1" > /tmp/famp-control')
  os.system(f'echo "loadlist famp.playlist" > /tmp/famp-control')
  os.system(f'echo "seek {pos}" > /tmp/famp-control')
  os.system(f'echo "loop -1" > /tmp/famp-control')
  state["playing"] = True

def get_file(state):
  while state["running"]:
    os.system("ps aux | grep mplayer > famp.log")
    with open("famp.log") as fl:
      running = len(fl.readlines()) > 2
    if not running:
      if state["playing"] and len(state["playlist"]) > 0:
        state["playlist"] = state["playlist"][1:]
        play()
      time.sleep(1)
      continue
    os.system("echo 'get_property filename' > /tmp/famp-control")
    os.system("echo 'get_property volume' > /tmp/famp-control")
    os.system("echo 'get_property time_pos' > /tmp/famp-control")
    time.sleep(0.05)
    with open("famp.log", errors='ignore') as fl:
      d = fl.readlines()
    got = 0
    for x in d[::-1]:
      if "ANS_filename=" in x:
        state["file"] = x.split("ANS_filename=")[1].strip()
        got = got + 1
      if "ANS_volume=" in x:
        state["vol"] = x.split("ANS_volume=")[1].strip()
        got = got + 1
      if "ANS_time_pos=" in x:
        state["pos"] = x.split("ANS_time_pos=")[1].strip()
        got = got + 1
      if got == 3:
        break
    state["updated"] = time.time()
    time.sleep(0.5)

if __name__=="__main__":
  if "famp-control" in os.listdir("/tmp"):
    os.system("unlink /tmp/famp-control")
  os.system("mkfifo /tmp/famp-control")
  os.system("amixer -c 1 set PCM 255")
  os.system("amixer -c 1 set LFE 0")
  os.system("amixer -c 1 set Center 0")
  os.system("amixer -c 1 set Front 0")

  get_file_thread = threading.Thread(target=get_file, args=(state,))
  get_file_thread.start()

  print("Prepped for mplayer and set system volume to max")

  try:
    print ("Frank's Awesome Media Player started! Hit port 8000 for controls =]")
    http.server.HTTPServer(('', 8000), famp).serve_forever()
  except:
    print("\rBuh-bye!")
    os.system("killall -9 mplayer")
    os.system("amixer -c 1 set PCM 0")
    state["running"] = False
    get_file_thread.join()
    os.system("rm -f /tmp/famp-control")
    os.system("rm -f famp.playlist")
    os.system("rm -f famp.log")
    print("Quit mplayer and set system volume to zero")
