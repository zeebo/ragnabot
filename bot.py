import asyncore
import socket

from packet import make_packet_parser
LoginResponseParser = make_packet_parser('6900', (
  ('length', 2),
  ('l_id1', 4),
  ('a_id', 4),
  ('l_id2', 4),
  ('_', 4),
  ('_', 24),
  ('_', 2),
  ('sex', 1),
  ('servers', (
    ('ip', 4),
    ('port', 2),
    ('name', 20),
    ('users', 2),
    ('_', 2),
    ('_', 2),
  )),
))

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
    return bytes

class BasicDispatcher(asyncore.dispatcher):
  def __init__(self, *args, **kwargs):
    asyncore.dispatcher.__init__(self, *args, **kwargs)
    self.chunker = PacketChunker()

  def handle_read(self):
    self.chunker.add_data(self.recv(1024))
    while self.chunker.has_packet():
      self.handle_packet(self.chunker.get_packet())
      
  def writable(self):
    return False
  
  def handle_open(self):
    print "Connection made"
  
  def handle_close(self):
    print "Connection closed"
    self.close()
    
class BotDispatcher(BasicDispatcher):
  def handle_packet(self, packet):
    print packet

class LoginState(object):
  def __init__(self, username, password):
    self.username = username
    self.password = password
    self.sent_credentials = False
  
  def needs_to_login(self):
    return not self.sent_credentials
  
  def sent_login(self):
    self.sent_credentials = True
  
  def login_packet(self):
    return '\x64\x00\x18\x00\x00\x00%s%s\x12' % (self.username.ljust(24, '\x00'), self.password.ljust(24, '\x00'))

class LoginDispatcher(asyncore.dispatcher):
  def __init__(self, username, password, *args, **kwargs):
    asyncore.dispatcher.__init__(self, *args, **kwargs)
    self.state = LoginState(username, password)
    self.buffer = []
    
  def writable(self):
    return self.state.needs_to_login()
  
  def handle_close(self):
    self.close()
  
  def handle_read(self):
    data = self.recv(1024)
    self.buffer.append(data)
    hex_data = ''.join("%.2X" % ord(c) for c in data)
    print hex_data
    packet = LoginResponseParser(hex_data)
    print packet.data_dict()
    print ' '.join(packet.chunks)
    
  def handle_write(self):
    self.send(self.state.login_packet())
    self.state.sent_login()




login_socket = socket.create_connection(('192.168.1.5', 6900))
login_dispatcher = LoginDispatcher('Test', 'Test', login_socket)

asyncore.loop()