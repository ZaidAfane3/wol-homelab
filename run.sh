#!/bin/bash

# Wake-on-LAN Docker Management Script
# Usage: ./run.sh [command] [options]

set -e

# Configuration
IMAGE_NAME="wol-app"
CONTAINER_NAME="wol-homelab"
DB_PATH="${PWD}/wol.db"
DATA_DIR="${PWD}/data"
PORT=5001

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
}

# Build the Docker image
build_image() {
    print_info "Building Docker image: ${IMAGE_NAME}"
    docker build -t "${IMAGE_NAME}:latest" .
    print_success "Image built successfully!"
}

# Check if image exists, build if not
ensure_image() {
    if ! docker image inspect "${IMAGE_NAME}:latest" &> /dev/null; then
        print_warning "Image '${IMAGE_NAME}:latest' not found. Building..."
        build_image
    fi
}

# Create data directory if it doesn't exist
ensure_data_dir() {
    if [ ! -d "${DATA_DIR}" ]; then
        mkdir -p "${DATA_DIR}"
        print_info "Created data directory: ${DATA_DIR}"
    fi
}

# Start the container
start_container() {
    check_docker
    ensure_image
    ensure_data_dir

    # Check if container already running
    if docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
        print_warning "Container '${CONTAINER_NAME}' is already running!"
        return 0
    fi

    print_info "Starting container '${CONTAINER_NAME}'..."

    # Remove stopped container if exists
    if docker ps -aq -f name="${CONTAINER_NAME}" | grep -q .; then
        docker rm "${CONTAINER_NAME}" &> /dev/null || true
    fi

    docker run -d \
        --name "${CONTAINER_NAME}" \
        --network host \
        -v "${DATA_DIR}:/data" \
        -v "${DB_PATH}:/app/wol.db" \
        -e PYTHONUNBUFFERED=1 \
        --restart unless-stopped \
        "${IMAGE_NAME}:latest"

    print_success "Container started successfully!"
    print_info "Access the app at: http://localhost:${PORT}"
}

# Stop the container
stop_container() {
    check_docker

    if ! docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
        print_warning "Container '${CONTAINER_NAME}' is not running."
        return 0
    fi

    print_info "Stopping container '${CONTAINER_NAME}'..."
    docker stop "${CONTAINER_NAME}"
    print_success "Container stopped!"
}

# Restart the container
restart_container() {
    print_info "Restarting container '${CONTAINER_NAME}'..."
    stop_container
    start_container
}

# Remove the container
remove_container() {
    check_docker

    stop_container &> /dev/null || true

    if docker ps -aq -f name="${CONTAINER_NAME}" | grep -q .; then
        print_info "Removing container '${CONTAINER_NAME}'..."
        docker rm "${CONTAINER_NAME}"
        print_success "Container removed!"
    else
        print_warning "No container to remove."
    fi
}

# View container logs
view_logs() {
    check_docker

    if [ "$1" == "-f" ] || [ "$1" == "--follow" ]; then
        print_info "Following logs (Ctrl+C to exit)..."
        docker logs -f "${CONTAINER_NAME}"
    else
        print_info "Container logs:"
        docker logs "${CONTAINER_NAME}"
    fi
}

# Show container status
status() {
    check_docker

    print_info "Container status:"
    echo ""

    if docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
        print_success "Container '${CONTAINER_NAME}' is RUNNING"
        echo ""
        docker ps -f name="${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        print_info "Access the app at: http://localhost:${PORT}"
    elif docker ps -aq -f name="${CONTAINER_NAME}" | grep -q .; then
        print_warning "Container '${CONTAINER_NAME}' exists but is STOPPED"
    else
        print_warning "Container '${CONTAINER_NAME}' does not exist"
    fi
}

# Clean up (remove container and image)
cleanup() {
    check_docker

    print_warning "This will remove the container and image. Continue? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_info "Cleanup cancelled."
        return 0
    fi

    remove_container
    print_info "Removing image '${IMAGE_NAME}:latest'..."
    docker rmi "${IMAGE_NAME}:latest" 2>/dev/null || true
    print_success "Cleanup complete!"
}

# Enter container shell
shell() {
    check_docker

    if ! docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
        print_error "Container '${CONTAINER_NAME}' is not running!"
        exit 1
    fi

    print_info "Entering container shell..."
    docker exec -it "${CONTAINER_NAME}" /bin/bash
}

# Show help
show_help() {
    cat << EOF
${BLUE}Wake-on-LAN Docker Management Script${NC}

${GREEN}Usage:${NC} ./run.sh [command] [options]

${GREEN}Commands:${NC}
  start       Start the container (builds image if needed)
  stop        Stop the container
  restart     Restart the container
  build       Build/rebuild the Docker image
  logs        View container logs (add -f to follow)
  status      Show container status
  shell       Enter container shell (bash)
  rm          Remove the container
  cleanup     Remove container and image
  help        Show this help message

${GREEN}Examples:${NC}
  ./run.sh start           # Start the container
  ./run.sh logs -f         # Follow logs
  ./run.sh restart         # Restart the container
  ./run.sh shell           # Enter container shell

${GREEN}Configuration:${NC}
  Image:      ${IMAGE_NAME}
  Container:  ${CONTAINER_NAME}
  Port:       ${PORT}
  Network:    host (required for WOL)

EOF
}

# Main script logic
case "${1:-}" in
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    build)
        build_image
        ;;
    logs)
        view_logs "$2"
        ;;
    status)
        status
        ;;
    shell)
        shell
        ;;
    rm)
        remove_container
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: ${1:-}"
        echo ""
        show_help
        exit 1
        ;;
esac
