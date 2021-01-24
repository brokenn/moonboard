#!/usr/bin/python3

import argparse
import dbus
import json
import logging
import neopixel
import numpy as np
import sys

from dbus.mainloop.glib import DBusGMainLoop
from functools import partial
from gi.repository import GLib
from typing import Tuple, Union


import neopixel
import board

logger = logging.getLogger('moonboard')

C_BLACK = (0, 0, 0)
C_BLUE = (0, 0, 255)
C_GREEN = (255, 0, 0)
C_RED =  (0, 255, 0)


class DisplayGrid:
    def __init__(self, n_rows: int=18, n_columns: int=11):
        """
        Initialize grid display with `n_rows` and `n_columns` size


        Coordinates are from (0,0) in the bottom-left,
        incrementing upwards-rightwards
        
        Columns can also be referred to using characters 'A'->...

        """
        self.n_pixels = 200
        self.n_rows = n_rows
        self.n_columns = n_columns
        # Grid represents the full display
        self.grid = np.ndarray((n_rows, n_columns), dtype=object)
        self.grid.fill(C_BLACK)
        # Driver, which can be accessed similar to the grid
        self.pixels = neopixel.NeoPixel(board.D18, self.n_pixels, auto_write=False)

    def set(self, row: int, column: Union[str, int], colour: Tuple[int, int, int]):
        """
        Set pixel at `row`,`column` to `colour`
        """
        if isinstance(column, str):
            assert len(column)==1
            column = ord(upper(column)) - ord('A')
        assert row < self.n_rows
        assert column < self.n_columns
        self.grid[row, column] = colour

    def show(self):
        for i in range(self.n_rows):
            for j in range(self.n_columns):
                colour = self.grid[i, j]
                self.pixels[i*self.n_columns + j] = colour
        self.pixels.show()
    
    def clear(self):
        self.grid.fill(C_BLACK)
    

class App:
    def __init__(self, logger):
        self.logger = logger
        self.display = DisplayGrid(n_rows=18, n_columns=11)

    def name_to_coord(self, name):
        """Turn a hold name such as B12 into row, column.
        
        .. warning:: Coordinates are zero-based, so B8 becomes (7, 1)
        """
        assert len(name) in (2, 3)
        col = ord(name[0]) - ord('A')
        row = int(name[1:]) - 1
        return row, col

    def new_problem(self, holds_string):
        holds = json.loads(holds_string)
        self.logger.debug("new_problem: ", json.dumps(holds_string))
        print(holds_string)
        self.display.clear()
        for hold in holds['START']:
            row, col = self.name_to_coord(hold)
            self.display.set(row, col, C_GREEN)
        for hold in holds['MOVES']:
            row, col = self.name_to_coord(hold)
            self.display.set(row, col, C_BLUE)
        for hold in holds['TOP']:
            row, col = self.name_to_coord(hold)
            self.display.set(row, col, C_RED)   
        self.display.show()

        
def main():

    parser = argparse.ArgumentParser(description="")

    parser.add_argument("--brightness", default=100, type=int)

    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Create the app
    app = App(logger)


    # connect to dbus signal new problem
    dbml = DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()
    proxy = bus.get_object("com.moonboard", "/com/moonboard")

    proxy.connect_to_signal("new_problem", app.new_problem)

    loop = GLib.MainLoop()

    dbus.set_default_main_loop(dbml)

    # Run the loop
    try:
        loop.run()
    except KeyboardInterrupt:
        print("keyboard interrupt received")
    except Exception as e:
        print("Unexpected exception occurred: '{}'".format(str(e)))
    finally:
        loop.quit()
        app.display.clear()
        app.display.show()


if __name__ == "__main__":
    main()