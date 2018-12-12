from random import choice
import sc2
from sc2 import run_game, maps, Race, Difficulty, Result
from sc2.player import Bot, Computer
from src.protoss_bot import BalancedProtossBot
from src.zergling_muta_bot import ZerglingMutaBot
from src.terran_bot import MarineBot
import os
import uuid

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
    return Bot(Race.Zerg, ZerglingMutaBot())


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
    game_map = get_random_map()
    players = []
    for _ in range(20):
        players = [
            get_bot(Race.Zerg),
            Computer(Race.Random, Difficulty.Harder)
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

        result = run_game(game_map, players, realtime=False,
                          save_replay_as=os.path.join(os.getcwd(), 'replays', str(uuid.uuid4())))
        record.append(result)
        print('RESULT {}'.format(result))
        print(record)
    victory_count = sum(map(lambda x: x == Result.Victory, record))
    defeat_count = len(record) - victory_count
    print('On map {} the bot {} had a record of {} wins to {} losses playing against computer {} on {} difficulty'.format(
        game_map, players[0], victory_count, defeat_count, players[1], players[1].difficulty))


if __name__ == '__main__':
    main()
