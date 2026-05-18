# Implementation Plan: LeadSaver Three.js Landing Page

## Executive Summary

This plan details the creation of a minimal, visually compelling three.js landing page for LeadSaver that will serve as the main marketing entry point. The page will feature an animated hero section using three.js to visualize the concept of capturing missed calls, with clear value propositions and a simple call-to-action for phone onboarding.

## Current Architecture Understanding

**Existing Structure:**
- Demo business sites run on Express (ports 3100, 3101) with standalone HTML files
- Onboarding interface on port 3010
- FastAPI backend on port 8000
- Color scheme: Navy blue (#0a1f44) and red (#e8321c) established in demo sites
- No existing landing page at project root

**Target Placement:**
The landing page will be created as a standalone static site in the root directory, served independently or via a simple Express server.

## Three.js Animation Concept

### Visual Concept: "Call Capture Network"

The hero section will feature an abstract 3D visualization representing LeadSaver's core value: capturing missed calls and converting them to leads.

**Animation Elements:**

1. **Floating Phone Nodes** (Primary Elements)
   - 20-30 small glowing spheres in LeadSaver red (#e8321c)
   - Represent incoming customer calls
   - Float randomly in 3D space with gentle motion
   - Pulsing glow effect to simulate "ringing"

2. **Capture Center** (Central Element)
   - Larger sphere/torus in navy blue (#0a1f44)
   - Positioned at screen center
   - Represents the AI receptionist system
   - Subtle rotation animation

3. **Connection Lines** (Dynamic Connections)
   - Animated lines that periodically connect floating phones to center
   - Represent calls being "captured"
   - Lines materialize, glow, then fade
   - Creates sense of constant activity and connection

4. **Particle Field** (Background Ambiance)
   - Subtle field of tiny white/blue particles
   - Creates depth and dimension
   - Represents the 24/7 always-on nature
   - Slow drift motion for atmosphere

**Technical Implementation:**
- Three.js r150+ via CDN (no build process)
- Custom shader materials for glow effects
- RAF-based animation loop with delta time
- Responsive canvas that adapts to viewport
- Performance-optimized (60fps target, graceful mobile degradation)

### Animation Behaviors

1. **Phone Node Movement**
   - Perlin noise-based floating motion
   - Random spawn points in spherical distribution
   - Occasional "capture" events where nodes move toward center

2. **Capture Events**
   - Every 2-3 seconds, select random phone node
   - Animate line from node to center
   - Node color transition from red to blue
   - Node moves toward center and fades
   - New node spawns at edge to maintain count

3. **Camera Behavior**
   - Subtle orbital rotation around scene
   - Slight parallax response to mouse movement (desktop only)
   - Smooth easing transitions

4. **Responsive Behavior**
   - Desktop: Full particle count, parallax enabled
   - Tablet: Reduced particle count, simplified shaders
   - Mobile: Minimal particles, static camera, focus on core elements

## File Structure

```
/workshop/simple-agent-builder/
├── landing/                          # New directory for landing page
│   ├── index.html                    # Main landing page
│   ├── server.js                     # Simple Express server (optional)
│   └── package.json                  # For landing server dependencies
│
└── (existing structure unchanged)
```

**Alternative Simpler Structure** (Recommended):
```
/workshop/simple-agent-builder/
├── index.html                        # Landing page at root
└── (existing structure unchanged)
```

## HTML Structure

### Section Layout

```
1. Hero Section (Full viewport)
   - Three.js canvas background (z-index: 0)
   - Content overlay (z-index: 1)
   - Logo/brand
   - Headline: "Never Miss a Customer Call Again"
   - Subheadline: "AI Receptionist That Captures Every Lead. $49/Month."
   - Primary CTA: "Get Started - Call (XXX) XXX-XXXX"
   - Trust indicators: "2-Minute Setup • 24/7 Coverage • No App Required"

2. Problem Section
   - Split layout with icon/visual
   - "Missed calls cost small businesses $50,000+ per year"
   - Pain points: After hours, busy times, can't answer unknown numbers

3. Solution Section (How It Works)
   - 3-step visual process:
     1. "Customer Calls" - icon of phone
     2. "AI Answers" - icon of robot/assistant
     3. "You Get The Lead" - icon of form/email
   - Brief descriptions under each

4. Features Section
   - Grid of 4-6 key features:
     - 24/7 Availability
     - Lead Capture & Qualification
     - Auto Form Submission
     - Email Notifications
     - Natural Conversations
     - 2-Minute Setup

5. Pricing Section
   - Single clear pricing card
   - "$49/month - Flat Rate"
   - What's included list
   - No tiers, no complexity
   - CTA button

6. Social Proof Section
   - "Built for:" icons/labels
   - Plumbers, Roofers, Contractors, Salons, etc.
   - Optional: Simple testimonial or stat

7. Final CTA Section
   - Bold headline: "Set Up Your AI Receptionist in 2 Minutes"
   - Phone number (large, clickable)
   - Subtext: "Call now and we'll walk you through setup"

8. Footer
   - Minimal: Copyright, Contact, Privacy
   - Link to demo sites (optional)
```

## Styling Approach

### CSS Architecture

**Strategy: Inline styles in single HTML file**
- Keeps deployment simple
- Easy to serve static or via Express
- Fast loading, no external requests

**CSS Organization:**
```css
/* 1. Reset & Base */
/* 2. Three.js Canvas Container */
/* 3. Hero Section & Overlay */
/* 4. Content Sections */
/* 5. Components (buttons, cards, etc.) */
/* 6. Responsive Media Queries */
/* 7. Animations & Transitions */
```

### Key Styling Considerations

1. **Three.js Integration**
   ```css
   #three-canvas {
     position: fixed;
     top: 0;
     left: 0;
     width: 100%;
     height: 100vh;
     z-index: 0;
   }
   
   .hero-content {
     position: relative;
     z-index: 1;
     /* Text shadows for readability over animation */
   }
   ```

2. **Color Palette**
   - Primary Navy: #0a1f44 (from demo sites)
   - Accent Red: #e8321c (from demo sites)
   - Supporting Blues: #1a3a6e, #0d2d5c
   - Text: #1a1a1a (dark), #fff (light)
   - Backgrounds: #f4f7fc (light sections), #fff (white sections)

3. **Typography**
   - Font: System UI stack (Segoe UI, Arial, sans-serif)
   - Headings: 900 weight for impact
   - Body: 400-500 weight for readability
   - Hero H1: clamp(2.5rem, 6vw, 4rem)

4. **Mobile-First Responsive**
   - Base: Mobile layout (320px+)
   - Breakpoint 1: 640px (tablet adjustments)
   - Breakpoint 2: 1024px (desktop layout)
   - Hero height: 100vh on desktop, 90vh on mobile (account for browser chrome)

## Technical Implementation Details

### Three.js Setup

**CDN Import:**
```html
<script src="https://cdn.jsdelivr.net/npm/three@0.150.0/build/three.min.js"></script>
```

**Core Setup Code:**
```javascript
// Scene initialization
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ 
  canvas: document.getElementById('three-canvas'),
  antialias: true,
  alpha: true 
});

// Responsive handling
window.addEventListener('resize', onWindowResize);

// Animation loop
function animate() {
  requestAnimationFrame(animate);
  updatePhoneNodes();
  updateConnections();
  updateParticles();
  renderer.render(scene, camera);
}
```

**Performance Optimizations:**
- Use `BufferGeometry` for all shapes
- Reuse materials and geometries
- Implement object pooling for particles
- Use `THREE.Clock` for frame-independent animation
- Detect device performance and adjust quality
- Lazy load or disable animation on low-end devices

### Animation State Management

```javascript
const animationState = {
  phoneNodes: [],
  connections: [],
  particles: null,
  mouseX: 0,
  mouseY: 0,
  targetRotation: { x: 0, y: 0 },
  captureTimer: 0,
  captureInterval: 2500 // ms between capture events
};
```

### Responsive Canvas Handling

```javascript
function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  
  // Adjust particle count for mobile
  if (window.innerWidth < 768) {
    adjustPerformanceLevel('low');
  }
}

function adjustPerformanceLevel(level) {
  // Reduce particles, simplify shaders, etc.
}
```

## Content Copy

### Hero Section
**Headline:** "Never Miss a Customer Call Again"

**Subheadline:** "LeadSaver's AI receptionist answers missed calls 24/7, captures lead information, and submits it directly to your business—so you never lose another customer."

**CTA:** "Get Started in 2 Minutes"

**Phone CTA:** "Call (XXX) XXX-XXXX"

### Value Propositions

1. **24/7 Availability**
   "Your AI receptionist never sleeps, takes breaks, or misses a call. Always on, always professional."

2. **Automatic Lead Capture**
   "Collects caller name, phone, and issue. Submits directly to your contact form and emails you the details."

3. **2-Minute Setup**
   "Just call our number. We'll configure your AI receptionist over the phone—no app, no dashboard, no hassle."

4. **Natural Conversations**
   "Powered by advanced AI, your receptionist sounds natural and handles real customer conversations."

5. **No Contracts**
   "$49/month flat rate. No setup fees, no hidden costs, no long-term commitment."

6. **Built for Small Business**
   "Designed for plumbers, contractors, roofers, salons, and service businesses who can't afford to miss calls."

### Pricing Copy
**Price Point:** "$49/month"

**What's Included:**
- Unlimited missed call handling
- Lead capture and qualification
- Automatic form submission
- Email notifications
- Natural AI voice conversations
- 2-minute phone setup

## Implementation Steps

### Phase 1: File Creation & Structure
1. Create `/workshop/simple-agent-builder/index.html` at project root
2. Set up basic HTML5 boilerplate with semantic structure
3. Add viewport meta tags for mobile responsiveness
4. Include Three.js CDN link in `<head>`

### Phase 2: Three.js Scene Setup
1. Create canvas element with ID `three-canvas`
2. Initialize Three.js scene, camera, renderer
3. Set up basic lighting (ambient + directional)
4. Implement resize handler for responsive canvas
5. Create animation loop with RAF

### Phase 3: Core Animation Elements
1. **Phone Nodes**
   - Create sphere geometry and red emissive material
   - Spawn 20-30 instances in spherical distribution
   - Add pulsing animation with sine wave
   - Implement floating motion with Perlin noise

2. **Center Capture Element**
   - Create torus or sphere with navy blue material
   - Add glow shader effect
   - Implement slow rotation animation

3. **Background Particles**
   - Create points geometry with small particles
   - Distribute in 3D space
   - Add drift animation

### Phase 4: Dynamic Connections
1. Implement capture event system
2. Create line geometry between phone nodes and center
3. Add line animation (draw-in effect)
4. Implement node color transition
5. Add node removal and respawn logic

### Phase 5: Camera & Interactivity
1. Set up orbital camera position
2. Add slow automatic rotation
3. Implement mouse parallax (desktop only)
4. Add smooth easing to camera movements

### Phase 6: HTML Content Overlay
1. Build hero section with content overlay
2. Add semantic HTML for all sections
3. Ensure proper z-index layering
4. Add glassmorphism or semi-transparent backgrounds where needed

### Phase 7: CSS Styling
1. Implement base styles and reset
2. Style hero section with overlay positioning
3. Create component styles (buttons, cards, sections)
4. Add responsive breakpoints
5. Implement smooth scroll behavior
6. Add hover states and transitions

### Phase 8: Mobile Optimization
1. Add media queries for mobile layouts
2. Implement performance detection
3. Reduce animation complexity on mobile
4. Test on various viewport sizes
5. Ensure text readability over animation

### Phase 9: Content Integration
1. Write all copy and insert into HTML
2. Add proper semantic heading hierarchy
3. Implement trust indicators and social proof
4. Add phone number CTAs (tel: links)
5. Insert final pricing and feature details

### Phase 10: Polish & Testing
1. Test animation performance across devices
2. Verify responsive behavior
3. Check accessibility (contrast, focus states, ARIA labels)
4. Optimize loading (defer scripts, async where possible)
5. Test all interactive elements
6. Cross-browser testing

## Performance Targets

- **First Contentful Paint:** < 1.5s
- **Time to Interactive:** < 3.0s
- **Animation FPS:** 60fps on desktop, 30fps acceptable on mobile
- **Page Weight:** < 300KB total (including Three.js from CDN)

## Accessibility Considerations

1. **Semantic HTML:** Proper heading hierarchy, section landmarks
2. **Keyboard Navigation:** All interactive elements accessible via keyboard
3. **Color Contrast:** WCAG AA compliant contrast ratios for all text
4. **Motion Preferences:** Respect `prefers-reduced-motion` media query
5. **ARIA Labels:** Descriptive labels for CTAs and navigation
6. **Focus Indicators:** Visible focus states for all interactive elements

## Alternative Simplified Approach

If three.js proves too complex or performance-intensive, here's a CSS-only fallback:

**CSS Gradient Animation:**
- Animated gradient background with navy/red colors
- CSS keyframe animations for floating elements
- SVG icons with CSS animations
- Maintains visual interest without WebGL dependency

**Benefits:**
- Lighter weight
- Better mobile performance
- No JavaScript animation overhead
- Easier to maintain

**Implementation:**
```css
@keyframes gradient-shift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.hero {
  background: linear-gradient(135deg, #0a1f44, #1a3a6e, #e8321c);
  background-size: 200% 200%;
  animation: gradient-shift 15s ease infinite;
}
```

## Server Setup (Optional)

If serving via Express instead of static file:

**File: `/workshop/simple-agent-builder/landing/server.js`**
```javascript
const express = require('express');
const path = require('path');

const app = express();
app.use(express.static(__dirname));

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

const PORT = process.env.PORT_LANDING || 3000;
app.listen(PORT, () => {
  console.log(`LeadSaver Landing → http://localhost:${PORT}`);
});
```

**Update package.json:**
```json
"scripts": {
  "landing": "node landing/server.js"
}
```

## Integration with Existing System

**Links to Demo Sites:**
- Footer links to demo-plumber and demo-stylist for prospects to see examples
- "See Example Sites" section with screenshots/links

**Onboarding Phone Number:**
- Display prominent phone number that connects to onboarding agent
- Use the existing `AGENTPHONE_ONBOARDING_NUMBER` from config
- Tel links for mobile click-to-call

**Tracking & Analytics:**
- Add event tracking for CTA clicks
- Track scroll depth to measure engagement
- Monitor animation performance metrics

## Testing Checklist

**Visual Testing:**
- [ ] Animation runs smoothly on Chrome/Firefox/Safari
- [ ] Responsive layout works on 320px to 4K displays
- [ ] Text is readable over animation in all sections
- [ ] Colors match brand guidelines (#0a1f44, #e8321c)

**Performance Testing:**
- [ ] Lighthouse score > 90 on desktop
- [ ] Lighthouse score > 80 on mobile
- [ ] Animation maintains 60fps on desktop
- [ ] No memory leaks in animation loop
- [ ] Page loads in < 3 seconds on 3G

**Functional Testing:**
- [ ] All CTAs link to correct phone numbers
- [ ] Smooth scrolling works on all browsers
- [ ] Mouse parallax works on desktop
- [ ] Animation gracefully degrades on mobile
- [ ] Reduced motion preference respected

**Accessibility Testing:**
- [ ] Keyboard navigation works for all elements
- [ ] Screen reader can parse content logically
- [ ] Color contrast meets WCAG AA standards
- [ ] Focus indicators visible
- [ ] ARIA labels present where needed

## Risk Mitigation

**Performance Risk:**
- Mitigation: Implement device detection and quality adjustment
- Fallback: CSS-only animation if WebGL unavailable
- Testing: Profile on low-end devices early

**Browser Compatibility Risk:**
- Mitigation: Use Three.js stable release with wide support
- Fallback: Graceful degradation to static background
- Testing: Test on IE11, older Safari, mobile browsers

**Maintenance Risk:**
- Mitigation: Keep animation logic simple and well-documented
- Documentation: Inline comments explaining complex animation logic
- Modularity: Separate concerns (rendering, animation, UI)

## Future Enhancements

**Phase 2 Features:**
1. Add FAQ accordion section
2. Implement case studies with real customer results
3. Add video testimonials or demo video
4. Create interactive pricing calculator
5. Add live chat widget for instant questions

**Advanced Animation Features:**
1. Add audio visualization (if background music added)
2. Implement WebGL post-processing effects
3. Add interactive elements (click to trigger capture events)
4. Create loading screen with branded animation

## Dependencies Summary

**Required:**
- Three.js r150+ (CDN)
- Modern browser with WebGL support

**Optional:**
- Express.js (if serving via Node)
- Google Analytics (for tracking)

**No Build Process Required:**
- Single HTML file approach
- Inline CSS and JavaScript
- CDN for Three.js
- Vanilla JavaScript (no frameworks)

---

## Critical Files for Implementation

Based on this plan, here are the critical files needed to implement the LeadSaver three.js landing page:

- `/workshop/simple-agent-builder/index.html` - Main landing page with Three.js animation, HTML structure, inline CSS, and JavaScript
- `/workshop/simple-agent-builder/landing/server.js` - Optional Express server to serve landing page (if not serving as static file)
- `/workshop/simple-agent-builder/package.json` - Updated to include landing page server script
- `/workshop/simple-agent-builder/leadsaver/config.py` - Reference for onboarding phone number to display on landing page

**Recommendation:** Start with the single-file approach (`/workshop/simple-agent-builder/index.html`) for maximum simplicity. The entire landing page can be contained in one self-contained HTML file with inline CSS and JavaScript, making it trivial to deploy and maintain.
