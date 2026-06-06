import customtkinter as ctk
import database

ctk.set_appearance_mode("dark")

class AdminGUI(ctk.CTk):
    def __init__(self, server_instance):
        super().__init__()
        self.title("SecureChat Admin | God Panel")
        self.geometry("950x650")
        self.server = server_instance
        
        # Override server log output to UI
        self.server.set_log_callback(self.log_to_console)
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Top Navbar
        self.nav = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#1E1E2E")
        self.nav.grid(row=0, column=0, sticky="ew")
        self.nav.pack_propagate(False)
        
        ctk.CTkLabel(self.nav, text="GOD MODE", font=("Arial", 18, "bold"), text_color="#F38BA8").pack(side="left", padx=25)
        
        ctk.CTkButton(self.nav, text="Console Logs", width=130, command=lambda: self.show_frame("Logs")).pack(side="left", padx=10)
        ctk.CTkButton(self.nav, text="Manage Users", width=130, command=lambda: self.show_frame("Users")).pack(side="left", padx=10)
        ctk.CTkButton(self.nav, text="Manage Rooms", width=130, command=lambda: self.show_frame("Rooms")).pack(side="left", padx=10)
        
        self.frames = {}
        
        # --- Logs Frame ---
        f_logs = ctk.CTkFrame(self, fg_color="transparent")
        self.frames["Logs"] = f_logs
        self.console = ctk.CTkTextbox(f_logs, state="disabled", font=("Consolas", 13), fg_color="#11111B")
        self.console.pack(fill="both", expand=True, padx=20, pady=20)
        
        # --- Users Frame ---
        f_users = ctk.CTkFrame(self, fg_color="transparent")
        self.frames["Users"] = f_users
        ctk.CTkButton(f_users, text="Refresh Users", command=self.load_users).pack(pady=10)
        self.users_scroll = ctk.CTkScrollableFrame(f_users, fg_color="#181825")
        self.users_scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        # --- Rooms Frame ---
        f_rooms = ctk.CTkFrame(self, fg_color="transparent")
        self.frames["Rooms"] = f_rooms
        ctk.CTkButton(f_rooms, text="Refresh Rooms", command=self.load_rooms).pack(pady=10)
        self.rooms_scroll = ctk.CTkScrollableFrame(f_rooms, fg_color="#181825")
        self.rooms_scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self.show_frame("Logs")

    def log_to_console(self, msg):
        self.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.console.configure(state="normal")
        self.console.insert("end", msg + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def show_frame(self, name):
        for f in self.frames.values():
            f.grid_forget()
        self.frames[name].grid(row=1, column=0, sticky="nsew")
        if name == "Users": self.load_users()
        if name == "Rooms": self.load_rooms()

    def load_users(self):
        for w in self.users_scroll.winfo_children(): w.destroy()
        users = database.get_all_users()
        for u in users:
            row = ctk.CTkFrame(self.users_scroll, fg_color="#313244", corner_radius=10)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=f"ID: {u['id']} | {u['username']}", width=250, anchor="w", font=("Arial", 14, "bold")).pack(side="left", padx=15, pady=10)
            
            is_online = u['id'] in self.server.active_clients
            status_text = "🟢 Online" if is_online else "⚪ Offline"
            ctk.CTkLabel(row, text=status_text, width=100).pack(side="left")
            
            if u['is_banned']:
                ctk.CTkButton(row, text="UNBAN", fg_color="#A6E3A1", text_color="#11111B", font=("Arial", 12, "bold"), width=90, command=lambda uid=u['id']: self.toggle_ban(uid, 0)).pack(side="right", padx=15)
            else:
                ctk.CTkButton(row, text="BAN", fg_color="#F38BA8", text_color="#11111B", font=("Arial", 12, "bold"), width=90, command=lambda uid=u['id']: self.toggle_ban(uid, 1)).pack(side="right", padx=15)

    def toggle_ban(self, user_id, ban_status):
        database.set_user_ban(user_id, ban_status)
        if ban_status == 1:
            self.server.kick_user_force(user_id, "Account suspended by Administrator.")
        self.load_users()
        self.log_to_console(f"[ADMIN] User {user_id} ban status updated.")

    def load_rooms(self):
        for w in self.rooms_scroll.winfo_children(): w.destroy()
        rooms = database.get_all_rooms()
        for r in rooms:
            row = ctk.CTkFrame(self.rooms_scroll, fg_color="#313244", corner_radius=10)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=f"Code: [{r['code']}] | {r['name']}", width=350, anchor="w", font=("Arial", 14, "bold")).pack(side="left", padx=15, pady=10)
            ctk.CTkButton(row, text="PURGE ROOM", fg_color="#F38BA8", text_color="#11111B", font=("Arial", 12, "bold"), width=120, command=lambda rid=r['id']: self.force_delete_room(rid)).pack(side="right", padx=15)

    def force_delete_room(self, room_id):
        database.delete_room(room_id)
        self.server.broadcast_to_room(room_id, {"action": "ROOM_DELETED", "room_id": room_id})
        self.load_rooms()
        self.log_to_console(f"[ADMIN] Room {room_id} has been forcefully purged.")