import os
import threading
from database import init_db
from server import ChatServer
from admin_ui import AdminGUI

if __name__ == "__main__":
    # Ensure database and certificates are always inside server_app/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base_dir, "certificate"), exist_ok=True)
    
    print("[SYSTEM] Initializing database...")
    init_db()
    
    # Initialize Core Network Server
    server = ChatServer()
    
    # Run the socket server in a background daemon thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    # Run the Professional Admin "God Panel" on the main GUI thread
    print("[SYSTEM] Launching Admin GUI...")
    admin_app = AdminGUI(server)
    admin_app.mainloop()