FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=http://localhost:8005
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM node:20-alpine

RUN npm install -g serve@14.2.4

COPY --from=build /app/dist /app

EXPOSE 3000

CMD ["serve", "-s", "/app", "-l", "3000"]
