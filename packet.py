from itertools import izip

class ParseError(Exception): pass

def make_packet_parser(header, data_spec):
  class Packet(object):
    def __init__(self, d_data = None):
      self.raw_data = ''
      self.fields = []
      if d_data is not None:
        assert len(d_data) > 4
        d_header = d_data[:4]
        del d_data[:4]        
        assert header == d_header
        if self.has_length():
          assert data_spec[0] == ('length', 2)      
        assert len(set(field_name for field_name, _ in data_spec)) == len(data_spec)
        self.parse(d_data)
    
    def data_len(self):
      if self.has_length():
        return -1
      
      #sum it
      return sum(bytes for _, bytes in data_spec if not isinstance(bytes, tuple))
    
    def repeat_len(self):
      if not self.has_repeat():
        return 0      
      repeat_tuple = [bytes for _, bytes in data_spec if isinstance(bytes, tuple)][0]      
      return sum(bytes for _, bytes in repeat_tuple)
      
    def has_repeat(self):
      return any(isinstance(bytes, tuple) for _, bytes in data_spec)
    
    def has_length(self):
      return 'length' in (field_name for field_name, _ in data_spec)
    
    def __repr__(self):
      chunks = []
      for field_name, bytes in data_spec:
        if isinstance(bytes, tuple):
          chunks.append('%s.{' % field_name)
          
          for sub_field_name, sub_bytes in bytes:
            chunks.append('%s:%d' % (sub_field_name, sub_bytes))
          
          chunks.append('}')
        else:
          if bytes == 0:
            chunks.append('%s:-' % field_name)
          else:
            chunks.append('%s:%d' % (field_name, bytes))
      return ' '.join(chunks)
    
    def get_data(self, data_gen, count):
      try:
        return [data_gen.next() for _ in xrange(count)]
      except StopIteration:
        raise ParseError('Not enough data in packet.')
    
    def set(self, name, data):
      self.fields.append(name)
      setattr(self, name, data)
  
    def parse(self, d_header, d_data):
      """
      parses data into specified data_spec.
      d_data: '00ab....1345' string of bytes in hex code format
      """
      assert d_header == header
      
      self.raw_data = d_data
      
      while len(self.fields):
        delattr(self, self.fields.pop(0))
      
      d_data_split = (''.join(x) for x in izip(*[iter(d_data)]*2))
      
      if self.data_len() == -1:
        data_len = int(''.join(reversed(self.get_data(d_data_split, 2))), 16) - 4 #Subtract header/len bytes
      else:
        data_len = self.data_len()
      
      offset = 0
      for count, (field_name, bytes) in enumerate(data_spec):
        if field_name == "length":
          self.set(field_name, data_len + 4)
        elif isinstance(bytes, tuple):
          #Figure out how many bytes are going to be left on the end
          other_data = sum(bytes for _, bytes in data_spec[count+1:])
          field_list = []
          
          while data_len - offset > other_data:
            sub_field_dict = {}
            for sub_field_name, sub_bytes in bytes:
              data = self.get_data(d_data_split, sub_bytes)
              offset += sub_bytes
              sub_field_dict[sub_field_name] = data
            field_list.append(sub_field_dict)
          
          self.set(field_name, field_list)
        else:
          if bytes == 0:
            #Figure out how many bytes we need to read
            other_data = sum(bytes for _, bytes in data_spec[count+1:])
            bytes = data_len - offset - other_data
          
          data = self.get_data(d_data_split, bytes)
          offset += bytes
          
          self.set(field_name, data)
  
  return Packet


test_parser = make_packet_parser('0012', (
  ('length', 2),
  ('field_2', 1),
  ('field_3', (
                ('lol', 1),
                ('what', 1),
              )),
  ('field_4', 1),
))

p = test_parser('0012080002123404')
for field in p.fields:
  print '%s: %s' % (field, str(getattr(p, field)))