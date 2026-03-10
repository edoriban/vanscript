"""Centralized theme constants for VanScript UI."""

# --- Color palette (dark dev-tool + green accent) ---
COLORS = {
    "bg": "#0F172A",  # deep navy background
    "surface": "#1E293B",  # card/panel surface
    "surface_hi": "#334155",  # elevated surface (inputs, hover)
    "border": "#475569",  # subtle borders
    "text": "#F8FAFC",  # primary text
    "text_dim": "#94A3B8",  # secondary/muted text
    "accent": "#22C55E",  # green CTA
    "accent_hover": "#16A34A",  # green hover
}

# --- Font presets ---
FONTS = {
    "mono": ("Consolas", 12),
    "mono_sm": ("Consolas", 10),
    "mono_label": ("Consolas", 11, "bold"),
    "mono_logo": ("Consolas", 24, "bold"),
    "mono_code": ("Consolas", 13),
    "ui": ("Segoe UI", 12),
    "ui_bold": ("Segoe UI", 12, "bold"),
    "ui_title": ("Segoe UI", 22, "bold"),
    "ui_btn": ("Segoe UI", 13, "bold"),
    "ui_sm": ("Segoe UI", 10),
    "ui_sm_bold": ("Segoe UI", 10, "bold"),
}

# Language presets: label -> language codes (for YouTube tab)
LANGUAGE_PRESETS = {
    "Spanish + English": ["es", "en"],
    "English + Spanish": ["en", "es"],
    "English only": ["en"],
    "Spanish only": ["es"],
    "Portuguese + English": ["pt", "en"],
    "French + English": ["fr", "en"],
    "German + English": ["de", "en"],
}

# Whisper language codes: label -> code (for Local Files tab)
WHISPER_LANGUAGES = {
    "Spanish (es)": "es",
    "English (en)": "en",
    "Portuguese (pt)": "pt",
    "French (fr)": "fr",
    "German (de)": "de",
    "Italian (it)": "it",
    "Japanese (ja)": "ja",
    "Chinese (zh)": "zh",
    "Korean (ko)": "ko",
    "Auto-detect": None,
}
