class FIFOBuffer(object):
  def __init__(self):
    self.buffer = ''
    
  def append(self, data):
    self.buffer += data
  
  def pop(self, bytes):
    self.buffer = self.buffer[bytes:]
  
  def get(self):
    return self.buffer
  
  def __len__(self):
    return len(self.buffer)

class DataProcessor(object):
  def __init__(self):
    #We have a client and a server
    self.buffers = {'client': FIFOBuffer(), 'server': FIFOBuffer()}
  
  def other(self, sid):
    return {'server':'client', 'client':'server'}[sid]
  
  def read_event(self, sid, data):
    #Put the data unmodified in the server's buffer
    self.buffers[self.other(sid)].append(data)
  
  def get_data(self, sid):
    return self.buffers[sid].get()
  
  def sent_bytes_event(self, sid, bytes):
    self.buffers[sid].pop(bytes)
  
  def is_writable(self, sid):
    return (len(self.buffers[sid]) > 0)

class EchoProcessor(DataProcessor):
  def read_event(self, sid, data):
    other_sid = self.other(sid)
    print "%s->%s[%d]: %s" % (sid, other_sid, len(data), data)
    self.buffers[other_sid].append(data)

def SimpleReplacerFactory(mappings):
  class SimpleReplacerProcessor(DataProcessor):
    def read_event(self, sid, data):
      for key in mappings:
        if key in data:
          count, data = data.count(key), data.replace(key, mappings[key])
          print "%s->%s: replaced %d occurences of %s by %s" % (sid, self.other(sid), count, key, mappings[key])
      self.buffers[self.other(sid)].append(data)
      
  return SimpleReplacerProcessor
