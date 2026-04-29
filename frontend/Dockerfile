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
# Add a custom nginx config for SPA routing (optional but recommended)
RUN echo "server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files \$uri \$uri/ /index.html; \
    } \
}" > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
