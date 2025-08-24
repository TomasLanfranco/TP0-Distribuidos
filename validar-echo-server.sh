#! /usr/bin/bash

NETWORK_NAME="tp0_testing_net"
EXPECTED='Hola mundo'
RESPONSE=$(docker run --rm --network $NETWORK_NAME busybox sh -c "echo '$EXPECTED'| nc server 12345")
if [ "$RESPONSE" = "$EXPECTED" ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi