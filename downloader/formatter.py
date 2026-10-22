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

VIDEO_CONTAINERS_CONFIG = [
    {
        'codec': 'mp4',
        'label': 'MP4',
        'badge': 'Universal',
        'desc': 'Maximum compatibility across all phones, computers, and TVs'
    },
    {
        'codec': 'mkv',
        'label': 'MKV',
        'badge': 'Matroska',
        'desc': 'Modern open container preserving high-definition streams and audio'
    },
    {
        'codec': 'webm',
        'label': 'WEBM',
        'badge': 'Modern Web',
        'desc': 'Web-optimized container format with high compression efficiency'
    },
    {
        'codec': '3gp',
        'label': '3GP',
        'badge': 'Compact',
        'desc': 'Ultra-compact video format suitable for storage saving'
    }
]


def detect_platform(info, url=""):
    """Detect platform from extraction metadata or URL domain"""
    extractor = (info.get('extractor_key') or info.get('extractor') or '').lower()
    url_lower = (url or '').lower()
    is_playlist = info.get('_type') == 'playlist' or ('entries' in info and len(info.get('entries', [])) > 1)
    
    if 'music.youtube' in url_lower:
        if is_playlist:
            return {'name': 'YouTube Music Playlist', 'icon': '🎵', 'color': '#ec4899'}
        return {'name': 'YouTube Music', 'icon': '🎵', 'color': '#ec4899'}
    elif 'youtube' in extractor or 'youtube' in url_lower or 'youtu.be' in url_lower:
        if is_playlist:
            return {'name': 'YouTube Playlist', 'icon': '📦', 'color': '#a855f7'}
        return {'name': 'YouTube', 'icon': '▶️', 'color': '#ef4444'}
    elif 'instagram' in extractor or 'instagram' in url_lower:
        return {'name': 'Instagram', 'icon': '📸', 'color': '#e1306c'}
    elif 'tiktok' in extractor or 'tiktok' in url_lower:
        return {'name': 'TikTok', 'icon': '🎵', 'color': '#06b6d4'}
    elif 'twitter' in extractor or 'x.com' in url_lower or 'twitter.com' in url_lower:
        return {'name': 'X / Twitter', 'icon': '🐦', 'color': '#38bdf8'}
    elif 'facebook' in extractor or 'fb.watch' in url_lower or 'facebook.com' in url_lower:
        return {'name': 'Facebook', 'icon': '📘', 'color': '#3b82f6'}
    elif 'pinterest' in extractor or 'pinterest' in url_lower:
        return {'name': 'Pinterest', 'icon': '📌', 'color': '#e11d48'}
    elif 'soundcloud' in extractor or 'soundcloud' in url_lower:
        return {'name': 'SoundCloud', 'icon': '☁️', 'color': '#f97316'}
    elif 'reddit' in extractor or 'reddit' in url_lower:
        return {'name': 'Reddit', 'icon': '🤖', 'color': '#ea580c'}
    else:
        name = info.get('extractor_key') or 'Universal Source'
        return {'name': name, 'icon': '🌐', 'color': '#818cf8'}

def format_extraction_results(info, url=""):
    """
    Filter and format yt-dlp extraction results into a unified structure
    supporting audio formats, bitrates, video resolutions, and playlists.
    """
    is_playlist = info.get('_type') == 'playlist' or ('entries' in info and len(info.get('entries', [])) > 1)
    platform_info = detect_platform(info, url)
    
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
            'platform': platform_info,
            'title': title,
            'uploader': uploader,
            'track_count': len(entries),
            'preview_url': preview_url,
            'entries': entries,
            'audio_formats': AUDIO_FORMATS_CONFIG,
            'video_formats': VIDEO_CONTAINERS_CONFIG,
            'video_resolutions': ['1080p', '720p', '480p', '360p']
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
    res_list = [item['resolution'] for item in sorted_res] or ['1080p', '720p', '480p', '360p']
        
    return {
        'success': True,
        'is_playlist': False,
        'platform': platform_info,
        'title': title,
        'uploader': uploader,
        'duration_str': format_duration(info.get('duration')),
        'preview_url': preview_url,
        'audio_formats': AUDIO_FORMATS_CONFIG,
        'video_formats': VIDEO_CONTAINERS_CONFIG,
        'video_resolutions': res_list
    }

