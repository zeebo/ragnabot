import asyncore

class ParseError(Exception): pass

def reverse_bytes(data):
  def chunks(iterable, amount):
    for i in xrange(0, len(iterable), amount):
      yield iterable[i:i+amount]
  return ''.join(reversed(tuple(chunks(data, 2))))

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
    self.packets = []
    
    self.state = None
  
  def get_bytes(self, amount):
    if len(self.data) < amount:
      raise ValueError('Not enough data')
    ret_val, self.data = self.data[:amount], self.data[amount:]
    return ret_val
    
  def add_data(self, data):
    #Data is raw bytes. Convert to hex.
    self.data.extend("%.2X" % ord(c) for c in data)
  
  def get_header(self):
    if len(self.data) < 2:
      return None
    return self.data[:2]
  
  def get_length(self, header):
    if header is None:
      return None
    
    packet_len = int(self.packets.get(header, 0))
    if packet_len == -1:
      packet_len = int(reverse_bytes(self.data[2:4]), 16)
    
    if packet_len == 0:
      raise ParseError('Error parsing header %s' % header)
    
    return packet_len
  
  def has_packet(self):
    data_required = self.get_length(self.get_header())
    return len(self.data) >= data_required
  
  def get_packet(self):
    data_required = self.get_length(self.get_header())
    bytes = self.get_bytes(data_required)
    return bytes[:2], bytes[2:]
  
class BotDispatcher(asyncore.dispatcher):
  def __init__(self, *args, **kwargs):
    super(self, BotDispatcher).__init__(self, *args, **kwargs)
    self.chunker = PacketChunker()
  
  def handle_read(self, data):
    self.chunker.add_data(data)
    while self.chunker.has_packet():
      print self.chunker.get_packet()

