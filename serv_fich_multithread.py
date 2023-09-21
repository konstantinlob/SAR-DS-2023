#!/usr/bin/env python3

import os
import sys
import enum
import socket
import signal
import threading
import szasar

PORT = 6013
FILES_PATH = "files"
MAX_FILE_SIZE = 10 * 1 << 20 # 10 MiB
SPACE_MARGIN = 50 * 1 << 20  # 50 MiB
USERS = ("anonymous", "sar", "sza", "konstantin")
PASSWORDS = ("", "sar", "sza", "")


class State(enum.IntEnum):
	Identification = enum.auto()
	Authentication = enum.auto()
	Main = enum.auto()
	Downloading = enum.auto()
	Uploading = enum.auto()


def sendOK(conn, params=""):
	conn.sendall(("OK{}\r\n".format(params)).encode("ascii"))


def sendError(conn, code=1):
	conn.sendall(("ER{}\r\n".format(code)).encode("ascii"))


def session(conn):
	state = State.Identification

	while True:
		print("New Iteration")
		message = szasar.recvline(conn).decode("ascii")
#		print( "---SERVER: Leido msg {} {}\r\n.".format( message[0:4], message[4:] ) )
		if not message:
			return

		if message.startswith( szasar.Command.User ):
			if( state != State.Identification ):
				sendError(conn)
				continue
			try:
				user = USERS.index( message[4:] )
			except:
				sendError(conn, 2)
			else:
				sendOK(conn)
				state = State.Authentication

		elif message.startswith( szasar.Command.Password ):
			if state != State.Authentication:
				sendError(conn)
				continue
			if( user == 0 or PASSWORDS[user] == message[4:] ):
				sendOK(conn)
				filespath = os.path.join( FILES_PATH, USERS[user] )
				state = State.Main
			else:
				sendError(conn, 3)
				state = State.Identification

		elif message.startswith( szasar.Command.List ):
			if state != State.Main:
				sendError(conn)
				continue
			try:
				message = "OK\r\n"
				for filename in os.listdir( filespath ):
					filesize = os.path.getsize( os.path.join( filespath, filename ) )
					message += "{}?{}\r\n".format( filename, filesize )
				message += "\r\n"
			except:
				sendError(conn, 4)
			else:
				conn.sendall(message.encode("ascii"))

		elif message.startswith( szasar.Command.Download ):
			if state != State.Main:
				sendError(conn)
				continue
			filename = os.path.join( filespath, message[4:] )
			try:
				filesize = os.path.getsize( filename )
			except:
				sendError(conn, 5)
				continue
			else:
				sendOK(conn, filesize)
				state = State.Downloading

		elif message.startswith( szasar.Command.Download2 ):
			if state != State.Downloading:
				sendError(conn)
				continue
			state = State.Main
			try:
				with open( filename, "rb" ) as f:
					filedata = f.read()
			except:
				sendError(conn, 6)
			else:
				sendOK(conn)
				conn.sendall(filedata)

		elif message.startswith( szasar.Command.Upload ):
			if state != State.Main:
				sendError(conn)
				continue
			if user == 0:
				sendError(conn, 7)
				continue
			filename, filesize = message[4:].split('?')
			filesize = int(filesize)
			if filesize > MAX_FILE_SIZE:
				sendError(conn, 8)
				continue
			svfs = os.statvfs( filespath )
			if filesize + SPACE_MARGIN > svfs.f_bsize * svfs.f_bavail:
				sendError(conn, 9)
				continue
			sendOK(conn)
			state = State.Uploading

		elif message.startswith( szasar.Command.Upload2 ):
			if state != State.Uploading:
				sendError(conn)
				continue
			state = State.Main
			try:
				with open( os.path.join( filespath, filename), "wb" ) as f:
					filedata = szasar.recvall(conn, filesize)
					f.write( filedata )
			except:
				sendError(conn, 10)
			else:
				sendOK(conn)

		elif message.startswith( szasar.Command.Delete ):
			if state != State.Main:
				sendError(conn)
				continue
			if user == 0:
				sendError(conn, 7)
				continue
			try:
				os.remove( os.path.join( filespath, message[4:] ) )
			except:
				sendError(conn, 11)
			else:
				sendOK(conn)

		elif message.startswith( szasar.Command.Exit ):
			sendOK(conn)
			conn.close()
			return

		else:
			sendError(conn)


if __name__ == "__main__":
	s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )

	s.bind( ('', PORT) )
	s.listen( 5 )

#	signal.signal(signal.SIGCHLD, signal.SIG_IGN)

	threads = []
	connections = []

	try:
		while (True):
			conn, address = s.accept()
			print( "Conexión aceptada del socket {0[0]}:{0[1]}.".format( address ) )
			connections.append(conn)
			t = threading.Thread(target=session, args=(conn,))
			threads.append(t)
			t.start()
	except KeyboardInterrupt:
		print("Waiting for active connections to close. ctrl+c again for instant-shutdown.")
		for thread in threads:
			thread.join()
