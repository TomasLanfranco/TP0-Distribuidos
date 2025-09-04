import queue
import threading
import logging

from .decode import DNI_SIZE, MSG_LEN_SIZE, NUMBER_SIZE, decode_batch
from .utils import store_bets

class AgencyHandler(threading.Thread):
    def __init__(self, client_socket, ready_clients_cond, ready_clients, q, storage_lock, server_queue):
        threading.Thread.__init__(self)
        self.client_socket = client_socket
        self.ready_clients_cond = ready_clients_cond
        self.ready_clients = ready_clients
        self.q = q
        self.server_queue = server_queue
        self.storage_lock = storage_lock


    def run(self):
        try:
            agency = self.__process_batches()
            if agency == -2:
                self.__send_ack(None)  # send ack with number 0 to indicate stop to client
                self.__notify_ready()
            if agency > -2:
                self.__notify_server(agency)
            if agency > -1:
                winners = self.q.get()
                self.__send_winners(winners)
        except Exception as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            self.client_socket.close()


    def __notify_server(self, agency):
        '''
        Notify to server that this agency is ready to receive winners
        If agency is -1, an error happened while processing bets
        '''
        self.__notify_ready()
        addr = self.client_socket.getpeername()
        self.server_queue.put((addr, agency))


    def __notify_ready(self):
        with self.ready_clients_cond:
            self.ready_clients[0] += 1
            self.ready_clients_cond.notify_all()


    def __process_batches(self):
        last_bet = None
        while True:
            try:
                res, bets, agency = self.__process_batch_if_active()
                last_bet = bets[-1] if bets else last_bet
                if res != 0:
                    return res
            except Exception as e:
                logging.error(f'action: apuesta_almacenada | result: fail | cantidad: {len(bets)} | agencia: {agency}')
                self.__send_ack(last_bet)
                self.__notify_server(-1)
                return -1


    def __process_batch_if_active(self):
        '''
        Check if server asked to stop processing batches
        If not, process a batch
        '''
        try:
            self.q.get_nowait()
        except queue.Empty:
            return self.__process_batch()
        else:
            # Server asked to stop
            return -2, [], None
        

    def __process_batch(self):
        '''
        Process a single batch of bets
        Return 0 if more batches are expected
        Return agency number if no more batches are expected
        '''
        msg_len = self.__read_exact(MSG_LEN_SIZE)
        msg = self.__read_exact(int.from_bytes(msg_len, 'big'))
        agency, bets, more_batches = decode_batch(msg)
        with self.storage_lock:
            store_bets(bets)
        logging.info(f'action: apuesta_recibida | result: success | cantidad: {len(bets)} | agencia: {agency}')
        last_bet = bets[-1]
        self.__send_ack(last_bet)
        if more_batches:
            return 0, bets, agency
        else:
            return agency, bets, agency
        

    def __send_ack(self, bet):
        msg = b''
        number = 0 if bet is None else int(bet.number)
        msg += number.to_bytes(NUMBER_SIZE, 'big')
        self.client_socket.sendall(msg)


    def __send_winners(self, winners):
        msg = b''
        msg += len(winners).to_bytes(2, 'big')
        for bet in winners:
            msg += int(bet.document).to_bytes(DNI_SIZE, 'big')
        self.client_socket.sendall(msg)


    def __read_exact(self, n):
        """
        Read exactly n bytes from the client socket
        """
        buf = b''
        while n > 0:
            chunk = self.client_socket.recv(n)
            if chunk == b'':
                raise ConnectionError("socket connection broken")
            buf += chunk
            n -= len(chunk)
        return buf