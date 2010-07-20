bytes = []
with open('testpacks.packs') as f:
  temp_datas = []
  for line in f:
    if line.strip() == '' and len(temp_datas):
      bytes.extend(temp_datas[54:])
      temp_datas = []
    else:
      temp_datas.extend(line.strip().split())

#ok listen, accept, print data, close.

import socket
import SocketServer

class RequestHandler(SocketServer.BaseRequestHandler):
  def handle(self):
    print 'Connected by', self.request.getsockname()
    for byte in bytes:
      self.request.send(chr(int(byte, 16)))
    self.request.close()

server = SocketServer.TCPServer(('', 50001), RequestHandler)
server.serve_forever()

