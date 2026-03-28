# docker compose update
dcupdate() {
  echo "Pulling latest images..."
  docker compose pull || return 1

  echo "Stopping current containers..."
  docker compose down || return 1

  echo "Starting updated containers..."
  docker compose up -d || return 1

  echo "Docker Compose update complete."
}
