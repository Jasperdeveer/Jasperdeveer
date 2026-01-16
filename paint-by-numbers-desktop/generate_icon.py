#!/usr/bin/env python3
"""
Generate a simple app icon for JSPR Beamer Setup
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """Create a simple icon with JSPR text"""
    # Create image with dark background
    size = 1024
    img = Image.new('RGBA', (size, size), (26, 26, 26, 255))
    draw = ImageDraw.Draw(img)

    # Draw border
    border_width = 20
    draw.rectangle(
        [(border_width, border_width), (size - border_width, size - border_width)],
        outline=(100, 200, 255, 255),
        width=border_width
    )

    # Draw grid pattern (paint by numbers theme)
    grid_spacing = size // 8
    for i in range(1, 8):
        y = i * grid_spacing
        draw.line([(border_width * 2, y), (size - border_width * 2, y)],
                  fill=(60, 60, 80, 150), width=2)
        x = i * grid_spacing
        draw.line([(x, border_width * 2), (x, size - border_width * 2)],
                  fill=(60, 60, 80, 150), width=2)

    # Draw JSPR text
    try:
        font_size = 280
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        font = ImageFont.load_default()

    text = "JSPR"

    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center text
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 40

    # Draw text with shadow
    shadow_offset = 8
    draw.text((x + shadow_offset, y + shadow_offset), text,
              fill=(0, 0, 0, 128), font=font)
    draw.text((x, y), text, fill=(100, 200, 255, 255), font=font)

    # Draw subtitle
    try:
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
    except:
        subtitle_font = font

    subtitle = "Beamer Setup"
    bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = bbox[2] - bbox[0]
    subtitle_x = (size - subtitle_width) // 2
    subtitle_y = y + text_height + 40

    draw.text((subtitle_x, subtitle_y), subtitle,
              fill=(180, 180, 180, 255), font=subtitle_font)

    return img

if __name__ == '__main__':
    print("Generating JSPR app icon...")
    icon = create_icon()

    # Save as PNG
    icon.save('app_icon.png')
    print("✓ Saved app_icon.png")

    # Also save smaller versions
    for size in [512, 256, 128]:
        resized = icon.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(f'app_icon_{size}.png')
        print(f"✓ Saved app_icon_{size}.png")

    print("\nNow convert to .icns:")
    print("  mkdir -p icon.iconset")
    print("  sips -z 16 16     app_icon.png --out icon.iconset/icon_16x16.png")
    print("  sips -z 32 32     app_icon.png --out icon.iconset/icon_32x32.png")
    print("  sips -z 128 128   app_icon.png --out icon.iconset/icon_128x128.png")
    print("  sips -z 256 256   app_icon.png --out icon.iconset/icon_256x256.png")
    print("  sips -z 512 512   app_icon.png --out icon.iconset/icon_512x512.png")
    print("  sips -z 1024 1024 app_icon.png --out icon.iconset/icon_512x512@2x.png")
    print("  iconutil -c icns icon.iconset")
    print("  cp icon.icns 'JSPR Beamer Setup.app/Contents/Resources/icon.icns'")
    print("  rm -rf icon.iconset")
    print("  killall Dock")
