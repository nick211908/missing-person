"""
Network Discovery and Bluetooth Connectivity API Routes.

Provides endpoints for:
- Network auto-discovery via mDNS/Bonjour
- QR code generation for easy connection
- Bluetooth PAN detection and status
- Connection helper tools
"""

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import qrcode
import io
import base64
import json
import platform
import psutil
import socket
import sys
import time
from datetime import datetime

router = APIRouter()

class NetworkInfo(BaseModel):
    """Network discovery information."""
    hostname: str
    primary_ip: str
    all_ips: List[str]
    mdns_running: bool
    service_name: Optional[str]
    port: int
    server_urls: Dict[str, str]


class QRCodeResponse(BaseModel):
    """QR code response containing connection information."""
    qrcode_base64: str
    connection_url: str
    connection_data: Dict[str, Any]


class BluetoothInterface(BaseModel):
    """Bluetooth network interface information."""
    name: str
    ip_address: str
    is_up: bool
    is_connected: bool
    type: str = "bluetooth"


class BluetoothStatusResponse(BaseModel):
    """Bluetooth PAN status response."""
    bluetooth_available: bool
    bluetooth_pan_supported: bool
    has_active_pan: bool
    is_windows: bool
    network_platform: str
    platform: str
    active_connections: List[BluetoothInterface]
    bluetooth_interfaces: List[BluetoothInterface]
    setup_instructions: Dict[str, str]
    timestamp: datetime


class ConnectionHelpersResponse(BaseModel):
    """Connection helper tools response."""
    wifi_methods: List[Dict[str, str]]
    bluetooth_methods: List[Dict[str, str]]
    direct_ip_methods: List[Dict[str, str]]
    recommended_method: str
    qrcode_url: str


def _get_all_ip_addresses() -> List[str]:
    """Get all IPv4 addresses across all interfaces."""
    addresses = []
    try:
        # Use psutil to get network interfaces
        interfaces = psutil.net_if_addrs()
        for interface_name, addrs in interfaces.items():
            for addr in addrs:
                if addr.family == socket.AF_INET:  # IPv4
                    ip = addr.address
                    if ip and ip != '127.0.0.1':
                        addresses.append(ip)
    except Exception:
        # Fallback using socket
        try:
            host = socket.gethostname()
            addresses = socket.gethostbyname_ex(host)[2]
        except:
            pass
    return addresses


def _get_primary_ip() -> str:
    """Get primary IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def _get_hostname() -> str:
    """Get system hostname."""
    return platform.node().lower().replace(' ', '-')


def detect_bluetooth_interfaces() -> List[BluetoothInterface]:
    """
    Detect Bluetooth PAN network interfaces.

    Returns:
        List of Bluetooth network interfaces
    """
    bluetooth_interfaces = []
    try:
        interfaces = psutil.net_if_addrs()
        interface_stats = psutil.net_if_stats() if hasattr(psutil, 'net_if_stats') else {}

        for interface_name, addrs in interfaces.items():
            # Check if interface name suggests Bluetooth
            is_bluetooth = (
                'bluetooth' in interface_name.lower() or
                'pan' in interface_name.lower() or
                'bnep' in interface_name.lower() or  # Bluetooth Network Encapsulation Protocol (Linux)
                interface_name.startswith('bt') or
                (interface_name.startswith('tap') and 'bluetooth' in interface_name.lower())
            )

            if is_bluetooth:
                # Get IPv4 address
                ipv4_addr = None
                for addr in addrs:
                    if hasattr(addr, 'family') and addr.family == socket.AF_INET:
                        ipv4_addr = addr.address
                        break
                    elif isinstance(addr, tuple) and len(addr) >= 2:
                        # Sometimes returned as tuple
                        ipv4_addr = addr[0]
                        break

                # Check if interface is up
                is_up = False
                if interface_name in interface_stats:
                    is_up = interface_stats.get(interface_name, {}).get('isup', False)

                if ipv4_addr:
                    bluetooth_interfaces.append(BluetoothInterface(
                        name=interface_name,
                        ip_address=ipv4_addr,
                        is_up=is_up,
                        is_connected=is_up and bool(ipv4_addr),
                        type="bluetooth"
                    ))
    except Exception as e:
        print(f"Error detecting Bluetooth interfaces: {e}")

    return bluetooth_interfaces


@router.get("/network/discovery/info", response_model=NetworkInfo)
async def get_network_info(request: Request):
    """
    Get network discovery information.

    Returns:
        Server IP addresses and connection URLs
    """
    try:
        # Get network info
        all_ips = _get_all_ip_addresses()
        primary_ip = _get_primary_ip()
        hostname = _get_hostname()

        # Determine protocol and URL generation
        protocol = "https" if request.url.scheme == "https" else "http"
        host_header = request.headers.get('host')
        host = host_header if host_header else f"localhost:{request.url.port or '8000'}"

        # Check if network discovery service is available
        try:
            from app.services.network_discovery import network_discovery_service as nds
            mdns_running = nds.is_running()
        except:
            mdns_running = False

        # Generate server URLs
        server_urls = {
            "api_base": f"{protocol}://{host}",
            "websocket": f"ws://{host}/ws",
            "phone_camera": f"{protocol}://{host}/phone-camera",
            "snapshot": f"{protocol}://{host}/phone-camera/snapshot",
            "network_info": f"{protocol}://{host}/network/discovery/info",
            "qr_code": f"{protocol}://{host}/network/discovery/qrcode"
        }

        return NetworkInfo(
            hostname=hostname,
            primary_ip=primary_ip,
            all_ips=all_ips,
            mdns_running=mdns_running,
            service_name=f"FaceDetection-{hostname}.local" if mdns_running else None,
            port=request.url.port or 8000,
            server_urls=server_urls
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get network info: {str(e)}")


@router.get("/network/discovery/qrcode", response_model=QRCodeResponse)
async def get_connection_qrcode(
    request: Request,
    ip_address: Optional[str] = Query(None),
    include_network_info: bool = Query(True, description="Include all network IPs in QR code")
):
    """
    Generate QR code for easy phone camera connection.

    Args:
        ip_address: Optional specific IP to use instead of auto-detection
        include_network_info: Include network details in metadata

    Returns:
        Base64 encoded QR code image
    """
    try:
        # Get connection URL
        protocol = "https" if request.url.scheme == "https" else "http"

        if ip_address:
            # Use provided IP address
            connection_url = f"{protocol}://{ip_address}:{request.url.port or '8000'}/phone-camera"
        else:
            # Auto-detect primary IP
            primary_ip = _get_primary_ip()
            connection_url = f"{protocol}://{primary_ip}:{request.url.port or '8000'}/phone-camera"

        # Create connection data
        all_ips = _get_all_ip_addresses() if include_network_info else []

        connection_data = {
            "server_url": connection_url,
            "websocket_url": connection_url.replace('http', 'ws').replace('/phone-camera', '/ws'),
            "api_url": connection_url.replace('/phone-camera', ''),
            "ip_address": _get_primary_ip(),
            "all_available_ips": all_ips,
            "timestamp": time.time(),
            "discovery_method": "qrcode",
            "hostname": _get_hostname(),
            "connection_type": "wifi_direct"
        }

        # Generate QR code
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )

        # Add human-readable URL + JSON data
        qr_text = f"CONNECT:{connection_url}|DATA:{json.dumps(connection_data)}"
        qr.add_data(qr_text)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        return QRCodeResponse(
            qrcode_base64=f"data:image/png;base64,{img_base64}",
            connection_url=connection_url,
            connection_data=connection_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QR code generation failed: {str(e)}")


@router.get("/bluetooth/status", response_model=BluetoothStatusResponse)
async def get_bluetooth_status():
    """
    Get Bluetooth PAN status and network information.

    Bluetooth PAN (Personal Area Network) allows phone-to-PC connectivity via Bluetooth
    when WiFi is unavailable. This endpoint provides setup instructions and detects
    active Bluetooth connections.

    Returns:
        Bluetooth status and setup instructions for various platforms
    """
    is_windows = platform.system() == 'Windows'
    network_platform = platform.system()

    # Detect Bluetooth interfaces
    bt_interfaces = detect_bluetooth_interfaces()
    active_connections = [iface for iface in bt_interfaces if iface.is_connected]

    return BluetoothStatusResponse(
        bluetooth_available=True,
        bluetooth_pan_supported=True,
        has_active_pan=len(active_connections) > 0,
        is_windows=is_windows,
        network_platform=network_platform,
        platform=platform.platform(),
        bluetooth_interfaces=bt_interfaces,
        active_connections=active_connections,
        setup_instructions={
            "windows": "1. Go to Settings > Bluetooth & devices > Add device.\n2. Pair your phone with the PC.\n3. Go to Network Connections > Bluetooth Network Connection.\n4. Enable Bluetooth PAN adapter.",
            "android": "1. Settings > Bluetooth > Pair with PC.\n2. Enable 'Bluetooth tethering' or 'Use for internet'.\n3. Note the IP address assigned to PC.",
            "ios": "1. Settings > Bluetooth > Pair with PC.\n2. Enable Personal Hotspot if available.\n3. On PC, connect via Bluetooth PAN.",
            "linux": "1. Use bluetoothctl or blueman to pair.\n2. Enable Network Access Point (NAP) profile.\n3. Check bnep0 interface for IP address."
        },
        timestamp=datetime.utcnow()
    )


@router.get("/bluetooth/connect-help")
async def get_bluetooth_connection_help(
    platform: Optional[str] = Query(None, description="Target platform: windows, android, ios, linux")
):
    """
    Get platform-specific Bluetooth PAN setup instructions.

    Args:
        platform: Specific platform or None for all platforms

    Returns:
        Step-by-step setup instructions
    """
    instructions = {
        "windows": {
            "title": "Windows Bluetooth PAN Setup",
            "steps": [
                "Go to Settings > Bluetooth & devices > Add device",
                "Enable Bluetooth on your phone and pair it",
                "Go to Control Panel > Network Connections",
                "Right-click 'Bluetooth Network Connection'",
                "Enable Bluetooth PAN adapter",
                "Ensure adapter gets an IP address",
                "Visit the provided IP in your phone's browser"
            ],
            "troubleshooting": [
                "If Bluetooth adapter not showing, update Bluetooth drivers",
                "Check Windows Mobile Device Center is enabled",
                "Restart Bluetooth Support Service",
                "Try using USB Bluetooth adapter if integrated one fails"
            ]
        },
        "android": {
            "title": "Android Bluetooth Tethering Setup",
            "steps": [
                "Enable Bluetooth on your phone",
                "Pair your phone with the PC in Bluetooth settings",
                "Go to Settings > Network & Internet > Hotspot & tethering",
                "Enable 'Bluetooth tethering'",
                "On PC, check for new network connection",
                "Note the IP address assigned to PC",
                "Open phone browser to that IP and port"
            ],
            "troubleshooting": [
                "Ensure phone supports Bluetooth tethering",
                "Check carrier allows tethering",
                "Try clearing Bluetooth cache",
                "Restart both devices"
            ]
        },
        "ios": {
            "title": "iOS Bluetooth Connection Setup",
            "steps": [
                "Enable Bluetooth on iPhone",
                "Pair with PC in Settings > Bluetooth",
                "Enable Personal Hotspot (if available)",
                "Connect PC to iPhone via Bluetooth PAN",
                "Check PC network settings for IP",
                "Open Safari/Chrome on iPhone",
                "Navigate to the PC's IP:port/phone-camera"
            ],
            "troubleshooting": [
                "iOS may limit Bluetooth PAN functionality",
                "Consider using WiFi instead if available",
                "Personal Hotspot via USB Lightning cable is alternative",
                "Check iOS and macOS versions for compatibility"
            ]
        },
        "linux": {
            "title": "Linux Bluetooth PAN Setup",
            "steps": [
                "Install bluez and blueman: sudo apt-get install bluez blueman",
                "Enable Bluetooth service: sudo systemctl enable bluetooth",
                "Use blueman-manager to pair phone",
                "Enable Network Access Point (NAP) profile",
                "Check bnep0 interface: ifconfig bnep0",
                "Note the IP address assigned",
                "Access from phone browser"
            ],
            "troubleshooting": [
                "Use bluetoothctl for command-line pairing",
                "Check kernel modules for bnep: lsmod | grep bnep",
                "May need to install linux-image-extra- packages",
                "Some distributions require manual configuration"
            ]
        }
    }

    if platform and platform.lower() in instructions:
        return JSONResponse(content={
            "platform": platform.lower(),
            "instructions": instructions[platform.lower()],
            "api_endpoints": {
                "bluetooth_status": "/bluetooth/status",
                "network_info": "/network/discovery/info",
                "qrcode": "/network/discovery/qrcode"
            }
        })

    return JSONResponse(content={
        "available_platforms": list(instructions.keys()),
        "instructions": instructions,
        "message": "Select a specific platform from available options"
    })


@router.get("/network/connection-helpers", response_model=ConnectionHelpersResponse)
async def get_connection_helpers(request: Request):
    """
    Get all available connection methods and helpers.

    Returns:
        List of available connection methods with descriptions and URLs
    """
    protocol = "https" if request.url.scheme == "https" else "http"
    host = request.headers.get('host', 'localhost:8000')

    primary_ip = _get_primary_ip()

    wifi_methods = [
        {
            "name": "Auto-Discovery (mDNS/Bonjour)",
            "description": "Server automatically broadcasts its presence on the network",
            "how_to_use": "Phone will automatically find the server if ZeroConf/Bonjour supported",
            "url": f"{protocol}://{host}",
            "status": "available"
        },
        {
            "name": "QR Code Scan",
            "description": "Scan QR code to automatically connect",
            "how_to_use": "Open /network/discovery/qrcode endpoint and scan with phone",
            "url": f"{protocol}://{host}/network/discovery/qrcode",
            "status": "available"
        },
        {
            "name": "Direct WiFi IP",
            "description": "Connect directly using server's IP address",
            "how_to_use": f"Open browser on phone to: {protocol}://{primary_ip}:8000/phone-camera",
            "url": f"{protocol}://{primary_ip}:8000",
            "status": "available",
            "ip_address": primary_ip
        }
    ]

    bluetooth_methods = [
        {
            "name": "Bluetooth PAN",
            "description": "Use Bluetooth tethering when WiFi unavailable",
            "how_to_use": "Pair phone with PC via Bluetooth and enable PAN",
            "url": f"{protocol}://[Bluetooth-PAN-IP]:8000",
            "status": "available_if_paired",
            "setup_guide": f"{protocol}://{host}/bluetooth/connect-help"
        }
    ]

    direct_ip_methods = [
        {
            "name": "Direct IP Access",
            "description": "Use any available IP address",
            "how_to_use": f"Try any of these IPs: {', '.join(_get_all_ip_addresses()[:3])}",
            "url": f"{protocol}://[IP-Address]:8000",
            "status": "available"
        }
    ]

    # Determine recommended method
    all_ips = _get_all_ip_addresses()
    if len([ip for ip in all_ips if not ip.startswith('127.')]) > 0:
        if _get_primary_ip() != "127.0.0.1":
            recommended = "Direct WiFi IP - check /network/discovery/qrcode"
        else:
            recommended = "Wait for mDNS or use QR code"
    else:
        recommended = "Enable WiFi or use Bluetooth PAN"

    return ConnectionHelpersResponse(
        wifi_methods=wifi_methods,
        bluetooth_methods=bluetooth_methods,
        direct_ip_methods=direct_ip_methods,
        recommended_method=recommended,
        qrcode_url=f"{protocol}://{host}/network/discovery/qrcode"
    )
