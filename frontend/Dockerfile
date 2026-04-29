# Stage 1: Build the React application
FROM node:20-slim AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:alpine
# Copy the build output to Nginx's html directory
COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx config for SPA routing and API proxying
# Increased client_max_body_size to allow large liveness frame payloads
RUN echo 'server { \
    listen 80; \
    server_name bioattend.duckdns.org; \
    client_max_body_size 50M; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api/ { \
        proxy_pass http://backend:8000/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
} \
server { \
    listen 443 ssl; \
    server_name bioattend.duckdns.org; \
    ssl_certificate /etc/letsencrypt/live/bioattend.duckdns.org/fullchain.pem; \
    ssl_certificate_key /etc/letsencrypt/live/bioattend.duckdns.org/privkey.pem; \
    client_max_body_size 50M; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api/ { \
        proxy_pass http://backend:8000/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
