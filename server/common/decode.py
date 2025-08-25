from utils import Bet

BIRTH_SIZE = 10
MSG_LEN_SIZE = 2
NUMBER_SIZE = 4

def decode_bet(bytes):
    agency = '0'
    name, bytes = decode_string(bytes)
    surname, bytes = decode_string(bytes)
    dni, bytes = decode_int(bytes)
    birth, bytes = decode_birth(bytes)
    number, _ = decode_int(bytes)
    return Bet(agency, name, surname, str(dni), birth, str(number))

def decode_birth(bytes):
    return bytes[:BIRTH_SIZE].decode("utf-8"), bytes[BIRTH_SIZE:]

def decode_string(bytes):
    length = bytes[0]
    return bytes[1:length + 1].decode("utf-8"), bytes[length + 1:]

def decode_int(bytes):
    return int.from_bytes(bytes[:4], "big"), bytes[4:]