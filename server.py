import socket
import threading
import SocketServer

class ThreadedRequestHandler(SocketServer.BaseRequestHandler):
  def handle(self):
    print "Got request (%s of %d): %s" % (threading.current_thread().getName(), threading.active_count(), self.request.getsockname())
    self.request.send('LOL YALL\n')
    self.request.recv(1024)
    self.request.shutdown(socket.SHUT_RDWR)
    self.request.close()

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
  pass
  
if __name__ == '__main__':
  HOST, PORT = "192.168.1.8", 9000
  server = ThreadedTCPServer((HOST, PORT), ThreadedRequestHandler)
  
  print server.server_address
  
  server.serve_forever()