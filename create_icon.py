import os
from PIL import Image, ImageDraw

def generate_icon(filepath="circle.ico"):
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer ring background (#1E1E2E)
    draw.ellipse([8, 8, size - 8, size - 8], fill=(30, 30, 46, 255), outline=(137, 180, 250, 255), width=10)

    # Inner glow / accent circle (#89B4FA)
    center_margin = 85
    draw.ellipse([center_margin, center_margin, size - center_margin, size - center_margin], fill=(137, 180, 250, 255))

    # Save as .ico with multiple standard sizes
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(filepath, format="ICO", sizes=sizes)
    print(f"Icon generated at {filepath}")

if __name__ == "__main__":
    generate_icon()
