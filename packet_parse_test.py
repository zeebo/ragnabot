def truncate(line, maxlen = 100):
  if len(line) > maxlen:
    return line[:maxlen-3] + "..."
  return line
  
#Read dem packets
packets = {}
with open('packets.txt') as f:
  for line in f:
    if line[:2] != '0x':
      continue
    header, length = line.strip().split(',')[:2]
    packets[header[4:6]+header[2:4]] = length

#Read dem datas
bytes = []
with open('testpacks.packs') as f:
  temp_datas = []
  for line in f:
    if line.strip() == '' and len(temp_datas):
      bytes.extend(temp_datas[54:])
      temp_datas = []
    else:
      temp_datas.extend(line.strip().split())

print "Attempting to parse %d bytes" % len(bytes)

class ByteSpitter(object):
  def __init__(self, data, pos = 0):
    self._pos = pos
    self._data = data
  def skip(self, amount = 1):
    self._pos += amount
  def spit(self, amount = 1):
    if self._pos >= len(self._data):
      return ''
    self._pos += amount
    return ''.join(map(str, self._data[self._pos-amount:self._pos]))
  def has_data(self):
    return self._pos < len(self._data)
    
def reverse_bytes(data):
  def chunks(iterable, amount):
    for i in xrange(0, len(iterable), amount):
      yield iterable[i:i+amount]
  return ''.join(reversed(tuple(chunks(data, 2))))

spitter = ByteSpitter(bytes)
count = 0
while spitter.has_data():
  header = spitter.spit(2)
  packet_len = int(packets.get(header, 0))
  print packet_len, 
  if packet_len == -1:
    packet_len = int(reverse_bytes(spitter.spit(2)), 16) - 2

  if packet_len == 0:
    print "ERROR parsing packet header %s (%d)" % (header, count)
    import sys; sys.exit(0)
  
  data = spitter.spit(packet_len - 2)  

  print header, truncate(data)
  count += 1





















