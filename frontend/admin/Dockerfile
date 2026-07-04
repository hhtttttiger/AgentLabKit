FROM node:22-alpine AS build
WORKDIR /workspace/admin
COPY admin/package.json admin/package-lock.json* ./
RUN npm ci
COPY admin/ ./
COPY shared/ ../shared/
ARG VITE_BASE=/admin/
RUN npx vite build --base=${VITE_BASE}

FROM nginx:alpine
COPY --from=build /workspace/admin/dist /usr/share/nginx/html/admin
COPY admin/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
