import streamlit as st
import streamlit.components.v1 as components

_CSS = """
    @import url('https://fonts.googleapis.com/css2?family=Tiro+Bangla:ital@0;1&family=Hind+Siliguri:wght@400;500;600;700&display=swap');

    :root {
        --paddy-deep: #1F3D1A;
        --paddy-green: #2D5A27;
        --paddy-green-light: #4A7A42;
        --wheat-gold: #C4941F;
        --wheat-gold-light: #E0B84D;
        --terracotta: #A85434;
        --soil-brown: #4A2E1A;
        --rice-cream: #FAF4E6;
        --card-cream: #F2E9D6;
        --text-dark: #2B2118;
        --text-muted: #6B6357;
    }

    @keyframes kk-fade-up {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes kk-sway {
        0%, 100% { transform: translateY(0) rotate(-3deg); }
        50% { transform: translateY(-6px) rotate(3deg); }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; }
    }

    /* Alpana-inspired dot/floral texture, used sparingly as a signature motif */
    .kk-alpana-texture {
        background-image:
            radial-gradient(circle, rgba(196,148,31,0.35) 1.4px, transparent 1.6px),
            radial-gradient(circle, rgba(196,148,31,0.22) 1px, transparent 1.2px);
        background-size: 26px 26px, 14px 14px;
        background-position: 0 0, 13px 13px;
    }

    /* Base app background */
    .stApp {
        background: var(--rice-cream);
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Widen the centered layout so content doesn't look stranded on larger screens */
    .main .block-container,
    [data-testid="stAppViewContainer"] .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {
        width: 1000px !important;
        max-width: 1000px !important;
        padding-top: 2.2rem !important;
        padding-bottom: 3rem !important;
    }

    @media (max-width: 1050px) {
        .main .block-container,
        [data-testid="stAppViewContainer"] .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"] {
            width: 92% !important;
        }
    }

    html, body, [class*="css"] {
        font-family: 'Hind Siliguri', sans-serif;
        color: var(--text-dark);
    }

    h1, h2, h3 {
        font-family: 'Tiro Bangla', 'Hind Siliguri', serif;
        color: var(--paddy-deep);
        font-weight: 400;
        letter-spacing: 0.01em;
    }

    /* Focus visibility for accessibility */
    a:focus-visible, button:focus-visible, [tabindex]:focus-visible {
        outline: 3px solid var(--wheat-gold);
        outline-offset: 2px;
    }

    /* Custom header banner — terraced edge instead of a plain rounded box */
    .kk-header {
        background: linear-gradient(155deg, var(--paddy-deep) 0%, var(--paddy-green) 100%);
        padding: 2.4rem 2rem 3rem 2rem;
        border-radius: 18px;
        margin-bottom: 2.2rem;
        box-shadow: 0 10px 26px rgba(31, 61, 26, 0.28);
        position: relative;
        overflow: hidden;
        animation: kk-fade-up 0.5s ease-out;
        clip-path: polygon(
            0% 0%, 100% 0%, 100% 88%,
            92% 100%, 84% 88%, 76% 100%, 68% 88%, 60% 100%,
            52% 88%, 44% 100%, 36% 88%, 28% 100%, 20% 88%,
            12% 100%, 4% 88%, 0% 100%
        );
    }

    .kk-header::before {
        content: "";
        position: absolute;
        inset: 0;
        background-image:
            radial-gradient(circle, rgba(255,255,255,0.10) 1.4px, transparent 1.6px);
        background-size: 24px 24px;
        opacity: 0.6;
        pointer-events: none;
    }

    .kk-header h1 {
        color: white !important;
        font-size: 2.15rem;
        margin: 0;
        position: relative;
        z-index: 1;
    }

    .kk-header p {
        color: rgba(255,255,255,0.88);
        font-family: 'Hind Siliguri', sans-serif;
        font-size: 1.05rem;
        margin-top: 0.55rem;
        margin-bottom: 0.4rem;
        position: relative;
        z-index: 1;
    }

    /* Card containers */
    .kk-card {
        background: var(--card-cream);
        border-radius: 14px;
        padding: 1.6rem;
        margin-bottom: 1.2rem;
        border: 1px solid rgba(74, 46, 26, 0.14);
        border-left: 3px solid var(--wheat-gold);
        transition: box-shadow 0.25s ease, transform 0.25s ease, border-left-color 0.25s ease;
        animation: kk-fade-up 0.5s ease-out;
    }

    .kk-card:hover {
        box-shadow: 0 6px 18px rgba(74, 46, 26, 0.12);
        transform: translateY(-2px);
        border-left-color: var(--terracotta);
    }

    .kk-card h3 {
        margin-top: 0;
        font-size: 1.18rem;
    }

    /* Step badges for manual page */
    .kk-step {
        display: flex;
        align-items: flex-start;
        gap: 1rem;
        margin-bottom: 1.3rem;
        background: var(--card-cream);
        padding: 1.1rem 1.3rem;
        border-radius: 12px;
        border: 1px solid rgba(74, 46, 26, 0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .kk-step:hover {
        transform: translateX(4px);
        border-color: rgba(196, 148, 31, 0.5);
    }

    .kk-step-number {
        background: var(--paddy-deep);
        color: var(--wheat-gold-light);
        font-family: 'Tiro Bangla', serif;
        font-weight: 400;
        min-width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        flex-shrink: 0;
        box-shadow: 0 3px 8px rgba(31, 61, 26, 0.35);
    }

    .kk-step-content {
        padding-top: 0.3rem;
    }

    .kk-step-content strong {
        color: var(--paddy-deep);
        display: block;
        margin-bottom: 0.3rem;
        font-size: 1.08rem;
    }

    /* Divider — paddy-grain rule instead of a plain gradient line */
    .kk-divider {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin: 2.1rem 0 1.4rem 0;
        color: var(--paddy-deep);
        font-weight: 600;
        font-size: 0.95rem;
    }

    .kk-divider::before, .kk-divider::after {
        content: "";
        flex: 1;
        height: 2px;
        background-image: radial-gradient(circle, var(--wheat-gold) 1px, transparent 1.4px);
        background-size: 8px 2px;
        background-repeat: repeat-x;
        opacity: 0.7;
    }

    /* Answer box styling */
    .kk-answer-box {
        background: white;
        border-left: 4px solid var(--terracotta);
        border-radius: 8px;
        padding: 1.3rem 1.5rem;
        margin-top: 1rem;
        box-shadow: 0 4px 14px rgba(0,0,0,0.05);
        animation: kk-fade-up 0.4s ease-out;
    }

    .kk-answer-label {
        color: var(--paddy-deep);
        font-weight: 700;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.5rem;
    }

    /* Landing page hero — the one place motion and the alpana motif get to be bold */
    .kk-hero {
        text-align: center;
        padding: 2.6rem 2.5rem 3.3rem 2.5rem;
        background: linear-gradient(155deg, var(--paddy-deep) 0%, var(--paddy-green) 100%);
        box-shadow: 0 12px 30px rgba(31, 61, 26, 0.28);
        margin-bottom: 0.5rem;
        position: relative;
        overflow: hidden;
        animation: kk-fade-up 0.6s ease-out;
        clip-path: polygon(
            0% 0%, 100% 0%, 100% 92%,
            95% 100%, 90% 92%, 85% 100%, 80% 92%, 75% 100%,
            70% 92%, 65% 100%, 60% 92%, 55% 100%, 50% 92%,
            45% 100%, 40% 92%, 35% 100%, 30% 92%, 25% 100%,
            20% 92%, 15% 100%, 10% 92%, 5% 100%, 0% 92%
        );
    }

    .kk-hero::before {
        content: "";
        position: absolute;
        inset: 0;
        background-image:
            radial-gradient(circle, rgba(255,255,255,0.14) 1.6px, transparent 1.8px),
            radial-gradient(circle, rgba(255,255,255,0.10) 1.2px, transparent 1.4px);
        background-size: 30px 30px, 16px 16px;
        background-position: 0 0, 15px 15px;
        pointer-events: none;
    }

    /* Depth blobs so the wide card doesn't read empty and flat at the sides */
    .kk-hero::after {
        content: "";
        position: absolute;
        inset: 0;
        background-image:
            radial-gradient(ellipse 420px 300px at 6% 10%, rgba(196, 148, 31, 0.28), transparent 70%),
            radial-gradient(ellipse 440px 320px at 95% 90%, rgba(168, 84, 52, 0.22), transparent 70%),
            radial-gradient(ellipse 300px 260px at 50% 100%, rgba(255, 255, 255, 0.08), transparent 75%);
        pointer-events: none;
    }

    .kk-hero-icon {
        font-size: 2.3rem;
        width: 62px;
        height: 62px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 0.4rem auto;
        position: relative;
        z-index: 1;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.22) 0%, rgba(255,255,255,0) 72%);
        animation: kk-sway 4s ease-in-out infinite;
        transform-origin: bottom center;
    }

    .kk-hero-title {
        font-family: 'Tiro Bangla', serif;
        font-size: 2.2rem;
        font-weight: 600;
        background: linear-gradient(135deg, #FFFFFF, var(--wheat-gold-light) 120%) !important;
        -webkit-background-clip: text !important;
        background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        color: transparent !important;
        margin: 0;
        letter-spacing: 0.015em;
        position: relative;
        z-index: 1;
    }

    /* Hide Streamlit's auto anchor-link icon on custom-styled headings (h1/h2/h3
       inside kk-header and kk-hero get wrapped with a hover "link" icon by default) */
    .kk-header [data-testid="stHeaderActionElements"],
    .kk-hero [data-testid="stHeaderActionElements"],
    .kk-card [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    /* Small gold rule marking the transition from title to subtitle */
    .kk-hero-subtitle::before {
        content: "";
        display: block;
        width: 40px;
        height: 3px;
        background: var(--wheat-gold-light);
        border-radius: 2px;
        margin: 0.6rem auto 0.5rem auto;
    }

    .kk-hero-subtitle {
        font-family: 'Hind Siliguri', sans-serif;
        font-size: 1.15rem;
        color: var(--wheat-gold-light);
        font-weight: 600;
        margin: 0.2rem 0 0.5rem 0;
        position: relative;
        z-index: 1;
    }

    .kk-hero-tagline {
        font-size: 1.02rem;
        color: rgba(255, 255, 255, 0.85);
        max-width: 440px;
        margin: 0 auto;
        line-height: 1.7;
        position: relative;
        z-index: 1;
    }

    /* Feature cards on landing page */
    .kk-feature-card {
        background: white;
        border-radius: 14px;
        padding: 1.6rem 1.1rem;
        text-align: center;
        height: 100%;
        border: 1px solid rgba(74, 46, 26, 0.1);
        border-top: 3px solid var(--wheat-gold);
        transition: transform 0.25s ease, box-shadow 0.25s ease, border-top-color 0.25s ease;
        animation: kk-fade-up 0.6s ease-out;
    }

    .kk-feature-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 22px rgba(74, 46, 26, 0.12);
        border-top-color: var(--terracotta);
    }

    .kk-feature-icon {
        font-size: 1.9rem;
        margin-bottom: 0.6rem;
    }

    .kk-feature-card strong {
        display: block;
        color: var(--paddy-deep);
        font-size: 1.02rem;
        margin-bottom: 0.45rem;
    }

    .kk-feature-card p {
        font-size: 0.88rem;
        color: var(--text-muted);
        margin: 0;
        line-height: 1.55;
    }

    /* CTA button wrapper on landing page */
    .kk-cta-wrap .stButton button {
        background: linear-gradient(135deg, var(--paddy-deep), var(--paddy-green));
        font-size: 1.1rem;
        padding: 0.9rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 8px 20px rgba(31, 61, 26, 0.32);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .kk-cta-wrap .stButton button:hover {
        transform: translateY(-2px) scale(1.01);
        box-shadow: 0 12px 26px rgba(31, 61, 26, 0.4);
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: var(--card-cream);
        border-right: 1px solid rgba(74, 46, 26, 0.12);
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 1.2rem;
    }

    [data-testid="stSidebarNavSeparator"] {
        display: none;
    }

    /* App/wordmark header — placed before the Home link specifically, identified
       by its href being the site root (ends in "/"), since :first-of-type doesn't
       work here (each nav link sits in its own separate wrapper, not shared siblings) */
    [data-testid="stSidebarNavLinkContainer"]:has(a[href$="/"])::before {
        content: "🌾  KrishiKotha";
        display: block;
        font-family: 'Tiro Bangla', serif;
        font-weight: 600;
        letter-spacing: 0.015em;
        background: linear-gradient(135deg, var(--paddy-deep), var(--paddy-green-light));
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        font-size: 1.3rem;
        padding: 0.5rem 0.9rem 0.9rem 0.9rem;
        border-bottom: 2px solid var(--wheat-gold);
        margin: 0 0 0.6rem 0;
    }

    [data-testid="stSidebarNavLinkContainer"] {
        margin-bottom: 0.3rem;
        padding: 0 0.6rem;
    }

    [data-testid="stSidebarNavLink"] {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.65rem 0.9rem;
        border-radius: 10px;
        border-left: 3px solid transparent;
        transition: background-color 0.18s ease, border-left-color 0.18s ease;
    }

    [data-testid="stSidebarNavLink"]:hover {
        background-color: rgba(196, 148, 31, 0.14);
        border-left-color: var(--wheat-gold);
    }

    [data-testid="stSidebarNavLink"] span,
    [data-testid="stSidebarNavLink"] p {
        color: var(--soil-brown) !important;
        font-weight: 600;
        font-size: 0.98rem;
    }

    [data-testid="stSidebarNavLink"][aria-current="page"] {
        background-color: var(--paddy-deep);
        border-left-color: var(--terracotta);
        box-shadow: 0 3px 10px rgba(31, 61, 26, 0.25);
    }

    [data-testid="stSidebarNavLink"][aria-current="page"] span,
    [data-testid="stSidebarNavLink"][aria-current="page"] p {
        color: white !important;
    }

    /* Relabel only the true Home link (auto-generated from "app.py"), matched by
       its root href rather than position */
    [data-testid="stSidebarNavLinkContainer"]:has(a[href$="/"]) [data-testid="stMarkdownContainer"] p {
        font-size: 0;
    }

    [data-testid="stSidebarNavLinkContainer"]:has(a[href$="/"]) [data-testid="stMarkdownContainer"] p::before {
        content: "🏠  হোম";
        font-size: 0.98rem;
    }

    /* Sidebar collapse control */
    [data-testid="stSidebarCollapseButton"] button {
        color: var(--paddy-deep);
    }

    /* Button styling override */
    .stButton button {
        background-color: var(--paddy-deep);
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        transition: background-color 0.2s ease, transform 0.15s ease;
    }

    .stButton button:hover {
        background-color: var(--paddy-green);
        transform: translateY(-1px);
    }

    /* Audio input widget container */
    div[data-testid="stAudioInput"] {
        background: white;
        border-radius: 14px;
        padding: 1.1rem;
        border: 2px dashed var(--wheat-gold);
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    div[data-testid="stAudioInput"]:hover {
        border-color: var(--terracotta);
        box-shadow: 0 4px 16px rgba(196, 148, 31, 0.18);
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: var(--card-cream);
        padding: 0.4rem;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        border-radius: 9px;
        color: var(--text-muted);
        font-weight: 600;
        background: transparent;
    }

    .stTabs [aria-selected="true"] {
        background: var(--paddy-deep) !important;
        color: white !important;
    }

    /* Camera input widget container */
    div[data-testid="stCameraInput"] {
        background: white;
        border-radius: 14px;
        padding: 1rem;
        border: 2px dashed var(--wheat-gold);
    }

    /* File uploader widget container */
    div[data-testid="stFileUploader"] {
        background: white;
        border-radius: 14px;
        padding: 0.5rem;
    }

    /* Selectbox / dropdown widget — otherwise picks up Streamlit's default
       secondaryBackgroundColor, which is the same cream as the page background
       and renders as an undefined, borderless floating box */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: white;
        border: 1.5px solid rgba(74, 46, 26, 0.15);
        border-radius: 10px;
        transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }

    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover {
        border-color: var(--wheat-gold);
    }

    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within {
        border-color: var(--wheat-gold);
        box-shadow: 0 0 0 2px rgba(196, 148, 31, 0.25);
    }

    div[data-testid="stSelectbox"] label p {
        color: var(--soil-brown) !important;
        font-weight: 600;
    }

    /* Caption/footer text */
    .kk-footer-note {
        text-align: center;
        color: var(--text-muted);
        font-size: 0.85rem;
        margin-top: 2.5rem;
        padding-top: 1.2rem;
        border-top: 1px solid rgba(74, 46, 26, 0.12);
    }

    /* Mobile tuning */
    @media (max-width: 480px) {
        .kk-hero-title { font-size: 1.9rem; }
        .kk-hero { padding: 2rem 1.1rem 2.6rem 1.1rem; }
        .kk-header { padding: 2rem 1.3rem 2.6rem 1.3rem; }
        .kk-header h1 { font-size: 1.7rem; }
    }
"""


def get_css():
    """Kept for compatibility: returns the CSS wrapped in a <style> tag.
    Prefer inject_css() in page scripts — it survives page navigation
    without a flash of unstyled content; this one gets torn down and
    re-created on every page switch like any other component."""
    return f"<style>{_CSS}</style>"


def inject_css():
    """Injects the CSS once into the real document <head> via a tiny
    zero-height component, instead of into the per-page component tree.
    Streamlit's client-side page navigation never touches <head>, so once
    this runs the first time, it survives every subsequent page switch —
    no re-injection, no flash of unstyled content in between pages."""
    css_escaped = _CSS.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    script = (
        "<script>\n"
        "(function() {\n"
        "    var doc = window.parent.document;\n"
        "    if (!doc.getElementById('kk-global-styles')) {\n"
        "        var style = doc.createElement('style');\n"
        "        style.id = 'kk-global-styles';\n"
        "        style.innerHTML = `" + css_escaped + "`;\n"
        "        doc.head.appendChild(style);\n"
        "    }\n"
        "})();\n"
        "</script>"
    )
    components.html(script, height=0)