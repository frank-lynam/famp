import sys, os, http.server, json, urllib.parse

mp = "/mount/files/Music"

class famp(http.server.BaseHTTPRequestHandler):

  def ww(s, txt, code=200, content="application/json"):
    # A simple little wrapper to make responses easier

    s.send_response(code)
    s.send_header("Content-type", content)
    s.end_headers()
    s.wfile.write(bytes(txt, "utf-8"))

  def do_GET(s):
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
      os.system('echo "seek_chapter 1" > /tmp/famp-control')
      s.ww("True")

    elif ep=="/volume":
      os.system(f'echo "volume {qp["to"]} 1" > /tmp/famp-control')
      s.ww("True")

    elif ep=="/play":
      os.system(f'find "{mp + urllib.parse.unquote(qp["path"])}" | egrep -i "mp3|wma|ogg|flac" > famp.playlist')
      os.system(f'echo "loadlist {os.getcwd()}/famp.playlist" > /tmp/famp-control')
      s.ww("True")

    elif ep=="/list":
      s.ww(json.dumps(os.listdir(mp + urllib.parse.unquote(qp["path"]))))

if __name__=="__main__":
  if "famp-control" not in os.listdir("/tmp"):
    os.system("mkfifo /tmp/famp-control")
  os.system("mplayer -slave -input file=/tmp/famp-control -loop 0 silence.mp3 > /dev/null 2>&1 &")
  os.system(f'echo "volume 30 1" > /tmp/famp-control')
  os.system("amixer -c 1 set PCM 255")
  print("Started mplayer and set system volume to max")
  try:
    print ("Frank's Awesome Media Player started! Hit port 8000 for controls =]")
    http.server.HTTPServer(('', 8000), famp).serve_forever()
  except KeyboardInterrupt:
    print("\rBuh-bye!")
    os.system("echo 'quit' > /tmp/famp-control &")
    os.system("amixer -c 1 set PCM 0")
    os.system("unlink /tmp/famp-control")
    os.system("unlink famp.playlist")
    print("Quit mplayer and set system volume to zero")
