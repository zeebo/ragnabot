import asyncore
import socket

class ParseError(Exception): pass

class PacketChunker(object):
  packets = {}
  with open('packets.txt') as f:
    for line in f:
      if line[:2] != '0x':
        continue
      header, length = line.strip().split(',')[:2]
      packets[header[4:6]+header[2:4]] = length
  
  def __init__(self):
    self.data = []
  
  def get_bytes(self, amount):
    if len(self.data) < amount:
      raise ValueError('Not enough data')
    ret_val = self.data[:amount]
    del self.data[:amount]
    return ret_val
    
  def add_data(self, data):
    #Data is raw bytes. Convert to hex.
    self.data.extend("%.2x" % ord(c) for c in data)
  
  def get_header(self):
    if len(self.data) < 2:
      return None
    return ''.join(self.data[:2])
  
  def get_length(self, header):
    if header is None:
      return 0
    
    packet_len = int(self.packets.get(header, 0))
    if packet_len == -1:
      if len(self.data) < 4:
        return 0
      packet_len = int(''.join(reversed(self.data[2:4])), 16)
    
    if packet_len == 0:
      raise ParseError('Error parsing header %s' % header)
    
    return packet_len
  
  def has_packet(self):
    data_required = self.get_length(self.get_header())
    return len(self.data) >= data_required and data_required > 0
  
  def get_packet(self):
    data_required = self.get_length(self.get_header())
    bytes = self.get_bytes(data_required)
    return ''.join(bytes[:2]), ''.join(bytes[2:])
  
class BotDispatcher(asyncore.dispatcher):
  def __init__(self, *args, **kwargs):
    asyncore.dispatcher.__init__(self, *args, **kwargs)
    self.chunker = PacketChunker()
  
  def handle_read(self):
    self.chunker.add_data(self.recv(1024))
    while self.chunker.has_packet():
      self.handle_packet(self.chunker.get_packet())
  
  def handle_packet(self, packet):
    print packet
  
  def writable(self):
    return False
  
  def handle_close(self):
    print "Connection closed"
    self.close()

client = socket.create_connection(('localhost', 50001))
my_dispatcher = BotDispatcher(sock=client)
asyncore.loop()