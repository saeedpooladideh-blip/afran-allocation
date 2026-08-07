FROM node:22.13-bookworm AS dependencies

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci


FROM dependencies AS build

COPY . .

RUN npm run build


FROM node:22.13-bookworm AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=80
ENV HOST=0.0.0.0
ENV VITE_API_URL=
ENV VITE_BENCHMARK_BM=2.99

COPY --from=build --chown=node:node /app/dist ./dist

USER node

EXPOSE 80

CMD ["npm", "run", "start"]
