import os
import hashlib
import mimetypes
from urllib.parse import urlparse

async def save_resource(session, url, output_dir):
    parsed_url = urlparse(url)
    if not parsed_url.scheme.startswith('http'):
        return None

    try:
        async with session.get(url, timeout=20) as response:
            content = await response.read()
            content_type = response.content_type or ''

            # Generate filename
            hash_digest = hashlib.md5(url.encode()).hexdigest()
            ext = mimetypes.guess_extension(response.content_type or '') or ''
            filename = f'{hash_digest}{ext}'

            if 'image' in content_type:
                subfolder = 'images'
            elif 'javascript' in content_type:
                subfolder = 'scripts'
            elif 'css' in content_type:
                subfolder = 'style'
            elif 'font' in content_type:
                subfolder = 'fonts'
            elif 'audio' in content_type:
                subfolder = 'audio'
            elif 'video' in content_type:
                subfolder = 'video'
            elif 'html' in content_type:
                subfolder = 'html'
            else:
                subfolder = 'other'


            subdir_path = os.path.join(output_dir, subfolder)
            os.makedirs(subdir_path, exist_ok=True)

            filepath = os.path.join(subdir_path, filename)
            with open(filepath, 'wb') as f:
                f.write(content)

            relative_path = os.path.join(subfolder, filename)
            return relative_path, url

    except Exception as e:
        print(f'Failed to download {url}: {e}')
        return None

