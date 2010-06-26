import time
import threading

def wait(secs = 5):
  time.sleep(secs)
  print "done after %d seconds" % secs


for i in xrange(5):
  threading.Thread(target=wait, args=(i, )).start()