import socket
import threading
import SocketServer
import asyncore

def RequestHandlerFactory(server, port):
  class ThreadedRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
      print "Got request (%s of %d): %s" % (threading.current_thread().getName(), threading.active_count(), self.request.getsockname())
      
      #Create a swapper object and pass in the client socket
      #and the address of the server to connect to
      s = SwapHandler(self.request, server, port)
      
      #Begin the asyncore runloop
      s.loop()
      
  return ThreadedRequestHandler

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
  pass
  
if __name__ == '__main__':
  HOST, PORT = "192.168.1.8", 9000
  server = ThreadedTCPServer((HOST, PORT), RequestHandlerFactory('dummy', 1234))
  print server.server_address
  server.serve_forever()
  