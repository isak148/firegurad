# FireGuard

## Prerequisites

Before running FireGuard locally, ensure you have the following installed:

### Docker
- **Purpose**: Runs the entire system in containers
- **Install**: https://www.docker.com/products/docker-desktop/
- **Verify**: 
  ```bash
docker --version
docker compose version
  ```

### Git
- **Purpose**: Used to download the source code from GitHub
- **Verify**:
  ```bash
git --version
  ```

## Installation

Follow these steps to set up and run FireGuard locally:

1. **Clone the repository**
   ```bash
git clone https://github.com/isak148/firegurad.git
   ```

2. **Navigate to the project folder**
   ```bash
cd firegurad
   ```

3. **Copy the example configuration**
   ```bash
cp .env.example .env
   ```

4. **Configure environment variables**
   ```bash
nano .env
   ```

5. **Build the application**
   ```bash
docker compose build
   ```

6. **Start the application**
   ```bash
docker compose up -d
   ```

7. **Open in browser**
   - http://localhost/

## Usage

FireGuard is a containerized full-stack web application with the following architecture:

- **Frontend**: Served using Nginx, a lightweight web server
- **Backend**: Python-based API service that processes application logic (fire risk calculations, weather data handling)
- **User Interaction**: Users interact with the system through a web browser
- **Infrastructure**: Docker manages and connects all services, with each component running in its own isolated container

## Limitations

- No HTTPS support
- Requires Docker
- Limited authentication
- SQLite database (small scale)
- No logging system
- No automated startup

---

For issues or contributions, please visit the [GitHub repository](https://github.com/isak148/firegurad).