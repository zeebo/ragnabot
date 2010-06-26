import socket
import threading
import SocketServer
from swapper import SwapHandler
from processor import EchoProcessor, SimpleReplacerFactory

def RequestHandlerFactory(server, port, processor):
  class ThreadedRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
      print "Got request (%s of %d): %s" % (threading.current_thread().getName(), threading.active_count(), self.request.getsockname())
      
      #Create a swapper object and pass in the client socket
      #and the address of the server to connect to
      s = SwapHandler(self.request, server, port, processor)
      
      #Begin the asyncore runloop
      s.loop()
      
  return ThreadedRequestHandler

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
  pass

def start_servers(servers):
  server_list = []
  for listen_port, server, port, processor in servers:
    temp_server = ThreadedTCPServer(('', listen_port), RequestHandlerFactory(server, port, processor))
    temp_thread = threading.Thread(target=temp_server.serve_forever)
    temp_thread.start()
    
    server_list.append(temp_server)
    print "Starting server on port [%d] and thread [%s] to [%s:%d]." % (listen_port, temp_thread.getName(), server, port)
  
  return server_list

if __name__ == '__main__':
  #ThreadedTCPServer(('localhost', 80), RequestHandlerFactory('google.com', 80)).serve_forever()
  
  server_list = (
    (8000, 'google.com', 80, EchoProcessor),
    (8001, 'forums.somethingawful.com', 80, SimpleReplacerFactory({'Python':'Doofus'})),
  )
  
  servers = start_servers(server_list)
  
  try:
    while True:
      if (raw_input('') == 'q'):
        break
  except KeyboardInterrupt:
    pass
  finally:
    for server in servers:
      print "Shutting down server on %s:%d" % server.server_address
      server.shutdown()
