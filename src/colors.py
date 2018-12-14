from typing import Callable


_COLORS = {
    'RESET': '\033[0m',
    'BOLD': '\033[01m',
    'DISABLE': '\033[02m',
    'UNDERLINE': '\033[04m',
    'REVERSE': '\033[07m',
    'STRIKETHROUGH': '\033[09m',
    'INVISIBLE': '\033[08m',
    'FG': {
        'BLACK': '\033[30m',
        'RED': '\033[31m',
        'GREEN': '\033[32m',
        'ORANGE': '\033[33m',
        'BLUE': '\033[34m',
        'PURPLE': '\033[35m',
        'CYAN': '\033[36m',
        'LIGHT_GREY': '\033[37m',
        'DARK_GREY': '\033[90m',
        'LIGHT_RED': '\033[91m',
        'LIGHT_GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'LIGHT_BLUE': '\033[94m',
        'PINK': '\033[95m',
        'LIGHT_CYAN': '\033[96m'
    },
    'BG': {
        'BLACK': '\033[40m',
        'RED': '\033[41m',
        'GREEN': '\033[42m',
        'ORANGE': '\033[43m',
        'BLUE': '\033[44m',
        'PURPLE': '\033[45m',
        'CYAN': '\033[46m',
        'LIGHT_GREY': '\033[47m'
    }
}

# _GENERAL_NAMES = [color for color in _COLORS if not color in ['FG', 'BG']]
# _FG_NAMES = [color for color in _COLORS.get('FG')]
# _BG_NAMES = [color for color in _COLORS.get('BG')]

# print(_GENERAL_NAMES)
# print(_FG_NAMES)
# print(_BG_NAMES)


class Colorizer(object):
    color_names = []

    def __init__(self):
        pass

    @staticmethod
    def _add_term_color(color, s):
        return '{}{}{}'.format(color, s, _COLORS.get('RESET'))

    @staticmethod
    def _create_color_adder(color) -> Callable[[str], str]:
        return lambda s: Colorizer._add_term_color(color, s)

    @staticmethod
    def _register_color_adder(color_name: str, terminal_code: str):
        color_adder = Colorizer._create_color_adder(terminal_code)
        color_adder.__doc__ = "Auto-generated method for {}".format(color_name)
        color_adder.__name__ = color_name.lower()
        staticmethod(color_adder)
        Colorizer.color_names.append(color_adder.__name__)
        setattr(Colorizer, color_adder.__name__, color_adder)

    @staticmethod
    def black(s: str) -> str:
        return s

    @staticmethod
    def red(s: str) -> str:
        return s

    @staticmethod
    def green(s: str) -> str:
        return s

    @staticmethod
    def orange(s: str) -> str:
        return s

    @staticmethod
    def blue(s: str) -> str:
        return s

    @staticmethod
    def purple(s: str) -> str:
        return s

    @staticmethod
    def cyan(s: str) -> str:
        return s

    @staticmethod
    def light_grey(s: str) -> str:
        return s

    @staticmethod
    def dark_grey(s: str) -> str:
        return s

    @staticmethod
    def light_red(s: str) -> str:
        return s

    @staticmethod
    def light_green(s: str) -> str:
        return s

    @staticmethod
    def yellow(s: str) -> str:
        return s

    @staticmethod
    def light_blue(s: str) -> str:
        return s

    @staticmethod
    def pink(s: str) -> str:
        return s

    @staticmethod
    def light_cyan(s: str) -> str:
        return s

    @staticmethod
    def bg_black(s: str) -> str:
        return s

    @staticmethod
    def bg_red(s: str) -> str:
        return s

    @staticmethod
    def bg_green(s: str) -> str:
        return s

    @staticmethod
    def bg_orange(s: str) -> str:
        return s

    @staticmethod
    def bg_blue(s: str) -> str:
        return s

    @staticmethod
    def bg_purple(s: str) -> str:
        return s

    @staticmethod
    def bg_cyan(s: str) -> str:
        return s

    @staticmethod
    def bg_light_grey(s: str) -> str:
        return s


for color_name, terminal_code in _COLORS.get('FG').items():
    Colorizer._register_color_adder(color_name, terminal_code)

for color_name, terminal_code in _COLORS.get('BG').items():
    Colorizer._register_color_adder('bg_{}'.format(color_name), terminal_code)

# print(dir(Colorizer))
