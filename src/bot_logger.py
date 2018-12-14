import datetime
from typing import Union, Callable
from sc2 import BotAI

from src.colors import Colorizer


def _format_time(seconds: Union[int, float]) -> str:
    return str(datetime.timedelta(seconds=round(seconds)))


def _get_message_prefix(bot: BotAI) -> str:
    time = Colorizer.yellow(_format_time(bot.time))
    supply_used = Colorizer.yellow(bot.supply_used)
    supply_cap = Colorizer.yellow(bot.supply_cap)
    minerals_per_second = Colorizer.light_cyan(
        bot.state.score.collection_rate_minerals)
    gas_per_second = Colorizer.green(bot.state.score.collection_rate_vespene)
    return 'TIME: {} SUPPLY: {} / {} MPS: {} GPS: {}'.format(time, supply_used, supply_cap, minerals_per_second, gas_per_second)


def _log(bot: BotAI, message: str, get_message_prefix: Callable[[BotAI], str]=_get_message_prefix):
    prefix = _get_message_prefix(bot)
    print('{} {}'.format(prefix, Colorizer.light_blue(message)))


def log_action(bot: BotAI, action_message: str):
    _log(bot, action_message)


def log_strategy_start(bot: BotAI, strategy_name: str):
    message = '++ STARTING {} STRATEGY ++'.format(strategy_name.upper())
    _log(bot, message)


def log_strategy_end(bot: BotAI, strategy_name: str):
    message = '-- ENDING {} STRATEGY --'.format(strategy_name.upper())
    _log(bot, message)
