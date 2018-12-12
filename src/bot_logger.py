from sc2 import BotAI


def log_action(bot: BotAI, action):
    print('SUPPLY: {} / {} {}'.format(bot.supply_used, bot.supply_cap, action))
