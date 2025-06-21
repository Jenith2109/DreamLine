# Dreamline AI Assistant

A responsive, cross-platform AI chat application optimized for mobile, tablet, and desktop devices.

## Features

### 🚀 **Multi-Device Optimization**
- **Mobile**: Touch-friendly interface with swipe gestures and mobile menu
- **Tablet**: Optimized layout for medium screens
- **Desktop**: Full-featured interface with sidebar navigation
- **PWA**: Install as a native app on mobile devices

### 💬 **AI Chat Capabilities**
- Real-time conversations with OpenAI GPT-3.5
- File upload support (PDF, DOCX, TXT)
- Conversation memory and history
- Google OAuth authentication

### 📱 **Mobile-First Design**
- Responsive design that adapts to any screen size
- Touch-optimized interactions
- Mobile menu with slide-out sidebar
- Swipe gestures for enhanced UX
- Prevents zoom on double-tap

### 🎨 **Modern UI/UX**
- Dark theme with gradient accents
- Smooth animations and transitions
- Accessibility features (high contrast, reduced motion)
- Loading states and visual feedback

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ui
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file with:
   ```
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   SECRET_KEY=your_secret_key
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the app**
   - Open `http://localhost:5000` in your browser
   - On mobile: Scan QR code or enter the local IP address

## Mobile Installation

### iOS (Safari)
1. Open the app in Safari
2. Tap the Share button
3. Select "Add to Home Screen"
4. The app will install as a native iOS app

### Android (Chrome)
1. Open the app in Chrome
2. Tap the menu (three dots)
3. Select "Add to Home screen"
4. The app will install as a native Android app

## Device Optimizations

### 📱 **Mobile (≤768px)**
- Collapsible sidebar with hamburger menu
- Touch-friendly buttons and inputs
- Swipe gestures for navigation
- Optimized text sizes and spacing
- Full-width suggestion cards

### 📱 **Tablet (769px-1024px)**
- Compact sidebar (80px width)
- 2-column suggestion grid
- Balanced text and element sizes
- Touch-optimized interactions

### 💻 **Desktop (≥1025px)**
- Full sidebar (90px width)
- 3-column suggestion grid
- Hover effects and animations
- Keyboard shortcuts

## Technical Features

### **Responsive Design**
- CSS Grid and Flexbox layouts
- Fluid typography with `clamp()`
- Breakpoint-specific optimizations
- Orientation handling

### **Performance**
- Optimized images and assets
- Service worker for caching
- Lazy loading where applicable
- Smooth 60fps animations

### **Accessibility**
- ARIA labels and semantic HTML
- Keyboard navigation support
- High contrast mode support
- Reduced motion preferences
- Screen reader compatibility

### **PWA Features**
- Web app manifest
- Service worker for offline support
- Install prompts
- App-like experience

## File Structure

```
├── app.py                 # Main Flask application
├── ai.py                  # OpenAI integration
├── db.py                  # Database operations
├── memory.py              # Conversation memory
├── requirements.txt       # Python dependencies
├── static/                # Static assets
│   ├── manifest.json     # PWA manifest
│   ├── sw.js            # Service worker
│   └── icon-*.png       # App icons
├── templates/             # HTML templates
│   ├── chat.html        # Main chat interface
│   └── landing.html     # Landing page
└── dip_users.db         # SQLite database
```

## Browser Support

- **Chrome**: 60+
- **Firefox**: 55+
- **Safari**: 11.1+
- **Edge**: 79+

## Mobile Browser Support

- **iOS Safari**: 11.3+
- **Chrome Mobile**: 60+
- **Samsung Internet**: 7.2+
- **Firefox Mobile**: 55+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on multiple devices
5. Submit a pull request

## License

This project is licensed under the MIT License.

---

**Dreamline** - Your AI companion for streamlined tasks and intelligent conversations.



