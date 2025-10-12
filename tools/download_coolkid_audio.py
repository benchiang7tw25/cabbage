import os
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, 'assets', 'sounds', 'coolkid')

AUDIO_FILES = {
    # BGM
    'theme_ready_or_not.mp3': 'https://forsaken2024.fandom.com/wiki/File:Ready-or-Not.mp3',
    # Optional layers
    'layer1.mp3': 'https://forsaken2024.fandom.com/wiki/File:C00lkidd-phase1-new.mp3',
    'layer2.mp3': 'https://forsaken2024.fandom.com/wiki/File:C00lkidd-phase2-new.mp3',
    'layer3.mp3': 'https://forsaken2024.fandom.com/wiki/File:C00lkidd-phase3-new.mp3',
    # SFX (placeholders – replace with your own links if you have better sources)
    'slash.ogg': 'https://upload.wikimedia.org/wikipedia/commons/4/45/SD_Foley_Sword_Swing.ogg',
    'dash_start.ogg': 'https://upload.wikimedia.org/wikipedia/commons/3/3a/Jet_engine_sound.ogg',
    'dash_hit_explosion.ogg': 'https://upload.wikimedia.org/wikipedia/commons/7/7f/Explosion.ogg',
    'clone_spawn.ogg': 'https://upload.wikimedia.org/wikipedia/commons/3/32/Pop.ogg',
}

WARN = (
    "Note: Some Fandom file URLs may require manual download if they block direct access.\n"
    "If a file ends up small or HTML, open the URL in a browser and Save As to: {}"
).format(OUT_DIR)


def safe_filename(name: str) -> str:
    return name.replace('..', '').replace('/', '_')


def download(url: str, out_path: str):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(out_path, 'wb') as f:
        f.write(data)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ok, fail = 0, 0
    for fname, url in AUDIO_FILES.items():
        out_path = os.path.join(OUT_DIR, safe_filename(fname))
        try:
            print(f'Downloading {fname} ...')
            download(url, out_path)
            size = os.path.getsize(out_path)
            print(f'  -> saved {size} bytes to {out_path}')
            ok += 1
        except Exception as e:
            print(f'  !! failed to download {fname} from {url}: {e}')
            fail += 1
    print(f'Finished. Success: {ok}, Failed: {fail}')
    if fail:
        print(WARN)


if __name__ == '__main__':
    sys.exit(main())


