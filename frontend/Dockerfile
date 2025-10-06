# Base image for building the frontend
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package.json and yarn.lock
COPY package.json yarn.lock ./

# Install dependencies with yarn
RUN yarn install --frozen-lockfile

# Copy the rest of the application source code
COPY . .

# Set the build-time argument
ARG NEXT_PUBLIC_API_BASE_URL

# Set the environment variable for the build
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

# Build the Next.js application
RUN yarn build

# Production image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy the built application from the builder stage
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public
COPY --from=builder /app/yarn.lock ./

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["yarn", "start"]