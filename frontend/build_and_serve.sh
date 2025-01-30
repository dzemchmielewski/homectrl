#!/bin/bash

BIN_DIR=/home/dzem/.nvm/versions/node/v23.6.1/bin

${BIN_DIR}/npm run build && ${BIN_DIR}/serve -p 80 build
