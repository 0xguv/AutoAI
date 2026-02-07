# AutoAI Video Editor - Svelte Frontend

A modern, responsive video editor built with Svelte and Tailwind CSS.

## Features

- **Fixed Left Navigation**: Clean icon-based sidebar
- **9:16 Video Player**: Optimized for mobile/short-form content
- **Draggable Subtitle Overlay**: Move and resize subtitles on the video
- **Timeline Panel**: Scrollable caption cards synced to video playback
- **Real-time Editing**: Edit captions inline with live preview

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Run development server:
```bash
npm run dev
```

3. Build for production:
```bash
npm run build
```

## Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Sidebar.svelte       # Fixed left navigation
│   │   ├── VideoEditor.svelte   # Main editor with video player
│   │   └── Timeline.svelte      # Right-side caption timeline
│   ├── App.svelte              # Root component
│   ├── main.js                 # Entry point
│   └── app.css                 # Tailwind styles
├── index.html
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Usage

Visit `/editor-new` route in your Flask app to use the new Svelte editor.

## Integration with Flask

The Flask app serves the built Svelte app from `static/dist/`:
- `/editor-new` - Main editor page
- `/assets/*` - Static assets (JS, CSS)

## Video Player Controls

- **Play/Pause**: Click play button or video
- **Seek**: Skip forward/backward 5 seconds
- **Volume**: Adjustable volume slider
- **Fullscreen**: Fullscreen toggle

## Subtitle Editing

- **Drag**: Click and drag subtitle to reposition
- **Resize**: Use corner handles to resize
- **Edit**: Click caption card in timeline to edit text
- **Sync**: Click caption to jump to that timestamp

## Keyboard Shortcuts

- `Space`: Play/Pause
- `←/→`: Seek backward/forward 5 seconds

## Customization

Edit `tailwind.config.js` to customize colors and theme.
