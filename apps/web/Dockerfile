FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm run build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup -S olive && adduser -S olive -G olive
COPY --from=build --chown=olive:olive /app/.next/standalone ./
COPY --from=build --chown=olive:olive /app/.next/static ./.next/static
USER olive
EXPOSE 3000
CMD ["node", "server.js"]
