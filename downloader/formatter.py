def format_duration(seconds):
    """Format seconds into HH:MM:SS or MM:SS"""
    if not seconds:
        return ""
    try:
        s = int(seconds)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
    except (ValueError, TypeError):
        return ""

AUDIO_FORMATS_CONFIG = [
    {
        'codec': 'mp3',
        'label': 'MP3',
        'badge': 'Universal',
        'desc': 'Maximum compatibility across cars, phones, and media players',
        'bitrates': ['320', '256', '192', '128'],
        'default_bitrate': '320'
    },
    {
        'codec': 'm4a',
        'label': 'M4A',
        'badge': 'Apple AAC',
        'desc': 'High efficiency AAC audio in an MP4 container, great for iPhone/Mac',
        'bitrates': ['256', '192', '128'],
        'default_bitrate': '256'
    },
    {
        'codec': 'aac',
        'label': 'AAC',
        'badge': 'Pure AAC',
        'desc': 'Advanced Audio Coding stream format',
        'bitrates': ['320', '256', '192', '128'],
        'default_bitrate': '256'
    },
    {
        'codec': 'flac',
        'label': 'FLAC',
        'badge': 'Lossless',
        'desc': 'Lossless audio preservation with pristine master fidelity',
        'bitrates': ['Lossless'],
        'default_bitrate': 'Lossless'
    },
    {
        'codec': 'wav',
        'label': 'WAV',
        'badge': 'Studio PCM',
        'desc': 'Uncompressed raw audio waveform',
        'bitrates': ['Lossless'],
        'default_bitrate': 'Lossless'
    },
    {
        'codec': 'opus',
        'label': 'OPUS',
        'badge': 'Modern',
        'desc': 'High-efficiency modern open codec with superior low-bitrate clarity',
        'bitrates': ['160', '128', '96'],
        'default_bitrate': '160'
    }
]

def format_extraction_results(info):
    """
    Filter and format yt-dlp extraction results into a unified structure
    supporting audio formats, bitrates, video resolutions, and playlists.
    """
    is_playlist = info.get('_type') == 'playlist' or ('entries' in info and len(info.get('entries', [])) > 1)
    
    preview_url = info.get('thumbnail')
    if not preview_url and info.get('thumbnails'):
        preview_url = info['thumbnails'][-1].get('url')
        
    title = info.get('title', 'Media Content')
    uploader = info.get('uploader') or info.get('channel') or info.get('artist') or ''
    
    if is_playlist:
        entries = []
        raw_entries = info.get('entries', [])
        for idx, e in enumerate(raw_entries):
            if not e:
                continue
            entry_thumb = e.get('thumbnail')
            if not entry_thumb and e.get('thumbnails'):
                entry_thumb = e['thumbnails'][-1].get('url')
            
            entry_url = e.get('url')
            if not entry_url and e.get('id'):
                entry_url = f"https://www.youtube.com/watch?v={e['id']}"
                
            entries.append({
                'index': idx + 1,
                'id': e.get('id'),
                'title': e.get('title') or f"Track {idx + 1}",
                'duration': e.get('duration'),
                'duration_str': format_duration(e.get('duration')),
                'uploader': e.get('uploader') or e.get('channel') or '',
                'url': entry_url,
                'thumbnail': entry_thumb
            })
            
        if not preview_url and entries and entries[0].get('thumbnail'):
            preview_url = entries[0]['thumbnail']
            
        return {
            'success': True,
            'is_playlist': True,
            'title': title,
            'uploader': uploader,
            'track_count': len(entries),
            'preview_url': preview_url,
            'entries': entries,
            'audio_formats': AUDIO_FORMATS_CONFIG,
            'video_formats': [
                {'id': '1080p', 'label': '1080p | Full HD (MP4)'},
                {'id': '720p', 'label': '720p | HD (MP4)'},
                {'id': '480p', 'label': '480p | Standard (MP4)'},
                {'id': '360p', 'label': '360p | Light (MP4)'}
            ]
        }
        
    # Single item
    formats = info.get('formats', [])
    video_resolutions = {}
    
    for f in formats:
        height = f.get('height')
        vcodec = f.get('vcodec')
        filesize = f.get('filesize') or f.get('filesize_approx')
        
        if height and vcodec != 'none':
            res_str = f"{height}p"
            if res_str not in video_resolutions or (filesize and (not video_resolutions[res_str].get('size') or filesize > video_resolutions[res_str]['size'])):
                video_resolutions[res_str] = {
                    'resolution': res_str,
                    'ext': 'mp4',
                    'size': filesize,
                    'height': height
                }
                
    sorted_res = sorted(video_resolutions.values(), key=lambda x: x['height'], reverse=True)
    video_formats = []
    for item in sorted_res:
        size_str = f" • {round(item['size'] / (1024*1024), 1)} MB" if item['size'] else ""
        video_formats.append({
            'id': item['resolution'],
            'label': f"{item['resolution']} | MP4{size_str}",
            'height': item['height']
        })
        
    return {
        'success': True,
        'is_playlist': False,
        'title': title,
        'uploader': uploader,
        'duration_str': format_duration(info.get('duration')),
        'preview_url': preview_url,
        'audio_formats': AUDIO_FORMATS_CONFIG,
        'video_formats': video_formats
    }

