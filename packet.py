from itertools import izip, izip_longest
import unittest

class ParseError(Exception): pass

def hex_repr(data):
  return ''.join('%.2X' % ord(c) for c in data)

def make_packet_parser(header, data_spec):
  if len(header) != 2:
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
  
  if len(set(field_name for field_name, _ in data_spec if field_name != '_')) != len([field_name for field_name, _ in data_spec if field_name != '_']):
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
  
  def parser(d_data, format = 'dict'):
    """
    parses data into specified data_spec.
    d_data: '\x00\xAB....\x13\x45' string of bytes
    """

    chunks = []
    data_dict = {}
    
    d_data_split = iter(d_data)
    raw_data_len = len(d_data)
    
    def set_field(name, data):
      if name != '_':
        data_dict[name] = data
    
    def get_data(data_gen, count):
      try:
        returned_data = ''.join(data_gen.next() for _ in xrange(count))
        chunks.append(hex_repr(returned_data))
        return returned_data
      except StopIteration:
        raise ParseError('Not enough data in packet.')
    
    if raw_data_len < 2:
      raise ParseError('No header to parse')
    
    d_header = get_data(d_data_split, 2)
    
    if d_header != header:
      raise ParseError('Header mismatch. Got %s, expected %s' % (hex_repr(d_header), hex_repr(header)))
    
    if data_len == -1:
      len_bytes = get_data(d_data_split, 2)
      p_data_len = ord(len_bytes[0]) + 256*ord(len_bytes[1]) - 4 #Subtract header/len bytes
    else:
      p_data_len = data_len - 2 #Subtract just the header bytes
    
    if (p_data_len + 4) != raw_data_len:
      raise ParseError('Length mismatch. Expected %d and got %d' % ((p_data_len + 4), raw_data_len))
    
    offset = 0
    for count, (field_name, bytes) in enumerate(data_spec):
      if field_name == "length":
        set_field(field_name, p_data_len + 4)
      elif isinstance(bytes, tuple):
        #Figure out how many bytes are going to be left on the end
        other_data = sum(bytes for _, bytes in data_spec[count+1:])
        field_list = []
        
        while p_data_len - offset > other_data:
          sub_field_dict = {}
          chunks.append('{')
          for sub_field_name, sub_bytes in bytes:
            data = get_data(d_data_split, sub_bytes)
            offset += sub_bytes
            if sub_field_name != '_':
              sub_field_dict[sub_field_name] = data
          field_list.append(sub_field_dict)
          chunks.append('}')
          
        set_field(field_name, field_list)
      else:
        if bytes == 0:
          #Figure out how many bytes we need to read
          other_data = sum(bytes for _, bytes in data_spec[count+1:])
          bytes = p_data_len - offset - other_data
        
        data = get_data(d_data_split, bytes)
        offset += bytes
        
        set_field(field_name, data)
      
    if format == 'dict':
      return data_dict
    elif format == 'chunks':
      return ' '.join(chunks)
    elif format == 'all':
      return data_dict, ' '.join(chunks)
    else:
      raise ParseError('Unknown format: %s' % format)
      
  return parser

class TestInvalidParsers(unittest.TestCase):
  def test_bad_header(self):
    self.assertRaises(ParseError, make_packet_parser, '\x00', None)
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00\x01', None)
  def test_bad_data_type(self):
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00', (
      ('repeat', 'lol'),
    ))

  def test_repeat_no_len(self):
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00', (
      ('repeat', (
                  ('field', 1),
                )),
      ))
  def test_len_not_first(self):
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00', (
      ('field_1', 2),
      ('length', 2),
      ('field_2', 0),
    ))
  def test_len_wrong_size(self):
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00', (
      ('length', 3),
      ('field_1', 0),
    ))
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00', (
      ('length', 1),
      ('field_1', 0),
    ))
  def test_length_no_indeterminate(self):
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00', (
      ('length', 2),
      ('field_1', 1),
    ))
  def test_length_too_many_indeterminate(self):
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00', (
      ('length', 2),
      ('field_1', 0),
      ('field_2', 0),
    ))
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00', (
      ('length', 2),
      ('field_1', (('thing', 0),) ),
      ('field_2', 0),
    ))
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00', (
      ('length', 2),
      ('field_1', (('thing', 0),) ),
      ('field_2', (('thing', 0),) ),
    ))
  def test_field_name_collision(self):
    self.assertRaises(ParseError, make_packet_parser, '\x00\x00', (
      ('field_1', 1),
      ('field_1', 1),
    ))

class TestInvalidParsing(unittest.TestCase):
  def setUp(self):
    self.basic_parser = make_packet_parser('\x00\x12', (
      ('field_1', 2),
      ('field_2', 2),
      ('field_3', 4),
    ))
    
    self.length_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_1', 4),
      ('field_2', 0),
    ))
    
    self.repeat_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_1', 1),
      ('field_2', (
        ('field_3', 1),
        ('field_4', 1),
      )),
    ))
  
  def test_basic_wrong_length(self):
    self.assertRaises(ParseError, self.basic_parser, '\x00\x12\x00\x01\x00\x02\x00\x00\x00')
    self.assertRaises(ParseError, self.basic_parser, '\x00\x12\x00\x01\x00\x02\x00\x00\x00\x03\x00')
  
  def test_length_wrong_length(self):
    self.assertRaises(ParseError, self.length_parser, '\x00\x12\x09\x00\x00\x00\x00\x00') #One too few bytes for length
    self.assertRaises(ParseError, self.length_parser, '\x00\x12\x08\x00\x00\x00\x00')   #One too few before it gets to length
  
  def test_repeat_wrong_length(self):
    self.assertRaises(ParseError, self.repeat_parser, '\x00\x12\x00\x00\x01\x03\x04')
    self.assertRaises(ParseError, self.repeat_parser, '\x00\x12\x08\x00\x01\x03\x04')
    self.assertRaises(ParseError, self.repeat_parser, '\x00\x12\x06\x00\x01\x03\x04')
    self.assertRaises(ParseError, self.repeat_parser, '\x00\x12\x08\x00\x01\x03\x04\x05\x06')
  
class TestValidParsing(unittest.TestCase):  
  def do_parse_test(self, parser, cases, responses, chunks):
    for data, response, chunk in izip_longest(cases, responses, chunks):
      data_dict, data_chunks = parser(data, format = "all")
      self.assertEqual(data_dict, response)
      self.assertEqual(data_chunks, chunk)
      
      pre_split_data = list(iter(data))
      data_dict, data_chunks = parser(pre_split_data, format = "all")
      self.assertEqual(data_dict, response)
      self.assertEqual(data_chunks, chunk)
  
  def test_multiple_uncaptured(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('field_1', 2),
      ('_', 2),
      ('_', 2),
    ))
    test_cases = ['\x00\x12\x00\x01\x99\x99\x00\x02']
    responses = [
      {'field_1': '\x00\x01'},
    ]
    chunks = [
      '0012 0001 9999 0002',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
  
  def test_uncaputred_in_repeat(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_1', (
        ('field_2', 2),
        ('_', 2),
        ('field_3', 2),
      )),
    ))
    test_cases = ['\x00\x12\x0A\x00\x00\x01\x99\x99\x00\x02', '\x00\x12\x10\x00\x00\x01\x99\x99\x00\x02\x00\x03\x99\x99\x00\x04']
    responses = [
      {'length': 10, 'field_1': [{'field_2': '\x00\x01', 'field_3': '\x00\x02'}]},
      {'length': 16, 'field_1': [{'field_2': '\x00\x01', 'field_3': '\x00\x02'}, {'field_2': '\x00\x03', 'field_3': '\x00\x04'}]},
    ]
    chunks = [
      '0012 0A00 { 0001 9999 0002 }',
      '0012 1000 { 0001 9999 0002 } { 0003 9999 0004 }',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
  
  def test_uncaputred(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('field_1', 2),
      ('_', 2),
      ('field_2', 2),
    ))
    test_cases = ['\x00\x12\x00\x01\x99\x99\x00\x02']
    responses = [
      {'field_1': '\x00\x01', 'field_2': '\x00\x02'},
    ]
    chunks = [
      '0012 0001 9999 0002',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
  
  def test_basic(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('field_1', 2),
      ('field_2', 2),
      ('field_3', 4),
    ))
    test_cases = ['\x00\x12\x00\x01\x00\x02\x00\x00\x00\x03']
    responses = [
      {'field_2': '\x00\x02', 'field_3': '\x00\x00\x00\x03', 'field_1': '\x00\x01'},
    ]
    chunks = [
      '0012 0001 0002 00000003',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
  
  def test_repeat(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_3', (
                    ('lol', 1),
                    ('what', 1),
                  )),
    ))
    test_cases = ['\x00\x12\x06\x00\x12\x34', '\x00\x12\x08\x00\x12\x34\x56\x78']
    responses = [
      {'length': 6, 'field_3': [{'what': '\x34', 'lol': '\x12'}]},
      {'length': 8, 'field_3': [{'what': '\x34', 'lol': '\x12'}, {'what': '\x78', 'lol': '\x56'}]},
    ]
    chunks = [
      '0012 0600 { 12 34 }',
      '0012 0800 { 12 34 } { 56 78 }',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
    
  def test_repeat_clamped(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_1', 2),
      ('field_3', (
                    ('lol', 1),
                    ('what', 1),
                  )),
      ('field_4', 1),
    ))
    test_cases = ['\x00\x12\x09\x00\x01\x00\x12\x34\x04', '\x00\x12\x0B\x00\x01\x00\x12\x34\x56\x78\x04']
    responses = [
      {'length': 9, 'field_4': '\x04', 'field_3': [{'what': '\x34', 'lol': '\x12'}], 'field_1': '\x01\x00'},
      {'length': 11, 'field_4': '\x04', 'field_3': [{'what': '\x34', 'lol': '\x12'}, {'what': '\x78', 'lol': '\x56'}], 'field_1': '\x01\x00'},
    ]
    chunks = [
      '0012 0900 0100 { 12 34 } 04',
      '0012 0B00 0100 { 12 34 } { 56 78 } 04',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
  
  def test_repeat_no_after(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_2', 1),
      ('field_3', (
                    ('lol', 1),
                    ('what', 1),
                  )),
    ))
    test_cases = ['\x00\x12\x07\x00\x02\x12\x34', '\x00\x12\x09\x00\x02\x12\x34\x56\x78']
    responses = [
      {'length': 7, 'field_2': '\x02', 'field_3': [{'what': '\x34', 'lol': '\x12'}]},
      {'length': 9, 'field_2': '\x02', 'field_3': [{'what': '\x34', 'lol': '\x12'}, {'what': '\x78', 'lol': '\x56'}]},
    ]
    chunks = [
      '0012 0700 02 { 12 34 }',
      '0012 0900 02 { 12 34 } { 56 78 }',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
    
  def test_repeat_no_before(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_3', (
                    ('lol', 1),
                    ('what', 1),
                  )),
      ('field_1', 1),
    ))
    test_cases = ['\x00\x12\x07\x00\x12\x34\x01', '\x00\x12\x09\x00\x12\x34\x56\x78\x01']
    responses = [
      {'length': 7, 'field_3': [{'what': '\x34', 'lol': '\x12'}], 'field_1': '\x01'},
      {'length': 9, 'field_3': [{'what': '\x34', 'lol': '\x12'}, {'what': '\x78', 'lol': '\x56'}], 'field_1': '\x01'},
    ]
    chunks = [
      '0012 0700 { 12 34 } 01',
      '0012 0900 { 12 34 } { 56 78 } 01',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
  
  def test_len(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_3', 0),
    ))
    test_cases = ['\x00\x12\x06\x00\x12\x34', '\x00\x12\x08\x00\x12\x34\x56\x78', '\x00\x12\x04\x00']
    responses = [
      {'length': 6, 'field_3': '\x12\x34'},
      {'length': 8, 'field_3': '\x12\x34\x56\x78'},
      {'length': 4, 'field_3': ''}
    ]
    chunks = [
      '0012 0600 1234',
      '0012 0800 12345678',
      '0012 0400 ',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
  
  def test_len_before(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_1', 1),
      ('field_3', 0),
    ))
    test_cases = ['\x00\x12\x07\x00\x01\x12\x34', '\x00\x12\x09\x00\x01\x12\x34\x56\x78']
    responses = [
      {'length': 7, 'field_3': '\x12\x34', 'field_1': '\x01'},
      {'length': 9, 'field_3': '\x12\x34\x56\x78', 'field_1': '\x01'},
    ]
    chunks = [
      '0012 0700 01 1234',
      '0012 0900 01 12345678',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
  
  def test_len_after(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_3', 0),
      ('field_1', 1),
    ))
    test_cases = ['\x00\x12\x06\x00\x12\x34', '\x00\x12\x08\x00\x12\x34\x56\x78']
    responses = [
      {'length': 6, 'field_3': '\x12', 'field_1': '\x34'},
      {'length': 8, 'field_3': '\x12\x34\x56', 'field_1': '\x78'},
    ]
    chunks = [
      '0012 0600 12 34',
      '0012 0800 123456 78',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)
  
  def test_len_clamped(self):
    test_parser = make_packet_parser('\x00\x12', (
      ('length', 2),
      ('field_1', 1),
      ('field_3', 0),
      ('field_2', 1),
    ))
    test_cases = ['\x00\x12\x07\x00\x12\x00\x34', '\x00\x12\x08\x00\x12\x34\x56\x78']
    responses = [
      {'length': 7, 'field_2': '\x34', 'field_3': '\x00', 'field_1': '\x12'},
      {'length': 8, 'field_2': '\x78', 'field_3': '\x34\x56', 'field_1': '\x12'}
    ]
    chunks = [
      '0012 0700 12 00 34',
      '0012 0800 12 3456 78',
    ]
    self.do_parse_test(test_parser, test_cases, responses, chunks)


if __name__ == '__main__':
  unittest.main()