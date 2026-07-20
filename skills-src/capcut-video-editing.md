---
name: capcut-video-editing
description: Use when editing video in CapCut desktop app via computer-use. Covers UI layout, keyboard shortcuts, timeline operations, adding text/effects/transitions/filters, and export workflows. Triggers on "CapCut", "edit video", "add transition", "add effect", "split clip", "video editing", "export video".
---

# CapCut Desktop Video Editing

## Overview

Control CapCut desktop (macOS/Windows) via computer-use tools to perform video edits. CapCut has a dark UI with panels for media, timeline, preview, and properties.

## Prerequisites

- Request computer-use access to "CapCut" before any interaction
- Always take a screenshot before and after actions to verify results
- Use `cmd` (Mac) instead of `ctrl` for all shortcuts

## UI Layout

```
+------------------+------------------------+------------------+
|   LEFT PANEL     |    CENTER PREVIEW      |   RIGHT PANEL    |
|                  |                        |                  |
| Top Tabs:        |  Video preview         | Properties/      |
| Media | Audio |  |  Playback controls     | Details of       |
| Text | Stickers| |  Timecode display      | selected item    |
| Effects |        |                        |                  |
| Transitions |    |                        | EditPilot (AI)   |
| Captions |       |                        | at bottom-right  |
| Filters |        |                        |                  |
| Adjustment |     +------------------------+                  |
| Templates |      |    TIMELINE            |                  |
| AI avatar        |  Tracks stacked top    |                  |
|                  |  to bottom:            |                  |
| Left sidebar:    |  - Effects (purple)    |                  |
|  Import          |  - Adjustments (orange)|                  |
|  Subprojects     |  - Text (blue)         |                  |
|  AI media        |  - Video (teal/green)  |                  |
|  Spaces          |  - Audio (green)       |                  |
|  Library         |                        |                  |
+------------------+------------------------+------------------+
```

## Essential Keyboard Shortcuts (Mac)

### Playback
| Action | Shortcut |
|--------|----------|
| Play/Pause | `Space` |
| Go to start | `Home` or `fn+Left` |
| Go to end | `End` or `fn+Right` |
| Frame forward | `Right Arrow` |
| Frame backward | `Left Arrow` |
| Speed up playback | `L` |
| Slow/reverse playback | `J` |
| Pause (during J/L) | `K` |

### Editing
| Action | Shortcut |
|--------|----------|
| Split clip at playhead | `Cmd+B` |
| Delete selected | `Delete` or `Backspace` |
| Delete left of playhead | `Q` |
| Delete right of playhead | `W` |
| Undo | `Cmd+Z` |
| Redo | `Cmd+Shift+Z` |
| Copy | `Cmd+C` |
| Paste | `Cmd+V` |
| Select all | `Cmd+A` |
| Save project | `Cmd+S` |

### Timeline
| Action | Shortcut |
|--------|----------|
| Zoom in timeline | `Cmd+=` or `Cmd+scroll` |
| Zoom out timeline | `Cmd+-` |
| Fit timeline to view | `Cmd+0` |

## Core Workflows

### 1. Split a Clip
1. Click on the video track in the timeline to select it
2. Move playhead to desired split point (click on timeline ruler or use arrow keys)
3. Press `Cmd+B` or click the Split icon (scissors) in the timeline toolbar
4. Result: clip splits into two segments at the playhead position

### 2. Add Text
1. Click **Text** tab in top toolbar
2. Drag "Default text" to timeline (creates new text track)
3. Double-click the text element in preview to edit
4. Use right panel to customize: font, size, color, animation
5. Drag edges of text clip in timeline to adjust duration

### 3. Add a Transition
1. **Must have 2+ clips** on the same track (split first if needed)
2. Click **Transitions** tab in top toolbar
3. Browse categories: Trending, Classic, Flash&Cutout, Overlay, Light, Movement, Blur, Basic, Mask, Slide
4. Drag a transition onto the cut point between two clips
5. Adjust transition duration by dragging its edges in timeline

### 4. Add an Effect
1. Click **Effects** tab in top toolbar
2. Browse: Video effects categories include Trending, Classic, Flash&Cutout, Intro & Outro, Wild Pics, Party, Motion, Light, Retro, Body effects
3. Drag effect onto timeline (creates purple effect track above video)
4. Adjust duration by dragging edges
5. Click effect in timeline to modify properties in right panel (speed, intensity)

### 5. Add a Filter
1. Click **Filters** tab in top toolbar
2. Browse categories: Featured, Life, Photo Booth, Pet, Landscape, Movies, Mono, Portrait, Retro, Night
3. Drag filter onto video clip in timeline
4. Adjust filter intensity in right panel

### 6. Add Audio
1. Click **Audio** tab in top toolbar (first tab, far left)
2. Browse categories: Easter, Trending, Hits, Vlog, Phonk, Reggaeton, Marketing, Beauty, Fitness, Sound effects
3. Click the download/add icon next to a song - it previews first ("Previewing — Audio" header)
4. Click the green "+" button again to add to timeline (creates blue audio track below video)
5. Audio is usually longer than video - split audio at video end point, delete excess
6. Set Fade in/out in right panel (Basic tab): double-click the value fields
7. Right panel also has: Volume, Voice changer, Speed, Normalize loudness, Enhance voice, Reduce noise

### 7. Add a Sticker
1. Click **Stickers** tab in top toolbar
2. Browse categories: Trending, Classic, Animal Meme, Hits, Nailoong, Icons, Emoji, Emphasis, Cover-ups, Wrong, Love
3. Drag sticker onto timeline (creates orange sticker track)
4. Right panel shows: Transform (Scale, Position, Rotate), Animation, Tracking tabs

### 8. Change Clip Speed
1. Select a video clip in timeline
2. Click **Speed** tab in right panel
3. Choose Standard, Curve, or Velocity effects mode
4. Drag Speed slider (left = slower, right = faster)
5. Duration auto-adjusts (e.g., 0.55x doubles the duration)
6. "Smooth slow-mo" option appears for slow speeds

### 9. Trim Audio to Match Video
1. Position playhead at the end of the video content
2. Click the audio track to select it
3. Press `Cmd+B` to split the audio
4. Click the excess audio segment (after the split)
5. Press `Backspace` to delete it

### 7. Export Video
1. Click green **Export** button (top-right corner)
2. Choose resolution, format (MP4/MOV), quality
3. Set filename and destination
4. Click Export

## Timeline Toolbar Icons (left to right above timeline)
- `+` Add track
- Arrow tools (selection modes)
- Undo / Redo
- Split (scissors icon)
- Freeze frame
- Delete
- Various view toggles

## Tips
- **Click on a clip/effect in timeline** to see its properties in the right panel
- **Double-click text** in preview to edit inline
- **Drag clip edges** to trim from start or end
- **Right-click** on timeline elements for context menu with more options
- Effects with download arrows need to be downloaded first (click the arrow)
- **EditPilot** (bottom-right) is CapCut's AI assistant - can describe edits in text

## Tested Workflows (Verified)

These workflows were tested on a real project and confirmed working:

1. **Split clip**: Click video track to select → position playhead → `Cmd+B` works reliably
2. **Add transition**: Drag from Transitions panel directly to cut point between 2 clips → transition properties appear in right panel showing Name and Duration
3. **Add text**: Drag "Default text" from Text panel to timeline → edit text content via the text field in the right panel (more reliable than double-clicking in preview) → adjust font size in the Font size field
4. **Add filter**: With video clip selected, drag filter from Filters panel onto the video clip → "Filters" label appears on the clip
5. **Add effect**: Drag from Effects panel to timeline above video → creates a separate effect track (green/teal colored)

## UI Details Learned

- **Top tabs scroll**: The full tab bar includes Media, Audio, Text, Stickers, Effects, Transitions, Captions, Filters, Adjustment, Templates, AI avatar - they scroll left/right
- **Effect tracks are color-coded**: Effects = purple/green, Adjustments = orange, Text = red/orange, Video = teal
- **Right panel context-switches**: Shows properties for whatever is selected (video clip → Transform/Blend/Stabilize; text → Font/Size/Color; effect → Speed/Color/Glow; transition → Name/Duration)
- **EditPilot** (bottom-right) is CapCut's built-in AI assistant that can suggest and apply edits
- **Font size field**: Double-click the number to select it, type new size, press Return to apply
- **fn+Left for Home doesn't work** via computer-use - click the timeline ruler at position 0 instead

## Common Mistakes
- Forgetting to select the clip before splitting (splits wrong track)
- Adding transitions without splitting first (need 2 clips for a transition)
- Not clicking on the timeline track before pressing shortcuts
- Dragging effects to wrong position (must go above video track)
- Using font size 40+ makes text overflow the preview - size 15-25 works well for titles
- Text editing is more reliable via the right panel text field than double-clicking preview

---

## Intermediate Skills

### 10. Animation Presets (In/Out/Combo)
1. Select a video clip in the timeline
2. Click **Animation** tab in the right panel (Video > Audio > Speed > **Animation** > Adjust > AI stylize)
3. Three sub-tabs:
   - **In** (entrance): Fade In, Zoom 1, Cross Shake, Tesseract, Big B...Magic, Collision, Smoke, Glitch Intro, Tearing Open, Film Reel, etc.
   - **Out** (exit): Fade Out, Flash Out, Black Hole, Blur Out, TV Off, Zoom Flip, etc.
   - **Combo** (continuous loop): Zoom 1/2, Bouncy Rush, Pan Left/Right, Pendulum, Bounce, etc.
4. Some presets need downloading first - click the download arrow (⬇), then click again to apply
5. When applied, thumbnail gets a **cyan border** and a **Duration** slider appears (default 0.5s)
6. Adjust duration by editing the value or dragging the slider
7. **Categories**: Trending, Basic, Light, Glitch, Mask, 3D, Vibra (In/Out), Cam Motion (Combo)

### 11. Curve Speed Ramping
1. Select a video clip → click **Speed** tab in right panel
2. Click **Curve** (middle option: Standard | **Curve** | Velocity effects)
3. Preset speed curves appear:
   - **None** (flat line), **Custom**, **Montage** (ramp up)
   - **Hero** (slow-fast-slow, dramatic), **Bullet** (dip then recovery)
   - **Jump cut** (sharp changes), **Flash in**, **Flash out**
4. Click a preset to apply - an interactive **speed curve graph** appears below
5. Graph shows speed (y-axis: 0.1x to 10x) over time (x-axis)
6. **Drag control points** on the curve to customize the speed ramp
7. Duration auto-adjusts based on the curve
8. **Reset** button at bottom right to clear

### 12. Adjust Color / Color Grading
1. Select a video clip → click **Adjust** tab in right panel
2. **Sub-tabs**: Basic | HSL | Curves | Color wheel | Mask
3. **Basic tab** features:
   - **Auto adjust** (Pro) - AI auto color correction
   - **Color match** (Pro) - match colors between clips
   - **Color correction** (Pro) toggle
   - **LUT** section: dropdown to apply Look-Up Tables, Intensity slider, Protect skin tone toggle
   - **Adjust** section with sliders:
     - **Color**: Temp, Tint, Saturation
     - **Lightness**: Exposure, Contrast, Highlight (and Shadow, Blacks, Whites below)
4. **Apply to all** button applies adjustments to all clips
5. **Save as preset** button saves your color grade for reuse
6. Each slider has keyframe diamonds (◇) for animating values over time

### 13. Captions / Auto Subtitles
1. Click **Captions** tab in top toolbar
2. Left sidebar options:
   - **Auto captions** (AI-powered speech-to-text)
   - **Templates** (styled caption presets)
   - **AI packaging** (AI-generated caption styling)
   - **Auto lyrics** (for music videos)
   - **Add captions** (manual)
   - **AI emojis** (auto emoji insertion)
3. **Auto captions settings**:
   - Spoken language: English (dropdown for other languages)
   - Bilingual captions toggle (Pro)
   - Auto highlight keywords toggle (Pro)
   - AI emojis toggle (New)
   - Identify filler words toggle (Pro)
4. Click **Generate** button (teal) to auto-transcribe - shows remaining uses
5. **Templates** has categories: Trending, Classic, NEW, Hits, Word, Glow, Basic, Aesthetic, Monoline, Multiline, Highlight

### 14. AI Stylize
1. Select a video clip → click **AI stylize** tab (last tab in right panel)
2. **Style** section with sub-tabs:
   - **Hair Salon**: AI hair color changing (Mint Green, Dark Blue, Pumpkin Orange, Chocolate, Pure White, etc.)
   - **Video effects**: AI artistic style filters
3. Each style shows remaining uses (e.g., "2 uses")
4. Click a style to apply - AI processes the clip
5. Usage-limited feature (Pro/AI)

### 15. Right-Click Context Menu (Advanced)
Right-clicking a clip in the timeline reveals powerful features:
- **EditPilot** - AI editing assistant
- **Copy/paste attributes** → apply one clip's settings to another
- **Split scenes** (New) - AI auto-splits at scene changes
- **Transcript** (New) - view/edit speech transcript
- **Generate captions** - quick access to auto captions
- **Isolate voice** (New) - separate voice from background
- **Extract audio** (`Cmd+5`) - separate audio from video
- **Remove background** → AI background removal
- **Enhance audio** → AI audio enhancement
- **Enhance visuals** (HD) → AI upscaling
- **Adjust color** → quick color adjustments
- **Enhance motion** → Motion blur, Camera tracking, AI movement (Pro)
- **Create compound clip** (`Cmd+G`) - group clips into a subproject
- **Save preset** - save current clip settings
- **Export selected clips** - export just the selected portion
- **Deactivate clip** (`V`) - temporarily disable without deleting

### Keyframe Animation Reference
- Each Transform property (Scale, Position, Rotate) has a **diamond icon (◇)** at the far right
- Diamond icons are flanked by **< >** navigation arrows to jump between keyframes
- The **Transform** group header also has a diamond to keyframe all properties at once
- Reset icon (↻) resets the property to default
- Keyframe workflow: position playhead → click diamond → move playhead → change value → CapCut auto-creates second keyframe

---

## Advanced: Using EditPilot (AI Assistant)

EditPilot is CapCut's built-in AI editor. It accepts natural language commands and autonomously executes multi-step edits. Access it via the **EditPilot** button at the bottom-right of the screen, or right-click a clip → EditPilot.

### How to Use EditPilot
1. Click the **EditPilot** input field at the bottom of the screen
2. Type a natural language command describing what you want
3. Press **Return** to submit
4. EditPilot shows its plan (numbered steps) and processes them automatically
5. Wait for "Processing... X/Y" to complete
6. EditPilot confirms what it did and shows **Recommended effects/transitions** for more ideas

### Verified EditPilot Commands (Tested & Working)
- `"Add a fade out animation to the last clip with 2 second duration"` → Applied fade out with correct duration
- `"Increase saturation by 30 and contrast by 20 on all clips"` → Applied color correction to all 3 clips individually
- `"Add a chromatic aberration effect to the second clip and add a zoom bounce combo animation to the second clip"` → Added both effect and animation
- `"Add a dramatic flash transition between clip 1 and clip 2"` → Added "Snap Dazzle" transition with 2.0s duration
- `"Add a pulse effect to the entire video and increase the color temperature to warm +15 on all clips"` → Added "Pulsing Echo" full-span effect + adjusted temp on all clips

### EditPilot Tips
- It can handle **multiple edits in one command** (e.g., effect + animation + color)
- It intelligently selects the closest matching preset (e.g., "dramatic flash" → "Snap Dazzle")
- It can target specific clips by number ("clip 1", "clip 2", "the last clip")
- It applies effects/transitions/animations and adjusts their properties (duration, strength, etc.)
- After each edit, it shows **Recommended effects** thumbnails for quick follow-up
- Use it for batch operations like "adjust color on all clips" - much faster than doing manually
- Pro features are available through EditPilot when you have a Pro subscription
