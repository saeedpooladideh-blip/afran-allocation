FROM node:22.13-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM dependencies AS build

COPY . .
RUN npm run build

FROM node:22.13-alpine AS runtime

ENV NODE_ENV=production \
    PORT=80 \
    HOST=0.0.0.0 \
    VITE_API_URL= \
    VITE_BENCHMARK_BM=2.99

WORKDIR /app

RUN apk add --no-cache libcap \
    && setcap 'cap_net_bind_service=+ep' /usr/local/bin/node \
    && addgroup -S afran \
    && adduser -S afran -G afran

COPY --from=build --chown=afran:afran /app/dist/standalone ./

USER afran

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:80/').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
