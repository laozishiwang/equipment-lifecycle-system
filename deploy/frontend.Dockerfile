FROM node:22-alpine AS build
WORKDIR /build
COPY frontend/ ./
RUN npm install --no-audit --no-fund && npm run build:prod
FROM nginx:alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist/ /usr/share/nginx/html/
