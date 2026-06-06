import socket
import ssl
import threading
import json
import struct

class NetworkManager:
    """Strict Single-Threaded Receive Architecture with Length-Prefixed Packets."""
    def __init__(self, host='127.0.0.1', port=55555):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.callbacks = {}

    def set_callback(self, action, func):
        self.callbacks[action] = func

    def connect(self):
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket = context.wrap_socket(raw_sock, server_hostname=self.host)
            self.socket.connect((self.host, self.port))
            
            self.running = True
            threading.Thread(target=self._recv_loop, daemon=True).start()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        self.running = False
        if self.socket:
            try: self.socket.close()
            except: pass
            self.socket = None

    def send(self, data):
        if not self.socket or not self.running: return
        try:
            payload = json.dumps(data).encode('utf-8')
            # Pack using 4-byte unsigned int format '!I' to ensure packet separation
            self.socket.sendall(struct.pack('!I', len(payload)) + payload)
        except:
            self.disconnect()

    def _recv_loop(self):
        while self.running:
            try:
                def recvall(n):
                    data = bytearray()
                    while len(data) < n:
                        packet = self.socket.recv(n - len(data))
                        if not packet: return None
                        data.extend(packet)
                    return data

                # Read EXACTLY 4 bytes for the length prefix
                raw_msglen = recvall(4)
                if not raw_msglen: break
                msglen = struct.unpack('!I', raw_msglen)[0]
                
                # Read EXACTLY the JSON payload
                raw_data = recvall(msglen)
                if not raw_data: break
                
                payload = json.loads(raw_data.decode('utf-8'))
                action = payload.get("action")
                if action in self.callbacks:
                    self.callbacks[action](payload)
            except:
                break
                
        self.disconnect()
        if "DISCONNECT" in self.callbacks:
            self.callbacks["DISCONNECT"]({})