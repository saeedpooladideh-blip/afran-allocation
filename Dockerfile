FROM node:22.13-bookworm AS dependencies

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci


FROM dependencies AS build

COPY . .

RUN ./node_modules/.bin/vinext build


FROM node:22.13-bookworm AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=80
ENV HOST=0.0.0.0

COPY --from=build /app/dist ./dist

EXPOSE 80

CMD ["npm", "run", "start"]
