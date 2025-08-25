import socket
import logging
import signal

from decode import MSG_LEN_SIZE, NUMBER_SIZE, decode_bet
from utils import store_bets

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._client_connections = []
        self._stop = False

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        signal.signal(signal.SIGTERM, self.__close_connections)
        while not self._stop:
            client_sock = self.__accept_new_connection()
            if client_sock:
                self._client_connections.append(client_sock)
                self.__handle_client_connection(client_sock)

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            msg_len = self.__read_exact(MSG_LEN_SIZE)
            msg = self.__read_exact(msg_len)
            
            addr = client_sock.getpeername()
            logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}')
            
            bet = decode_bet(msg)
            store_bets([bet])
            logging.info(f'action: apuesta_almacenada | result: success | dni: {bet.document} | numero: {bet.number}')
            
            client_sock.sendall(bet.number.to_bytes(NUMBER_SIZE, 'big'))
        except OSError as e:
            logging.error("action: receive_message | result: fail | error: {e}")
        finally:
            self._client_connections.remove(client_sock)
            client_sock.close()
            
    def __read_exact(self, n):
        """
        Read exactly n bytes from the server socket
        """
        buf = b''
        while n > 0:
            chunk = self._server_socket.recv(n)
            if chunk == b'':
                raise ConnectionError("socket connection broken")
            buf += chunk
            n -= len(chunk)
        return buf

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        try:
            c, addr = self._server_socket.accept()
            logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
            return c
        except OSError as e:
            logging.error(f'action: accept_connections | result: fail | error: {e}')
            return None

    def __close_connections(self, _signo, _frame):
        """
        Stop the server, closing all client connections
        """
        self._stop = True
        logging.info('action: stop_server | result: in_progress')
        self._server_socket.close()
        for conn in self._client_connections:
            conn.close()
        logging.info('action: stop_server | result: success')
