# Premium Modern Deep Dark Theme Palette (Discord / Notion aesthetic)
class Theme:
    BG_MAIN = "#0E1116"        # Deepest dark for background app frame
    BG_SIDEBAR = "#171B21"     # Sidebar panels
    BG_TERTIARY = "#22272E"    # Input fields, borders, hover states
    BG_POPUP = "#1C2128"       # Dialogs and settings modals
    
    BUBBLE_ME = "#5865F2"      # Premium Discord-style blue for sender
    BUBBLE_OTHER = "#2D333B"   # Deep charcoal for recipient messages
    
    TEXT_MAIN = "#F0F6FC"      # Crisp readable text
    TEXT_MUTED = "#8B949E"     # Metadata, timestamps, placeholders
    
    ACCENT = "#5865F2"         # Primary interaction color
    ACCENT_HOVER = "#4752C4"   
    ERROR = "#F85149"
    SUCCESS = "#2EA043"
    
    STATUS_DELIVERED = "#8B949E" # Single gray tick
    STATUS_READ = "#3FB950"      # Double green tick

    @staticmethod
    def font_main(size=14): return ("Vazirmatn", size)
    @staticmethod
    def font_bold(size=14): return ("Vazirmatn", size, "bold")
    @staticmethod
    def font_title(size=22): return ("Vazirmatn", size, "bold")
    @staticmethod
    def font_small(size=11): return ("Vazirmatn", size)