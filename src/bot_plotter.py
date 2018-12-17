import matplotlib.pyplot as plt
from typing import List, Tuple, Dict


class BotPlotter(object):
    def __init__(self, initial_plots: Dict[str, List[Tuple[Tuple, Dict]]]):
        plt.close('all')
        subplot_count = len(initial_plots)
        plt.style.use('ggplot')
        figure, axes = plt.subplots(subplot_count, sharex=True)
        self.axes = {}
        self.figure = figure
        for (key, plots), axis in zip(initial_plots.items(), axes):
            for args, kwargs in plots:
                self.axes[key] = axis
                axis.plot(*args, **kwargs)
            legend = axis.legend(
                loc='upper left', shadow=True, fontsize='large')
            legend.get_frame()

    def plot(self, key, *args, **kwargs):
        axis = self.axes.get(key)
        assert(axis is not None)
        axis.plot(*args, **kwargs)

    def show(self):
        plt.draw()
        plt.pause(0.0001)

    def save(self, filename):
        self.figure.savefig(filename)

    def reset(self):
        plt.close(self.figure)
