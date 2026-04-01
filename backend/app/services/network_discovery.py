"""
Network Discovery Service.

Provides mDNS/Bonjour service advertisement for automatic server discovery on local networks.
Enables phones to find the face detection server without manual IP entry.
"""

from zeroconf import ServiceInfo, Zeroconf
import socket
import platform
import time
import json

class NetworkDiscoveryService:
    """
    Service for broadcasting and discovering the face detection server on local networks.
    Uses mDNS (Multicast DNS) to advertise the service, making it discoverable via Bonjour/Avahi.
    """

    def __init__(self, app_host: str = "0.0.0.0", app_port: int = 8000):
        """
        Initialize network discovery service.

        Args:
            app_host: Host address the FastAPI app is running on
            app_port: Port the FastAPI app is running on
        """
        self.zeroconf = None
        self.service_info = None
        self.host = app_host
        self.port = app_port
        self.service_name = "_face-detection._tcp.local."
        self._started = False

    def start_service_advertisement(self):
        """
        Start broadcasting mDNS service advertisement.
        This allows devices on the same network to discover the server automatically.
        """
        if self._started:
            print("mDNS service is already running")
            return

        try:
            # Get all available IP addresses
            ip_addresses = self._get_all_ip_addresses()
            if not ip_addresses:
                print("Warning: No network interfaces found for mDNS broadcasting")
                return

            # Service properties that clients can use
            primary_ip = self._get_primary_ip()
            props = {
                'service_type': 'missing_person_detection',
                'websocket_url': f'ws://{primary_ip}:{self.port}/ws',
                'http_url': f'http://{primary_ip}:{self.port}',
                'phone_camera_url': f'http://{primary_ip}:{self.port}/phone-camera',
                'api_url': f'http://{primary_ip}:{self.port}',
                'version': '1.0',
                'protocols': 'websocket,http',
                'description': 'Face detection for missing persons'
            }

            # Create service info for broadcasting
            hostname = self._get_hostname()
            self.service_info = ServiceInfo(
                "_http._tcp.local.",
                f"FaceDetection-{hostname}._http._tcp.local.",
                addresses=ip_addresses,
                port=self.port,
                properties=props,
                server=f"{hostname}.local."
            )

            # Initialize and register service
            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.service_info)
            self._started = True

            print(f"✓ mDNS service registered: FaceDetection available at http://{primary_ip}:{self.port}")
            print(f"  Service: FaceDetection-{hostname}.local")
            print(f"  Phone camera: http://{primary_ip}:{self.port}/phone-camera")
            print(f"  WebSocket: ws://{primary_ip}:{self.port}/ws")

        except Exception as e:
            print(f"Warning: Could not start mDNS service: {e}")
            print("  Network discovery via Bluetooth/WiFi will still work via direct IP connection")
            self._started = False

    def stop_service_advertisement(self):
        """Stop mDNS service advertisement."""
        if not self._started:
            return

        if self.zeroconf and self.service_info:
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
                print("✓ mDNS service unregistered")
            except Exception as e:
                print(f"Error stopping mDNS: {e}")
            finally:
                self._started = False

    def is_running(self) -> bool:
        """Check if mDNS service advertisement is active."""
        return self._started

    def _get_hostname(self) -> str:
        """Get system hostname for service naming."""
        return platform.node().lower().replace(' ', '-')

    def _get_all_ip_addresses(self) -> list:
        """
        Get all IPv4 addresses across all network interfaces.

        Returns:
            List of IP addresses as bytes objects for zeroconf
        """
        addresses = []
        try:
            # Use psutil to get network interfaces
            import ipaddress
            interfaces = psutil.net_if_addrs()
            for interface_name, addrs in interfaces.items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:  # IPv4
                        ip = addr.address
                        # Skip localhost
                        if ip and ip != '127.0.0.1':
                            ip_bytes = ipaddress.IPv4Address(ip).packed
                            if ip_bytes not in addresses:
                                addresses.append(ip_bytes)
        except Exception as e:
            print(f"Warning: Error getting interfaces with psutil: {e}, using socket fallback")

        # Fallback using socket
        if not addresses:
            try:
                import ipaddress
                host = socket.gethostname()
                ips = socket.gethostbyname_ex(host)[2]
                for ip in ips:
                    if ip != '127.0.0.1':
                        ip_bytes = ipaddress.IPv4Address(ip).packed
                        if ip_bytes not in addresses:
                            addresses.append(ip_bytes)
            except:
                pass

        return addresses

    def _get_primary_ip(self) -> str:
        """
        Get the primary IP address that external devices can connect to.

        Returns:
            Primary IP address as string
        """
        try:
            # Use Google's DNS to determine primary IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def get_network_info(self) -> dict:
        """
        Get comprehensive network information for connection purposes.

        Returns:
            Dictionary containing network information
        """
        return {
            "hostname": self._get_hostname(),
            "primary_ip": self._get_primary_ip(),
            "all_ips": ["%d.%d.%d.%d" % (byte[0], byte[1], byte[2], byte[3]) for byte in self._get_all_ip_addresses()],
            "port": self.port,
            "mdns_running": self.is_running(),
            "service_name": f"FaceDetection-{self._get_hostname()}.local" if self.is_running() else None
        }
