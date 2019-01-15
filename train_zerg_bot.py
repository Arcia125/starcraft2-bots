import argparse
import math
from random import choice
import sc2
from sc2 import run_game, maps, Race, Difficulty, Result
from sc2.player import Bot, Computer

from src.balanced_zerg_bot import BalancedZergBot
from src.colors import Colorizer
from src.helpers import get_replay_name
from src.timing_manager import Timing

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

all_races = {
    'zerg': 'Zerg',
    'terran': 'Terran',
    'protoss': 'Protoss',
    'random': 'Random'
}

all_difficulties = {
    'very-easy': 'VeryEasy',
    'easy': 'Easy',
    'medium': 'Medium',
    'medium-hard': 'MediumHard',
    'hard': 'Hard',
    'harder': 'Harder',
    'very-hard': 'VeryHard',
    'cheat-vision': 'CheatVision',
    'cheat-money': 'CheatMoney',
    'cheat-insane': 'CheatInsane'
}

parser = argparse.ArgumentParser(
    description='Test BalancedZergBot against other bots and get results')
parser.add_argument('iterations', metavar='iterations', type=int,
                    help='number of matches to play')
parser.add_argument('race', metavar='race', type=str,
                    help='race of opponent', choices=[*all_races], default='random')
parser.add_argument('difficulty', metavar='difficulty',
                    type=str, help='difficulty of opponent', choices=[*all_difficulties], default='hard')
parser.add_argument(
    '--no-camera', help='do not use auto camera', action='store_true')
parser.add_argument(
    '--no-plots', help='hide histogram plot graphs.', action='store_true')
parser.add_argument(
    '--no-debug',  help='hide debugging lines', action='store_true'
)


default_timings = {
    'boom': [
        Timing(-1, 500),
        Timing(550, 775),
        Timing(800, 1000),
        Timing(1500, 1900),
        Timing(2000, math.inf)
    ],
    'rush': [
        Timing(400, 850),
        Timing(950, 1000),
        Timing(1250, 1300),
        Timing(1450, 1500),
        Timing(1650, 1700),
        Timing(1850, 1900),
        Timing(2050, 2100),
        Timing(2250, 2300),
        Timing(2600, math.inf)
    ],
    'mutalisk': [
        Timing(200, 800),
        Timing(900, 1200)
    ],
    'ultralisk': [
        Timing(400, math.inf)
    ],
    'roach': [
        Timing(400, 700),
        Timing(1000, math.inf)
    ],
    'hydralisk': [
        Timing(600, math.inf)
    ]
}

later_hydras = {
    'boom': [
        Timing(-1, 550),
        Timing(600, 775),
        Timing(800, 1000),
        Timing(1500, 1900),
        Timing(2000, math.inf)
    ],
    'rush': [
        Timing(450, 850),
        Timing(950, 1000),
        Timing(1250, 1300),
        Timing(1450, 1500),
        Timing(1650, 1700),
        Timing(1850, 1900),
        Timing(2050, 2100),
        Timing(2250, 2300),
        Timing(2600, math.inf)
    ],
    'mutalisk': [
        Timing(250, 800),
        Timing(900, 1200)
    ],
    'ultralisk': [
        Timing(450, math.inf)
    ],
    'roach': [
        Timing(350, 600),
        Timing(1000, math.inf)
    ],
    'hydralisk': [
        Timing(800, math.inf)
    ]
}

much_later_muta_timing = {
    'boom': [
        Timing(-1, 550),
        Timing(600, 775),
        Timing(800, 1000),
        Timing(1500, 1900),
        Timing(2000, math.inf)
    ],
    'rush': [
        Timing(450, 850),
        Timing(950, 1000),
        Timing(1250, 1300),
        Timing(1450, 1500),
        Timing(1650, 1700),
        Timing(1850, 1900),
        Timing(2050, 2100),
        Timing(2250, 2300),
        Timing(2600, math.inf)
    ],
    'mutalisk': [
        Timing(3000, math.inf)
    ],
    'ultralisk': [
        Timing(400, math.inf)
    ],
    'roach': [
        Timing(1000, math.inf)
    ],
    'hydralisk': [
        Timing(800, math.inf)
    ]
}

# one of the bests of those tested
early_roach_timing = {
    'boom': [
        Timing(-1, 375),
        Timing(550, 775),
        Timing(800, 1000),
        Timing(1500, 1900),
        Timing(2000, math.inf)
    ],
    'rush': [
        Timing(950, 1000),
        Timing(1250, 1300),
        Timing(1450, 1500),
        Timing(1650, 1700),
        Timing(1850, 1900),
        Timing(2050, 2100),
        Timing(2250, 2300),
        Timing(2600, math.inf)
    ],
    'mutalisk': [
        Timing(200, 800),
        Timing(900, 1200)
    ],
    'ultralisk': [
        Timing(400, math.inf)
    ],
    'roach': [
        Timing(200, 700),
        Timing(1000, math.inf)
    ],
    'hydralisk': [
        Timing(600, math.inf)
    ],
    'broodlord': [
        Timing(50, 200)
    ]
}

# doesn't seem to make many roaches, sits on tons of resources and then loses.
roach_hydra_all_the_way_timing = {
    'boom': [
        Timing(-1, 375),
        Timing(550, 775),
        Timing(800, 1000),
        Timing(1500, 1900),
        Timing(2000, math.inf)
    ],
    'rush': [
        Timing(450, 850),
        Timing(950, 1000),
        Timing(1250, 1300),
        Timing(1450, 1500),
        Timing(1650, 1700),
        Timing(1850, 1900),
        Timing(2050, 2100),
        Timing(2250, 2300),
        Timing(2600, math.inf)
    ],
    'mutalisk': [],
    'ultralisk': [],
    'roach': [
        Timing(200, 400),
        Timing(1000, math.inf)
    ],
    'hydralisk': [
        Timing(200, math.inf)
    ]
}

# doesn't really work out very well, army value lost gets really high
ling_muta_ultra_timing = {
    'boom': [
        Timing(-1, 350),
        Timing(500, 775),
        Timing(800, 1000),
        Timing(1500, 1900),
        Timing(2000, math.inf)
    ],
    'rush': [
        Timing(450, 850),
        Timing(950, 1000),
        Timing(1250, 1300),
        Timing(1450, 1500),
        Timing(1650, 1700),
        Timing(1850, 1900),
        Timing(2050, 2100),
        Timing(2250, 2300),
        Timing(2600, math.inf)
    ],
    'mutalisk': [
        Timing(-1, math.inf),
    ],
    'ultralisk': [
        Timing(-1, math.inf)
    ],
    'roach': [
    ],
    'hydralisk': [
    ]
}

all_timings = {
    # 'current': default_timings,
    # 'later_hydras': later_hydras,
    # 'much_later_muta': much_later_muta_timing,
    'early_roach': early_roach_timing,
    'ling_muta': ling_muta_ultra_timing,
    'roach_hydra': roach_hydra_all_the_way_timing
}


def test_bot(timings=default_timings, training_map=maps.get(all_map_names[1]), iterations=1, use_camera=True, should_show_plot=True, opponent_race=Race.Random, opponent_difficulty=Difficulty.Hard, show_debug=True):
    record = []
    for i in range(iterations):
        players = [
            Bot(Race.Zerg, BalancedZergBot(auto_camera=use_camera,
                                           should_show_plot=should_show_plot, show_debug=show_debug, timings=timings)),
            Computer(opponent_race, opponent_difficulty)
        ]
        replay_name = get_replay_name(players, training_map)
        result = run_game(training_map, players, realtime=False,
                          save_replay_as=replay_name)
        record.append(result)
        print('RESULT {}'.format(result))
        print(Colorizer.bg_green(Colorizer.black(record)))
    victory_count = sum(map(lambda x: x == Result.Victory, record))
    defeat_count = len(record) - victory_count
    return record, victory_count, defeat_count


if __name__ == '__main__':
    args = parser.parse_args()
    training_map = maps.get(all_map_names[2])
    iterations = args.iterations
    use_camera = not args.no_camera
    should_show_plot = not args.no_plots
    should_show_debug = not args.no_debug
    opponent_race = Race[all_races[args.race]]
    opponent_difficulty = Difficulty[all_difficulties[args.difficulty]]
    total_record = []
    for timing_name, timings in all_timings.items():
        record, victory_count, defeat_count = test_bot(timings=timings, training_map=training_map, iterations=iterations, use_camera=use_camera, should_show_plot=should_show_plot,
                                                       opponent_race=opponent_race, opponent_difficulty=opponent_difficulty, show_debug=should_show_debug)
        total_record.append({
            'record': record,
            'wins': victory_count,
            'losses': defeat_count,
            'timings': timings
        })
        with open('balanced_zerg_bot_record.txt', 'a') as f:
            f.write(',\n{}'.format(
                [record, victory_count, defeat_count, timings]))
    print(total_record)
    with open('balanced_zerg_bot_record_total.txt', 'a') as f:
        f.write('\n{}'.format(total_record))
