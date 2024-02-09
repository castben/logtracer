#!./system/bin/python

# MIT License
#
# Copyright (c) 2021 Eugenio Parodi <ceccopierangiolieugenio AT googlemail DOT com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys, os, argparse, math, random

sys.path.append(os.path.join(sys.path[0], '..'))
import TermTk as ttk
from TermTk.TTkCore.signal import pyTTkSlot

def main():
    global pb1
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help='Full Screen', action='store_true')
    args = parser.parse_args()

    ttk.TTkLog.use_default_file_logging()

    root = ttk.TTk()
    layout = ttk.TTkGridLayout(columnMinHeight=1)
    button_load = ttk.TTkButton(text="Load", parent=root)

    if args.f:
        rootW = root
        root.setLayout(layout)
    else:
        rootW = ttk.TTkWindow(
            parent=root,pos=(1,1), size=(55,9), border=True, layout=layout,
            title="Test Progressbar (resize me)")

    text_window = ttk.TTkWindow(parent=root, pos=(10, 10), size=(100, 20), layout=ttk.TTkGridLayout())
    text_content = ttk.TTkTextEdit(parent=text_window)

    rootW.layout().addWidget(pb1 := ttk.TTkFancyProgressBar(), row=0, col=0)
    # rootW.layout().addWidget(pb2 := ttk.TTkFancyProgressBar(textWidth=0), row=2, col=0)
    # rootW.layout().addWidget(pb3 := ttk.TTkFancyProgressBar(textWidth=6), row=4, col=0)

    def fade_green_red(value, minimum, maximum):
        red, green = round(value*255), round((1-value)*255)
        fg = f"#{red:02x}{green:02x}00"
        return ttk.TTkColor.fg(fg)

    # pb2.setStyle()_lookAndFeel().color = fade_green_red
    # pb3._lookAndFeel().text = lambda value, minimum, maximum: 'low' if value < 0.5 else 'high'

    timer = ttk.TTkTimer()

    @pyTTkSlot()
    def _timerEvent(current_line, lines):
        global pb1

        pb1 = ((current_line*100)/lines)/100

        # last_value = pb1.value()
        # pb.setValue(0 if last_value == 1 else last_value + 0.02)

        timer.start(0.2)

    @ttk.pyTTkSlot()
    def _loadFile(filename):
        global current_line
        lines = 0
        with open(filename, "r") as check_file:
            lines = len(check_file.read())

        current_line = 0

        text_content.textChanged.connect(lambda: _timerEvent(current_line, lines))
        with open(filename, "r") as load_file:
            for each_line in load_file:
                # line = load_file.readline()
                text_content.append(each_line)
                current_line += 1
                #timer.timeout.connect(lambda: _timerEvent(current_line, lines))
                timer.start(1)

    # timer.timeout.connect(_timerEvent)
    # timer.start(1)
    #_loadFile('sdx-25MB.log')
    button_load.clicked.connect(lambda: _loadFile('sdx-25MB.log'))
    root.mainloop()


if __name__ == "__main__":
    pb1 = None
    current_line = 0

    main()
