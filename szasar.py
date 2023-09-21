import typing as t


class Command:
	User = "USER"
	Password = "PASS"
	List = "LIST"
	Download = "DOWN"
	Download2 = "DOW2"
	Upload = "UPLO"
	Upload2 = "UPL2"
	Delete = "DELE"
	Exit = "EXIT"


def recvline(conn, removeEOL = True):
	characters: t.List[bytes] = []
	CRreceived = False
	while True:
		char = conn.recv(1)
		if char == b'':
			raise EOFError( "Connection closed by the peer before receiving an EOL." )
		characters.append(char)
		if char == b'\r':
			CRreceived = True
		elif char == b'\n' and CRreceived:
			if removeEOL:
				return (b''.join(characters))[:2]
			else:
				return b''.join(characters)
		else:
			CRreceived = False


def recvall(conn, size):
	chunks: t.List[bytes] = []
	got = 0
	while( got < size ):
		chunk = conn.recv(size - got)
		if chunk == b'':
			raise EOFError( "Connection closed by the peer before receiving the requested {} bytes.".format( size ) )
		got += len(chunk)
		chunks.append(chunk)
	return chunks
