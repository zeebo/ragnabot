import asyncore, socket

class http_client(asyncore.dispatcher):

    def __init__(self, host, path):
        asyncore.dispatcher.__init__(self)
        self.buffer = 'GET %s HTTP/1.0\r\n\r\n' % path

    def handle_connect(self):
        print "Connected"

    def handle_close(self):
        print "Closed"
        self.close()

    def handle_read(self):
        print "Received %d bytes" % len(self.recv(8192))

    def writable(self):
        return (len(self.buffer) > 0)

    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]

c = http_client('www.google.com', '/')
c.set_socket(socket.create_connection(('www.google.com', 80)))
asyncore.loop()