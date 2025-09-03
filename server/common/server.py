import socket
import logging
import signal
from time import time

from .decode import DNI_SIZE, MSG_LEN_SIZE, NUMBER_SIZE, decode_batch, decode_bet
from .utils import has_won, load_bets, store_bets

class Server:
    def __init__(self, port, listen_backlog, agency_count):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._active_agencies_conn = []
        self._waiting_agencies_conn = {}
        self._agency_count = int(agency_count)
        self._stop = False

    def run(self):
        signal.signal(signal.SIGTERM, self.__close_connections)
        while not self._stop:
            client_sock = self.__accept_new_connection()
            if client_sock:
                self._active_agencies_conn.append(client_sock)
                self.__handle_client_connection(client_sock)
            if self._agency_count == len(self._waiting_agencies_conn):
                logging.info('action: sorteo | result: success')
                self.notify_agencies()

    def notify_agencies(self):
        try:
            winners_per_agency = self.collect_winning_bets()

            for agency in range(1, self._agency_count + 1):
                client_sock = self._waiting_agencies_conn[agency]
                self.__send_winners(client_sock, winners_per_agency[agency - 1])
        except Exception as e:
            logging.error(f'action: notify_agencies | result: fail | error: {e}')
        finally:
            self.__close_connections(None, None)

    def collect_winning_bets(self):
        bets = load_bets()
        winners_per_agency = {i: [] for i in range(self._agency_count)}
        for bet in bets:
            if has_won(bet):
                logging.info(f'action: apuesta_ganadora | result: success | dni: {bet.document} | numero: {bet.number}')
                winners_per_agency[bet.agency - 1].append(bet)
        return winners_per_agency

    def __handle_client_connection(self, client_sock):
        try:
            self.process_batch(client_sock)
        except OSError as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            self._active_agencies_conn.remove(client_sock)

    def process_batch(self, client_sock):
        try: 
            while True:
                msg_len = self.__read_exact(MSG_LEN_SIZE, client_sock)
                msg = self.__read_exact(int.from_bytes(msg_len, 'big'), client_sock)
                agency, bets, more_batches = decode_batch(msg)
                store_bets(bets)
                logging.info(f'action: apuesta_recibida | result: success | cantidad: {len(bets)}')
                if not more_batches:
                    self._waiting_agencies_conn[agency] = client_sock
                    return
                self.__send_ack(client_sock, bets[-1])
        except Exception as e:
            logging.error(f'action: apuesta_almacenada | result: fail | cantidad: {len(bets)}')
            self.__send_ack(client_sock, 0)


    def __send_ack(self, client_sock, bet):
        msg = b''
        msg += bet.number.to_bytes(NUMBER_SIZE, 'big')
        client_sock.sendall(msg)


    def __send_winners(self, client_sock, winners):
        msg = b''
        msg += len(winners).to_bytes(2, 'big')
        for bet in winners:
            msg += int(bet.document).to_bytes(DNI_SIZE, 'big')
        client_sock.sendall(msg)


    def __read_exact(self, n, client_sock):
        """
        Read exactly n bytes from the client socket
        """
        buf = b''
        while n > 0:
            chunk = client_sock.recv(n)
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
        for conn in self._active_agencies_conn:
            conn.close()
        for conn in self._waiting_agencies_conn.values():
            conn.close()
        logging.info('action: stop_server | result: success')
