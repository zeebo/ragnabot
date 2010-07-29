#!/usr/bin/env python
# encoding: utf-8
"""
stream_chunker.py

Created by zeebo on 2010-07-28.
"""

import unittest

class StreamChunker(object):
  def __init__(self, callback = None):
    self.chunks = []
    self.buffer = []
    self.to_chunk = []
    self.callback = callback
  
  def add_data(self, data):
    self.buffer.append(data)
    while len(self.to_chunk) > 0 and len(self.data()) >= self.to_chunk[0]:
      self.chunk(self.to_chunk.pop(0))
  
  def data(self):
    return ''.join(self.buffer)
  
  def chunk(self, count):
    if len(self.data()) >= count:
      temp_data = []
      while count >= len(self.buffer[0]):
        popped = self.buffer.pop(0)
        temp_data.append(popped)
        count -= len(popped)
        if len(self.buffer) == 0:
          break
      if count > 0:
        temp_data.append(self.buffer[0][:count])
        self.buffer[0] = self.buffer[0][count:]
      
      self.chunks.append(''.join(temp_data))
      
      if callable(self.callback):
        self.callback(self.chunks.pop(0))
    else:
      self.to_chunk.append(count)
  
  def has_chunk(self):
    return len(self.chunks) > 0
  
  def pop(self):
    return self.chunks.pop(0)

def PacketChunker(packet_file = 'packets.txt', memo_dict={}, *args, **kwargs):
  if packet_file in memo_dict:
    return memo_dict[packet_file](*args, **kwargs)
  
  class PacketChunkerClass(StreamChunker):
    packets = {}
    with open(packet_file) as f:
      for line in f:
        if line[:2] != '0x':
          continue
        header, length = line.strip().split(',')[:2]
        header = chr(int(header[4:6], 16)) + chr(int(header[2:4], 16))
        #print r'\x' + r'\x'.join('%.2X' % ord(c) for c in header), length
        packets[header] = int(length)
    
    def add_data(self, data):
      super(PacketChunkerClass, self).add_data(data)
      
      #check if we're waiting to chunk already
      #if we aren't, then we're at a header
      while len(self.to_chunk) == 0 and len(self.data()) >= 2:
        current_data = self.data()
      
        #check if we have enough data for the header
        if len(current_data) >= 2:
          #see if the header is in our packet database
          amount_to_chunk = self.packets.get(current_data[:2], None)
          
          #flat amount, chunk it
          if amount_to_chunk > 0:
            self.chunk(amount_to_chunk)
          
          #-1, check for length and chunk it
          elif amount_to_chunk == -1:
            if len(current_data) >= 4:
              raw_length = current_data[2:4]
              #little endian
              amount_to_chunk = ord(raw_length[0]) + 256*ord(raw_length[1])
              self.chunk(amount_to_chunk)
            else:
              #must wait for more data
              break
          else:
            #Unknown packet header. Chunk it and discard
            self.chunk(2)
      
  memo_dict[packet_file] = PacketChunkerClass
  return PacketChunkerClass(*args, **kwargs)

class packet_chunker(unittest.TestCase):
  def test_callback(self):
    self.should_pass = False
    def callback(chunk):
      self.assertEqual(chunk, '\x66\x00\x00')
      self.should_pass = True
      
    chunker = PacketChunker(callback = callback)
    chunker.add_data('\x66\x00\x00')
    
    self.assertTrue(self.should_pass)
    
  def test_correct_chunk(self):
    chunker = PacketChunker()
    chunker.add_data('\x66\x00\x00')
    self.assertEqual(chunker.pop(), '\x66\x00\x00')
  
  def test_multiple_chunks(self):
    chunker = PacketChunker()
    chunker.add_data('\x66\x00\x00\x66\x00\x00')
    self.assertEqual(chunker.pop(), '\x66\x00\x00')
    self.assertEqual(chunker.pop(), '\x66\x00\x00')
  
  def test_variable_length_chunk(self):
    chunker = PacketChunker()
    chunker.add_data('\x6b\x00\x0a\x00\x11\x22\x33\x44\x55\x66')
    self.assertEqual(chunker.pop(), '\x6b\x00\x0a\x00\x11\x22\x33\x44\x55\x66')
  
  def test_split_packet(self):
    chunker = PacketChunker()
    data = '\x6b\x00\x0a\x00\x11\x22\x33\x44\x55\x66'
    for c in data:
      chunker.add_data(c)
    self.assertEqual(chunker.pop(), '\x6b\x00\x0a\x00\x11\x22\x33\x44\x55\x66')
  
  def test_specified_chunk(self):
    chunker = PacketChunker()
    chunker.chunk(4)
    chunker.add_data('test\x6b\x00\x0a\x00\x11\x22\x33\x44\x55\x66')
    
    self.assertEqual(chunker.pop(), 'test')
    self.assertEqual(chunker.pop(), '\x6b\x00\x0a\x00\x11\x22\x33\x44\x55\x66')

class stream_chunker(unittest.TestCase):
  def test_add_stream(self):
    chunker = StreamChunker()
    chunker.add_data('data!')
  
  def test_every_permutation(self):
    from itertools import permutations
    for p in permutations('1111222', 7):
      chunker = StreamChunker()
      for digit in p:
        if digit == '1':
          chunker.chunk(3)
        elif digit == '2':
          chunker.add_data('test')
      self.assertEqual(chunker.pop(), 'tes')
      self.assertEqual(chunker.pop(), 'tte')
      self.assertEqual(chunker.pop(), 'stt')
      self.assertEqual(chunker.pop(), 'est')
  
  def test_multiple_future_chunk(self):
    chunker = StreamChunker()
    chunker.chunk(3)
    chunker.chunk(3)
    chunker.chunk(3)
    chunker.chunk(3)
    chunker.add_data('test')
    chunker.add_data('test')
    chunker.add_data('test')
    self.assertEqual(chunker.pop(), 'tes')
    self.assertEqual(chunker.pop(), 'tte')
    self.assertEqual(chunker.pop(), 'stt')
    self.assertEqual(chunker.pop(), 'est')
  
  def test_future_chunk(self):
    chunker = StreamChunker()
    chunker.chunk(4)
    chunker.add_data('test')
    
    self.assertEqual(chunker.pop(), 'test')
  
  def test_small_adds(self):
    chunker = StreamChunker()
    chunker.add_data('t')
    chunker.add_data('e')
    chunker.add_data('s')
    chunker.add_data('t')
    chunker.chunk(4)
    
    self.assertEqual(chunker.pop(), 'test')
  
  def test_callback(self):
    self.should_pass = False
    
    def callback(chunk):
      self.should_pass = True
    
    chunker = StreamChunker(callback = callback)
    chunker.add_data('test')
    chunker.chunk(4)
    
    self.assertTrue(self.should_pass)
  
  def test_has_chunk(self):
    chunker = StreamChunker()
    chunker.add_data('test')
    chunker.chunk(4)
    
    self.assertTrue(chunker.has_chunk())
  
  def test_correct_chunk(self):
    chunker = StreamChunker()
    chunker.add_data('test')
    chunker.chunk(4)
    
    self.assertEqual(chunker.pop(), 'test')
  
  def test_multiple_chunks(self):
    chunker = StreamChunker()
    chunker.add_data('test')
    chunker.add_data('test')
    chunker.add_data('test')
    chunker.chunk(3)
    chunker.chunk(3)
    chunker.chunk(3)
    chunker.chunk(3)
    
    self.assertEqual(chunker.pop(), 'tes')
    self.assertEqual(chunker.pop(), 'tte')
    self.assertEqual(chunker.pop(), 'stt')
    self.assertEqual(chunker.pop(), 'est')

if __name__ == '__main__':
  unittest.main()