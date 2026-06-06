import arabic_reshaper
from bidi.algorithm import get_display
import hashlib
import io
import base64
from PIL import Image, ImageDraw, ImageOps
import customtkinter as ctk

IMAGE_CACHE = {}

def fix_rtl(text):
    """Applies Arabic/Persian reshaping and bidirectional text rendering."""
    if not text: return ""
    return get_display(arabic_reshaper.reshape(str(text)))

def get_color_from_string(s):
    """Generates a consistent hex color for fallback avatars based on a string."""
    colors = ["#F85149", "#D29922", "#2EA043", "#58A6FF", "#BC8BFF", "#EC6CB9", "#FF7B72", "#79C0FF", "#D2A8FF"]
    hash_val = int(hashlib.md5(s.encode()).hexdigest(), 16)
    return colors[hash_val % len(colors)]

def create_circular_image(img, size):
    """Produces high-quality anti-aliased circular avatars."""
    img = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size * 2, size * 2), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size * 2, size * 2), fill=255)
    
    result = Image.new("RGBA", (size * 2, size * 2), (0,0,0,0))
    result.paste(img, (0,0), mask=mask)
    result = result.resize((size, size), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=result, dark_image=result, size=(size, size))

def make_fallback_avatar(name, size=60):
    cache_key = f"fallback_{name}_{size}"
    if cache_key in IMAGE_CACHE: return IMAGE_CACHE[cache_key]
    
    img = Image.new("RGBA", (size*2, size*2), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    color = get_color_from_string(name)
    draw.ellipse([0, 0, size*2, size*2], fill=color)
    char = name[0].upper() if name else "?"
    draw.text((size, size), char, fill="#FFFFFF", anchor="mm", font_size=int(size*0.9))
    
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    res = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    IMAGE_CACHE[cache_key] = res
    return res

def convert_base64_to_image(b64_str, size=60):
    if not b64_str or not b64_str.strip(): return None
    cache_key = f"{hashlib.md5(b64_str.encode()).hexdigest()}_{size}"
    if cache_key in IMAGE_CACHE: return IMAGE_CACHE[cache_key]
    
    try:
        raw_bytes = base64.b64decode(b64_str.encode('utf-8'))
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        img = ImageOps.fit(img, (size*2, size*2), method=Image.Resampling.LANCZOS)
        res = create_circular_image(img, size)
        IMAGE_CACHE[cache_key] = res
        return res
    except:
        return None

def convert_image_to_base64(filepath, max_size=200):
    try:
        img = Image.open(filepath).convert("RGB")
        img = ImageOps.fit(img, (max_size, max_size), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except:
        return ""