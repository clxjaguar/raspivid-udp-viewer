#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
	https://github.com/clxjaguar/raspivid-udp-viewer/
	https://gitlab.com/cLxJaguar/raspivid-udp-viewer/

	This viewer (a UDP server listening by default on port 1234) was made because
	all other means for streaming video of a remote raspberry pi camera are very
	laggy and complicated. Transmitting a video stream by UDP packets is supported
	natively by raspivid, and if the video stream is encoded as MJPEG, it's easy
	to process, and quite realtime.

	Once this program is running, try executing this on your raspberry:
	$ raspivid --nopreview --flush --bitrate 5000000 --framerate 40 --exposure auto -t 0 --codec MJPEG -w 640 -h 480 -v -o udp://YOUR_PC_IP:1234
"""

import sys, socket, time

# sudo apt-get install python3-pyqt5
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

class ServerWorker(QObject):
	newFrame = pyqtSignal()

	def run(self, port=1234):
		self.exitLoop = False
		bufferSize  = 100000

		receive_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
		receive_socket.bind(('', port))

		frameCounter=0; frameCounterSaved = 0; nextFrameCounterTime = time.time()+1
		img=b''; i = 0; lastSize = 0

		while not self.exitLoop:
			msg, addr = receive_socket.recvfrom(bufferSize)
			if msg[0:7] == b'\xff\xd8\xff\xdb\x00\x84\x00':
				frameCounter+=1;
				if time.time() >= nextFrameCounterTime:
					nextFrameCounterTime+=1
					frameCounterSaved, frameCounter = frameCounter, 0
				img=b''

			img+=msg
			if len(msg) < lastSize:
				print("%s %06d %2d %d" % (addr[0], i, frameCounterSaved, len(img)))
				self.img = img
				img=b''
				self.newFrame.emit()
				i+=1
			lastSize=len(msg)

	def stop(self):
		self.exitLoop = True

class PiVideoWindow(QMainWindow):
	def __init__(self):
		super(PiVideoWindow, self).__init__()
		self.isMousePressed = False
		self.initUI()

		self.serverThread = QThread()
		self.serverThread.setObjectName("Server Thread")
		self.serverWorker = ServerWorker()
		self.serverWorker.moveToThread(self.serverThread)

		self.serverThread.started.connect(self.serverWorker.run)
		self.serverWorker.newFrame.connect(self.imageRefresh)
		self.serverThread.start()

	def mousePressEvent(self, event):
		if self.childAt(event.pos()) == self.painterWidget:
			self.cursorStartPos = QCursor().pos()
			self.windowStartPos = self.pos()
			self.isMousePressed = True

	def mouseMoveEvent(self, event):
		if(self.isMousePressed):
			deltaPos = QCursor().pos() - self.cursorStartPos
			self.move(self.windowStartPos + deltaPos)

	def mouseReleaseEvent(self, event):
		self.isMousePressed = False

	def initUI(self):
		self.canvas = QPixmap(560, 320)
		self.painterWidget = QLabel()
		self.painterWidget.setStyleSheet("color: white; background: black;")
		self.painterWidget.setPixmap(self.canvas)
		self.setCentralWidget(self.painterWidget)

		self.setWindowTitle(u"Close-to-Realtime Raspivid UDP Viewer/Server")
		self.show()
		self.painterWidget.setAlignment(Qt.AlignCenter)
		self.painterWidget.setText("Awaiting UDP streaming from Raspberry Pi")

	def imageRefresh(self):
		data = self.serverWorker.img
		self.canvas.loadFromData(data)
		self.painterWidget.setPixmap(self.canvas)
		self.adjustSize()

def main():
	app = QApplication(sys.argv)
	win = PiVideoWindow()
	ret = app.exec_()
	sys.exit(ret)

if __name__ == '__main__':
	main()
