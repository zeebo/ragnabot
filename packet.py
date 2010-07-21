from itertools import izip, izip_longest
import unittest

class ParseError(Exception): pass

def make_packet_parser(header, data_spec):
  if len(header) != 4:
    raise ParseError('Header must be two bytes')
  
  if not all(isinstance(bytes, tuple) or isinstance(bytes, int) for _, bytes in data_spec):
    raise ParseError('Invalid data type')
  
  has_length = 'length' in (field_name for field_name, _ in data_spec)
  has_repeat = any(isinstance(bytes, tuple) for _, bytes in data_spec)
  if not has_repeat:
    repeat_len = 0
  else:
    repeat_tuple = (bytes for _, bytes in data_spec if isinstance(bytes, tuple)).next() 
    repeat_len = sum(bytes for _, bytes in repeat_tuple)
  
  if len(set(field_name for field_name, _ in data_spec)) != len(data_spec):
    raise ParseError('Duplicate field names')
  if has_repeat and not has_length:
    raise ParseError('Repeat without length field')
  if has_length and data_spec[0] != ('length', 2):
    raise ParseError('Length must be first field of two bytes')
  if has_length and not has_repeat:
    if not any(bytes == 0 for _, bytes in data_spec):
      raise ParseError('Length but no indeterminate field')
  
  if sum(1 for _, bytes in data_spec if (bytes == 0 or isinstance(bytes, tuple))) > 1:
    raise ParseError('Too many indeterminate fields')
  
  if has_length:
    data_len = -1
  else:
    data_len = sum(bytes for _, bytes in data_spec)
  
  class Packet(object):
    def __init__(self, d_data = None):
      self.raw_data = d_data
      self.fields = []
      self.chunks = []
      
      if d_data != None:
        self.parse(d_data)
    
    def data_len(self):
      if has_length:
        return -1
      #sum it
      return sum(bytes for _, bytes in data_spec if not isinstance(bytes, tuple))
    
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
    
    def data_dict(self):
      return dict((name, getattr(self, name)) for name in self.fields)
    
    def get_data(self, data_gen, count):
      try:
        returned_data = [data_gen.next() for _ in xrange(count)]
        self.chunks.append(''.join(returned_data))
        return returned_data
      except StopIteration:
        raise ParseError('Not enough data in packet.')
    
    def set(self, name, data):
      self.fields.append(name)
      setattr(self, name, data)
  
    def parse(self, d_data):
      """
      parses data into specified data_spec.
      d_data: '00ab....1345' string of bytes in hex code format
      """
      
      self.raw_data = d_data
      self.chunks = []
      
      while len(self.fields):
        delattr(self, self.fields.pop(0))
      
      if isinstance(d_data, str):
        d_data_split = (''.join(x) for x in izip(*[iter(d_data)]*2))
        raw_data_len = len(d_data) / 2
      elif isinstance(d_data, list):
        d_data_split = iter(d_data)
        raw_data_len = len(d_data)
      else:
        raise ParseError('Unable to handle data type %s' % type(d_data))
      
      if raw_data_len < 4:
        raise ParseError('No header to parse')
      
      d_header = ''.join(self.get_data(d_data_split, 2))
      if d_header != header:
        raise ParseError('Header mismatch. Got %s, expected %s' % (d_header, header))
      
      if data_len == -1:
        len_bytes = self.get_data(d_data_split, 2)
        p_data_len = int(''.join(reversed(len_bytes)), 16) - 4 #Subtract header/len bytes
      else:
        p_data_len = data_len - 2
      
      if (p_data_len + 4) != raw_data_len:
        raise ParseError('Length mismatch. Expected %d and got %d' % ((p_data_len + 4), raw_data_len))
      
      offset = 0
      for count, (field_name, bytes) in enumerate(data_spec):
        if field_name == "length":
          self.set(field_name, p_data_len + 4)
        elif isinstance(bytes, tuple):
          #Figure out how many bytes are going to be left on the end
          other_data = sum(bytes for _, bytes in data_spec[count+1:])
          field_list = []
          
          while p_data_len - offset > other_data:
            sub_field_dict = {}
            self.chunks.append('{')
            for sub_field_name, sub_bytes in bytes:
              data = self.get_data(d_data_split, sub_bytes)
              offset += sub_bytes
              sub_field_dict[sub_field_name] = data
            field_list.append(sub_field_dict)
            self.chunks.append('}')
            
          self.set(field_name, field_list)
        else:
          if bytes == 0:
            #Figure out how many bytes we need to read
            other_data = sum(bytes for _, bytes in data_spec[count+1:])
            bytes = p_data_len - offset - other_data
          
          data = self.get_data(d_data_split, bytes)
          offset += bytes
          
          self.set(field_name, data)
  
  return Packet

class TestInvalidParsers(unittest.TestCase):
  def test_bad_header(self):
    self.assertRaises(ParseError, make_packet_parser, '00', None)
    self.assertRaises(ParseError, make_packet_parser, '000001', None)
  def test_bad_data_type(self):
    self.assertRaises(ParseError, make_packet_parser, '0000', (
      ('repeat', 'lol'),
    ))

  def test_repeat_no_len(self):
    self.assertRaises(ParseError, make_packet_parser, '0000', (
      ('repeat', (
                  ('field', 1),
                )),
      ))
  def test_len_not_first(self):
    self.assertRaises(ParseError, make_packet_parser, '0000', (
      ('field_1', 2),
      ('length', 2),
      ('field_2', 0),
    ))
  def test_len_wrong_size(self):
    self.assertRaises(ParseError, make_packet_parser, '0000', (
      ('length', 3),
      ('field_1', 0),
    ))
    self.assertRaises(ParseError, make_packet_parser, '0000', (
      ('length', 1),
      ('field_1', 0),
    ))
  def test_length_no_indeterminate(self):
    self.assertRaises(ParseError, make_packet_parser, '0000', (
      ('length', 2),
      ('field_1', 1),
    ))
  def test_length_too_many_indeterminate(self):
    self.assertRaises(ParseError, make_packet_parser, '0000', (
      ('length', 2),
      ('field_1', 0),
      ('field_2', 0),
    ))
    self.assertRaises(ParseError, make_packet_parser, '0000', (
      ('length', 2),
      ('field_1', (('thing', 0),) ),
      ('field_2', 0),
    ))
    self.assertRaises(ParseError, make_packet_parser, '0000', (
      ('length', 2),
      ('field_1', (('thing', 0),) ),
      ('field_2', (('thing', 0),) ),
    ))
  def test_field_name_collision(self):
    self.assertRaises(ParseError, make_packet_parser, '0000', (
      ('field_1', 1),
      ('field_1', 1),
    ))

class TestInvalidParsing(unittest.TestCase):
  def setUp(self):
    self.basic_parser = make_packet_parser('0012', (
      ('field_1', 2),
      ('field_2', 2),
      ('field_3', 4),
    ))().parse
    
    self.length_parser = make_packet_parser('0012', (
      ('length', 2),
      ('field_1', 4),
      ('field_2', 0),
    ))().parse
    
    self.repeat_parser = make_packet_parser('0012', (
      ('length', 2),
      ('field_1', 1),
      ('field_2', (
        ('field_3', 1),
        ('field_4', 1),
      )),
    ))().parse
  
  def test_basic_wrong_length(self):
    self.assertRaises(ParseError, self.basic_parser, '001200010002000000')
    self.assertRaises(ParseError, self.basic_parser, '0012000100020000000300')
  
  def test_length_wrong_length(self):
    self.assertRaises(ParseError, self.length_parser, '0012090000000000') #One too few bytes for length
    self.assertRaises(ParseError, self.length_parser, '00120800000000')   #One too few before it gets to length
  
  def test_repeat_wrong_length(self):
    self.assertRaises(ParseError, self.repeat_parser, '00120000010304')
    self.assertRaises(ParseError, self.repeat_parser, '00120800010304')
    self.assertRaises(ParseError, self.repeat_parser, '00120600010304')
    self.assertRaises(ParseError, self.repeat_parser, '0012080001030405')
  
class TestValidParsing(unittest.TestCase):  
  def do_parse_test(self, parser, cases, responses, chunks):
    for data, response, chunk in izip_longest(cases, responses, chunks):
      parser.parse(data)
      self.assertEqual(parser.data_dict(), response)
      self.assertEqual(' '.join(parser.chunks), chunk)
      
      pre_split_data = list(''.join(x) for x in izip(*[iter(data)]*2))
      parser.parse(pre_split_data)
      self.assertEqual(parser.data_dict(), response)
      self.assertEqual(' '.join(parser.chunks), chunk)

      
  def test_basic(self):
    test_parser = make_packet_parser('0012', (
      ('field_1', 2),
      ('field_2', 2),
      ('field_3', 4),
    ))
    p = test_parser()
    test_cases = ['00120001000200000003']
    responses = [
      {'field_2': ['00', '02'], 'field_3': ['00', '00', '00', '03'], 'field_1': ['00', '01']},
    ]
    chunks = [
      '0012 0001 0002 00000003',
    ]
    self.do_parse_test(p, test_cases, responses, chunks)
  
  def test_repeat(self):
    test_parser = make_packet_parser('0012', (
      ('length', 2),
      ('field_3', (
                    ('lol', 1),
                    ('what', 1),
                  )),
    ))
    p = test_parser()
    test_cases = ['001206001234', '0012080012345678']
    responses = [
      {'length': 6, 'field_3': [{'what': ['34'], 'lol': ['12']}]},
      {'length': 8, 'field_3': [{'what': ['34'], 'lol': ['12']}, {'what': ['78'], 'lol': ['56']}]},
    ]
    chunks = [
      '0012 0600 { 12 34 }',
      '0012 0800 { 12 34 } { 56 78 }',
    ]
    self.do_parse_test(p, test_cases, responses, chunks)
    
  
  def test_repeat_clamped(self):
    test_parser = make_packet_parser('0012', (
      ('length', 2),
      ('field_1', 2),
      ('field_3', (
                    ('lol', 1),
                    ('what', 1),
                  )),
      ('field_4', 1),
    ))
    p = test_parser()
    test_cases = ['001209000100123404', '00120b0001001234567804']
    responses = [
      {'length': 9, 'field_4': ['04'], 'field_3': [{'what': ['34'], 'lol': ['12']}], 'field_1': ['01', '00']},
      {'length': 11, 'field_4': ['04'], 'field_3': [{'what': ['34'], 'lol': ['12']}, {'what': ['78'], 'lol': ['56']}], 'field_1': ['01', '00']},
    ]
    chunks = [
      '0012 0900 0100 { 12 34 } 04',
      '0012 0b00 0100 { 12 34 } { 56 78 } 04',
    ]
    self.do_parse_test(p, test_cases, responses, chunks)
  
  def test_repeat_no_after(self):
    test_parser = make_packet_parser('0012', (
      ('length', 2),
      ('field_2', 1),
      ('field_3', (
                    ('lol', 1),
                    ('what', 1),
                  )),
    ))
    p = test_parser()
    test_cases = ['00120700021234', '001209000212345678']
    responses = [
      {'length': 7, 'field_2': ['02'], 'field_3': [{'what': ['34'], 'lol': ['12']}]},
      {'length': 9, 'field_2': ['02'], 'field_3': [{'what': ['34'], 'lol': ['12']}, {'what': ['78'], 'lol': ['56']}]},
    ]
    chunks = [
      '0012 0700 02 { 12 34 }',
      '0012 0900 02 { 12 34 } { 56 78 }',
    ]
    self.do_parse_test(p, test_cases, responses, chunks)
    
  def test_repeat_no_before(self):
    test_parser = make_packet_parser('0012', (
      ('length', 2),
      ('field_3', (
                    ('lol', 1),
                    ('what', 1),
                  )),
      ('field_1', 1),
    ))
    p = test_parser()
    test_cases = ['00120700123401', '001209001234567801']
    responses = [
      {'length': 7, 'field_3': [{'what': ['34'], 'lol': ['12']}], 'field_1': ['01']},
      {'length': 9, 'field_3': [{'what': ['34'], 'lol': ['12']}, {'what': ['78'], 'lol': ['56']}], 'field_1': ['01']},
    ]
    chunks = [
      '0012 0700 { 12 34 } 01',
      '0012 0900 { 12 34 } { 56 78 } 01',
    ]
    self.do_parse_test(p, test_cases, responses, chunks)
  
  def test_len(self):
    test_parser = make_packet_parser('0012', (
      ('length', 2),
      ('field_3', 0),
    ))
    p = test_parser()
    test_cases = ['001206001234', '0012080012345678', '00120400']
    responses = [
      {'length': 6, 'field_3': ['12', '34']},
      {'length': 8, 'field_3': ['12', '34', '56', '78']},
      {'length': 4, 'field_3': []}
    ]
    chunks = [
      '0012 0600 1234',
      '0012 0800 12345678',
      '0012 0400 ',
    ]
    self.do_parse_test(p, test_cases, responses, chunks)
  
  def test_len_before(self):
    test_parser = make_packet_parser('0012', (
      ('length', 2),
      ('field_1', 1),
      ('field_3', 0),
    ))
    p = test_parser()
    test_cases = ['00120700011234', '001209000112345678']
    responses = [
      {'length': 7, 'field_3': ['12', '34'], 'field_1': ['01']},
      {'length': 9, 'field_3': ['12', '34', '56', '78'], 'field_1': ['01']},
    ]
    chunks = [
      '0012 0700 01 1234',
      '0012 0900 01 12345678',
    ]
    self.do_parse_test(p, test_cases, responses, chunks)
  
  def test_len_after(self):
    test_parser = make_packet_parser('0012', (
      ('length', 2),
      ('field_3', 0),
      ('field_1', 1),
    ))
    p = test_parser()
    test_cases = ['001206001234', '0012080012345678']
    responses = [
      {'length': 6, 'field_3': ['12'], 'field_1': ['34']},
      {'length': 8, 'field_3': ['12', '34', '56'], 'field_1': ['78']},
    ]
    chunks = [
      '0012 0600 12 34',
      '0012 0800 123456 78',
    ]
    self.do_parse_test(p, test_cases, responses, chunks)
    
  
  def test_len_clamped(self):
    test_parser = make_packet_parser('0012', (
      ('length', 2),
      ('field_1', 1),
      ('field_3', 0),
      ('field_2', 1),
    ))
    p = test_parser()
    test_cases = ['00120700120034', '0012080012345678']
    responses = [
      {'length': 7, 'field_2': ['34'], 'field_3': ['00'], 'field_1': ['12']},
      {'length': 8, 'field_2': ['78'], 'field_3': ['34', '56'], 'field_1': ['12']}
    ]
    chunks = [
      '0012 0700 12 00 34',
      '0012 0800 12 3456 78',
    ]
    self.do_parse_test(p, test_cases, responses, chunks)


if __name__ == '__main__':
  unittest.main()