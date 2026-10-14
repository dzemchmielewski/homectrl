#!/bin/bash

#SERVE=/home/dzem/.nvm/versions/node/v23.6.1/bin/serve
#SERVE=node_modules/serve/bin/serve.js
#npm run build && ${SERVE} -p 80 build
npm run build && npm run serve -p 80 build
