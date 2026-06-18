FROM node:20-alpine

WORKDIR /app

COPY package.json .
RUN npm install --save-dev

COPY hardhat.config.cjs .

EXPOSE 8545

HEALTHCHECK --interval=5s --timeout=5s --retries=30 \
  CMD node -e \
    "const h=require('http');h.request({hostname:'localhost',port:8545,method:'POST',headers:{'Content-Type':'application/json'}},r=>{process.exit(0)}).on('error',()=>process.exit(1)).end('{\"jsonrpc\":\"2.0\",\"method\":\"net_version\",\"params\":[],\"id\":1}')"

CMD ["npx", "hardhat", "node", "--hostname", "0.0.0.0"]
