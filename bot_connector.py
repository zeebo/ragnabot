#!/usr/bin/env python
# encoding: utf-8
"""
bot_connector.py

Created by zeebo on 2010-07-29.
"""
import socket
from stream_chunker import PacketChunker
from itertools import takewhile
from parsers import *

def hex_repr(string):
  return ''.join('%.2X' % ord(c) for c in string)

def fix_addr(ip, port):
  return '.'.join(`ord(x)` for x in ip), ord(port[0]) + 256*ord(port[1])
  
def grab_name(string):
  return ''.join(takewhile(lambda x: x != '\x00', string))

def read_to_chunk(socket, chunker, count=1024):
  while not chunker.has_chunk():
    chunker.add_data(socket.recv(count))
  return chunker.pop()

def connect(server, auth, character_name, char_srv = 0):
  auth_sock = socket.create_connection(server)
  username, password = auth
  auth_sock.send(
    '\x64\x00\x18\x00\x00\x00%s%s\x12' % (username.ljust(24, '\x00'), password.ljust(24, '\x00'))
  )
  chunker = PacketChunker()  
  packet = read_to_chunk(auth_sock, chunker)  
  auth_sock.close()  
  auth_dict = login_response_parser(packet)    
  char_sock = socket.create_connection(fix_addr(auth_dict['servers'][char_srv]['ip'], auth_dict['servers'][char_srv]['port']))
  char_sock.send(
    '\x65\x00%s%s%s\x00\x00\x01' % (auth_dict['a_id'], auth_dict['l_id1'], auth_dict['l_id2'])
  )  
  chunker.chunk(4)
  read_to_chunk(char_sock, chunker)
  
  packet = read_to_chunk(char_sock, chunker)
  parsed_dict = char_response_parser(packet)
  
  names = dict((grab_name(char['name']), i) for i, char in enumerate(parsed_dict['characters']))
  if character_name not in names:
    raise ValueError('%s not in character list: %s' % (character_name, names))
  
  the_char = parsed_dict['characters'][names[character_name]]
  
  char_sock.send(
    '\x66\x00%s' % the_char['slot'][0]
  )
  
  packet = read_to_chunk(char_sock, chunker)
  parsed_dict = map_login_parser(packet)
  
  char_sock.close()
  
  return {
    'char_id': parsed_dict['char_id'],
    'server': fix_addr(parsed_dict['ip'], parsed_dict['port']),
    'map_name': grab_name(parsed_dict['map_name']),
  }
  
if __name__ == '__main__':  
  data = connect(('192.168.1.5', 6900), ('Test', 'Test'), 'Poopstick')
  
  print data