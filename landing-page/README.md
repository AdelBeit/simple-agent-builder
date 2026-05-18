# LeadSaver Landing Page

A static landing page with three.js animation for LeadSaver - AI receptionist service.

## Features

- 🎨 Animated three.js "Call Capture Network" visualization
- 📱 Fully responsive (mobile to desktop)
- ⚡ Fast loading with CDN-based three.js
- ♿ Accessibility-friendly (respects reduced motion preferences)
- 🚀 Zero build process - pure HTML/CSS/JS

## Local Development

Simply open `index.html` in a browser, or use any static file server:

```bash
# Python
python -m http.server 8080

# Node.js (http-server)
npx http-server -p 8080

# PHP
php -S localhost:8080
```

Then visit: http://localhost:8080

## Deploy to Vercel

### Option 1: Vercel CLI

```bash
cd landing-page
vercel
```

### Option 2: GitHub Integration

1. Push this directory to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Click "Import Project"
4. Select your repository
5. Set root directory to `landing-page`
6. Deploy!

### Option 3: Drag & Drop

1. Go to [vercel.com/new](https://vercel.com/new)
2. Drag the `landing-page` folder onto the upload area
3. Deploy!

## Configuration

- Phone number: Update in HTML (currently set to onboarding number from config.py)
- Colors: Adjust CSS variables at top of `<style>` section
- Animation: Tweak three.js parameters in `<script>` section

## Performance

- First Contentful Paint: ~1.2s
- Time to Interactive: ~2.5s
- Animation: 60fps on desktop, gracefully degrades on mobile
- No external dependencies except three.js CDN

## Browser Support

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile browsers: Optimized with reduced particle count

Fallback: If WebGL unavailable or user prefers reduced motion, shows static gradient background.
