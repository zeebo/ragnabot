#!/usr/bin/env python
# encoding: utf-8
"""
patterns.py

Created by zeebo on 2010-07-19.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""

def defaults_to_self(*args):
  """
  Decorator to make specified values default to self.attrib.
  
  Example:
  
  class Test(object):
    def test_func(self, x, y):
      if hasattr(self, 'x'):
        x = self.x
      return x, y
  
  is the same as:
  
  class Test(object):
    @defaults_to_self('x')
    def test_func(self, x, y):
      return x, y
  
  and
  
  class Test2(object):
    def test_func(self, x, y):
      if hasattr(self, 'x'):
        x = self.x
      if hasattr(self, 'y'):
        y = self.y
      return x, y
  
  is the same as:
  
  class Test2(object):
    @defaults_to_self('x', 'y')
    #or just @defaults_to_self()
    def test_func(self, x, y):
      return x, y
  
  """
  def the_decorator(fn):
    if fn.__code__.co_varnames[0] != 'self':
      return fn
    if 'args' not in locals():
      args = fn.__code__.co_varnames[1:]
    def decorated(self, *f_args, **f_kwargs):
      for arg_name in args:
        if hasattr(self, arg_name) and arg_name not in f_kwargs:
          f_kwargs[arg_name] = getattr(self, arg_name)      
      for index, (arg_name, val) in enumerate(zip(fn.__code__.co_varnames[1:], f_args)):
        print index, arg_name, val
        if arg_name in f_kwargs and (index < len(f_args) or val is not None):
          del f_kwargs[arg_name]      
      return fn(self, *f_args, **f_kwargs)
    return decorated
  return the_decorator

