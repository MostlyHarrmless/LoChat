import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from network import NetworkManager
from theme import Theme
from utils import fix_rtl, get_color_from_string, make_fallback_avatar, convert_base64_to_image, convert_image_to_base64
import time
from datetime import datetime

ctk.set_appearance_mode("dark")

class HoverButton(ctk.CTkButton):
    """Button with smooth hover transition effect."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
    def on_enter(self, e): pass
    def on_leave(self, e): pass

class ChatApp(ctk.CTk):
    """Root Window Architecture - Ensures ONE CTk instance."""
    def __init__(self):
        super().__init__()
        self.title("SecureChat Professional")
        self.geometry("1200x800")
        self.minsize(1050, 650)
        self.configure(fg_color=Theme.BG_MAIN)
        
        self.net = NetworkManager()
        self.user_data = None
        self.online_users = set()
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        for F in (LoginFrame, RegisterFrame, MainChatFrame):
            page_name = F.__name__
            frame = F(parent=self, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            
        self.show_frame("LoginFrame")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, 'on_show'):
            frame.on_show()

    def connect_server(self):
        if not self.net.running: return self.net.connect()
        return True, "Connected"

class BaseAuthFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=Theme.BG_MAIN)
        self.controller = controller
        
        # Premium Center Card with subtle shadows/borders
        self.card = ctk.CTkFrame(self, fg_color=Theme.BG_SIDEBAR, corner_radius=24, width=450, height=580, border_width=1, border_color=Theme.BG_TERTIARY)
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        self.card.pack_propagate(False)
        
        self.title_lbl = ctk.CTkLabel(self.card, text="", font=Theme.font_title(26), text_color=Theme.TEXT_MAIN)
        self.title_lbl.pack(pady=(55, 35))
        
        self.user_entry = ctk.CTkEntry(self.card, placeholder_text="Username", width=340, height=52, font=Theme.font_main(15), fg_color=Theme.BG_TERTIARY, border_width=0, corner_radius=12)
        self.user_entry.pack(pady=12)
        
        self.pass_entry = ctk.CTkEntry(self.card, placeholder_text="Password", width=340, height=52, font=Theme.font_main(15), fg_color=Theme.BG_TERTIARY, border_width=0, show="•", corner_radius=12)
        self.pass_entry.pack(pady=12)
        
        self.error_lbl = ctk.CTkLabel(self.card, text="", text_color=Theme.ERROR, font=Theme.font_small(12), wraplength=300)
        self.error_lbl.pack(pady=8)
        
        self.action_btn = HoverButton(self.card, text="", width=340, height=52, font=Theme.font_bold(16), fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, text_color="#FFFFFF", corner_radius=12)
        self.action_btn.pack(pady=(10, 20))
        
        self.switch_btn = ctk.CTkButton(self.card, text="", width=340, height=40, font=Theme.font_small(13), fg_color="transparent", text_color=Theme.TEXT_MUTED, hover_color=Theme.BG_TERTIARY, corner_radius=8)
        self.switch_btn.pack(pady=5)

class LoginFrame(BaseAuthFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.title_lbl.configure(text="Welcome Back")
        self.action_btn.configure(text="Sign In", command=self.attempt_login)
        self.switch_btn.configure(text="Don't have an account? Register", command=lambda: self.controller.show_frame("RegisterFrame"))

    def attempt_login(self):
        user, pw = self.user_entry.get().strip(), self.pass_entry.get().strip()
        if not user or not pw: return self.error_lbl.configure(text="Credentials cannot be empty.")
        success, msg = self.controller.connect_server()
        if not success: return self.error_lbl.configure(text="Server connection failed.")
            
        self.controller.net.set_callback("LOGIN_RESP", lambda d: self.after(0, self._process_login, d))
        self.controller.net.set_callback("FORCE_LOGOUT", lambda d: self.after(0, self._force_logout, d))
        self.controller.net.send({"action": "LOGIN", "username": user, "password": pw})

    def _process_login(self, data):
        if data.get("success"):
            self.controller.user_data = data["user"]
            self.error_lbl.configure(text="")
            self.pass_entry.delete(0, 'end')
            self.controller.show_frame("MainChatFrame")
        else:
            self.error_lbl.configure(text=data.get("error", "Access denied."))
            self.controller.net.disconnect()

    def _force_logout(self, data):
        messagebox.showerror("Session Terminated", data.get("reason", "Disconnected."))
        self.controller.net.disconnect()
        self.controller.show_frame("LoginFrame")

class RegisterFrame(BaseAuthFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.title_lbl.configure(text="Create Account")
        self.action_btn.configure(text="Register", command=self.attempt_register)
        self.switch_btn.configure(text="Back to Sign In", command=lambda: self.controller.show_frame("LoginFrame"))

    def attempt_register(self):
        user, pw = self.user_entry.get().strip(), self.pass_entry.get().strip()
        if not user or not pw: return self.error_lbl.configure(text="Fields cannot be empty.")
        success, msg = self.controller.connect_server()
        if not success: return self.error_lbl.configure(text="Server connection failed.")
            
        self.controller.net.set_callback("REGISTER_RESP", lambda d: self.after(0, self._process_register, d))
        self.controller.net.send({"action": "REGISTER", "username": user, "password": pw})

    def _process_register(self, data):
        if data.get("success"):
            self.error_lbl.configure(text="Account registered securely!", text_color=Theme.SUCCESS)
            self.after(1200, lambda: self.controller.show_frame("LoginFrame"))
            self.controller.net.disconnect()
        else:
            self.error_lbl.configure(text="Username already taken.", text_color=Theme.ERROR)
            self.controller.net.disconnect()

class MainChatFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=Theme.BG_MAIN)
        self.controller = controller
        self.current_room = None
        self.is_admin = False
        self.unread_badges = {}
        self.last_typing_sent = 0.0
        self.last_sender_id = None
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1) # Main Chat Area
        
        # ==========================================
        # LEFT SIDEBAR (Rooms & Navigation)
        # ==========================================
        self.sidebar = ctk.CTkFrame(self, width=320, fg_color=Theme.BG_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1)
        
        # User Header
        self.user_header = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=80, corner_radius=0)
        self.user_header.grid(row=0, column=0, sticky="ew")
        self.user_header.pack_propagate(False)
        
        self.my_avatar_lbl = ctk.CTkLabel(self.user_header, text="", cursor="hand2")
        self.my_avatar_lbl.pack(side="left", padx=15, pady=15)
        self.my_avatar_lbl.bind("<Button-1>", lambda e: self.open_user_settings())
        
        self.my_name_lbl = ctk.CTkLabel(self.user_header, text="", font=Theme.font_bold(16), text_color=Theme.TEXT_MAIN)
        self.my_name_lbl.pack(side="left", padx=5)
        
        self.settings_btn = ctk.CTkButton(self.user_header, text="⚙", width=40, height=40, fg_color="transparent", font=("Arial", 20), text_color=Theme.TEXT_MUTED, hover_color=Theme.BG_TERTIARY, command=self.open_user_settings)
        self.settings_btn.pack(side="right", padx=15)

        # Actions Row
        self.room_actions = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.room_actions.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="ew")
        self.room_actions.grid_columnconfigure(0, weight=1)
        self.room_actions.grid_columnconfigure(1, weight=1)
        HoverButton(self.room_actions, text="Create Room", font=Theme.font_bold(13), fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, text_color="#FFFFFF", corner_radius=10, command=self.popup_create_room).grid(row=0, column=0, padx=(0,5), sticky="ew")
        HoverButton(self.room_actions, text="Join Room", font=Theme.font_bold(13), fg_color=Theme.BG_TERTIARY, hover_color=Theme.BG_POPUP, text_color=Theme.TEXT_MAIN, corner_radius=10, command=self.popup_join_room).grid(row=0, column=1, padx=(5,0), sticky="ew")
        
        # Scrollable Room List
        self.rooms_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.rooms_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Footer Action
        HoverButton(self.sidebar, text="Sign Out", fg_color="transparent", border_color=Theme.ERROR, border_width=1, hover_color=Theme.ERROR, text_color=Theme.TEXT_MAIN, corner_radius=10, height=40, command=self.logout).grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        # ==========================================
        # CENTER (Chat Area)
        # ==========================================
        self.chat_area = ctk.CTkFrame(self, fg_color=Theme.BG_MAIN, corner_radius=0)
        self.chat_area.grid(row=0, column=1, sticky="nsew")
        self.chat_area.grid_rowconfigure(1, weight=1)
        self.chat_area.grid_columnconfigure(0, weight=1)
        
        # Top Header (Room Info)
        self.header = ctk.CTkFrame(self.chat_area, height=80, fg_color=Theme.BG_MAIN, corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.pack_propagate(False)
        
        self.header_avatar_lbl = ctk.CTkLabel(self.header, text="")
        self.header_avatar_lbl.pack(side="left", padx=20, pady=15)
        
        self.header_info = ctk.CTkFrame(self.header, fg_color="transparent")
        self.header_info.pack(side="left", fill="y", pady=15)
        self.room_title = ctk.CTkLabel(self.header_info, text="Select a Room", font=Theme.font_title(20), text_color=Theme.TEXT_MAIN, anchor="w")
        self.room_title.pack(anchor="w")
        self.room_status_lbl = ctk.CTkLabel(self.header_info, text="", font=Theme.font_small(12), text_color=Theme.TEXT_MUTED, anchor="w")
        self.room_status_lbl.pack(anchor="w")
        
        self.room_settings_btn = ctk.CTkButton(self.header, text="Manage Room", width=120, height=36, font=Theme.font_bold(13), fg_color=Theme.BG_TERTIARY, hover_color=Theme.BG_SIDEBAR, corner_radius=8, command=self.open_room_settings)
        
        # Divider Line
        divider = ctk.CTkFrame(self.chat_area, height=1, fg_color=Theme.BG_TERTIARY)
        divider.grid(row=1, column=0, sticky="new")
        
        # Messages List Stream
        self.msg_scroll = ctk.CTkScrollableFrame(self.chat_area, fg_color="transparent")
        self.msg_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(5, 5))
        self.msg_scroll.bind("<Configure>", lambda e: self.check_scroll_position())
        
        # Floating Badges
        self.floating_btn = HoverButton(self.chat_area, text="↓ New Messages", fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, text_color="#FFFFFF", font=Theme.font_bold(13), corner_radius=20, width=160, height=40, command=self.scroll_stream_bottom)
        
        # Input Dock
        self.input_dock = ctk.CTkFrame(self.chat_area, height=85, fg_color="transparent", corner_radius=0)
        self.input_dock.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.input_dock.grid_columnconfigure(0, weight=1)
        
        self.input_bg = ctk.CTkFrame(self.input_dock, fg_color=Theme.BG_TERTIARY, corner_radius=16)
        self.input_bg.grid(row=0, column=0, sticky="nsew")
        self.input_bg.grid_columnconfigure(0, weight=1)
        
        # Using Textbox for Shift+Enter multi-line support
        self.msg_entry = ctk.CTkTextbox(self.input_bg, height=45, font=Theme.font_main(15), fg_color="transparent", text_color=Theme.TEXT_MAIN, border_width=0, wrap="word")
        self.msg_entry.grid(row=0, column=0, sticky="nsew", padx=15, pady=10)
        self.msg_entry.bind("<KeyRelease>", self.on_typing_detect)
        self.msg_entry.bind("<Return>", self.handle_enter_press)
        self.msg_entry.bind("<Shift-Return>", lambda e: None)
        
        self.send_btn = HoverButton(self.input_bg, text="Send", width=80, height=45, font=Theme.font_bold(14), fg_color=Theme.ACCENT, text_color="#FFFFFF", hover_color=Theme.ACCENT_HOVER, corner_radius=12, command=self.send_message_stream)
        self.send_btn.grid(row=0, column=1, padx=10, pady=10)

        # ==========================================
        # RIGHT SIDEBAR (Members)
        # ==========================================
        self.members_sidebar = ctk.CTkFrame(self, width=260, fg_color=Theme.BG_SIDEBAR, corner_radius=0, border_width=1, border_color=Theme.BG_MAIN)
        self.members_sidebar.grid(row=0, column=2, sticky="nsew")
        self.members_sidebar.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.members_sidebar, text="MEMBERS —", font=Theme.font_bold(12), text_color=Theme.TEXT_MUTED).grid(row=0, column=0, pady=(25, 10), padx=20, sticky="w")
        self.members_scroll = ctk.CTkScrollableFrame(self.members_sidebar, fg_color="transparent")
        self.members_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

    def on_show(self):
        self.update_my_header_ui()
        self.msg_entry.configure(state="disabled")
        
        net = self.controller.net
        net.set_callback("ROOMS_LIST", lambda d: self.after(0, self.ui_refresh_rooms, d))
        net.set_callback("HISTORY_LIST", lambda d: self.after(0, self.ui_refresh_history, d))
        net.set_callback("MEMBERS_LIST", lambda d: self.after(0, self.ui_refresh_members, d))
        net.set_callback("NEW_MESSAGE", lambda d: self.after(0, self.ui_append_msg, d))
        net.set_callback("ROOM_JOINED", lambda d: self.after(0, self.ui_handle_join_resp, d))
        net.set_callback("PROFILE_DATA", lambda d: self.after(0, self.ui_render_avatar_popup, d))
        net.set_callback("PROFILE_UPDATED", lambda d: self.after(0, self.ui_profile_synced, d))
        net.set_callback("ROOM_DELETED", lambda d: self.after(0, self.ui_handle_room_purged, d))
        net.set_callback("PRESENCE_UPDATE", lambda d: self.after(0, self.ui_update_presence, d))
        net.set_callback("READ_RECEIPT", lambda d: self.after(0, self.ui_handle_read_receipt, d))
        net.set_callback("TYPING_BROADCAST", lambda d: self.after(0, self.ui_handle_typing_status, d))
        net.set_callback("SPAM_WARNING", lambda d: messagebox.showwarning("Anti-Spam", d["message"]))
        net.set_callback("DISCONNECT", lambda d: self.after(0, self.logout))
        
        net.send({"action": "FETCH_ROOMS"})

    def handle_enter_press(self, event):
        self.send_message_stream()
        return "break" # Prevent actual newline

    def ui_update_presence(self, data):
        self.controller.online_users = set(data["online_users"])
        if self.current_room:
            self.controller.net.send({"action": "FETCH_MEMBERS", "room_id": self.current_room["id"]})

    def update_my_header_ui(self):
        user = self.controller.user_data
        self.my_name_lbl.configure(text=user["username"])
        img = convert_base64_to_image(user.get("avatar_base64"), size=46)
        if not img: img = make_fallback_avatar(user["username"], size=46)
        self.my_avatar_lbl.configure(image=img)

    def ui_refresh_rooms(self, data):
        for widget in self.rooms_scroll.winfo_children(): widget.destroy()
        for room in data.get("rooms", []):
            is_active = (self.current_room and self.current_room["id"] == room["id"])
            frame = ctk.CTkFrame(self.rooms_scroll, fg_color=Theme.BG_TERTIARY if is_active else "transparent", corner_radius=10)
            frame.pack(fill="x", pady=2, padx=5)
            
            r_img = convert_base64_to_image(room.get("avatar_base64"), size=38)
            if not r_img: r_img = make_fallback_avatar(room["name"], size=38)
            ctk.CTkLabel(frame, image=r_img, text="").pack(side="left", padx=8, pady=8)
            
            btn_text = fix_rtl(room["name"]) + (" 🔒" if room.get("has_password") else "")
            
            btn = ctk.CTkButton(frame, text=btn_text, anchor="w", font=Theme.font_bold(14), fg_color="transparent", hover_color=Theme.BG_TERTIARY, text_color=Theme.TEXT_MAIN, command=lambda r=room: self.action_room_select(r))
            btn.pack(side="left", fill="x", expand=True)
            
            # Unread Badge (Red circle)
            rid = room["id"]
            if rid in self.unread_badges and self.unread_badges[rid] > 0:
                ctk.CTkLabel(frame, text=str(self.unread_badges[rid]), font=Theme.font_bold(11), fg_color=Theme.ERROR, text_color="#FFFFFF", width=24, height=24, corner_radius=12).pack(side="right", padx=10)

    def action_room_select(self, room):
        self.current_room = room
        self.unread_badges[room["id"]] = 0
        self.last_sender_id = None
        
        self.room_title.configure(text=fix_rtl(room["name"]))
        self.room_status_lbl.configure(text=f"Invite Code: {room['code']}")
        self.msg_entry.configure(state="normal")
        
        r_img = convert_base64_to_image(room.get("avatar_base64"), size=50)
        if not r_img: r_img = make_fallback_avatar(room["name"], size=50)
        self.header_avatar_lbl.configure(image=r_img)
        
        self.is_admin = (room["creator_id"] == self.controller.user_data["id"])
        if self.is_admin: self.room_settings_btn.pack(side="right", padx=25)
        else: self.room_settings_btn.pack_forget()
            
        self.controller.net.send({"action": "FETCH_HISTORY", "room_id": room["id"]})
        self.controller.net.send({"action": "FETCH_MEMBERS", "room_id": room["id"]})
        self.controller.net.send({"action": "MARK_READ", "room_id": room["id"]})
        self.controller.net.send({"action": "FETCH_ROOMS"}) 

    def ui_refresh_history(self, data):
        if not self.current_room or data["room_id"] != self.current_room["id"]: return
        for widget in self.msg_scroll.winfo_children(): widget.destroy()
        self.last_sender_id = None
        for msg in data.get("history", []):
            self.render_message_card(msg)
        self.scroll_stream_bottom()

    def ui_refresh_members(self, data):
        if not self.current_room or data["room_id"] != self.current_room["id"]: return
        for widget in self.members_scroll.winfo_children(): widget.destroy()
        for member in data.get("members", []):
            m_frame = ctk.CTkFrame(self.members_scroll, fg_color="transparent")
            m_frame.pack(fill="x", pady=4, padx=5)
            
            m_img = convert_base64_to_image(member.get("avatar_base64"), size=36)
            if not m_img: m_img = make_fallback_avatar(member["username"], size=36)
            m_lbl = ctk.CTkLabel(m_frame, image=m_img, text="", cursor="hand2")
            m_lbl.pack(side="left", padx=5)
            m_lbl.bind("<Button-1>", lambda e, uid=member["id"]: self.action_fetch_profile(uid))
            
            name_lbl = ctk.CTkLabel(m_frame, text=member["username"], text_color=Theme.TEXT_MAIN, font=Theme.font_bold(13), cursor="hand2")
            name_lbl.pack(side="left", padx=8)
            name_lbl.bind("<Button-1>", lambda e, uid=member["id"]: self.action_fetch_profile(uid))
            
            is_online = member["id"] in self.controller.online_users
            status_color = Theme.SUCCESS if is_online else Theme.BG_TERTIARY
            ctk.CTkFrame(m_frame, width=10, height=10, corner_radius=5, fg_color=status_color).pack(side="right", padx=10)

    def check_scroll_position(self):
        try:
            pos = self.msg_scroll._parent_canvas.yview()
            if pos[1] >= 0.95:
                self.floating_btn.place_forget()
        except: pass

    def ui_append_msg(self, data):
        msg = data["message"]
        rid = msg["room_id"]
        
        if self.current_room and rid == self.current_room["id"]:
            self.render_message_card(msg)
            pos = self.msg_scroll._parent_canvas.yview()
            if pos[1] < 0.9:
                self.floating_btn.place(relx=0.5, rely=0.85, anchor="center")
            else:
                self.scroll_stream_bottom()
                
            if msg["sender_id"] != self.controller.user_data["id"]:
                self.controller.net.send({"action": "MARK_READ", "room_id": rid})
        else:
            self.unread_badges[rid] = self.unread_badges.get(rid, 0) + 1
            self.controller.net.send({"action": "FETCH_ROOMS"})

    def ui_handle_read_receipt(self, data):
        if self.current_room and data["room_id"] == self.current_room["id"]:
            self.controller.net.send({"action": "FETCH_HISTORY", "room_id": self.current_room["id"]})

    def render_message_card(self, msg):
        """Advanced Message Bubble Rendering with Grouping and Perfect Alignment"""
        is_me = (msg["sender_id"] == self.controller.user_data["id"])
        is_grouped = (self.last_sender_id == msg["sender_id"])
        
        dt = datetime.fromisoformat(msg["timestamp"])
        time_str = dt.strftime("%H:%M")
        
        # Row Container spans full width to allow left/right anchoring
        row_container = ctk.CTkFrame(self.msg_scroll, fg_color="transparent")
        row_container.pack(fill="x", pady=2 if is_grouped else 10)
        
        # --- Recipient Avatar (Left side) ---
        if not is_me:
            if not is_grouped:
                av_img = convert_base64_to_image(msg.get("avatar_base64"), size=40)
                if not av_img: av_img = make_fallback_avatar(msg["username"], size=40)
                avatar_btn = ctk.CTkLabel(row_container, image=av_img, text="", cursor="hand2")
                avatar_btn.bind("<Button-1>", lambda e, uid=msg["sender_id"]: self.action_fetch_profile(uid))
                avatar_btn.pack(side="left", padx=(5, 10), anchor="n")
            else:
                # Keep indentation for grouped messages
                ctk.CTkFrame(row_container, width=40, height=40, fg_color="transparent").pack(side="left", padx=(5, 10))
        
        # --- Bubble Container ---
        bubble_wrapper = ctk.CTkFrame(row_container, fg_color=Theme.BUBBLE_ME if is_me else Theme.BUBBLE_OTHER, corner_radius=16)
        
        # If it's grouped, tweak the corner radius slightly to look cohesive (advanced UI detail)
        # CTk doesn't natively support per-corner radius, so we just stick to 16.
        bubble_wrapper.pack(side="right" if is_me else "left", ipadx=14, ipady=8, padx=10)
        
        # Name Header (For others, un-grouped)
        if not is_me and not is_grouped:
            name_lbl = ctk.CTkLabel(bubble_wrapper, text=msg["username"], font=Theme.font_bold(13), text_color=Theme.ACCENT)
            name_lbl.pack(anchor="w", pady=(0, 2))
            
        # Message Content (Fixed wraplength for UI stability)
        content_lbl = ctk.CTkLabel(bubble_wrapper, text=fix_rtl(msg["content"]), font=Theme.font_main(15), text_color=Theme.TEXT_MAIN, justify="left", wraplength=450)
        content_lbl.pack(anchor="w")
        
        # Meta footer (Time + Read Ticks)
        meta_frame = ctk.CTkFrame(bubble_wrapper, fg_color="transparent")
        meta_frame.pack(anchor="e", pady=(4, 0))
        
        ctk.CTkLabel(meta_frame, text=time_str, font=("Arial", 10), text_color=Theme.TEXT_MUTED if not is_me else "#B9BCCC").pack(side="left", padx=(0, 4))
        
        if is_me:
            ticks = "✓✓" if msg.get("status") == "read" else "✓"
            t_color = Theme.STATUS_READ if ticks == "✓✓" else Theme.STATUS_DELIVERED
            ctk.CTkLabel(meta_frame, text=ticks, font=("Arial", 11, "bold"), text_color=t_color).pack(side="left")

        self.last_sender_id = msg["sender_id"]

    def on_typing_detect(self, event):
        now = time.time()
        if self.current_room and (now - self.last_typing_sent > 2.0):
            self.last_typing_sent = now
            self.controller.net.send({"action": "TYPING_STATUS", "room_id": self.current_room["id"], "is_typing": True})
            self.after(3000, self.clear_my_typing_state)

    def clear_my_typing_state(self):
        if self.current_room:
            self.controller.net.send({"action": "TYPING_STATUS", "room_id": self.current_room["id"], "is_typing": False})

    def ui_handle_typing_status(self, data):
        if self.current_room and data["room_id"] == self.current_room["id"]:
            if data["is_typing"]:
                self.room_status_lbl.configure(text=f"{data['username']} is typing...", text_color=Theme.SUCCESS)
            else:
                self.room_status_lbl.configure(text=f"Invite Code: {self.current_room['code']}", text_color=Theme.TEXT_MUTED)

    def send_message_stream(self):
        content = self.msg_entry.get("1.0", "end").strip()
        if content and self.current_room:
            self.controller.net.send({"action": "SEND_MESSAGE", "room_id": self.current_room["id"], "content": content})
            self.msg_entry.delete("1.0", "end")
            self.clear_my_typing_state()

    def scroll_stream_bottom(self):
        self.floating_btn.place_forget()
        self.msg_scroll.update_idletasks()
        self.msg_scroll._parent_canvas.yview_moveto(1.0)

    # --- POPUPS / MODALS ---
    
    def popup_create_room(self):
        top = ctk.CTkToplevel(self)
        top.title("New Server")
        top.geometry("450x480")
        top.configure(fg_color=Theme.BG_POPUP)
        top.attributes("-topmost", True)
        
        ctk.CTkLabel(top, text="Create a Channel", font=Theme.font_title(), text_color=Theme.TEXT_MAIN).pack(pady=(30, 20))
        
        name_ent = ctk.CTkEntry(top, placeholder_text="Server Name", width=340, height=45, font=Theme.font_main(), fg_color=Theme.BG_TERTIARY, border_width=0, corner_radius=10)
        name_ent.pack(pady=10)
        pass_ent = ctk.CTkEntry(top, placeholder_text="Password (Optional)", width=340, height=45, font=Theme.font_main(), fg_color=Theme.BG_TERTIARY, border_width=0, corner_radius=10)
        pass_ent.pack(pady=10)
        
        avatar_b64 = [""]
        def load_avatar():
            fp = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp")])
            if fp:
                avatar_b64[0] = convert_image_to_base64(fp)
                lbl_status.configure(text="Avatar Image Loaded.", text_color=Theme.SUCCESS)
                
        HoverButton(top, text="Upload Server Icon", width=340, height=40, font=Theme.font_bold(13), fg_color=Theme.BG_TERTIARY, hover_color=Theme.BG_SIDEBAR, corner_radius=10, command=load_avatar).pack(pady=10)
        lbl_status = ctk.CTkLabel(top, text="", font=Theme.font_small())
        lbl_status.pack()

        def commit():
            if name_ent.get().strip():
                self.controller.net.send({"action": "CREATE_ROOM", "name": name_ent.get().strip(), "password": pass_ent.get().strip(), "avatar_base64": avatar_b64[0]})
                top.destroy()
        HoverButton(top, text="Deploy Server", width=340, height=45, font=Theme.font_bold(), fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, corner_radius=10, command=commit).pack(pady=(15, 20))

    def popup_join_room(self):
        top = ctk.CTkToplevel(self)
        top.title("Join Server")
        top.geometry("420x350")
        top.configure(fg_color=Theme.BG_POPUP)
        top.attributes("-topmost", True)
        
        ctk.CTkLabel(top, text="Join via Code", font=Theme.font_title()).pack(pady=(30, 20))
        code_ent = ctk.CTkEntry(top, placeholder_text="Invite Code (e.g., A1B2C3D4)", width=340, height=45, font=Theme.font_main(), fg_color=Theme.BG_TERTIARY, border_width=0, corner_radius=10)
        code_ent.pack(pady=10)
        pass_ent = ctk.CTkEntry(top, placeholder_text="Password (If required)", width=340, height=45, font=Theme.font_main(), fg_color=Theme.BG_TERTIARY, border_width=0, show="•", corner_radius=10)
        pass_ent.pack(pady=10)
        
        def commit():
            c = code_ent.get().strip().upper()
            if c:
                self.controller.net.send({"action": "JOIN_ROOM", "code": c, "password": pass_ent.get().strip()})
                top.destroy()
        HoverButton(top, text="Join Server", width=340, height=45, font=Theme.font_bold(), fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, corner_radius=10, command=commit).pack(pady=(15, 20))

    def ui_handle_join_resp(self, data):
        if not data.get("success"): messagebox.showerror("Connection Error", data.get("error", "Link rejected."))

    def open_user_settings(self):
        top = ctk.CTkToplevel(self)
        top.title("User Settings")
        top.geometry("480x600")
        top.configure(fg_color=Theme.BG_POPUP)
        top.attributes("-topmost", True)
        
        user = self.controller.user_data
        ctk.CTkLabel(top, text="My Profile", font=Theme.font_title()).pack(pady=(30, 20))
        
        name_ent = ctk.CTkEntry(top, width=360, height=45, font=Theme.font_main(), fg_color=Theme.BG_TERTIARY, border_width=0, corner_radius=10)
        name_ent.insert(0, user["username"])
        name_ent.pack(pady=10)
        
        bio_ent = ctk.CTkEntry(top, placeholder_text="About Me", width=360, height=45, font=Theme.font_main(), fg_color=Theme.BG_TERTIARY, border_width=0, corner_radius=10)
        bio_ent.insert(0, user.get("bio", ""))
        bio_ent.pack(pady=10)
        
        pass_ent = ctk.CTkEntry(top, placeholder_text="New Password (Leave blank to keep)", width=360, height=45, font=Theme.font_main(), fg_color=Theme.BG_TERTIARY, border_width=0, show="•", corner_radius=10)
        pass_ent.pack(pady=10)
        
        avatar_b64 = [user.get("avatar_base64", "")]
        
        def load_img():
            fp = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp")])
            if fp:
                avatar_b64[0] = convert_image_to_base64(fp)
                lbl_info.configure(text="Avatar optimized and loaded.", text_color=Theme.SUCCESS)
                
        HoverButton(top, text="Change Avatar", width=360, height=40, font=Theme.font_bold(13), fg_color=Theme.BG_TERTIARY, hover_color=Theme.BG_SIDEBAR, corner_radius=10, command=load_img).pack(pady=(10, 5))
        lbl_info = ctk.CTkLabel(top, text="", font=Theme.font_small())
        lbl_info.pack()
        
        def save():
            self.controller.net.send({"action": "UPDATE_PROFILE", "username": name_ent.get().strip(), "bio": bio_ent.get().strip(), "password": pass_ent.get().strip(), "avatar_base64": avatar_b64[0]})
            top.destroy()
            
        HoverButton(top, text="Save Changes", width=360, height=45, fg_color=Theme.SUCCESS, hover_color="#238636", text_color="#FFFFFF", font=Theme.font_bold(), corner_radius=10, command=save).pack(pady=(15, 20))

    def ui_profile_synced(self, data):
        if data.get("success"):
            self.controller.user_data = data["user"]
            self.update_my_header_ui()
            if self.current_room: self.controller.net.send({"action": "FETCH_MEMBERS", "room_id": self.current_room["id"]})
        else:
            messagebox.showerror("Error", data.get("error"))

    def open_room_settings(self):
        if not self.current_room or not self.is_admin: return
        top = ctk.CTkToplevel(self)
        top.title("Server Settings")
        top.geometry("480x550")
        top.configure(fg_color=Theme.BG_POPUP)
        top.attributes("-topmost", True)
        
        ctk.CTkLabel(top, text="Server Configuration", font=Theme.font_title()).pack(pady=(30, 20))
        name_ent = ctk.CTkEntry(top, width=360, height=45, font=Theme.font_main(), fg_color=Theme.BG_TERTIARY, border_width=0, corner_radius=10)
        name_ent.insert(0, self.current_room["name"])
        name_ent.pack(pady=10)
        pass_ent = ctk.CTkEntry(top, placeholder_text="Update Password", width=360, height=45, font=Theme.font_main(), fg_color=Theme.BG_TERTIARY, border_width=0, corner_radius=10)
        pass_ent.pack(pady=10)
        
        avatar_b64 = [self.current_room.get("avatar_base64", "")]
        def load_img():
            fp = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp")])
            if fp: avatar_b64[0] = convert_image_to_base64(fp)
        HoverButton(top, text="Change Server Icon", width=360, height=40, font=Theme.font_bold(13), fg_color=Theme.BG_TERTIARY, hover_color=Theme.BG_SIDEBAR, corner_radius=10, command=load_img).pack(pady=(10, 20))

        def save():
            self.controller.net.send({"action": "UPDATE_ROOM_SETTINGS", "room_id": self.current_room["id"], "name": name_ent.get().strip(), "password": pass_ent.get().strip(), "avatar_base64": avatar_b64[0]})
            top.destroy()
            
        def delete_r():
            if messagebox.askyesno("Delete Server", "This action cannot be undone. Are you sure?"):
                self.controller.net.send({"action": "DELETE_ROOM", "room_id": self.current_room["id"]})
                top.destroy()

        HoverButton(top, text="Save Settings", width=360, height=45, fg_color=Theme.SUCCESS, hover_color="#238636", font=Theme.font_bold(), corner_radius=10, command=save).pack(pady=10)
        HoverButton(top, text="Delete Server", width=360, height=45, fg_color=Theme.ERROR, hover_color="#DA3633", font=Theme.font_bold(), corner_radius=10, command=delete_r).pack(pady=10)

    def action_fetch_profile(self, user_id):
        self.controller.net.send({"action": "GET_PROFILE", "user_id": user_id})

    def ui_render_avatar_popup(self, data):
        prof = data["profile"]
        top = ctk.CTkToplevel(self)
        top.title("User Profile")
        top.geometry("400x520")
        top.configure(fg_color=Theme.BG_POPUP)
        top.attributes("-topmost", True)
        
        img = convert_base64_to_image(prof.get("avatar_base64"), size=180)
        if not img: img = make_fallback_avatar(prof["username"], size=180)
        ctk.CTkLabel(top, image=img, text="").pack(pady=(35, 20))
        
        ctk.CTkLabel(top, text=prof["username"], font=Theme.font_title(24), text_color=Theme.TEXT_MAIN).pack(pady=5)
        status = "🟢 Online" if prof['id'] in self.controller.online_users else "⚪ Offline"
        ctk.CTkLabel(top, text=status, font=Theme.font_bold(13), text_color=Theme.TEXT_MUTED).pack()
        
        bio_frame = ctk.CTkFrame(top, fg_color=Theme.BG_TERTIARY, corner_radius=10)
        bio_frame.pack(fill="x", padx=40, pady=20)
        ctk.CTkLabel(bio_frame, text=fix_rtl(prof.get("bio", "Available")), font=Theme.font_main(), text_color=Theme.TEXT_MAIN, wraplength=280).pack(padx=20, pady=20)

    def ui_handle_room_purged(self, data):
        if self.current_room and self.current_room["id"] == data["room_id"]:
            self.current_room = None
            self.room_title.configure(text="Select a Room")
            self.room_status_lbl.configure(text="")
            self.msg_entry.configure(state="disabled")
            self.header_avatar_lbl.configure(image=None)
            for widget in self.msg_scroll.winfo_children(): widget.destroy()
            for widget in self.members_scroll.winfo_children(): widget.destroy()
            self.room_settings_btn.pack_forget()
        self.controller.net.send({"action": "FETCH_ROOMS"})

    def logout(self):
        self.current_room = None
        self.controller.net.disconnect()
        self.controller.user_data = None
        for widget in self.msg_scroll.winfo_children(): widget.destroy()
        for widget in self.rooms_scroll.winfo_children(): widget.destroy()
        for widget in self.members_scroll.winfo_children(): widget.destroy()
        self.controller.show_frame("LoginFrame")