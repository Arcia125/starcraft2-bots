from random import choice
import sc2
from sc2 import run_game, maps, Race, Difficulty, Result
from sc2.player import Bot, Computer

from src.protoss_bot import BalancedProtossBot
from src.balanced_zerg_bot import BalancedZergBot
from src.terran_bot import MarineBot
from src.colors import Colorizer
from src.helpers import get_replay_name

# 4 player maps
# "CactusValleyLE",
# "PaladinoTerminalLE",

# "HonorgroundsLE" # is throwing errors
all_map_names = [
    "AbyssalReefLE",
    "BelShirVestigeLE",
    "NewkirkPrecinctTE",
    "ProximaStationLE"
]


def get_random_map():
    return maps.get(choice(all_map_names))


def get_protoss_bot():
    return Bot(Race.Protoss, BalancedProtossBot())


def get_zerg_bot():
    return Bot(Race.Zerg, BalancedZergBot())


def get_terran_bot():
    return Bot(Race.Terran, MarineBot())


def get_bot(bot_race: Race = None):
    if bot_race == Race.Protoss:
        return get_protoss_bot()
    if bot_race == Race.Zerg:
        return get_zerg_bot()
    if bot_race == Race.Terran:
        return get_terran_bot()
    return choice([get_protoss_bot, get_zerg_bot, get_terran_bot])()


def main():
    record = []
    # game_map = get_random_map()
    game_map = maps.get(all_map_names[1])
    players = []
    for _ in range(50):
        players = [
            BalancedZergBot(auto_camera=True, should_show_plot=False),
            Computer(Race.Random, Difficulty.Hard)
        ]

        # players = [
        #     Bot(Race.Protoss, Sc2Bot()),
        #     Computer(Race.Terran, Difficulty.Hard)
        # ]

        # players = [
        #     Bot(Race.Protoss, BalancedProtossBot()),
        #     Computer(Race.Random, Difficulty.Medium)
        # ]

        #
        # players = [
        #     Bot(Race.Zerg, ZerglingMutaBot()),
        #     Computer(Race.Random, Difficulty.Hard)
        # ]

        # players = [
        #     Bot(Race.Terran, MarineBot()),
        #     Computer(Race.Random, Difficulty.Medium)
        # ]
        replay_name = get_replay_name(players, game_map)
        result = run_game(game_map, players, realtime=False,
                          save_replay_as=replay_name)
        record.append(result)
        print('RESULT {}'.format(result))
        print(Colorizer.bg_green(record))
    victory_count = sum(map(lambda x: x == Result.Victory, record))
    defeat_count = len(record) - victory_count
    result_message = 'On map {} the bot {} had a record of {} wins to {} losses playing against computer {}'.format(
        game_map, players[0], Colorizer.green(str(victory_count)), Colorizer.red(str(defeat_count)), players[1])
    print(result_message)


if __name__ == '__main__':
    main()
