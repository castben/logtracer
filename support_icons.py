# support_icons.py
import sys
import platform

def supports_icons():
    """Detecta si el sistema soporta iconos básicos (emojis)"""
    # Windows 10+ tiene buen soporte
    if platform.system() == "Windows" and sys.getwindowsversion().build >= 10240:
        return True

    # macOS siempre tiene buen soporte
    if platform.system() == "Darwin":
        return True

    # Linux: depende de la configuración
    if platform.system() == "Linux":
        # Verificar si hay soporte para UTF-8
        return sys.stdout.encoding and "utf" in sys.stdout.encoding.lower()

    return False

class Icons:
    """Clase para manejar iconos con fallback automático"""
    # Estados
    SUCCESS = "✅" if supports_icons() else "[OK]"
    ERROR = "❌" if supports_icons() else "[ERR]"
    WARNING = "⚠️" if supports_icons() else "[WARN]"
    INFO = "ℹ️" if supports_icons() else "[INFO]"

    # Acciones
    CLOCK = "⏱️" if supports_icons() else "[TIME]"
    MAGNIFYING_GLASS = "🔍" if supports_icons() else "[SEARCH]"
    CHECK = "❗" if supports_icons() else "[CHECK]"
    FOLDER = "📁" if supports_icons() else "[FOLDER]"
    CHART = "📈" if supports_icons() else "[CHART]"

    # Nodos
    LOCAL_NODE = "🏠" if supports_icons() else "[LOCAL]"
    REMOTE_NODE = "🌍" if supports_icons() else "[REMOTE]"

    icons = {
        "SUCCESS": SUCCESS,
        "ERROR": ERROR,
        "WARNING": WARNING,
        "INFO": INFO,
        "CLOCK": CLOCK,
        "MAGNIFYING_GLASS": MAGNIFYING_GLASS,
        "FOLDER": FOLDER,
        "CHART": CHART,
        "LOCAL_NODE": LOCAL_NODE,
        "REMOTE_NODE": REMOTE_NODE,
        "CHECK": CHECK
    }

    @classmethod
    def get(cls, icon_name):
        """

        :param icon_name:
        :return:
        """

        if icon_name in cls.icons:
            return cls.icons[icon_name]

        return ""

    @staticmethod
    def format(text):
        """Aplica fallback a texto con iconos"""
        replacements = {
            "✅": Icons.SUCCESS,
            "❌": Icons.ERROR,
            "⚠️": Icons.WARNING,
            "ℹ️": Icons.INFO,
            "⏱️": Icons.CLOCK,
            "🔍": Icons.MAGNIFYING_GLASS,
            "📁": Icons.FOLDER,
            "📈": Icons.CHART,
            "🏠": Icons.LOCAL_NODE,
            "🌍": Icons.REMOTE_NODE
        }

        for icon, replacement in replacements.items():
            text = text.replace(icon, replacement)

        return text