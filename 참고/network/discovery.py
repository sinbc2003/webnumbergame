# network/discovery.py
import socket
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser
import time

class ZeroconfService:
    """
    Manages the registration of a service (a game host) using zeroconf.
    This allows other devices on the network to discover it.
    """
    def __init__(self, name, port, properties={}, service_type="_mygame._tcp.local."):
        self.name = name
        self.port = port
        self.properties = properties
        self.service_type = service_type
        self.zeroconf = Zeroconf()
        self.service_info = None

    def register_service(self):
        """Registers the service on the local network."""
        try:
            host_ip = socket.gethostbyname(socket.gethostname())
            # self.properties에 기본 version 정보 추가
            self.properties.setdefault('version', '1.0')
            
            self.service_info = ServiceInfo(
                self.service_type,
                f"{self.name}.{self.service_type}",
                addresses=[socket.inet_aton(host_ip)],
                port=self.port,
                properties=self.properties, # 전달받은 properties 사용
            )
            self.zeroconf.register_service(self.service_info)
            print(f"Service '{self.name}' registered with properties {self.properties}")
            return True
        except Exception as e:
            print(f"Error registering service: {e}")
            return False

    def unregister_service(self):
        """Unregisters the service from the network."""
        if self.service_info:
            print(f"Unregistering service '{self.name}'")
            self.zeroconf.unregister_service(self.service_info)
            self.zeroconf.close()

class ZeroconfBrowser:
    """
    Browses for services of a specific type on the network.
    """
    def __init__(self, service_type="_mygame._tcp.local."):
        self.service_type = service_type
        self.zeroconf = Zeroconf()
        self.browser = None
        self.found_services = {} # {name: (ip, port, properties)}

    class MyListener:
        def __init__(self, browser_instance):
            self.browser_instance = browser_instance

        def remove_service(self, zeroconf, type, name):
            print(f"Service {name} removed")
            if name in self.browser_instance.found_services:
                del self.browser_instance.found_services[name]
                if self.browser_instance.update_callback:
                    self.browser_instance.update_callback()


        def add_service(self, zeroconf, type, name):
            info = zeroconf.get_service_info(type, name)
            if info:
                ip_address = socket.inet_ntoa(info.addresses[0])
                properties = {key.decode(): value.decode() for key, value in info.properties.items()}
                print(f"Service {name} added, IP: {ip_address}, Port: {info.port}, Properties: {properties}")
                self.browser_instance.found_services[name] = (ip_address, info.port, properties)
                if self.browser_instance.update_callback:
                    self.browser_instance.update_callback()

    def start_browsing(self, update_callback=None):
        """Starts browsing for services."""
        self.update_callback = update_callback
        listener = self.MyListener(self)
        self.browser = ServiceBrowser(self.zeroconf, self.service_type, listener)
        print("Started browsing for services...")

    def stop_browsing(self):
        """Stops browsing for services."""
        if self.browser:
            self.zeroconf.close()
            print("Stopped browsing.")

if __name__ == '__main__':
    # --- Test ---
    # 1. Start a service
    service = ZeroconfService(name="Player_A_Game", port=8080)
    service.register_service()

    # 2. Browse for services
    browser = ZeroconfBrowser()
    browser.start_browsing()

    print("Running for 30 seconds...")
    try:
        time.sleep(30)
    finally:
        print("\nDiscovered services:", browser.found_services)
        browser.stop_browsing()
        service.unregister_service()
