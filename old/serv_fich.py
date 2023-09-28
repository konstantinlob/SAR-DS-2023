#!/usr/bin/env python3

import os
import enum
import socket
import signal
import szasar

PORT = 6012
FILES_PATH = "../files"
MAX_FILE_SIZE = 10 * 1 << 20 # 10 MiB
SPACE_MARGIN = 50 * 1 << 20  # 50 MiB
USERS = ("anonimous", "sar", "sza", "kon")
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


def session( s ):
	state = State.Identification

	while True:
		message = szasar.recvline(s).decode("ascii")
		if not message:
			return

		if message.startswith(szasar.Command.User):
			if( state != State.Identification ):
				sendError(s)
				continue
			try:
				user = USERS.index( message[4:] )
			except:
				sendError(s, 2)
			else:
				sendOK( s )
				state = State.Authentication

		elif message.startswith(szasar.Command.Password):
			if state != State.Authentication:
				sendError(s)
				continue
			if( user == 0 or PASSWORDS[user] == message[4:] ):
				sendOK( s )
				state = State.Main
			else:
				sendError(s, 3)
				state = State.Identification

		elif message.startswith(szasar.Command.List):
			if state != State.Main:
				sendError(s)
				continue
			try:
				message = "OK\r\n"
				for filename in os.listdir( FILES_PATH ):
					filesize = os.path.getsize( os.path.join( FILES_PATH, filename ) )
					message += "{}?{}\r\n".format( filename, filesize )
				message += "\r\n"
			except:
				sendError(s, 4)
			else:
				s.sendall( message.encode( "ascii" ) )

		elif message.startswith(szasar.Command.Download):
			if state != State.Main:
				sendError(s)
				continue
			filename = os.path.join( FILES_PATH, message[4:] )
			try:
				filesize = os.path.getsize( filename )
			except:
				sendError(s, 5)
				continue
			else:
				sendOK( s, filesize )
				state = State.Downloading

		elif message.startswith(szasar.Command.Download2):
			if state != State.Downloading:
				sendError(s)
				continue
			state = State.Main
			try:
				with open( filename, "rb" ) as f:
					filedata = f.read()
			except:
				sendError(s, 6)
			else:
				sendOK( s )
				s.sendall( filedata )

		elif message.startswith(szasar.Command.Upload):
			if state != State.Main:
				sendError(s)
				continue
			if user == 0:
				sendError(s, 7)
				continue
			filename, filesize = message[4:].split('?')
			filesize = int(filesize)
			if filesize > MAX_FILE_SIZE:
				sendError(s, 8)
				continue
			svfs = os.statvfs( FILES_PATH )
			if filesize + SPACE_MARGIN > svfs.f_bsize * svfs.f_bavail:
				sendError(s, 9)
				continue
			sendOK( s )
			state = State.Uploading

		elif message.startswith(szasar.Command.Upload2):
			if state != State.Uploading:
				sendError(s)
				continue
			state = State.Main
			try:
				with open( os.path.join( FILES_PATH, filename), "wb" ) as f:
					filedata = szasar.recvall(s, filesize)
					f.write( filedata )
			except:
				sendError(s, 10)
			else:
				sendOK( s )

		elif message.startswith(szasar.Command.Delete):
			if state != State.Main:
				sendError(s)
				continue
			if user == 0:
				sendError(s, 7)
				continue
			try:
				os.remove( os.path.join( FILES_PATH, message[4:] ) )
			except:
				sendError(s, 11)
			else:
				sendOK( s )

		elif message.startswith(szasar.Command.Exit):
			sendOK( s )
			return

		else:
			sendError(s)


if __name__ == "__main__":
	s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )

	s.bind( ('', PORT) )
	s.listen( 5 )

	signal.signal(signal.SIGCHLD, signal.SIG_IGN)

	while True:
		dialog, address = s.accept()
		print(f"Socket connection accepted {address[0]}:{address[1]}.")
		if os.fork():
			dialog.close()
		else:
			s.close()
			session(dialog)
			dialog.close()
			exit(0)
