# -*- coding: utf-8 -*-
"""
	Simple sockjs-tornado chat application. By default will listen on port 8080.
"""
import tornado.ioloop
import tornado.web
import tornado.tcpserver

import sockjs.tornado


class IndexHandler(tornado.web.RequestHandler):
	"""Regular HTTP handler to serve the chatroom page"""
	def get(self):
		self.render('index.html')

class SimpleTcpClient(object):
	client_id = 0

	def __init__(self, stream):
		#super().__init__()
		SimpleTcpClient.client_id += 1
		self.id = SimpleTcpClient.client_id
		self.stream = stream

		#self.stream.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
		#self.stream.socket.setsockopt(socket.IPPROTO_TCP, socket.SO_KEEPALIVE, 1)
		self.stream.set_close_callback(self.on_disconnect)

	@tornado.gen.coroutine
	def on_disconnect(self):
		self.log("disconnected")
		yield []

	@tornado.gen.coroutine
	def dispatch_client(self):
		try:
			while True:
				line = yield self.stream.read_until(b'\n')
				self.log('got |%s|' % line.decode('utf-8').strip())
				yield self.stream.write(line)
		except tornado.iostream.StreamClosedError:
			pass

	@tornado.gen.coroutine
	def on_connect(self):
		raddr = 'closed'
		try:
			raddr = '%s:%d' % self.stream.socket.getpeername()
		except Exception:
			pass
		self.log('new, %s' % raddr)

		yield self.dispatch_client()

	def log(self, msg, *args, **kwargs):
		print('[connection %d] %s' % (self.id, msg.format(*args, **kwargs)))

class SimpleTcpServer(tornado.tcpserver.TCPServer):
	#client_id = 0
	@tornado.gen.coroutine
	def handle_stream(self, stream, address):
		"""
		Called for each new connection, stream.socket is
		a reference to socket object
		"""
		#SimpleTcpServer.client_id += 1
		#stream.set_close_callback(on_disconnect)
		#print('[connection %d] In!' % SimpleTcpServer.client_id)
		connection = SimpleTcpClient(stream)
		yield connection.on_connect()

class ChatConnection(sockjs.tornado.SockJSConnection):
	"""Chat connection implementation"""
	# Class level variable
	participants = set()

	def on_open(self, info):
		# Send that someone joined
		self.broadcast(self.participants, "Someone joined.")

		# Add client to the clients list
		self.participants.add(self)

	def on_message(self, message):
		# Broadcast message
		self.broadcast(self.participants, message)

	def on_close(self):
		# Remove client from the clients list and broadcast leave message
		self.participants.remove(self)

		self.broadcast(self.participants, "Someone left.")

if __name__ == "__main__":
	import logging
	logging.getLogger().setLevel(logging.DEBUG)

	# 1. Create chat router
	ChatRouter = sockjs.tornado.SockJSRouter(ChatConnection, '/chat')

	# 2. Create Tornado application
	app = tornado.web.Application(
			[(r"/", IndexHandler)] + ChatRouter.urls
	)

	# 3. Make Tornado app listen on port 80
	app.listen(80)
	tcpserver = SimpleTcpServer()
	tcpserver.listen(5552)

	# 4. Start IOLoop
	tornado.ioloop.IOLoop.instance().start()
