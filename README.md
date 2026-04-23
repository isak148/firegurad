Prerequisites
In order to run FireGuard locally, you need: 
Docker, runs the entire system in containers
Install: https://www.docker.com/products/docker-desktop/
Verify installation (in cmd)
docker --version
docker compose version
Git, used to download the source code from GitHub
git --version

Installation
These step shows how to set up and run fireguard locally. Note that the prerequisites must be installed
1.	Clone the repo
git clone https://github.com/isak148/firegurad.git
2.	Navigate to folder

Cd firegurad
3.	Copy the example configuration
cp .env.example .env

4.	Configure variables 

nano .env 
5.	Build the application

docker compose build

6.	Start the application

docker compose up -d

7.	Open in browser
http://localhost/

Usage
FireGuard is a containerized full-stack web application consisting of a frontend, a backend API, and supporting infrastructure managed by Docker.
The frontend is served using Nginx, a lightweight web server.
The backend is a Python-based API service. it processes all application logic (e.g., fire risk calculations and weather data handling)
The user interacts with the system through a web browser. The browser loads the website from Nginx
Docker is used to run and connect all services. each component runs in its own isolated container.

Limitations
•	No HTTPS
•	Requires Docker
•	Limited authentication
•	SQLite (Small database)
•	No logging
•	No automated startup

