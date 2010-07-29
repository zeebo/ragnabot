import asyncore
import socket

from packet import make_packet_parser
login_response_parser = make_packet_parser('\x69\x00', (
  ('length', 2),
  ('l_id1', 4),
  ('a_id', 4),
  ('l_id2', 4),
  ('_', 4),
  ('_', 24),
  ('_', 2),
  ('sex', 1),
  ('servers', (
    ('ip', 4),
    ('port', 2),
    ('name', 20),
    ('users', 2),
    ('_', 2),
    ('_', 2),
  )),
))

class BotDispatcher(asyncore.dispatcher):
  pass

