def format_extraction_results(info):
    """
    Filter and simplify yt-dlp extraction results into a clean list of video and audio formats.
    """
    formats = info.get('formats', [])
    clean_formats = []
    resolutions = {}
    
    # Stable Preview: Favor high-res thumbnail
    preview_url = info.get('thumbnail')

    for f in formats:
        height = f.get('height')
        ext = (f.get('ext') or '').lower()
        vcodec = f.get('vcodec')
        filesize = f.get('filesize') or f.get('filesize_approx')
        
        # Filter for Video resolutions (where vcodec is present)
        if height and vcodec != 'none':
            res_str = f"{height}p"
            # Keep the one with better filesize info or just the first/best one
            if res_str not in resolutions or (filesize and (not resolutions[res_str].get('size') or filesize > resolutions[res_str]['size'])):
                resolutions[res_str] = {
                    'resolution': res_str,
                    'ext': ext,
                    'size': filesize,
                    'height': height
                }

    # Sort and add video formats (Descending by height)
    sorted_res = sorted(resolutions.values(), key=lambda x: x['height'], reverse=True)
    for item in sorted_res:
        size_str = f"{round(item['size'] / (1024*1024), 1)} MB" if item['size'] else "N/A"
        clean_formats.append({
            'id': item['resolution'],
            'label': f"{item['resolution']} | {item['ext']} | {size_str}",
            'type': 'video',
            'height': item['height']
        })

    # Add Audio option if video/audio was found
    # acodec != 'none' means there is audio track available
    if sorted_res or any(f.get('acodec') != 'none' for f in formats):
        clean_formats.append({
            'id': 'audio',
            'label': 'Audio Only | mp3 | Best Quality',
            'type': 'audio'
        })

    return {
        'success': True,
        'title': info.get('title', 'Media Content'),
        'formats': clean_formats,
        'preview_url': preview_url
    }
