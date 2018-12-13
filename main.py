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


def get_replay_name(players, game_map) -> str:
    replay_part = '{}-{}-{}-vs-{}'.format(
        game_map.name, players[0].__class__.__name__, players[1].race, players[1].difficulty)
    unique_str = str(uuid.uuid4())[:5]
    replay_name = os.path.join(
        os.getcwd(), 'replays', '{}_{}'.format(replay_part, unique_str))
    sanitized_replay_name = replay_name.replace('.', '_')
    return '{}.SC2Replay'.format(sanitized_replay_name)


def main():
    record = []
    # game_map = get_random_map()
    game_map = maps.get(all_map_names[1])
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
        replay_name = get_replay_name(players, game_map)
        result = run_game(game_map, players, realtime=False,
                          save_replay_as=replay_name)
        record.append(result)
        print('RESULT {}'.format(result))
        print(record)
    victory_count = sum(map(lambda x: x == Result.Victory, record))
    defeat_count = len(record) - victory_count
    result_message = 'On map {} the bot {} had a record of {} wins to {} losses playing against computer {}'.format(
        game_map, players[0], victory_count, defeat_count, players[1])
    print(result_message)


if __name__ == '__main__':
    main()
