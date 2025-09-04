import threading
import logging

from .decode import DNI_SIZE, MSG_LEN_SIZE, NUMBER_SIZE, decode_batch
from .utils import store_bets

class AgencyHandler(threading.Thread):
    def __init__(self, client_socket, ready_clients_cond, ready_clients, q):
        threading.Thread.__init__(self)
        self.client_socket = client_socket
        self.ready_clients_cond = ready_clients_cond
        self.ready_clients = ready_clients
        self.q = q

    def run(self):
        try:
            agency = self.process_batch()
            self.notify_server_and_send_winners(agency)
        except OSError as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            self.client_socket.close()

    def notify_server_and_send_winners(self, agency):
        try:
            with self.ready_clients_cond:
                self.ready_clients += 1
                self.ready_clients_cond.notify_all()
            # Notify the server the agency ID to collect winners
            self.q.put(agency)
            winners = self.q.get()
            self.__send_winners(winners)
        except Exception as e:
            logging.error(f"action: notify_server_and_send_winners | result: fail | error: {e}")

    def process_batch(self):
        try: 
            while True:
                msg_len = self.__read_exact(MSG_LEN_SIZE)
                msg = self.__read_exact(int.from_bytes(msg_len, 'big'))
                agency, bets, more_batches = decode_batch(msg)
                store_bets(bets)
                logging.info(f'action: apuesta_recibida | result: success | cantidad: {len(bets)}')
                if more_batches:
                    self.__send_ack(bets[-1])
                else:
                    return agency
                
        except Exception as e:
            logging.error(f'action: apuesta_almacenada | result: fail | cantidad: {len(bets)}')
            self.__send_ack(0)


    def __send_ack(self, bet):
        msg = b''
        msg += bet.number.to_bytes(NUMBER_SIZE, 'big')
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