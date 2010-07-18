class InvalidPacket(Exception): pass
class ParseError(Exception): pass
class EatingException(Exception): pass
class FormatException(Exception): pass

class PrintingMetaclass(type):
  def __new__(meta, classname, bases, classDict):
    print 'meta:', meta
    print 'name:', classname
    print 'base:', bases
    print 'dict:', classDict
    return type.__new__(meta, classname, bases, classDict)

class Length(object):
  def __init__(self, length):
    self.length = length

class BasePacket(object):
  _format = tuple()
  def __init__(self, parse_data = None):
    pass

def get_len(val):
  if isinstance(val, int):
    return val
  if isinstance(val, str):
    if len(val) % 2 != 0:
      raise FormatException('String not an integer number of bytes')
    return len(val) / 2
  if isinstance(val, Length):
    return val.length
  if isinstance(val, tuple):
    total = 0
    for _, arg in val:
      total += get_len(arg)
    return total

def Packet(name, format):
  if not isinstance(format[0], str):
    raise FormatException("No header field")
  if len(format[0]) % 2 != 0:
    raise FormatException("Header not an integer number of bytes")
  
  has_length = has_len_zero = False
  for _, val in format[1:]:
    if val == 0:
      if has_len_zero:
        raise FormatException('Multiple indeterminate lengths')
      if not has_length:
        raise FormatException('Indeterminate length before total length')
      has_len_zero = True
    if isinstance(val, Length):
      if has_length:
        raise FormatException('Length already specified')
      has_length = True
  
  if has_length and not has_len_zero:
    raise FormatException('Length but no indeterminate length')
  
  counter = before = get_len(format[0])
  for _, val in format[1:]:
    counter += get_len(val)
    if val == 0:
      before = counter
  after = counter - before
  
  if not has_ind:
    before = counter
    after = 0
  
  data = {
    '_format' : format,
    '_has_length' : has_length,
    '_before' : before,
    '_after' : after,
  }
  
  print data
  
  return type.__new__(type, "%sPacket" % name, (BasePacket, ), data)

f = ('0035',
      ('some_shit', 2),
      ('item_list', (
        ('id', 2),
        ('count', 4),
      )),
    )

ItemListPacket = Packet('ItemList', f)
