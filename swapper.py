import StringIO as sio
import asyncore
import socket



def hex_print(data, bytes_per_line = 20, bytes_per_break = 5):
  if bytes_per_line > 100:
    bytes_per_line = 100
    
  if bytes_per_break <= 0 or bytes_per_line % bytes_per_break != 0:
    bytes_per_break = bytes_per_line
  
  for offset in xrange(0, len(data), bytes_per_line):
    for break_counter in xrange(0, bytes_per_line, bytes_per_break):
      print ' '.join("%x" % ord(char) for char in data[offset+break_counter:offset+break_counter+bytes_per_break]),
      if break_counter != bytes_per_line - bytes_per_break and offset+break_counter+bytes_per_break < len(data):
        print '|',
    print ''

class Swapper(object):
  def __init__(self):
    self.client = None
    self.client_buffer = ''
    self.server = None
    self.server_buffer = ''
  
  def register(self, async_obj, async_type):
    if async_type not in ['server', 'client']:
      raise ValueError('%s not a valid type' % async_type)
      
    if (async_type == 'client' and self.client != None) or
         (async_type == 'server' and self.server != None):
         
      raise ValueError('Already registered a %s' % async_type)
    
    
      