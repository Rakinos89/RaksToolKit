"""Local privacy preferences and display masking."""
import getpass, ipaddress, json, os, platform, re
from pathlib import Path
SETTINGS = Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'WinToolKit' / 'settings.json'
def load_privacy():
    try: return json.loads(SETTINGS.read_text(encoding='utf-8')).get('privacy_mode') is True
    except (OSError, ValueError, TypeError): return False
def save_privacy(value):
    SETTINGS.parent.mkdir(parents=True,exist_ok=True)
    tmp=SETTINGS.with_suffix('.tmp')
    tmp.write_text(json.dumps({'privacy_mode':bool(value)},indent=2),encoding='utf-8')
    tmp.replace(SETTINGS)
def redact(value, enabled):
    text=str(value)
    if not enabled: return text
    names={platform.node(),os.getenv('COMPUTERNAME',''),getpass.getuser(),os.getenv('USERNAME','')}
    for name in sorted(filter(None,names),key=len,reverse=True):
        text=re.sub(re.escape(name),'[hidden]',text,flags=re.IGNORECASE)
    def mask(m):
        try: ipaddress.ip_address(m.group()); return '[IP hidden]'
        except ValueError: return m.group()
    text=re.sub(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])',mask,text)
    return text
