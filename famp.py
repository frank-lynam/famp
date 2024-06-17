import time, threading, sys, os, http.server, json, urllib.parse

mp = "/mount/files/Music"
state = {"running": True, "in": False, "out": False, "vol": 30, "file": ""}

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
      os.system('echo "pause" > /tmp/famp-control')
      s.ww("True")

    elif ep=="/next":
      os.system('echo "pt_step 1" > /tmp/famp-control')
      s.ww("True")

    elif ep=="/volume":
      os.system(f'echo "volume {qp["to"]} 1" > /tmp/famp-control')
      state["vol"] = qp["to"]
      s.ww("True")

    elif ep=="/play":
      os.system(f'find "{mp + urllib.parse.unquote(qp["path"])}" | egrep -i "mp3|wma|ogg|flac" | tac > famp.playlist')
      os.system(f'echo "loadlist {os.getcwd()}/famp.playlist" > /tmp/famp-control')
      s.ww("True")

    elif ep=="/list":
      s.ww(json.dumps(os.listdir(mp + urllib.parse.unquote(qp["path"]))))

    elif ep=="/mute":
      state[qp["side"]] = not state[qp["side"]]
      if qp["side"] == "in":
        os.system(f"amixer -c 1 set LFE {255 if state['in'] else 0}")
        os.system(f"amixer -c 1 set Center {255 if state['in'] else 0}")
      else:
        os.system(f"amixer -c 1 set Front {255 if state['out'] else 0}")
      s.ww(json.dumps(state[qp["side"]]))

    elif ep=="/state":
      s.ww(json.dumps(state))

def get_file(state):
  while state["running"]:
    os.system("echo '' > famp.log")
    os.system("echo 'get_property filename' > /tmp/famp-control")
    os.system("echo 'get_property volume' > /tmp/famp-control")
    time.sleep(0.5)
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
      if got == 2:
        break

if __name__=="__main__":
  if "famp-control" not in os.listdir("/tmp"):
    os.system("mkfifo /tmp/famp-control")

  os.system("mplayer -slave -input file=/tmp/famp-control -loop 0 -msglevel all=4 silence.mp3 > famp.log &")
  os.system(f'echo "volume 30 1" > /tmp/famp-control')
  os.system("amixer -c 1 set PCM 255")
  os.system("amixer -c 1 set LFE 0")
  os.system("amixer -c 1 set Center 0")
  os.system("amixer -c 1 set Front 0")

  get_file_thread = threading.Thread(target=get_file, args=(state,))
  get_file_thread.start()

  print("Started mplayer and set system volume to max")

  try:
    print ("Frank's Awesome Media Player started! Hit port 8000 for controls =]")
    http.server.HTTPServer(('', 8000), famp).serve_forever()

  except KeyboardInterrupt:
    print("\rBuh-bye!")
    os.system("echo 'quit' > /tmp/famp-control &")
    os.system("amixer -c 1 set PCM 0")
    state["running"] = False
    get_file_thread.join()
    os.system("unlink /tmp/famp-control")
    os.system("unlink famp.playlist")
    os.system("unlink famp.log")
    print("Quit mplayer and set system volume to zero")
