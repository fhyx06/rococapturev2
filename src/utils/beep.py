"""按钮反馈音效工具"""
import winsound
from pathlib import Path

# WAV 音效文件路径（相对于本文件所在的 utils/ 向上两级到 src/assets/sounds/）
_WAV_PATH = Path(__file__).parent.parent / "assets" / "sounds" / "beep.wav"


def beep() -> None:
    """播放按钮反馈音效；WAV 缺失时回退到系统蜂鸣"""
    try:
        if _WAV_PATH.exists():
            winsound.PlaySound(str(_WAV_PATH), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        else:
            winsound.Beep(800, 100)
    except (RuntimeError, OSError):
        pass
