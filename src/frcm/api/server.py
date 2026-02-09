"""Server startup script for FRCM API with HTTPS support."""
import os
import sys
import subprocess
from pathlib import Path
import uvicorn
from .config import settings

def generate_self_signed_cert(cert_path: str, key_path: str):
    """
    Generate a self-signed SSL certificate for development/testing.
    
    Args:
        cert_path: Path to save the certificate file
        key_path: Path to save the private key file
    """
    cert_dir = Path(cert_path).parent
    cert_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating self-signed SSL certificate...")
    print(f"Certificate: {cert_path}")
    print(f"Private key: {key_path}")
    
    try:
        # Generate self-signed certificate using openssl
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", key_path,
            "-out", cert_path,
            "-days", "365",
            "-nodes",
            "-subj", "/C=NO/ST=Norway/L=Bergen/O=FRCM/CN=localhost"
        ], check=True, capture_output=True)
        
        print("✓ Self-signed certificate generated successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to generate certificate: {e}", file=sys.stderr)
        print(f"  Error output: {e.stderr.decode()}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("✗ OpenSSL not found. Please install OpenSSL to generate certificates.", file=sys.stderr)
        print("  On Ubuntu/Debian: sudo apt-get install openssl", file=sys.stderr)
        print("  On macOS: brew install openssl", file=sys.stderr)
        return False

def check_ssl_files():
    """
    Check if SSL certificate and key files exist, generate if missing.
    
    Returns:
        tuple: (cert_path, key_path) if available, (None, None) if HTTPS is disabled
    """
    if not settings.REQUIRE_HTTPS:
        print("⚠ HTTPS is disabled (FRCM_REQUIRE_HTTPS=False)")
        return None, None
    
    cert_path = settings.SSL_CERT_PATH
    key_path = settings.SSL_KEY_PATH
    
    # Check if both files exist
    cert_exists = os.path.exists(cert_path)
    key_exists = os.path.exists(key_path)
    
    if cert_exists and key_exists:
        print(f"✓ Using existing SSL certificate: {cert_path}")
        return cert_path, key_path
    
    # Generate new certificate if missing
    print("⚠ SSL certificate not found")
    if generate_self_signed_cert(cert_path, key_path):
        return cert_path, key_path
    else:
        print("✗ Failed to generate SSL certificate", file=sys.stderr)
        print("  You can disable HTTPS by setting FRCM_REQUIRE_HTTPS=False", file=sys.stderr)
        return None, None

def main():
    """Start the FRCM API server with HTTPS support."""
    print("=" * 60)
    print("FRCM Fire Risk Calculation API Server")
    print("=" * 60)
    
    # Check authentication status
    if settings.is_auth_enabled:
        print(f"✓ Authentication: ENABLED ({len(settings.API_KEYS)} API key(s) configured)")
    else:
        print("⚠ Authentication: DISABLED (no API keys configured)")
        print("  Set FRCM_API_KEYS environment variable to enable authentication")
    
    # Check SSL configuration
    cert_path, key_path = check_ssl_files()
    
    if settings.REQUIRE_HTTPS and (not cert_path or not key_path):
        print("\n✗ Cannot start server: HTTPS is required but SSL files are not available")
        sys.exit(1)
    
    # Prepare server configuration
    server_config = {
        "app": "frcm.api.app:app",
        "host": settings.HOST,
        "port": settings.PORT,
        "log_level": "info",
    }
    
    if cert_path and key_path:
        server_config["ssl_certfile"] = cert_path
        server_config["ssl_keyfile"] = key_path
        protocol = "https"
    else:
        protocol = "http"
    
    # Display server information
    print("\n" + "=" * 60)
    print(f"Server starting at: {protocol}://{settings.HOST}:{settings.PORT}")
    print(f"API Documentation: {protocol}://localhost:{settings.PORT}/docs")
    print(f"Health Check: {protocol}://localhost:{settings.PORT}/health")
    print("=" * 60)
    
    if not settings.is_auth_enabled:
        print("\n⚠ WARNING: Authentication is disabled!")
        print("  Anyone can access the API without authentication.")
        print("  Set FRCM_API_KEYS to enable API key authentication.")
    
    if not settings.REQUIRE_HTTPS:
        print("\n⚠ WARNING: HTTPS is disabled!")
        print("  Data is transmitted in plain text without encryption.")
        print("  Set FRCM_REQUIRE_HTTPS=True to enable HTTPS.")
    
    print("\nPress CTRL+C to stop the server\n")
    
    # Start the server
    try:
        uvicorn.run(**server_config)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
