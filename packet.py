class ParseError(Exception): pass

def make_packet_parser(header, data_spec):
  class Packet(object):
    def __init__(self, d_header, d_data):
      assert header == d_header
      
      self.parse(d_data)
    
    def len(self):
      if any(isinstance(bytes, tuple) for _, bytes in data_spec):
        return -1
      if any(field_name == 'length', for field_name, _ in data_spec):
        return -1
      #sum it
      return 0
    
    def parse(self, d_data):
      for field_name, bytes in data_spec:
        if isinstance(bytes, tuple):
          pass