import os
import base64
import io
from pathlib import Path
from typing import Optional, Tuple, Union, List
from PIL import Image, UnidentifiedImageError
import logging

logger = logging.getLogger("OrcaStatLLM-Scientist")

class ImageHelper:
    @staticmethod
    def convert_to_base64(image_path: Union[str, Path]) -> Optional[str]:
        try:
            if not os.path.exists(image_path):
                logger.warning(f"Image not found: {image_path}")
                return None
            file_ext = os.path.splitext(str(image_path))[1].lower().lstrip('.')
            mime_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'svg': 'image/svg+xml',
                'webp': 'image/webp'
            }
            
            mime_type = mime_types.get(file_ext, 'image/png')
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
            return f"data:{mime_type};base64,{encoded_string}"
            
        except Exception as e:
            logger.error(f"Error converting image to base64: {str(e)}")
            return None
    
    @staticmethod
    def optimize_image(
        input_path: Union[str, Path], 
        output_path: Optional[Union[str, Path]] = None, 
        max_size: int = 800,
        quality: int = 85
    ) -> str:
        try:
            if not os.path.exists(input_path):
                logger.warning(f"Image not found: {input_path}")
                return str(input_path)
            if output_path is None:
                path = Path(input_path)
                stem = path.stem
                suffix = path.suffix
                output_path = path.parent / f"{stem}_optimized{suffix}"
            with Image.open(input_path) as img:
                width, height = img.size
                if width > height:
                    if width > max_size:
                        new_width = max_size
                        new_height = int(height * (max_size / width))
                    else:
                        new_width, new_height = width, height
                else:
                    if height > max_size:
                        new_height = max_size
                        new_width = int(width * (max_size / height))
                    else:
                        new_width, new_height = width, height
                if new_width != width or new_height != height:
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                if img.mode == 'RGBA':
                    img.save(output_path, optimize=True)
                else:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(output_path, 'JPEG', quality=quality, optimize=True)
                
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error optimizing image: {str(e)}")
            return str(input_path)  
    
    @staticmethod
    def verify_image(image_path: Union[str, Path]) -> bool:
        if not os.path.exists(image_path):
            return False
            
        try:
            with Image.open(image_path) as img:
                img.verify() 
            return True
        except (IOError, SyntaxError, UnidentifiedImageError):
            return False
    
    @staticmethod
    def ensure_image_exists(image_path: Union[str, Path], fallback_text: str) -> str:
        if ImageHelper.verify_image(image_path):
            return str(image_path)
        placeholder_path = str(Path(image_path).parent / f"placeholder_{Path(image_path).name}")
        try:
            img = Image.new('RGB', (800, 400), color=(245, 245, 245))
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("Arial", 24)
            except IOError:
                font = ImageFont.load_default()
            text = f"Image: {fallback_text}"
            text_width, text_height = draw.textsize(text, font=font)
            position = ((800 - text_width) // 2, (400 - text_height) // 2)
            draw.text(position, text, fill=(0, 0, 0), font=font)
            img.save(placeholder_path)
            return placeholder_path
            
        except Exception as e:
            logger.error(f"Error creating placeholder image: {str(e)}")
            return str(image_path)  
    
    @staticmethod
    def create_blank_image(
        width: int = 800, 
        height: int = 600, 
        color: Tuple[int, int, int] = (255, 255, 255),
        text: Optional[str] = None, 
        output_path: Optional[str] = None
    ) -> str:
        try:
            img = Image.new('RGB', (width, height), color=color)
            if text:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("Arial", 24)
                except IOError:
                    font = ImageFont.load_default()
                text_width, text_height = draw.textsize(text, font=font)
                x = (width - text_width) // 2
                y = (height - text_height) // 2
                draw.text((x, y), text, fill=(100, 100, 100), font=font)
            if not output_path:
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                output_path = temp_file.name
                temp_file.close()
                
            img.save(output_path)
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating blank image: {str(e)}")
            return ""
