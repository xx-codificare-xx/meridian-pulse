FROM node:20-alpine AS build

WORKDIR /app
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_FIREBASE_DATABASE_URL=http://localhost:9000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_FIREBASE_DATABASE_URL=$VITE_FIREBASE_DATABASE_URL
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
