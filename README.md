# Wake-on-LAN (WOL) Web Application

A simple Flask-based web interface for sending Wake-on-LAN magic packets to machines on your network.

## Features

- 🌐 **Web Interface**: Modern, responsive dark-themed UI
- 💾 **Machine Management**: Save and manage multiple machines by MAC address and alias
- ⚡ **One-Click Wake**: Send WOL packets with a single click
- 🔍 **MAC Validation**: Automatic MAC address formatting and validation
- 🐳 **Docker Support**: Containerized deployment with Docker or Docker Compose
- 📊 **Activity Tracking**: Tracks last WOL timestamp for each machine

## Architecture

```
wol-homelab/
├── app.py              # Flask REST API
├── wol.py              # WOL magic packet utility
├── database.py         # SQLite database operations
├── templates/
│   └── index.html      # Single-page web UI
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Docker Compose configuration
├── run.sh              # Docker management script
└── requirements.txt    # Python dependencies
```

## Requirements

- Docker and Docker Compose (for containerized deployment)
- OR Python 3.9+ with Flask (for local development)
- Network interface that supports broadcast packets

## Quick Start

### Option 1: Using the Management Script (Recommended)

The `run.sh` script provides an easy way to manage the container:

```bash
# Make the script executable (first time only)
chmod +x run.sh

# Start the application
./run.sh start

# Check status
./run.sh status

# View logs
./run.sh logs -f

# Stop the application
./run.sh stop
```

**Available commands:**
| Command | Description |
|---------|-------------|
| `./run.sh start` | Start container (auto-builds if needed) |
| `./run.sh stop` | Stop the container |
| `./run.sh restart` | Restart the container |
| `./run.sh build` | Build/rebuild the image |
| `./run.sh logs` | View logs (add `-f` to follow) |
| `./run.sh status` | Show container status |
| `./run.sh shell` | Enter container bash shell |
| `./run.sh rm` | Remove the container |
| `./run.sh cleanup` | Remove container + image |

### Option 2: Using Docker Compose

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Option 3: Using Docker Run

```bash
# Build the image
docker build -t wol-app:latest .

# Run the container (host networking required for WOL)
docker run -d \
  --name wol-homelab \
  --network host \
  -v $(pwd)/wol.db:/app/wol.db \
  -v $(pwd)/data:/data \
  wol-app:latest
```

### Option 4: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The app will be available at `http://localhost:5001`

## Accessing the Application

Once running, open your browser and navigate to:

```
http://localhost:5001
```

Or from any device on your network:

```
http://<your-server-ip>:5001
```

## Usage

### Adding a Machine

1. Enter the **MAC Address** (format: `AA:BB:CC:DD:EE:FF`)
2. Enter an **Alias/Hostname** (e.g., "My Gaming PC", "Home Server")
3. Click **"Add Machine & Send WOL"**

The app will automatically:
- Validate the MAC address format
- Add the machine to your saved list
- Send a WOL packet immediately

### Waking a Saved Machine

Click the **"Wake"** button next to any saved machine to send a WOL packet.

### Deleting a Machine

Click the **"Delete"** button to remove a machine from your list.

## API Endpoints

The application exposes a REST API:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve the web interface |
| `GET` | `/api/machines` | Get all saved machines |
| `POST` | `/api/machines` | Add a new machine |
| `POST` | `/api/wol/<id>` | Send WOL packet to machine |
| `DELETE` | `/api/machines/<id>` | Delete a machine |

### Example API Usage

```bash
# Get all machines
curl http://localhost:5001/api/machines

# Add a machine
curl -X POST http://localhost:5001/api/machines \
  -H "Content-Type: application/json" \
  -d '{"mac_address": "AA:BB:CC:DD:EE:FF", "alias": "My PC"}'

# Send WOL packet
curl -X POST http://localhost:5001/api/wol/1

# Delete a machine
curl -X DELETE http://localhost:5001/api/machines/1
```

## Configuration

The application uses the following default configuration:

| Setting | Value | Description |
|---------|-------|-------------|
| Port | `5001` | Web server port |
| Network | `host` | Host networking (required for WOL) |
| Database | `wol.db` | SQLite database file |
| Broadcast | `255.255.255.255:9` | WOL broadcast address |

### Environment Variables

You can override settings with environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering |

## How WOL Works

Wake-on-LAN sends a "magic packet" to wake up machines on your network:

1. The magic packet is a UDP broadcast frame
2. It contains 6 bytes of `FF` followed by the target MAC address repeated 16 times
3. The target machine's network card detects the packet and powers on the system
4. The machine must have WOL enabled in BIOS/UEFI and network settings

### Important Notes

- **Host Networking**: The container uses `--network host` to send broadcast packets to your physical network
- **Subnet Limitations**: WOL only works on the same Layer 2 network (broadcast domain)
- **Target Configuration**: The target machine must have WOL enabled in BIOS/UEFI
- **Power State**: The machine must be in soft-off state (not hibernating or fully powered off)

## Data Persistence

- **Database**: `wol.db` - SQLite database storing your machines
- **Docker Volume**: `/data` - Mounted container data directory

### Backing Up Your Data

```bash
# Backup the database
cp wol.db wol.db.backup

# Or use Docker volume backup
docker run --rm -v wol-homelab_wol-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/wol-backup.tar.gz /data
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
./run.sh logs

# Or with Docker
docker logs wol-homelab
```

### WOL Packets Not Working

1. **Verify Network**: Ensure container is using host networking (`--network host`)
2. **Check Target Machine**: Confirm WOL is enabled in BIOS/UEFI
3. **Verify MAC Address**: Double-check the target MAC address
4. **Network Configuration**: Some routers/switches may block broadcast packets

### Port Already in Use

```bash
# Find process using port 5001
lsof -i :5001

# Kill the process or change the port in app.py
```

### Database Issues

```bash
# Reset database (removes all saved machines)
rm wol.db
./run.sh restart
```

## Security Considerations

⚠️ **Important**: This application has no built-in authentication. Consider:

- Running it on a trusted local network only
- Adding authentication via reverse proxy (nginx, traefik)
- Using firewall rules to restrict access
- Disabling debug mode in production (`app.run(debug=False)`)

## Building from Scratch

```bash
# Clone or download the project
cd wol-homelab

# Build the Docker image
docker build -t wol-app:latest .

# Run with any of the options listed above
./run.sh start
```

## License

This project is provided as-is for personal and educational use.

## Contributing

Feel free to submit issues and enhancement requests!
