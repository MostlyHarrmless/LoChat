import socket
import threading
import json
import struct
import time
import database
from ssl_context import get_server_context

class ChatServer:
    def __init__(self, host='0.0.0.0', port=55555):
        self.host = host
        self.port = port
        self.active_clients = {}      # user_id -> socket
        self.client_metadata = {}     # socket -> {"user_id": int, "username": str}
        self.spam_tracker = {}        
        self.clients_lock = threading.Lock()
        self.log_callback = None
        self.running = False
        self.secure_server = None

    def set_log_callback(self, callback):
        self.log_callback = callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def send_json(self, sock, data):
        try:
            payload = json.dumps(data).encode('utf-8')
            sock.sendall(struct.pack('!I', len(payload)) + payload)
        except Exception as e:
            pass

    def recv_json(self, sock):
        try:
            def recvall(n):
                data = bytearray()
                while len(data) < n:
                    packet = sock.recv(n - len(data))
                    if not packet: return None
                    data.extend(packet)
                return data
                
            raw_msglen = recvall(4)
            if not raw_msglen: return None
            msglen = struct.unpack('!I', raw_msglen)[0]
            raw_data = recvall(msglen)
            if not raw_data: return None
            return json.loads(raw_data.decode('utf-8'))
        except:
            return None

    def check_anti_spam(self, user_id, content):
        now = time.time()
        if user_id not in self.spam_tracker:
            self.spam_tracker[user_id] = {"timestamps": [], "last_msg": "", "muted_until": 0.0}
            
        track = self.spam_tracker[user_id]
        if now < track["muted_until"]:
            return False, f"Anti-Spam: Muted for {int(track['muted_until'] - now)}s."
            
        track["timestamps"] = [t for t in track["timestamps"] if now - t < 3.0]
        if len(track["timestamps"]) >= 5:
            track["muted_until"] = now + 10.0
            return False, "Spam detected. Muted for 10 seconds."
            
        if content == track["last_msg"] and (len(track["timestamps"]) > 0 and now - track["timestamps"][-1] < 1.0):
            return False, "Duplicate message blocked."
            
        track["timestamps"].append(now)
        track["last_msg"] = content
        return True, ""

    def broadcast_to_room(self, room_id, payload, exclude_user_id=None):
        members = database.get_room_members(room_id)
        member_ids = {m['id'] for m in members}
        with self.clients_lock:
            for uid in member_ids:
                if uid != exclude_user_id and uid in self.active_clients:
                    self.send_json(self.active_clients[uid], payload)

    def broadcast_presence(self):
        with self.clients_lock:
            online_users = list(self.active_clients.keys())
        for sock in list(self.client_metadata.keys()):
            self.send_json(sock, {"action": "PRESENCE_UPDATE", "online_users": online_users})

    def kick_user_force(self, user_id, reason="Banned by admin"):
        with self.clients_lock:
            if user_id in self.active_clients:
                sock = self.active_clients[user_id]
                self.send_json(sock, {"action": "FORCE_LOGOUT", "reason": reason})
                sock.close()

    def handle_client(self, client_socket, client_address):
        self.log(f"[+] Connection established: {client_address}")
        user_id = None
        
        with self.clients_lock:
            self.client_metadata[client_socket] = {"user_id": None, "username": None}

        try:
            while True:
                req = self.recv_json(client_socket)
                if not req: break
                action = req.get("action")

                if action == "REGISTER":
                    success = database.create_user(req["username"], req["password"])
                    self.send_json(client_socket, {"action": "REGISTER_RESP", "success": success})

                elif action == "LOGIN":
                    user = database.validate_user(req["username"], req["password"])
                    if user:
                        if user["is_banned"]:
                            self.send_json(client_socket, {"action": "LOGIN_RESP", "success": False, "error": "Account has been suspended."})
                            continue
                        
                        user_id = user["id"]
                        with self.clients_lock:
                            self.active_clients[user_id] = client_socket
                            self.client_metadata[client_socket] = {"user_id": user_id, "username": user["username"]}
                        self.send_json(client_socket, {"action": "LOGIN_RESP", "success": True, "user": user})
                        self.log(f"[*] User '{user['username']}' logged in.")
                        self.broadcast_presence()
                    else:
                        self.send_json(client_socket, {"action": "LOGIN_RESP", "success": False, "error": "Invalid credentials."})

                elif user_id:  # Authenticated Routes
                    
                    if action == "FETCH_ROOMS":
                        self.send_json(client_socket, {"action": "ROOMS_LIST", "rooms": database.get_user_rooms(user_id)})

                    elif action == "CREATE_ROOM":
                        room = database.create_room(req["name"], user_id, req.get("password", ""), req.get("avatar_base64", ""))
                        self.send_json(client_socket, {"action": "ROOM_CREATED", "room": room})
                        self.send_json(client_socket, {"action": "ROOMS_LIST", "rooms": database.get_user_rooms(user_id)})

                    elif action == "JOIN_ROOM":
                        room, msg = database.join_room(req["code"], user_id, req.get("password", ""))
                        if room:
                            self.send_json(client_socket, {"action": "ROOM_JOINED", "success": True, "room": room})
                            self.send_json(client_socket, {"action": "ROOMS_LIST", "rooms": database.get_user_rooms(user_id)})
                        else:
                            self.send_json(client_socket, {"action": "ROOM_JOINED", "success": False, "error": msg})

                    elif action == "SEND_MESSAGE":
                        room_id = req["room_id"]
                        content = req["content"].strip()
                        
                        is_valid, warning = self.check_anti_spam(user_id, content)
                        if not is_valid:
                            self.send_json(client_socket, {"action": "SPAM_WARNING", "message": warning})
                            continue
                            
                        profile = database.get_user_profile(user_id)
                        msg = database.save_message(room_id, user_id, content)
                        msg["username"] = profile["username"]
                        msg["avatar_base64"] = profile["avatar_base64"]
                        
                        # Send confirmation to sender (single tick status)
                        self.send_json(client_socket, {"action": "NEW_MESSAGE", "message": msg})
                        # Broadcast to room members
                        self.broadcast_to_room(room_id, {"action": "NEW_MESSAGE", "message": msg}, exclude_user_id=user_id)

                    elif action == "MARK_READ":
                        room_id = req["room_id"]
                        if database.mark_room_messages_read(room_id, user_id):
                            # Broadcast read receipt so senders get the double-tick update
                            self.broadcast_to_room(room_id, {"action": "READ_RECEIPT", "room_id": room_id})

                    elif action == "TYPING_STATUS":
                        self.broadcast_to_room(req["room_id"], {
                            "action": "TYPING_BROADCAST",
                            "room_id": req["room_id"],
                            "username": self.client_metadata[client_socket]["username"],
                            "is_typing": req["is_typing"]
                        }, exclude_user_id=user_id)

                    elif action == "FETCH_HISTORY":
                        history = database.get_room_history(req["room_id"])
                        self.send_json(client_socket, {"action": "HISTORY_LIST", "room_id": req["room_id"], "history": history})

                    elif action == "FETCH_MEMBERS":
                        members = database.get_room_members(req["room_id"])
                        self.send_json(client_socket, {"action": "MEMBERS_LIST", "room_id": req["room_id"], "members": members})

                    elif action == "UPDATE_PROFILE":
                        success = database.update_user_profile(user_id, req["bio"], req["avatar_base64"], req.get("password"), req.get("username"))
                        if success:
                            if req.get("username"):
                                with self.clients_lock: self.client_metadata[client_socket]["username"] = req["username"]
                            self.send_json(client_socket, {"action": "PROFILE_UPDATED", "success": True, "user": database.get_user_profile(user_id)})
                            self.broadcast_presence()
                        else:
                            self.send_json(client_socket, {"action": "PROFILE_UPDATED", "success": False, "error": "Username already taken."})

                    elif action == "GET_PROFILE":
                        self.send_json(client_socket, {"action": "PROFILE_DATA", "profile": database.get_user_profile(req["user_id"])})

                    elif action == "UPDATE_ROOM_SETTINGS":
                        room_id = req["room_id"]
                        rooms = database.get_user_rooms(user_id)
                        room = next((r for r in rooms if r["id"] == room_id), None)
                        if room and room["creator_id"] == user_id:
                            database.update_room_settings(room_id, req["name"], req["password"], req["avatar_base64"])
                            self.broadcast_to_room(room_id, {"action": "ROOM_SETTINGS_UPDATED", "room_id": room_id})

                    elif action == "KICK_USER":
                        room_id = req["room_id"]
                        target_id = req["target_id"]
                        rooms = database.get_user_rooms(user_id)
                        room = next((r for r in rooms if r["id"] == room_id), None)
                        if room and room["creator_id"] == user_id:
                            database.remove_user_from_room(room_id, target_id)
                            self.broadcast_to_room(room_id, {"action": "KICK_EVENT", "room_id": room_id, "target_id": target_id})
                            with self.clients_lock:
                                if target_id in self.active_clients:
                                    self.send_json(self.active_clients[target_id], {"action": "ROOMS_LIST", "rooms": database.get_user_rooms(target_id)})

                    elif action == "DELETE_ROOM":
                        room_id = req["room_id"]
                        rooms = database.get_user_rooms(user_id)
                        room = next((r for r in rooms if r["id"] == room_id), None)
                        if room and room["creator_id"] == user_id:
                            self.broadcast_to_room(room_id, {"action": "ROOM_DELETED", "room_id": room_id})
                            database.delete_room(room_id)
                            self.send_json(client_socket, {"action": "ROOMS_LIST", "rooms": database.get_user_rooms(user_id)})

        except Exception as e:
            pass
        finally:
            with self.clients_lock:
                username = self.client_metadata.get(client_socket, {}).get("username")
                if client_socket in self.client_metadata: del self.client_metadata[client_socket]
                if user_id and user_id in self.active_clients: del self.active_clients[user_id]
            if username:
                self.log(f"[-] User '{username}' disconnected.")
                self.broadcast_presence()
            client_socket.close()

    def start(self):
        context = get_server_context()
        raw_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        raw_server.bind((self.host, self.port))
        raw_server.listen(128)
        
        self.secure_server = context.wrap_socket(raw_server, server_side=True)
        self.log(f"[SYSTEM] Secure gateway listening on TLS://{self.host}:{self.port}")
        self.running = True
        
        try:
            while self.running:
                client_sock, client_addr = self.secure_server.accept()
                threading.Thread(target=self.handle_client, args=(client_sock, client_addr), daemon=True).start()
        except:
            self.log("[SYSTEM] Server shutting down.")