# Data Evolution

Create motion chart videos from CSV datasets. Generate engaging visualizations that show how rankings change over time - perfect for social media content about population, companies, sports, or any ranked data.

## Features

- **Generic CSV input** - Works with any dataset that has Entity, Time, and Value columns
- **Multiple formats** - Create shorts (9:16), landscape (16:9), or square (1:1) videos
- **Intro/Outro** - Add custom intro and outro images with configurable duration
- **Audio support** - Add custom background music or use silent audio track
- **Auto-thumbnail** - Automatically extracts thumbnail from intro image
- **Configurable styling** - Custom chart styles, colors, and dynamic titles
- **Universal compatibility** - Videos work on VLC, YouTube, X, LinkedIn

## Installation

```bash
# Clone the repository
cd data_evolution

# Install dependencies
pip install -e .
# Or use uv
uv pip install -e .
```

Required: Python 3.9+ and ffmpeg installed on your system.

## Quick Start

```bash
# Run with the example dataset
python src/main.py examples/world_population/config.yaml
```

## CSV Format

Your CSV should have three columns:

```csv
Entity,Year,Value
China,2000,1262645000
India,2000,1053481072
United States,2000,282162411
...
```

- **Column 1**: Entity (country, company, team, etc.)
- **Column 2**: Time (year, month, etc.)
- **Column 3**: Value (population, revenue, score, etc.)

Headers are used for axis labels. The system auto-detects columns, but you can override in config.

## Configuration

Each video project needs a `config.yaml` file:

```yaml
# Input
csv_path: "./data.csv"

# Output directories (relative to this config file)
output_dir: "."
frames_dir: "frames"
videos_dir: "videos"
thumbnails_dir: "thumbnails"

# Video settings
format: "landscape"   # shorts | landscape | square
fps: 30
duration_per_frame: 0.5

# Intro (optional)
intro_image: "./intro.png"
intro_duration: 2.0

# Outro (optional)
outro_image: "./outro.png"
outro_duration: 2.0

# Audio (optional)
audio_track: null          # null = silent audio (default)
# audio_track: "./music.mp3"  # or path to audio file (MP3, WAV, OGG, M4A)

# Chart styling
chart:
  style: null                    # matplotlib style name or null for default
  title_template: "Top 10 - {Year}"  # {Year} gets replaced with time value
  top_n: 10                      # Number of entities to show
  colors: null                   # List of colors or null for auto
```

## Video Formats

| Format | Resolution | Aspect Ratio | Best For |
|--------|------------|--------------|----------|
| `shorts` | 1080x1920 | 9:16 | YouTube Shorts, TikTok, Reels |
| `landscape` | 1920x1080 | 16:9 | YouTube, LinkedIn |
| `square` | 1080x1080 | 1:1 | Instagram, LinkedIn |

## Chart Styling

### Available Matplotlib Styles

Common styles: `seaborn-v0_8-darkgrid`, `ggplot`, `bmh`, `fast`, `grayscale`

### Custom Colors

```yaml
chart:
  colors:
    - "#FF6B6B"
    - "#4ECDC4"
    - "#45B7D1"
    - "#96CEB4"
    - "#FFEAA7"
```

### Dynamic Titles

Use `{column_name}` in title_template to include time values:

```yaml
chart:
  title_template: "Top 10 Countries - {Year}"   # → "Top 10 Countries - 2020"
```

## CLI Options

```bash
python src/main.py <config.yaml> [options]

Options:
  --skip-frames   Skip frame generation (use existing frames)
  --skip-video    Skip video creation
```

## Project Structure

```
data_evolution/
├── src/
│   ├── __init__.py
│   ├── config.py        # Config loading
│   ├── dataset.py       # CSV handling
│   ├── charts.py        # Chart generation
│   ├── video.py        # Video creation
│   └── main.py         # CLI entry point
├── examples/
│   └── world_population/
│       ├── config.yaml
│       ├── data.csv
│       ├── frames/
│       ├── videos/
│       └── thumbnails/
```

## Output

After running, you'll find:

- `frames/` - Individual chart images (one per time period)
- `videos/` - Final video(s)
- `thumbnails/` - Thumbnail image (if intro provided)

## Creating Intro/Outro Images

Your intro/outro images should be high-quality. Recommended:

- Shorts: 1080x1920 pixels
- Landscape: 1920x1080 pixels  
- Square: 1080x1080 pixels

You can use tools like Canva, Figma, or PowerPoint to create them.

## License

MIT
