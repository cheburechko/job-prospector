#!/bin/bash

echo "$CERT_BLOB" > cert.pem
echo "$KEY_BLOB" > key.pem

simple-proxy -basic-auth $USERNAME:$PASSWORD -protocol https -port $PORT -cert cert.pem -key key.pem
