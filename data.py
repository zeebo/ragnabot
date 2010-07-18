def unpack(hex_data, lengths):
  import binascii
  data = binascii.unhexlify(hex_data)
  binary = ''.join(bin(ord(c))[2:].zfill(8) for c in data)
  if sum(lengths) != len(binary):
    raise ValueError('Lengths dont sum to binary data (%d != %d)' % (sum(lengths), len(binary)))
  counter = 0
  unpacked = []
  for l in lengths:
    unpacked.append(int(binary[counter:counter+l], 2))
    counter += l
  return unpacked

def pack(values, lengths):
  bins = []
  for i, v in enumerate(values):
    bins.append(bin(v)[2:].zfill(lengths[i]))
  return ("%x" % int(''.join(bins), 2)).zfill(sum(lengths) / 4)

def test():
  import binascii, random
  for _ in xrange(100000):
    h = ''.join(random.choice("0123456789abcdef") for _ in xrange(10))
    vals = unpack(h, (10,10,10,10))
    ret = pack(vals, (10,10,10,10))
    if h != ret:
      return False
  return True

if __name__ == "__main__":
  if test():
    print "Yay it works"