#!/usr/bin/python3

import argparse
import dbus
import enum
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
C_BLUE = (0, 0, 200)
C_GREEN = (200, 0, 0)
C_RED =  (0, 200, 0)

class Direction(enum.Enum):
    """Directions, as per pygame screen coordinates"""
    RIGHT = (1, 0)
    LEFT = (-1, 0)
    UP = (0, -1)
    DOWN = (0, 1)

# Size of the Moonboard
N_ROWS = 18
N_COLUMNS = 11

class Layout:
    """
    A Layout defines the pattern in which LEDs were wired into the Moonboard

    This can be used to convert from hold name, e.g. 'C12' to LED number
    or from hold name to coordinate, start at 0,0 in the top-left of the grid
    """
    def __init__(self, start_hold: str, direction: Direction):
        """
        Generate a layout for LED string starting from `start_hold` and
        moving in `direction`.
        """
        # grid is a mapping from (x, y) -> pixel number
        # NOTE: this is transposed from the usual Numpy row,col ordering
        self.grid = np.ndarray((N_COLUMNS, N_ROWS), np.int32)
        self.grid.fill(-1)
        n_leds = N_ROWS * N_COLUMNS
        x, y = self.hold_to_coordinate(start_hold)
        i = 0
        while i < n_leds:
            self.grid[x ,y] = i
            i += 1
            x += direction.value[0]
            y += direction.value[1]

            if x < 0 or x >= N_COLUMNS:
                if x < 0:
                    direction = Direction.RIGHT
                    x = 0
                else:
                    direction = Direction.LEFT
                    x = N_COLUMNS - 1
                if y == 0  or self.grid[x, y-1] != -1:
                    y += 1
                else:
                    y -= 1        
            elif y < 0 or y >= N_ROWS:
                if y < 0:
                    direction = Direction.DOWN
                    y = 0
                else:
                    direction = Direction.UP
                    y = N_ROWS - 1
                if x == 0  or self.grid[x-1, y] != -1:
                    x += 1
                else:
                    x -= 1
        assert not (self.grid == -1).any()

    def hold_to_coordinate(self, hold: str) -> Tuple[int, int]:
        """
        Convert a `hold` name to a screen coordinate which starts
        at (0,0) in the top-left corner and is listed (x, y) with `x`
        being the horizontal axis. 
        
        For example, A18 -> (0,0)
                     B16 -> (1,2)
        """
        assert len(hold) in (2,3)
        x = ord(hold[0])-ord('A')
        y = N_ROWS - int(hold[1:])
        assert 0 <= x < N_COLUMNS
        assert 0 <= y < N_ROWS
        return (x,y)

    def coordinate_to_pixel(self, x: int, y:int) -> int:
        """
        Convert a screen coordinate into a LED pixel according
        to the layout.
        """
        assert 0 <= x < N_COLUMNS
        assert 0 <= y < N_ROWS
        return self.grid[x, y]

    def hold_to_pixel(self, hold: str) -> int:
        """
        Convert a hold name (eg A12) to pixel index (0->197)
        """
        return self.coordinate_to_pixel(*self.hold_to_coordinate(hold))


class DisplayGrid:
    def __init__(self):
        """
        Initialize grid display

        # TODO: implement back-end of either Neopixels or pygame
        """
        # NOTE: unusually I've only got 198 pixels instead of a round 200
        self.n_pixels = 198
        # My LED layout starts bottom-right and zigzags up/down from there
        self.layout = Layout('K1', Direction.UP)
        
        # Grid is in coordinates (0,0) being top-left, with (x,y) as the indexing
        self.grid = np.ndarray((N_COLUMNS, N_ROWS), dtype=object)
        self.grid.fill(C_BLACK)
        # Pixels, with indexing looked up via 'self.lookup'
        self.pixels = neopixel.NeoPixel(board.D18, self.n_pixels, auto_write=False)

    def set(self, *, x: int=None, y: int=None, hold: str=None, colour: Tuple[int, int, int]):
        """
        Set pixel at `x`,`y` or `hold` to `colour`
        """
        assert (x is None and y is None and hold is not None) or (x is not None and y is not None and hold is None), 'specify either x,y or hold'
        if hold is not None:
            x, y = self.layout.hold_to_coordinate(hold)   
        self.grid[x,y] = colour

    def show(self):
        for x in range(self.grid.shape[0]):
            for y in range(self.grid.shape[1]):
                colour = self.grid[x, y]
                i = self.layout.coordinate_to_pixel(x, y)
                self.pixels[i] = colour
        self.pixels.show()
    
    def clear(self):
        self.grid.fill(C_BLACK)
    

class App:
    def __init__(self, logger):
        self.logger = logger
        self.display = DisplayGrid()

    def new_problem(self, holds_string):
        holds = json.loads(holds_string)
        self.logger.debug("new_problem: ", json.dumps(holds_string))
        print(holds_string)
        self.display.clear()
        for hold in holds['START']:
            self.display.set(hold=hold, colour=C_GREEN)
        for hold in holds['MOVES']:
            self.display.set(hold=hold, colour=C_BLUE)
        for hold in holds['TOP']:
            self.display.set(hold=hold, colour=C_RED)   
        self.display.show()

        
def main():

    parser = argparse.ArgumentParser(description="")

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