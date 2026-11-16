import os
from PIL import Image, ImageDraw

def create_icons():
    src_path = 'static/app_icon.png'
    if not os.path.exists(src_path):
        print(f"Error: {src_path} not found")
        return

    base_img = Image.open(src_path).convert('RGBA')
    W, H = base_img.size

    # 1. Create a circular mask for round launcher icons
    circle_mask = Image.new('L', (W, H), 0)
    draw_circle = ImageDraw.Draw(circle_mask)
    draw_circle.ellipse((4, 4, W - 4, H - 4), fill=255)

    round_img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    round_img.paste(base_img, (0, 0), circle_mask)

    # 2. Create squircle mask with smooth rounded corners for standard launcher icons
    squircle_mask = Image.new('L', (W, H), 0)
    draw_sq = ImageDraw.Draw(squircle_mask)
    radius = int(W * 0.22)  # modern squircle radius
    draw_sq.rounded_rectangle((2, 2, W - 2, H - 2), radius=radius, fill=255)

    square_img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    square_img.paste(base_img, (0, 0), squircle_mask)

    # 3. Create Adaptive Foreground (432x432 with padding so nothing is clipped by Android masks)
    adaptive_fg = Image.new('RGBA', (432, 432), (0, 0, 0, 0))
    # Scale icon to fit 70% safe zone (approx 300x300)
    scaled_icon = base_img.resize((302, 302), Image.Resampling.LANCZOS)
    # Mask it with squircle
    fg_mask = Image.new('L', (302, 302), 0)
    ImageDraw.Draw(fg_mask).rounded_rectangle((0, 0, 302, 302), radius=60, fill=255)
    
    offset_x = (432 - 302) // 2
    offset_y = (432 - 302) // 2
    adaptive_fg.paste(scaled_icon, (offset_x, offset_y), fg_mask)

    # 4. Standard Android density sizes
    densities = {
        'mipmap-mdpi': 48,
        'mipmap-hdpi': 72,
        'mipmap-xhdpi': 96,
        'mipmap-xxhdpi': 144,
        'mipmap-xxxhdpi': 192,
    }

    res_root = os.path.join('android', 'app', 'src', 'main', 'res')

    for folder_name, size in densities.items():
        folder_path = os.path.join(res_root, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Standard launcher icon
        std_icon = square_img.resize((size, size), Image.Resampling.LANCZOS)
        std_icon.save(os.path.join(folder_path, 'ic_launcher.png'))

        # Round launcher icon
        rnd_icon = round_img.resize((size, size), Image.Resampling.LANCZOS)
        rnd_icon.save(os.path.join(folder_path, 'ic_launcher_round.png'))
        
        print(f"Generated {folder_name} (size: {size}x{size})")

    # 5. Save Play Store 512x512 Web Icon
    square_img.resize((512, 512), Image.Resampling.LANCZOS).save(os.path.join(res_root, 'ic_launcher-web.png'))
    square_img.resize((512, 512), Image.Resampling.LANCZOS).save('static/app_icon.png')
    
    # Save adaptive foreground to drawable
    adaptive_fg.save(os.path.join(res_root, 'drawable', 'ic_launcher_foreground.png'))
    print("All icons successfully generated!")

if __name__ == '__main__':
    create_icons()
