import asyncore
import socket
import threading

def hex_print(data, bytes_per_line = 20, bytes_per_break = 5):
  if bytes_per_line > 100:
    bytes_per_line = 100
    
  if bytes_per_break <= 0 or bytes_per_line % bytes_per_break != 0:
    bytes_per_break = bytes_per_line
  
  for offset in xrange(0, len(data), bytes_per_line):
    for break_counter in xrange(0, bytes_per_line, bytes_per_break):
      print ' '.join("%02x" % ord(char) for char in data[offset+break_counter:offset+break_counter+bytes_per_break]),
      if break_counter != bytes_per_line - bytes_per_break and offset+break_counter+bytes_per_break < len(data):
        print '|',
    print ''


class AsyncHandler(asyncore.dispatcher):
  def __init__(self, socket, sid, swapper):
    asyncore.dispatcher.__init__(self, sock=socket, map=swapper.map)
    self.swapper = swapper
    self.id = sid
  
  def fileno(self):
    return self.socket.fileno()
  
  def handle_connect(self):
    pass
  
  def handle_close(self):
    self.swapper.handle_close(self.id)
  
  def handle_read(self):
    self.swapper.handle_read(self.id, self.recv(8192))
  
  def handle_write(self):
    self.swapper.handle_write(self.id)
  
  def writable(self):
    return self.swapper.writable(self.id)
  
class SwapHandler(object):
  def __init__(self, client_socket, server_address, server_port, processor):
    server_socket = socket.create_connection((server_address, server_port))
      
    self.map = {}
    
    self.sockets = {
                      'client': AsyncHandler(client_socket, 'client', self),
                      'server': AsyncHandler(server_socket, 'server', self),
                   }
    
    self.processor = processor()
  
  def other(self, sid):
    return {'client':'server', 'server':'client'}[sid]
  
  def handle_close(self, sid):
    if not self.processor.is_writable(sid):
      self.sockets[sid].close()
    
    if not self.processor.is_writable(self.other(sid)):
      self.sockets[self.other(sid)].close()
    
  
  def handle_read(self, sid, data):
    self.processor.read_event(sid, data)
  
  def handle_write(self, sid):
    sent = self.sockets[sid].send(self.processor.get_data(sid))
    self.processor.sent_bytes_event(sid, sent)
    
    #check if theres no data and the other socket is closed
    if not self.processor.is_writable(sid) and not self.sockets[self.other(sid)].connected:
      self.sockets[sid].close()
  
  def writable(self, sid):
    return self.processor.is_writable(sid)
  
  def loop(self):
    asyncore.loop(map = self.map)