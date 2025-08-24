#! /usr/bin/bash

NARGS=1
if [ $# -ne $NARGS ]; then
    echo "Usage: ./validar-echo-server.sh NETWORK_NAME"
    exit 1
fi

NETWORK_NAME=$1
EXPECTED='Hola mundo'
RESPONSE=$(docker run --rm --network $NETWORK_NAME busybox sh -c "echo '$EXPECTED'| nc server 12345")
if [ "$RESPONSE" = "$EXPECTED" ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi