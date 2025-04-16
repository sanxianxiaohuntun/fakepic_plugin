from io import BytesIO
import os
from pathlib import Path
from PIL import Image as PILImage, ImageDraw, ImageFont
from .config import config
res_path = Path(__file__).parent / "resources"
BOT = res_path / "bot_icon.png"
LEVEL = res_path / "level_icon.png"
NICK_FONT = config.nick_font
CHAT_FONT = config.chat_font
NICK_FALLBACK = config.fallback_nickfonts
CHAT_FALLBACK = config.fallback_chatfont
NICK_COR = config.correct_nick
TEXT_COR = config.correct_chat

BOT_ICON = config.add_bot_icon
LEVEL_ICON = config.add_level_icon

chatfont_size = 32
chatfont_spacing = 8
nickfont_size = 22

default_font = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts', 'msyh.ttc')

class Text2Image:
    def __init__(self, text, font_size=32, spacing=8, width=0, height=0, fontname=""):
        self.text = text
        self.font_size = font_size
        self.spacing = spacing
        self.width = width
        self.height = height
        self.fontname = fontname if fontname else default_font
        self.font = ImageFont.truetype(self.fontname, self.font_size)

        if self.text:
            lines = self.text.split('\n')
            max_width = 0
            for line in lines:
                line_width = self.font.getlength(line)
                max_width = max(max_width, line_width)
            
            self.width = max_width
            self.height = (self.font_size + self.spacing) * len(lines)
    
    @classmethod
    def from_text(cls, text, font_size=32, spacing=8, fontname=""):
        return cls(text, font_size, spacing, 0, 0, fontname)
    
    def wrap(self, max_width):
        if not self.text:
            return
            
        lines = []
        for origin_line in self.text.split('\n'):
            if not origin_line:
                lines.append("")
                continue
                
            current_line = ""
            for char in origin_line:
                char_width = self.font.getlength(char)
                line_width = self.font.getlength(current_line)
                
                if line_width + char_width <= max_width:
                    current_line += char
                else:
                    lines.append(current_line)
                    current_line = char
            
            if current_line:
                lines.append(current_line)
        
        self.text = '\n'.join(lines)
        
        max_width = 0
        for line in lines:
            line_width = self.font.getlength(line)
            max_width = max(max_width, line_width)
        
        self.width = max_width
        self.height = (self.font_size + self.spacing) * len(lines)
    
    def draw_on_image(self, image, pos):
        if not self.text:
            return
            
        draw = ImageDraw.Draw(image)
        lines = self.text.split('\n')
        y = pos[1]
        
        for line in lines:
            draw.text((pos[0], y), line, font=self.font, fill=(0, 0, 0))
            y += self.font_size + self.spacing


class BuildImage:
    def __init__(self, image):
        self.image = image
        self.width = image.width
        self.height = image.height
        self.draw = ImageDraw.Draw(image)
    
    @classmethod
    def new(cls, mode, size, color=None):
        return cls(PILImage.new(mode, size, color))
    
    @classmethod
    def open(cls, fp):
        if isinstance(fp, BytesIO):
            return cls(PILImage.open(fp))
        return cls(PILImage.open(fp))
    
    def resize(self, size):
        self.image = self.image.resize(size, PILImage.LANCZOS)
        self.width, self.height = size
        return self
    
    def circle(self):
        circle_image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        circle_draw = ImageDraw.Draw(circle_image)
        circle_draw.ellipse((0, 0, self.width, self.height), fill=(255, 255, 255, 255))
        
        if self.image.mode != 'RGBA':
            self.image = self.image.convert('RGBA')
        
        result = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        result.paste(self.image, (0, 0), mask=circle_image)
        
        return BuildImage(result)
    
    def circle_corner(self, radius):
        circle = PILImage.new('L', (radius * 2, radius * 2), 0)
        circle_draw = ImageDraw.Draw(circle)
        circle_draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)
        
        if self.image.mode != 'RGBA':
            self.image = self.image.convert('RGBA')
        
        result = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        result.paste(self.image, (0, 0))
        
        corner = circle.crop((0, 0, radius, radius))
        result.paste(corner, (0, 0), corner)
        
        corner = circle.crop((radius, 0, radius * 2, radius))
        result.paste(corner, (self.width - radius, 0), corner)
        
        corner = circle.crop((0, radius, radius, radius * 2))
        result.paste(corner, (0, self.height - radius), corner)
        
        corner = circle.crop((radius, radius, radius * 2, radius * 2))
        result.paste(corner, (self.width - radius, self.height - radius), corner)
        
        return BuildImage(result)
    
    def paste(self, img, pos, alpha=False):
        if isinstance(img, BuildImage):
            img = img.image
        
        if alpha:
            self.image.paste(img, pos, img)
        else:
            self.image.paste(img, pos)
        
        return self
    
    def draw_text(self, pos, text, fontsize=10, fill=(0, 0, 0), fontname=""):
        font = ImageFont.truetype(fontname if fontname else default_font, fontsize)
        self.draw.text(pos, text, font=font, fill=fill)
        return self
    
    def draw_rounded_rectangle(self, xy, radius, fill=None):
        x1, y1, x2, y2 = xy
        
        self.draw.rectangle((x1 + radius, y1, x2 - radius, y2), fill=fill)
        self.draw.rectangle((x1, y1 + radius, x2, y2 - radius), fill=fill)
        
        self.draw.pieslice((x1, y1, x1 + radius * 2, y1 + radius * 2), 180, 270, fill=fill)
        self.draw.pieslice((x2 - radius * 2, y1, x2, y1 + radius * 2), 270, 0, fill=fill)
        self.draw.pieslice((x1, y2 - radius * 2, x1 + radius * 2, y2), 90, 180, fill=fill)
        self.draw.pieslice((x2 - radius * 2, y2 - radius * 2, x2, y2), 0, 90, fill=fill)
        
        return self
    
    def crop(self, box):
        return BuildImage(self.image.crop(box))
    
    def save(self, format='PNG'):
        output = BytesIO()
        self.image.save(output, format=format)
        output.seek(0)
        return output


class SeparateMsg:
    def __init__(
            self,
            head: BytesIO,
            nick_name: str,
            is_robot: bool,
            text: str,
            images: list[BytesIO],
    ) -> None:
        self.head = head
        self.nick_name = nick_name
        self.is_robot = is_robot
        self.text = Text2Image.from_text(text, chatfont_size, spacing=chatfont_spacing, fontname=CHAT_FONT)
        self.images = images

    background: BuildImage
    current_height: int

    @property
    def is_only_one_picture(self) -> bool:
        return not self.text.width and len(self.images) == 1

    @property
    def height(self) -> int:
        width = self.text.width
        if width > 600:
            self.text.wrap(600)
        _, img_height, _ = self._handel_pictures() if self.images else (None, 0, None)
        return img_height + 80 + self.text.height + int(bool(self.text.height)) * 30
    
    def _handel_pictures(self) -> tuple[int, int, list[BuildImage]]:
        if self.is_only_one_picture:
            max_size = 500
            pic_spacing = 0
        else:
            max_size = 300
            pic_spacing = 10
        width_list = []
        pictures = []
        total_height = 0
        for img in self.images:
            pic = BuildImage.open(img)
            aspect_ratio = pic.width / pic.height
            if aspect_ratio >= 1:
                width = max_size
                height = int(width / aspect_ratio)
            else:
                height = max_size
                width = int(height * aspect_ratio)
            width_list.append(width)
            total_height += height + pic_spacing
            pic = pic.resize((width, height)).circle_corner(15)
            pictures.append(pic)
        return max(width_list), total_height, pictures
    
    def draw_on_picture(self):
        BackGround = self.background
        Y = self.current_height
        X = 155
        head_img = BuildImage.open(self.head)
        circle_head = head_img.circle().resize((85, 85))
        BackGround.paste(circle_head, (50, Y), True)
        x_nick = X
        x_nick = X
        if self.is_robot:
            if BOT_ICON:
                icon_width = 35
                icon = BuildImage.open(BOT).resize((icon_width, icon_width))
                BackGround.paste(icon, (x_nick, Y), alpha=True)
                x_nick += icon_width + 10
        else:
            if LEVEL_ICON:
                icon_width = 70
                icon = BuildImage.open(LEVEL).resize((icon_width, int(icon_width * 0.36)))
                BackGround.paste(icon, (x_nick, Y + 3), alpha=True)
                x_nick += icon_width + 10
        p_nick = (x_nick + NICK_COR[0], Y + NICK_COR[1])
        BackGround.draw_text(p_nick, self.nick_name, fontsize=nickfont_size, fill=(149, 149, 149), fontname=NICK_FONT)
        if self.is_only_one_picture:
            pass
        else:
            max_width, _, _ = self._handel_pictures() if self.images else (0, None, None)
            if max_width >= self.text.width:
                box_width = max_width + 200
            else:
                box_width = self.text.width + 200
            p_box = (X, Y + 50, box_width, Y + self.height - 20)
            BackGround.draw_rounded_rectangle(
                xy=p_box,
                radius=15,
                fill=(255, 255, 255)
            )
        p_text = (X + 22 + TEXT_COR[0], Y + 70 + TEXT_COR[1])
        self.text.draw_on_image(BackGround.image, p_text)
        if self.images:
            _, _, pictures = self._handel_pictures()
            if self.is_only_one_picture:
                BackGround.paste(pictures[0], (X, Y + 50), True)
            else:
                current_pic_height = Y + self.text.height + int(bool(self.text.height)) * 15 + 65
                for pic in pictures:
                    BackGround.paste(pic, (X + 20, current_pic_height), True)
                    current_pic_height += pic.height + 10


def draw_pic(sep_list: list[SeparateMsg], height=1920) -> BytesIO:
    image = BuildImage.new('RGB', (900, height), '#F1F1F1')
    position = 30
    for s in sep_list:
        s.background = image
        s.current_height = position
        position += s.height + 20
        s.draw_on_picture()
    if position > height:
        return draw_pic(sep_list, position)
    result = image.crop((0, 0, 900, position))
    image_bytes = result.save(format='PNG')
    return image_bytes 