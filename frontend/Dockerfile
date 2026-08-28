# Stage 1: Build Vite frontend application
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ENV VITE_API_BASE_URL=https://sentinelai-backend-w23eki576a-uc.a.run.app/api/v1
RUN npm run build

# Stage 2: Serve production assets via Nginx
FROM nginx:alpine

# Copy custom Nginx SPA routing config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build dist output to nginx web root
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
