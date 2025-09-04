import queue
import socket
import logging
import signal
import threading
from time import time

from .agency_handler import AgencyHandler
from .utils import has_won, load_bets

class Server:
    def __init__(self, port, listen_backlog, agency_count):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._agency_count = int(agency_count)
        self._threads = []
        # Diccionario de colas para cada agencia, segun la IP
        self._agency_queues = {}
        # Cola para leer mensajes de las agencias
        self._read_queue = queue.Queue()
        # Contador compartido entre las agencias
        self._active_agencies = 0
        self._stop = False

    def run(self):
        ready_clients = 0
        ready_clients_lock = threading.Lock()
        ready_clients_cond = threading.Condition(ready_clients_lock)
        storage_lock = threading.Lock()

        signal.signal(signal.SIGTERM, self.__close_connections)
        
        while not self._stop and self._active_agencies < self._agency_count:
            client_sock = self.__accept_new_connection()
            if client_sock:
                q = queue.Queue(1)
                self._active_agencies += 1
                addr = client_sock.getpeername()
                self._agency_queues[addr] = q
                agency = AgencyHandler(client_sock, ready_clients_cond, ready_clients, q, storage_lock, self._read_queue)
                self._threads.append(agency)
                agency.start()

        logging.info('action: sorteo | result: success')
        with ready_clients_cond:
            while ready_clients < self._agency_count:
                ready_clients_cond.wait()
            self.notify_agencies()

    def notify_agencies(self):
        try:
            winners_per_agency = self.collect_winning_bets()
            for i in range(self._agency_count):
                addr, agency = self._read_queue.get()
                self._agency_queues[addr].put(winners_per_agency[agency])
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
        if self._server_socket:
            self._server_socket.close()
        for t in self._threads:
            t.join()
        logging.info('action: stop_server | result: success')
