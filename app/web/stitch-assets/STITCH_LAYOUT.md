# Stitch Dashboard Layout Reference

Screen: FrameSense Dashboard  
Project: 961443659593553430  
Screen ID: 3d90b06dd31c486bab31dea1b223c716

## Grid

- **Main**: `grid grid-cols-12 gap-6`, max-w-7xl, mx-auto, pt-32 pb-12 px-6
- **Row 1**: Video Player (col-span-12 lg:col-span-8) | Detected Objects (col-span-12 lg:col-span-4)
- **Row 2**: Upload (col-span-12 md:col-span-6 lg:col-span-3) | Prompt (col-span-12 md:col-span-6 lg:col-span-6) | Status (col-span-12 lg:col-span-3)
- **Row 3**: Stats — 3 equal cards in grid-cols-1 md:grid-cols-3

## Design Tokens (from Stitch)

- **Primary**: #76a838 (yellow-green 500)
- **Background dark**: #0f1510
- **Font**: Be Vietnam Pro (display)
- **Glass**: `.liquid-glass` — rgba(118,168,56,0.03), blur(12px), border rgba(118,168,56,0.1)
- **Glass card**: `.glass-card` — rgba(255,255,255,0.02), blur(20px), border rgba(255,255,255,0.05)
- **Border radius**: 2xl = 1rem for panels; rounded-full for nav, buttons, progress

## Nav

- Fixed top-6, centered, w-[90%] max-w-6xl, z-50
- Liquid glass, rounded-full, px-6 py-3
- Left: logo (primary bg) + "FrameSense" (text-xl font-bold)
- Center: Dashboard (active, border-b-2 border-primary), Projects, Documentation, API
- Right: notifications icon, profile circle (primary/20 border)

## Panel Structure

1. **Video Player**: glass-card rounded-2xl p-4; aspect-video container; overlay for boxes; bottom gradient controls (progress bar, play/pause/seek, time, cc/settings/fullscreen)
2. **Detected Objects**: glass-card rounded-2xl p-6; title + "Live Stream" badge; list of items (icon, label, frame range, confidence %)
3. **Upload**: glass-card rounded-2xl p-6; icon, "Upload Video", "MP4, MOV up to 2GB"; filename + progress bar
4. **Prompt**: glass-card rounded-2xl p-6; icon + "Detection Prompt"; input placeholder; green "Run Analysis" button
5. **Status**: glass-card rounded-2xl p-6; "Status"; pulse dot + "Processing..."; large %; "STEP 4/5"; progress bar with shimmer
6. **Stats**: 3x glass-card rounded-2xl p-6; icon + label (uppercase) + value (text-2xl font-black)

## Assets

- screen.html — full Stitch HTML (Tailwind CDN, Be Vietnam Pro from Google Fonts)
- screenshot.png — design reference (512x410)
