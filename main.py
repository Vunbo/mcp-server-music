from bs4 import BeautifulSoup
import requests
from mcp.server.fastmcp import FastMCP
from typing import List, Dict
import webbrowser
import tempfile
import html

mcp = FastMCP("musicmcp", logger_level="error")

# 获取网页内容
def get_html(url):
    response = requests.get(url)
    return response.text

@mcp.tool(
    description="""
    通过提供的歌曲名称获取符合的音乐播放列表。
    """
)
def get_music_list(song_name: str) -> List[Dict[str, str]]:
    """获取指定歌曲名的歌曲列表。
    args:
        song_name: 歌曲名称
    return:
        List: List[Dict[str, str]]: 返回一个包含歌曲名称和播放链接的字典列表。
            - name: 歌曲名称
            - url: 歌曲详情页面链接
            - id: 歌曲ID
    """
    try:
        url = f"https://www.mvmp3.com/so.php?wd={song_name}"
        html_content = get_html(url)
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        # 提取歌曲列表
        songs = []
        for li in soup.select('ul > li'):
            name_link = li.select_one('.name a.url')
            if name_link:
                song_name = name_link.get_text(strip=True)
                song_url = f"https://www.mvmp3.com{name_link['href']}"
                song_id = name_link['href'].split("mp3/")[1].split(".")[0]
                
                # 提取MV链接（如果存在）
                # mv_link = li.select_one('.name a.mv')
                # mv_url = mv_link['href'] if mv_link else "无MV"
                
                songs.append({
                    'name': song_name,
                    'url': song_url,
                    'id': song_id
                })
                
        return songs
    
    except Exception as e:
        return f"发生错误: {e}"
    

def get_music_info(song_id) -> dict:
    url = "https://www.mvmp3.com/style/js/play.php"
    data = {
        "id": song_id,
        "type": "dance"
    }

    response = requests.post(url, data=data, verify=False)
    return response.json()

@mcp.tool(
    description="""
    根据歌曲列表选择的song_id播放歌曲。
    """
)
def play_music(id):
    """根据歌曲列表选中歌曲的id播放。
    args:
        song_id: 歌曲ID
    """
    # 歌曲信息
    song_info = get_music_info(id)
    if not song_info:
        return "歌曲信息获取失败，请检查歌曲ID。"
    # 提取歌曲信息
    title = song_info['title']
    artist = song_info['singer']
    cover = song_info['pic']
    music_url = song_info['url']
    lrc_text = song_info['lrc']

    # 转义歌词防止 HTML 注入问题
    safe_lrc = html.escape(lrc_text)

    # HTML 内容拼接（使用你提供的美化模板）
    html_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>音乐播放器</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background-color: #f5f5f5;
            }}
            .player {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                text-align: center;
                width: 350px;
            }}
            .song-info {{
                margin-bottom: 15px;
            }}
            .song-title {{
                font-size: 18px;
                font-weight: bold;
                margin: 5px 0;
            }}
            .song-artist {{
                font-size: 14px;
                color: #666;
            }}
            .album-cover {{
                width: 200px;
                height: 200px;
                border-radius: 5px;
                object-fit: cover;
                margin: 10px auto;
            }}
            audio {{
                width: 100%;
                margin: 15px 0;
            }}
            .lyrics-container {{
                margin-top: 20px;
                max-height: 200px;
                overflow-y: auto;
                text-align: left;
                padding: 10px;
                border-top: 1px solid #eee;
            }}
            .lyric-line {{
                margin: 5px 0;
                color: #666;
            }}
            .lyric-line.active {{
                color: #1db954;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="player">
            <h1>音乐播放器</h1>
            <div class="song-info">
                <img id="albumCover" class="album-cover" src="{cover}" alt="专辑封面">
                <div class="song-title">{title}</div>
                <div class="song-artist">{artist}</div>
            </div>
            <audio id="audioPlayer" controls src="{music_url}">
                您的浏览器不支持audio元素
            </audio>
            <div class="lyrics-container" id="lyricsContainer" style="height: 300px;"></div>
        </div>
        <script>
            const lrcText = `{safe_lrc}`;
            const lines = lrcText.split('\\n');
            const container = document.getElementById('lyricsContainer');
            lines.forEach(line => {{
                const div = document.createElement('div');
                div.className = 'lyric-line';
                div.textContent = line.replace(/\\[\\d{{2}}:\\d{{2}}\\.\\d{{2}}\\]/, '');
                container.appendChild(div);
            }});

            const audio = document.getElementById('audioPlayer');
            audio.addEventListener('timeupdate', () => {{
                const currentTime = audio.currentTime;
                const lyricLines = document.querySelectorAll('.lyric-line');
                lyricLines.forEach(line => line.classList.remove('active'));

                for (let i = 0; i < lines.length; i++) {{
                    const match = lines[i].match(/\\[(\\d{{2}}):(\\d{{2}})\\.(\\d{{2}})\\]/);
                    if (match) {{
                        const min = parseInt(match[1]);
                        const sec = parseInt(match[2]);
                        const time = min * 60 + sec;
                        const nextMatch = lines[i+1] ? lines[i+1].match(/\\[(\\d{{2}}):(\\d{{2}})\\.(\\d{{2}})\\]/) : null;
                        const nextTime = nextMatch ? parseInt(nextMatch[1]) * 60 + parseInt(nextMatch[2]) : Infinity;

                        if (currentTime >= time && currentTime < nextTime) {{
                            lyricLines[i].classList.add('active');
                            lyricLines[i].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                            break;
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """

    # 保存临时 HTML 文件
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
        f.write(html_content)
        file_path = f.name

    # 打开本地 HTML 页面
    webbrowser.open(f'file:///{file_path}')
    
    return f"正在播放: {title} - {artist}，请查看浏览器。"


if __name__ == "__main__":
    mcp.run()