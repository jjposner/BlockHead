#!/usr/bin/env python
# BlockHead.py -- visual calculator for addition and subtraction of whole numbers
# Copyright 2008, 2009 John Posner

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
visual calculator, for adding or subtracting two multiple-digit numbers,
base-10 or another number base < 10
"""

import os
import sys
from time import sleep
import Tkinter as T

__date__ = '26-Jun-2009'
__version__ = 1127

class G():
    """
    global variables
    """
    # debug flag
    DEBUG = True

    # show texts?
    HELP_WINDOW = None
    HELP_ENABLE = True
    SPLASH_ENABLE = False

    # configure for 800x600 display screen, required for ShowMeDo videos
    ShowMeDo_800_600 = False
    SHOWMEDO_GEOM = (760, 520, 20, 20)

    # number of columns
    COL_COUNT = 3

    # number base
    BASE = 10
    VALID_DIGITS = map(str, range(BASE))

    ### sizes

    # block width
    BLOCK_WID = 30
    # padding between block and column edge
    BLOCK_PAD = 10
    # height of one unit
    UNIT_HGT = BLOCK_WID
    # column width (make the columns contiguous)
    COL_WID = BLOCK_WID + 2*BLOCK_PAD
    # column height
    COL_HGT = BASE * UNIT_HGT
    # distance between bottom of column and carry/borrow arrow
    ARROW_OFFSET = 16
    # distance between carry/borrow arrow and digit
    ANSR_OFFSET = ARROW_OFFSET + 25
    # height adjustment for control panel, to ensure display of carry/borrow blocks
    WINDOW_HGT_ADJ = 160

    # operation modes
    ADD_MODE = 1
    SUB_MODE = 2

    # fonts
    if os.name == 'nt':
        FONTNAME = 'verdana'
    else:
        FONTNAME = 'helvetica'

    if ShowMeDo_800_600:
        FONT = (FONTNAME, 8, 'bold')
        SPLASHFONT = (FONTNAME, 12, 'bold')
    else:
        FONT = (FONTNAME, 10, 'bold')
        SPLASHFONT = (FONTNAME, 14, 'bold')

    # colors

    HELP_BG_COLOR = '#DDDAFA'
    CANV_BG_COLOR = '#D8D8D8'
    INPT_COLOR = '#00FF00'
    ANSW_COLOR = '#00CCFF'
    SUBTRACT_COLOR = '#CCCCCC'
    CAN_DROP_COLOR = '#00FF00'
    CANNOT_DROP_COLOR = '#222222'

    # colors repeat every N columns
    COL_COLORS = ['#A6E2F4', '#FFD5D7', '#D3FFD3', '#FEEDB1',
                  '#A6E2F4', '#FFD5D7', '#D3FFD3', '#FEEDB1',
                  ]
    assert(len(COL_COLORS) >= COL_COUNT)
    # get rid of unneeded column colors
    del COL_COLORS[COL_COUNT:]
    # gray column for final carry
    COL_COLORS.append('#e8e8e8')

    BLOCK_COLORS = ['#3280EA', '#E35BA0', '#6FD48A', '#F2BC02',
                    '#3280EA', '#E35BA0', '#6FD48A', '#F2BC02',
                    ]
    # get rid of unneeded block colors
    del BLOCK_COLORS[COL_COUNT:]
    # add gray color for block created by final carry
    BLOCK_COLORS.append('#C0C0C0')

    # texts and strings

    BLOCK_SUFFIX = "_blk"
    ANSW_COL_PREFIX = "nA"
    BORROW_ARROW_SUFFIX = "_borrow_arrow"

    # strings whose widths are computed at runtime
    DISPLAY_STR = {
        'first': "First Number",
        'second': "Second Number",
        'larger': "Larger Number",
        'smaller': "Smaller Number",
        'answer': "Answer",
    }

###
### non-constant globals
###

# registries of columns and blocks
# each is a dictionary, with Canvas tags as keys
Columns = {}
Blocks = {}

# block selections and movements
MouseLastX = MouseLastY = MouseStartX = MouseStartY = CarryCount = 0
SelectedBlockTag = DropOk = AnswerColTag = None
# list to be populated by Number.InitBlocks(), Column.Add(), and DrawBorrowButtons()
SelectableBlockTags = []

# Number objects: two inputs and "A"nswer
Num1 = Num2 = NumA = None

####################
#################### classes
####################

class HelpWindow(T.Toplevel):
    """
    window to display help text for ADD mode or SUB mode
    """
    # help texts
    HELP_ADD = """
ADD TWO NUMBERS

Enter two numbers to be added, then click "Draw Blocks".

Drag each of the blocks you've drawn to the corresponding
(same-color) answer column.

If an answer column's total is 10 or more, click the
"carry" arrow that appears below the answer column.

Click the "+" operator between the numbers to change
it to "-".

"""

    HELP_SUB = """
SUBTRACT TWO NUMBERS

Enter the larger and smaller numbers, then click
"Draw Blocks".

Drag the blocks for the smaller number to the
corresponding columns of the larger number.

In the larger number, you may need to click one
or more "borrow" arrows -- they appear below columns
whose blocks are too short to subtract from.

Click the "-" operator between the numbers to change
it to "+".

"""

    def __init__(self):
        T.Toplevel.__init__(self)
        self.canv = T.Canvas(self, bg=G.HELP_BG_COLOR)
        self.canv.pack(expand=True, fill=T.BOTH)
        self.help_id = None
        self.title("BlockHead Help")
        self.transient(RootWin)
        self.wm_protocol("WM_DELETE_WINDOW", self.Cleanup)

    def Update(self):
        """
        get rid of old text, display new text
        """
        if self.help_id:
            self.canv.delete(self.help_id)

        help_text = self.HELP_ADD if Mode.get() == G.ADD_MODE else self.HELP_SUB
        self.help_id = self.canv.create_text(0, 0, font=G.FONT, text=help_text, justify=T.LEFT)
        xlow, ylow, xhigh, yhigh = self.canv.bbox(self.help_id)
        self.canv.move(self.help_id, -xlow+10, -ylow+10)
        self.geometry("%dx%d" % (xhigh-xlow+20, yhigh-ylow+20))
        self.lift()

    def Cleanup(self):
        G.HELP_WINDOW = None
        self.destroy()

class BlockHeadCanvas(T.Canvas):
    """
    canvas for BlockHead application: columns and blocks
    """
    def __init__(self, master):
        T.Canvas.__init__(self, master)

        self['bg'] = G.CANV_BG_COLOR

        # set up mouse bindings
        #self.bind('<Button-1>', MouseDown)
        #self.bind('<Button1-Motion>', MouseMotion)
        #self.bind('<Button1-ButtonRelease>', MouseUp)

class BlockHeadControlPanel(T.Frame):
    """
    control panel for BlockHead application
    """
    def __init__(self, master):
        T.Frame.__init__(self, master)

        self.option_add("*Entry*width", G.COL_COUNT+2)
        self.option_add("*Button*borderWidth", 2)

        # variables for entry fields
        self.number_1 = T.StringVar()
        self.number_2 = T.StringVar()

        # initial values, to prevent chicken-and-egg with InitializeMode()
        self.label_1_text = self.label_2_text = "?"
        self.signbtn_bitmap = "@plus.xbm"

        # GRID subframe containing numbers, their labels, and operators
        numbers_frm = T.Frame(self)
        numbers_frm.pack(side=T.LEFT, expand=True, fill=T.X)

        self.numbers_grid = T.Frame(numbers_frm)
        self.numbers_grid.pack(anchor=T.CENTER)

        # grid column names
        (g_spacer_0, g_first, g_spacer_1, g_sign, g_spacer_2, g_second, g_spacer_3,
            g_equals, g_spacer_4, g_answer, g_spacer_5) = range(11)

        # spacer
        self.spacer_0 = T.Frame(self.numbers_grid, width=50)
        self.spacer_0.grid(row=0, column=g_spacer_0)

        # first number
        self.entry_1 = T.Entry(self.numbers_grid, justify=T.CENTER, textvariable=self.number_1)
        self.label_1 = T.Label(self.numbers_grid, text=self.label_1_text)
        self.entry_1.grid(row=0, column=g_first)
        self.label_1.grid(row=1, column=g_first)

        # spacer
        self.spacer_1 = T.Frame(self.numbers_grid, width=50)
        self.spacer_1.grid(row=0, column=g_spacer_1)

        # sign (+ or -)
        self.signbtn = T.Button(self.numbers_grid, bitmap=self.signbtn_bitmap, command=ChangeSign)
        self.signbtn.grid(row=0, column=g_sign)

        # spacer
        self.spacer_2 = T.Frame(self.numbers_grid, width=50)
        self.spacer_2.grid(row=0, column=g_spacer_2)

        # second number
        self.entry_2 = T.Entry(self.numbers_grid, justify=T.CENTER, textvariable=self.number_2)
        self.label_2 = T.Label(self.numbers_grid, text=self.label_2_text)
        self.entry_2.grid(row=0, column=g_second)
        self.label_2.grid(row=1, column=g_second)

        # spacer
        self.spacer_3 = T.Frame(self.numbers_grid, width=50)
        self.spacer_3.grid(row=0, column=g_spacer_3)

        # equals
        T.Label(self.numbers_grid, text="=", width=1, font=(G.FONTNAME, 20, 'bold')).grid(row=0, column=g_equals)

        # spacer
        self.spacer_4 = T.Frame(self.numbers_grid, width=50)
        self.spacer_4.grid(row=0, column=g_spacer_4)

        # answer
        # use standard width for Entry, not Label
        self.answ = T.Label(self.numbers_grid, justify=T.CENTER, width=G.COL_COUNT+2, text="")
        self.answ.grid(row=0, column=g_answer)
        T.Label(self.numbers_grid, text=G.DISPLAY_STR["answer"]).grid(row=1, column=g_answer)

        # spacer
        self.spacer_5 = T.Frame(self.numbers_grid, width=50)
        self.spacer_5.grid(row=0, column=g_spacer_5)

        ##
        ## PACK subframe containing control buttons
        ##
        btns_frm = T.Frame(self)
        btns_frm.pack(side=T.RIGHT, padx=8)

        self.drawbtn = T.Button(btns_frm, text="Draw Blocks", command=DrawBlocks)
        self.drawbtn.pack(side=T.LEFT, padx=9)
        T.Button(btns_frm, text="New" , command=NewCmd).pack(side=T.LEFT)
        if G.HELP_ENABLE:
            T.Button(btns_frm, text="Help", command=HelpCmd).pack(side=T.LEFT)
        T.Button(btns_frm, text="Exit", command=ExitCmd).pack(side=T.LEFT)

        # initialize control panel

        self.number_1.set("")
        self.number_2.set("")
        self.entry_1.bind('<KeyRelease>', ValidateKey)
        self.entry_2.bind('<KeyRelease>', ValidateKey)
        self.answ['bg'] = G.CANV_BG_COLOR
        self.entry_1['bg'] = G.INPT_COLOR
        self.entry_2['bg'] = G.INPT_COLOR


class Number(object):
    """
    one number, to be added or subtracted
    (or the answer number)
    """
    def __init__(self, id, digits, x, y):
        self.id = id
        self.digits = digits # STRING, not INT
        # X-coordinate of center of column-set
        self.center_x = x
        # Y-coordinate of bottom of column-set
        self.base_y = y
        self.columns = None

    def InitColumns(self, count):
        """
        create Column objects in self.columns list
        determine the X-coord of each Column object
        call Draw() to draw the columns
        """
        # all X-coordinates are offsets from the middle column's position

        if count % 2 == 1:
            # odd number of columns
            middle_idx = count // 2 # which is the middle column?
            offset = -G.COL_WID / 2 # middle column does not start at center of column-set
        else:
            # even number of columns
            middle_idx = count / 2 - 1
            offset = 0 # middle column DOES start at center of column-set

        # create columns
        self.columns = [Column(i) for i in range(count)]

        # configure column locations, register column in global list
        for (idx, col) in enumerate(self.columns):
            col.x = self.center_x + (middle_idx - idx) * G.COL_WID + offset
            col.y = self.base_y
            col.tag = "%s_col_%d" % (self.id, idx)

            Columns[col.tag] = col

        # draw the columns
        for col in self.columns:
            col.Draw()

    def InitBlocks(self):
        """
        create Block objects in each Column of self.columns list,
        using self.digits
        """
        #global SelectableBlockTags
        assert(len(self.columns) == len(self.digits))

        # convert STRING to list of INTs
        digit_list = map(int, list(self.digits))
        # we will process digits starting at the ONES column
        digit_list.reverse()

        # draw a block in each column
        for (idx, col) in enumerate(self.columns):
            # block tag is extension of column tag
            tag = col.tag + G.BLOCK_SUFFIX

            # block size is corresponding digit in digit_list
            val = digit_list[idx]

            # nothing to do if size is ZERO
            if val == 0:
                continue

            # create block, place it in column, and draw it
            blk = Block(val, idx, tag)
            col.Add(blk)
            
            # enable mouse interaction with block,
            # unless it's answer column in SUB mode
            if G.ANSW_COL_PREFIX not in col.tag:
                Canv.tag_bind(tag, '<Button-1>', MouseDown)
                Canv.tag_bind(tag, '<Button1-Motion>', MouseMotion)
                Canv.tag_bind(tag, '<Button1-ButtonRelease>', MouseUp)            

            # make this block selectable, unless it's answer column in SUB mode
            # NOTE: InitBlocks() for answer column is invoked only in SUB mode
            #if G.ANSW_COL_PREFIX not in col.tag:
                #SelectableBlockTags.append(tag)

class Column():
    """
    represents one column (ones, tens, hundreds)
    """
    def __init__(self, index):
        """
        initialize a column, either input or answer
        """
        self.id = None # set by self.Draw()
        self.color = G.COL_COLORS[index]

        # these will be set by Number.InitColumns()
        self.tag = None
        self.x = None # (x,y) is lower left corner of column rectangle
        self.y = None

        # list of Block objects in this column
        self.blocks = []

        # carry button id will be created by Add()
        self.carryarrow = None

    def Draw(self):
        """
        draw a column, starting at lower left corner (x,y)
        """
        self.id = Canv.create_rectangle(self.x, self.y,
                                   self.x+G.COL_WID, self.y-G.COL_HGT,
                                   tags=self.tag,
                                   outline=self.color, fill=self.color)

    def ColumnToRight(self):
        """
        return Column to right of this column
        """
        # "subtract 1" from final character of column tag
        new_index = int(self.tag[-1]) - 1
        return Columns[self.tag[:-1] + str(new_index)]

    def ColumnToLeft(self):
        """
        return Column to left of this column
        """
        # "add 1" to final character of column tag
        new_index = int(self.tag[-1]) + 1
        return Columns[self.tag[:-1] + str(new_index)]

    def DrawBlk(self, blk, offset=0):
        """
        draw a block in this Column
        """
        # no block to draw for zero value
        if blk.value == 0:
            return

        startx = self.x + G.BLOCK_PAD
        height = blk.value * G.UNIT_HGT

        # might need to draw this block on top of others
        hgt_offset = offset * G.UNIT_HGT

        # create Tkinter rectangle item for block
        # note: Y-axis is reversed!
        blk.id = Canv.create_rectangle(startx, self.y-hgt_offset,
                                       startx+G.BLOCK_WID, self.y-hgt_offset - height,
                                       fill=blk.color, tags=blk.tag)

        # save location of rectangle item, for "snap back" in cancelled move operation
        blk.startloc = Canv.coords(blk.id)

        # create horizontal lines to show individual units
        for i in range(1, blk.value):
            line_y = self.y - (i * G.UNIT_HGT) - hgt_offset
            Canv.create_line(startx, line_y,
                             startx + G.BLOCK_WID, line_y,
                             fill='black', tags=blk.tag)

    def Add(self, blk, carry_button_suppress=False):
        """
        send a block to this column
        """
        # carry_button_suppress is needed when creating a G.BASE-size ("filled") block
        # during execution of Carry() method

        global CarryCount

        # save current column total, before adding new block
        old_total = self.Total()

        self.blocks.append(blk)
        self.DrawBlk(blk, old_total)

        # update numeric value display
        self.ShowValue(self.Total())

        # maybe we're done
        if Mode.get() == G.SUB_MODE or blk.value == 0:
            return

        # maybe: display carry arrow
        carrytag = self.tag + "_carry_arrow"
        if self.Total() >= G.BASE and not carry_button_suppress and not Canv.find_withtag(carrytag):
            startx, starty = LowerLeft(self.id)
            self.carryarrow = Canv.create_image(startx, starty+G.ARROW_OFFSET,
                                                image=LEFT_ARROW, tags=carrytag)
            DbgPrint("Created carry arrow: %d, %s" % (self.carryarrow, carrytag))

            # activate the carry arrow
            Canv.tag_bind(carrytag, "<Button-1>", self.Carry)
            CarryCount += 1

    def ShowValue(self, value=None):
        """
        display a block's value below this column
        """
        if value is None:
            value = self.Total()

        texttag = self.tag + "_text"

        # delete previous value, if necessary
        Canv.delete(texttag)

        # convert value to string, using G.BASE

        # special case: ERASE
        if value == -1:
            strval = ""
        # single digit
        elif value < G.BASE:
            strval = str(value)
        # two digits
        else:
            digit_list = map(str, list(divmod(value, G.BASE)))
            strval = "".join(digit_list)

        # create new text item
        Canv.create_text(self.x + G.COL_WID/2, self.y+G.ANSR_OFFSET,
                         tag = texttag, text=strval, font=G.FONT, justify=T.CENTER)

    def Total(self):
        """
        total of column's blocks
        """
        values = [blk.value for blk in self.blocks]
        return sum(values)

    def Carry(self, event):
        """
        calculate carry for specified column
        btn = ID of dynamically-created carry button, to be deleted
        """
        global CarryCount

        # make sure that MouseXXX() routines don't get invoked
        SelectedBlockTag = None

        # index of this column
        column_index = int(self.tag[-1])
        # carry destination column
        destcol = self.ColumnToLeft()

        # delete carry arrow
        Canv.tag_unbind(self.carryarrow, "<Button-1>")
        Canv.delete(self.carryarrow)
        CarryCount -= 1

        # save total value of blocks, for creation of new blocks
        total = self.Total()

        # create some block tags, specific to this column
        filledblk_tag = self.tag + "_filled_xformblock"
        excessblk_tag = self.tag + "_excess_xformblock"
        carry_newblk_tag = self.tag + "_carry_xformblock"
        carry_newblk_sep_tag = self.tag + "_carry_xformblock_line"

        # clear out all the blocks in this column
        for blk in self.blocks:
            Canv.delete(blk.tag)
        self.blocks = []

        # block of G.BASE units
        Block(G.BASE, column_index, filledblk_tag)
        self.Add(Blocks[filledblk_tag], True)

        # "excess" block (1+ units)
        if total > G.BASE:
            excess = total - G.BASE
            Block(excess, column_index, excessblk_tag)
            self.Add(Blocks[excessblk_tag], True)

        sleep(0.25)

        # transform G.BASE units into 1 unit of the next column
        startx, starty = UpperLeft(filledblk_tag)

        Canv.lift(filledblk_tag)

        # scale carry block vertically from G.BASE units to 1 unit,
        # while gradually migrating start color (s) toward end color (e),
        s = HexString2List(G.BLOCK_COLORS[column_index])
        e = HexString2List(G.BLOCK_COLORS[column_index+1])

        count = 20
        for i in range(count):
            sleep(1.0/count)
            color = '#'
            for n in range(3):
                level = s[n] + i*((e[n] - s[n])/count)
                # make sure roundoff error doesn't take us out-of-bounds
                if level > 255: level = 255
                if level < 0: level = 0
                color += '%02x' % level

            Canv.itemconfig(filledblk_tag, fill=color)
            Canv.scale(filledblk_tag, startx, starty, 1.0, (1.0/G.BASE) ** (1.0/count))
            Canv.update()
        sleep(0.25)

        # move the shrunken blocks to the next column
        startx, starty, = LowerLeft(filledblk_tag)
        endx = Canv.coords(destcol.tag)[0]+G.BLOCK_PAD
        endy = self.y - destcol.Total()*G.UNIT_HGT

        count = 20
        for i in range(count):
            Canv.move(filledblk_tag, (endx-startx)/count, (endy-starty)/count)
            Canv.update()
            sleep(1.0/count)

        # replace shrunken G.BASE-unit block with 1-unit "carry block"
        # NOTE: "+1" makes the carry block use the color of the "TO" column
        Canv.delete(filledblk_tag)
        Block(1, column_index+1, carry_newblk_tag)

        destcol.Add(Blocks[carry_newblk_tag])

        # delete the block from this column, and update column total
        del self.blocks[0]
        self.ShowValue()

        # did we create an "excess" block? if so, drop it down
        if total > G.BASE:
            sleep(0.25)
            count = 20
            for i in range(count):
                sleep(1.0/count)
                Canv.move(excessblk_tag, 0, 1.0*G.BASE*G.UNIT_HGT/count)
                Canv.update()

        # are we done?
        CalcAnswer()

        # do not propagate event
        return "break"

    def Borrow(self,event):
        """
        borrow 1 unit from this column:
        send G.BASE units to the column to the right
        """
        # make sure that MouseXXX() routines don't get invoked
        SelectedBlockTag = None

        # can we borrow from this column?
        # if not, first borrow from column to the left
        if self.Total() == 0:
            self.ColumnToLeft().Borrow(event)
            Canv.update()
            sleep(0.5)

        # decompose last block in this column (ex: 8 --> 7+1)
        borrow_blk = self.blocks[-1]
        borrow_tag = borrow_blk.tag
        borrow_val = borrow_blk.value

        # block and separator lines have different tags, because we will
        # morph the block color but not the separator-line color
        borrow_newblk_tag = borrow_tag + "_borrow_xformblock"
        borrow_newblk_sep_tag = borrow_tag + "_borrow_xformblock_line"

        # delete the topmost block from this column
        Canv.delete(borrow_tag)
        del self.blocks[-1]
        # delete the borrow arrow
        Canv.delete(self.tag + G.BORROW_ARROW_SUFFIX)

        column_index = int(self.tag[-1])

        # 1. create block of size N-1, to be left behind in this column
        if borrow_val > 1:
            self.Add( Block(borrow_val-1, column_index, borrow_tag) )

        # 2. create block of size 1, which will get borrowed
        self.Add( Block(1, column_index, borrow_newblk_tag) )

        # insert separator lines
        startx, starty = LowerLeft(borrow_newblk_tag)
        for i in range(1,G.BASE):
            line_y = starty - (1.0 * i * G.UNIT_HGT / G.BASE)
            Canv.create_line(startx, line_y,
                             startx + G.BLOCK_WID, line_y,
                             fill='black', tags=borrow_newblk_sep_tag)
        Canv.update()

        # scale borrow block vertically from 1 unit to G.BASE units,
        # while gradually migrating start color (s) toward end color (e),
        s = HexString2List(G.BLOCK_COLORS[column_index])
        e = HexString2List(G.BLOCK_COLORS[column_index-1])

        count = 20
        for i in range(count):
            sleep(1.0/count)
            color = '#'
            for n in range(3):
                level = s[n] + i*((e[n] - s[n])/count)
                # make sure roundoff error doesn't take us out-of-bounds
                if level > 255: level = 255
                if level < 0: level = 0
                color += '%02x' % level

            Canv.itemconfig(borrow_newblk_tag, fill=color)
            for tag in (borrow_newblk_tag, borrow_newblk_sep_tag):
                Canv.scale(tag, startx, starty, 1.0, (1.0*G.BASE) ** (1.0/count))
            Canv.update()

        sleep(0.25)

        # move the scaled borrow block to the next column
        destcol = self.ColumnToRight()

        if destcol.blocks:
            # there's a block in the dest column
            tgtblk = destcol.blocks[-1]
            endx, endy = UpperLeft(tgtblk.tag)
        else:
            # dest column is empty
            endx = Canv.coords(destcol.tag)[0] + G.BLOCK_PAD
            endy = self.y

        count = 20
        for i in range(count):
            for tag in (borrow_newblk_tag, borrow_newblk_sep_tag):
                Canv.move(tag, (endx-startx)/count, (endy-starty)/count)
            Canv.update()
            sleep(1.0/count)

        # remove the borrow block from this column
        del self.blocks[-1]
        self.ShowValue()

        # destination column: replace stretched block (value=1) with new block (value=G.BASE)
        for tag in (borrow_newblk_tag, borrow_newblk_sep_tag):
            Canv.delete(tag)
        destcol.Add( Block(G.BASE, column_index-1, destcol.tag + "_borrowto") )

        # recalc the borrow buttons
        DrawBorrowButtons()

        # do not propagate event
        return "break"

class Block(object):
    """
    represents one digit of a multiple-digit number
    """
    def __init__(self, value, index, tag):
        self.value = value
        self.color = G.BLOCK_COLORS[index]
        self.tag = tag

        # id of Canvas item; will be set to integer ID by Canvas create_rectangle()
        self.id = None

        # register the block in the global list
        Blocks[self.tag] = self

        # will be filled in by Column's Draw()
        self.startloc = None

####################
#################### functions
####################

def MouseDown(event):
    """
    set AnswerColTag = tag of one column, based on which block was selected
    """
    global MouseLastX, MouseLastY, MouseStartX, MouseStartY, SelectedBlockTag, AnswerColTag, DropOk

    MouseLastX = MouseStartX = Canv.canvasx(event.x)
    MouseLastY = MouseStartY = Canv.canvasy(event.y)

    SelectedBlockTag = None

    # identify selected block, if any
    closest_item_id = Canv.find_closest(MouseStartX, MouseStartY)
    if not closest_item_id:
        return "break"

    try:
        closest_item_tag = Canv.gettags(closest_item_id)[0]
    except IndexError:
        DbgPrint("Could not determine tag of item with id '%d'" % closest_item_id)
        return "break"

    DbgPrint("Closest:", closest_item_id, closest_item_tag)

    # close is not enough -- did we actually click on a selectable block?
    leftx, topy, rightx, boty = Canv.bbox(closest_item_tag)

    if not (leftx <= MouseLastX <= rightx and topy <= MouseLastY <= boty):
        DbgPrint(" ... clicked close to item '%s', but not within a selectable block" % closest_item_tag)
        return "break"

    # we found a selectable block!
    SelectedBlockTag = closest_item_tag
    AnswerColTag = AnswerColumnTag(SelectedBlockTag)
    Canv.lift(SelectedBlockTag)

    # do not propagate event
    return "break"

def MouseMotion(event):
    """
    move a block, and determine whether it can be dropped
    """
    global MouseLastX, MouseLastY, MouseStartX, MouseStartY, SelectedBlockTag, AnswerColTag, DropOk

    if not SelectedBlockTag:
        return "break"

    cx = Canv.canvasx(event.x)
    cy = Canv.canvasy(event.y)
    Canv.move(SelectedBlockTag, cx-MouseLastX, cy-MouseLastY)
    MouseLastX = cx
    MouseLastY = cy

    if InAnswerColumn():
        if Mode.get() == G.ADD_MODE:
            Canv.itemconfig(AnswerColTag, outline=G.CAN_DROP_COLOR, fill=G.CAN_DROP_COLOR)
            DropOk = True
        elif Mode.get() == G.SUB_MODE:
            if Blocks[SelectedBlockTag].value <= Columns[AnswerColTag].Total():
                # can subtract now, without borrowing
                Canv.itemconfig(AnswerColTag, outline=G.CAN_DROP_COLOR, fill=G.CAN_DROP_COLOR)
                DropOk = True
            else:
                # cannot subtract now, need to borrow
                Canv.itemconfig(AnswerColTag, outline=G.CANNOT_DROP_COLOR, fill=G.CANNOT_DROP_COLOR)
                DropOk = False
    else:
        # reset target column background
        clr = Columns[AnswerColTag].color
        Canv.itemconfig(AnswerColTag, outline=clr, fill=clr)
        DropOk = False

def MouseUp(event):
    """
    dispatch a mouse-up event, depending on the ADD/SUB mode
    """
    global MouseLastX, MouseLastY, SelectedBlockTag

    if not SelectedBlockTag:
        return "break"

    DbgPrint("SelectedBlockTag:", SelectedBlockTag)

    # update global vars
    MouseLastX = Canv.canvasx(event.x)
    MouseLastY = Canv.canvasy(event.y)

    # dispatch ADD/SUB
    if Mode.get() == G.ADD_MODE:
        MouseUp_Add(event)
    elif Mode.get() == G.SUB_MODE:
        MouseUp_Sub(event)

    SelectedBlockTag = None
    CalcAnswer()

    # do not propagate event
    return "break"

def MouseUp_Sub(event):
    """
    handle a mouse-up event in SUB mode
    """
    global MouseLastX, MouseLastY, MouseStartX, MouseStartY, SelectedBlockTag, AnswerColTag, DropOk

    # Answer column was determined during MouseDown event
    tgtcol = Columns[AnswerColTag]

    if DropOk:
        # superimpose block to be subtracted at top of current set of blocks

        sub_offset = 12

        current_value = tgtcol.Total()
        sub_value = Blocks[SelectedBlockTag].value

        startx, starty = UpperLeft(SelectedBlockTag)
        endx, endy = UpperLeft(tgtcol.blocks[-1].tag)

        # adjust destination rightward a bit
        endx += sub_offset

        # move the block to be subtracted
        count = 12
        for i in range(count):
            Canv.move(SelectedBlockTag, (endx-startx)/count, (endy-starty)/count)
            Canv.update()
            sleep(0.15/count)
        sleep(0.25)

        # gradually migrate start color (s) toward end color (e),
        # while also sliding the block leftward into place
        s = HexString2List(Blocks[SelectedBlockTag].color)
        e = HexString2List(G.SUBTRACT_COLOR)

        for i in range(12):
            color = '#'
            for n in range(3):
                level = s[n] + i*((e[n] - s[n])/count)
                # make sure roundoff error doesn't take us out-of-bounds
                if level > 255: level = 255
                if level < 0: level = 0
                color += '%02x' % level

            Canv.itemconfig(SelectedBlockTag, fill=color)
            Canv.move(SelectedBlockTag, -sub_offset/count, 0)
            Canv.update()
            sleep(0.5/count)

        Canv.itemconfig(SelectedBlockTag, fill=G.SUBTRACT_COLOR)
        Canv.update()
        sleep(0.5)

        # delete block from original column
        Canv.delete(SelectedBlockTag)
        origcol = OrigColumn(SelectedBlockTag)
        origcol.blocks = []
        origcol.ShowValue(-1) # erase

        ##
        ## process result
        ##
        result = current_value - sub_value

        # clear target column
        for blk in tgtcol.blocks:
            Canv.delete(blk.tag)
        tgtcol.blocks = []

        # create result block (maybe) and show value
        if result > 0:
            # last character of AnswerColTag indicates column index
            tgtcol.Add( Block(result, int(AnswerColTag[-1]), AnswerColTag+"_result") )
        tgtcol.ShowValue()

        # recalc the borrow buttons
        DrawBorrowButtons()

        # reset target column background
        Canv.itemconfig(AnswerColTag, outline=tgtcol.color, fill=tgtcol.color)

        # no more mouse interactions with this block
        Canv.tag_unbind(SelectedBlockTag, '<Button-1>')
        Canv.tag_unbind(SelectedBlockTag, '<Button1-Motion>')
        Canv.tag_unbind(SelectedBlockTag, '<Button1-ButtonRelease>')
        # a block can be moved only once
        #SelectableBlockTags.remove(SelectedBlockTag)

        # maybe show answer
        CalcAnswer()

    else:
        # snap back: return the block to its original position
        # where is block now?
        newX, newY = UpperLeft(SelectedBlockTag)
        # what is original position?
        origX, origY = Blocks[SelectedBlockTag].startloc[:2]

        # perform the move
        count = 12
        for i in range(count):
            Canv.move(SelectedBlockTag, (origX-newX)/count, (origY-newY)/count)
            Canv.update()
            sleep(0.5/count)

        # reset target column background
        clr = tgtcol.color
        Canv.itemconfig(AnswerColTag, outline=clr, fill=clr)

    # in all cases, reset flag
    DropOk = False

def MouseUp_Add(event):
    """
    handle a mouse-up event in ADD mode
    """
    global SelectedBlockTag, AnswerColTag, DropOk

    # Answer column was determined during MouseDown event
    tgtcol = Columns[AnswerColTag]

    if DropOk:
        sleep(0.1)
        # move block toward target location
        # where is block now?
        startx, starty = LowerLeft(SelectedBlockTag)
        # where should block go?
        endx, endy = LowerLeft(tgtcol.tag)
        endx += G.BLOCK_PAD
        endy -= tgtcol.Total()*G.UNIT_HGT

        # perform the move
        count = 12
        for i in range(count):
            Canv.move(SelectedBlockTag, (endx-startx)/count, (endy-starty)/count)
            Canv.update()
            sleep(0.15/count)

        # delete block from original column
        Canv.delete(SelectedBlockTag)
        origcol = OrigColumn(SelectedBlockTag)
        origcol.blocks = []
        origcol.ShowValue(-1) # erase

        # recreate block at the target location, with its top
        # aligned with the top of the column's existing blocks
        tgtcol.Add(Blocks[SelectedBlockTag])

        # reset target column background, and drop flag
        clr = tgtcol.color
        Canv.itemconfig(AnswerColTag, outline=clr, fill=clr)

        # no more mouse interactions with this block
        Canv.tag_unbind(SelectedBlockTag, '<Button-1>')
        Canv.tag_unbind(SelectedBlockTag, '<Button1-Motion>')
        Canv.tag_unbind(SelectedBlockTag, '<Button1-ButtonRelease>')
        
        #SelectableBlockTags.remove(SelectedBlockTag)

    else:
        # snap-back: return the block to its original position
        # where is block now?
        newX, newY = UpperLeft(SelectedBlockTag)
        # what is original position?
        origX, origY = Blocks[SelectedBlockTag].startloc[:2]

        # perform the move
        count = 12
        for i in range(count):
            Canv.move(SelectedBlockTag, (origX-newX)/count, (origY-newY)/count)
            Canv.update()
            sleep(0.5/count)

    # in all cases, reset flag
    DropOk = False

def UpperLeft(tag):
    """
    return the coordinates of the UPPER-LEFT corner
    of the rectangle with the specified tag
    """
    a,b,c,d = BlockCoords(tag)
    return (a,b)

def LowerLeft(tag):
    """
    return the coordinates of the LOWER-LEFT corner
    of the rectangle with the specified tag
    """
    a,b,c,d = BlockCoords(tag)
    return (a,d)

def BlockCoords(blktag):
    """
    return the coordinates of the rectangle with the specified tag
    """
    # assumption: rectangle is the FIRST (i.e. 0th) object created with the tag
    # or the only such object
    try:
        rectID = Canv.find_withtag(blktag)[0]
    except:
        DbgPrint("Could not find block with tag '%s'" % blktag)
    return Canv.coords(rectID)

def OrigColumn(blktag):
    """
    return the column object where the block with a specified tag originated
    """
    # to recover the column tag, remove the block-tag "extension"
    coltag = blktag[:-len(G.BLOCK_SUFFIX)]
    return Columns[coltag]

def AnswerColumnTag(blktag):
    """
    return the tag of the "answer" column that corresponds to the selected block
    (ex: n2_col_1_blk_0 --> nA_col_1)
    """
    coltag = blktag[0] + 'A' + blktag[2:-len(G.BLOCK_SUFFIX)]
    return coltag

def InAnswerColumn():
    """
    is the mouse in the bounding box of the target column? (ID'd by global: AnswerColTag)
    """
    leftx, topy, rightx, boty = Canv.bbox(AnswerColTag)
    return (leftx <= MouseLastX <= rightx and topy <= MouseLastY <= boty)

def StdColor(arg):
    """
    return standard color for a column or block,
    based on the first letter of its tag
    """
    return "white"
    if isinstance(arg, Block):
        return COLORS[arg.tag[0] + 'b']
    elif isinstance(arg, Column):
        return COLORS[arg.tag[0] + 'c']

def ValidateKey(event=None):
    """
    after a keystroke, determine whether the two input fields have valid numbers
    """
    # don't worry about special keys
    if event and event.keysym != 'space' and len(event.keysym) > 1:
        return

    # if a digit that is not between 0 and G.BASE-1, delete it
    # if already at max number of digits, delete it
    # if SPACE, delete it
    if (event and event.char
        and
        (event.char not in G.VALID_DIGITS or len(event.widget.get()) > G.COL_COUNT)
        ):
        idx = event.widget.get().index(event.char)
        event.widget.delete(idx)
        return

    # Draw button disabled by default
    Ctrl.drawbtn['state'] = T.DISABLED

    # input values are STRINGs not INTs, to support non-decimal arithmetic
    s1 = s2 = None
    s1 = Ctrl.number_1.get()
    s2 = Ctrl.number_2.get()

    # cannot enable Draw key if one or both of the input fields is blank
    if not s1 or not s2:
        return

    # enable Draw button if entries are valid
    if (len(s1.zfill(G.COL_COUNT)) <= G.COL_COUNT
        and
        len(s2.zfill(G.COL_COUNT)) <= G.COL_COUNT
        and
        (Mode.get()==G.ADD_MODE or (Mode.get()==G.SUB_MODE and int(s1) >= int(s2)))
        ):

        Ctrl.drawbtn['state'] = T.NORMAL

def DrawBlocks():
    """
    get values from Entry fields
    draw columns
    draw a block to represent each digit
    """
    global Num1, Num2, NumA

    # these are STRINGs, not INTs, normalize to G.COL_COUNT width
    n1_digits = Ctrl.number_1.get().zfill(G.COL_COUNT)
    n2_digits = Ctrl.number_2.get().zfill(G.COL_COUNT)

    # base y-coordinate for columns
    base = Ctrl.winfo_y() - G.ANSR_OFFSET - LEFT_ARROW.height() - 8
    # ... but Answer in SUB mode is a little higher
    sub_mode_y_offset = G.UNIT_HGT

    if Mode.get() == G.ADD_MODE:
        Num1 = Number("n1", n1_digits,
                      Ctrl.numbers_grid.winfo_x() + Ctrl.entry_1.winfo_x() + 0.5*Ctrl.entry_1.winfo_width(),
                      base)
        Num2 = Number("n2", n2_digits,
                      Ctrl.numbers_grid.winfo_x() + Ctrl.entry_2.winfo_x() + 0.5*Ctrl.entry_2.winfo_width(),
                      base)
        NumA = Number(G.ANSW_COL_PREFIX, 0,
                      Ctrl.numbers_grid.winfo_x() + Ctrl.answ.winfo_x() + 0.5*Ctrl.answ.winfo_width(),
                      base)

        for n in (Num1, Num2):
            n.InitColumns(G.COL_COUNT)
            n.InitBlocks()

        # answer: extra column, no initial blocks
        NumA.InitColumns(G.COL_COUNT + 1)

    elif Mode.get() == G.SUB_MODE:
        NumA = Number(G.ANSW_COL_PREFIX, n1_digits,
                      Ctrl.numbers_grid.winfo_x() + Ctrl.entry_1.winfo_x() + 0.5*Ctrl.entry_1.winfo_width(),
                      base - sub_mode_y_offset)
        Num2 = Number("n2", n2_digits,
                      Ctrl.numbers_grid.winfo_x() + Ctrl.entry_2.winfo_x() + 0.5*Ctrl.entry_2.winfo_width(),
                      base)

        for n in (NumA, Num2):
            n.InitColumns(G.COL_COUNT)
            n.InitBlocks()

    # disable button and entry fields
    for obj in (Ctrl.signbtn, Ctrl.drawbtn, Ctrl.entry_1, Ctrl.entry_2):
        obj['state'] = T.DISABLED

    # maybe: enable some borrow buttons
    if Mode.get() == G.SUB_MODE:
        DrawBorrowButtons()

def DrawBorrowButtons():
    """
    reconfigure borrow buttons for all columns
    """
    # "-1" because largest column cannot be the "to" of a borrow operation
    for idx in range(G.COL_COUNT-1):
        to_col = NumA.columns[idx]
        current_val = to_col.Total()
        subtract_val = Num2.columns[idx].Total()

        from_col = NumA.columns[idx+1]
        borrow_arrow = from_col.tag + G.BORROW_ARROW_SUFFIX

        # remove any existing borrow arrow (should not need this)
        Canv.delete(borrow_arrow)

        # as appropariate, create borrow image and set binding
        if current_val < subtract_val:
            startx, starty = LowerLeft(to_col.tag)
            item_id = Canv.create_image(startx, starty+G.ARROW_OFFSET,
                                   image=RIGHT_ARROW, tags=borrow_arrow)
            Canv.tag_bind(borrow_arrow, "<Button-1>", from_col.Borrow)
            DbgPrint("Created borrow arrow: %d, %s" % (item_id, borrow_arrow))

def CalcAnswer():
    """
    show the final answer, if all original blocks have been "played"
    and no more carrying/borrowing needs to be done
    """
    # are we ready to calculate?
    if Mode.get() == G.ADD_MODE:
        if any([col.Total() for col in Num1.columns + Num2.columns]) or CarryCount > 0:
            return
    elif Mode.get() == G.SUB_MODE: # note: there is no 'BorrowCount' to check
        if any([col.Total() for col in Num2.columns]):
            return

    # transcribe column totals, in reverse order
    digit_list = [col.Total() for col in NumA.columns]

    # special case: ZERO answer
    if sum(digit_list) == 0:
        strval = "0"

    # std case: INT list -> STRING, in reversed order
    else:
        # get rid of leading ZEROs (which are at the end of the list)
        while digit_list[-1] == 0:
            del digit_list[-1]
        strval = "".join(map(str, reversed(digit_list)))

    # show and bell
    Ctrl.answ.configure(text=strval, bg=G.ANSW_COLOR)
    Canv.bell()

def DbgPrint(*arglist):
    """
    display debug data
    """
    if not G.DEBUG:
        return

    for arg in arglist:
        print arg,
    print

def Debug(evt):
    """
    set breakpoint here to drop into debugger
    during program execution
    """
    _=1

def NewCmd():
    """
    start over
    """
    # empty the canvas
    for obj in Canv.find_all():
        Canv.delete(obj)

    # reinit entry fields
    Ctrl.number_1.set("")
    Ctrl.number_2.set("")
    for obj in (Ctrl.signbtn, Ctrl.entry_1, Ctrl.entry_2):
        obj['state'] = T.NORMAL
    Ctrl.drawbtn['state'] = T.DISABLED
    Ctrl.entry_1.focus()
    Ctrl.answ['bg'] = G.CANV_BG_COLOR
    Ctrl.answ['text'] = ""

    InitializeMode()

def ExitCmd():
    """
    end the program
    """
    sys.exit(0)

def ClearSplash():
    """
    erase the splash screen
    """
    Canv.delete(splash_id)

def HexString2List(hexstr):
    """
    convert a hex string: e.g. "#00FF03"
    to a list: [0, 255, 3]
    """
    rtn = []
    rtn.append(int(hexstr[1:3], 16))
    rtn.append(int(hexstr[3:5], 16))
    rtn.append(int(hexstr[5:], 16))

    return rtn

def ChangeSign():
    """
    toggle between ADD/SUB modes
    """
    if Mode.get() == G.ADD_MODE:
        Mode.set(G.SUB_MODE)
        InitializeMode()
    elif Mode.get() == G.SUB_MODE:
        Mode.set(G.ADD_MODE)
        InitializeMode()

    if G.HELP_WINDOW:
        G.HELP_WINDOW.Update()
        G.HELP_WINDOW.lift()

    ValidateKey(None)

def InitializeMode():
    """
    adjust labels on entry fields for ADD/SUB mode
    display help text
    """
    # config: help text positions
    HELP_ADD_OFFSET = -95
    HELP_SUB_OFFSET = -105

    # tags
    ADD_TAG = "help_add"
    SUB_TAG = "help_sub"

    # get control panel background color
    # (for carry/borrow arrows implemented as BitmapImage)
    # G.CTRL_BG_COLOR = Ctrl.cget('bg')

    # adjust text
    if Mode.get() == G.ADD_MODE:
        Ctrl.label_1_text = G.DISPLAY_STR['first']
        Ctrl.label_2_text = G.DISPLAY_STR['second']
        Ctrl.signbtn_bitmap = "@plus.xbm"
    else:
        Ctrl.label_1_text = G.DISPLAY_STR['larger']
        Ctrl.label_2_text = G.DISPLAY_STR['smaller']
        Ctrl.signbtn_bitmap = "@minus.xbm"

    Ctrl.label_1['text'] = Ctrl.label_1_text
    Ctrl.label_2['text'] = Ctrl.label_2_text
    Ctrl.signbtn['bitmap'] = Ctrl.signbtn_bitmap

def SpacerWidth(label_width, answ_col_flag=False):
    """
    determine width for spacer Frame for a specified label-width
    flag indicates this is answer column (needs wider spacer in ADD mode, for carry column)
    """
    # width of column set; extra answer column for carry in ADD mode
    col_set_width = G.COL_COUNT * G.COL_WID
    if answ_col_flag:
        col_set_width += G.COL_WID

    extra = G.COL_WID // 2

    # case: label is wider than column set
    if label_width >= col_set_width:
        spacer_width = extra

    # case: column set is wider than label
    else:
        spacer_width = (col_set_width - label_width) // 2 + extra

    return spacer_width

def SetWidths():
    """
    determine the widths of strings to be displayed in control panel
    set control panel elements, so that no jitter occurs when toggling
    ADD/SUB mode
    """
    # find display widths of number labels
    keys = "first second larger smaller answer".split()
    texts = [ G.DISPLAY_STR[k] for k in keys ]
    ids = [ Canv.create_text(100,100, font=G.FONT, text=t, fill='red') for t in texts ]
    # enable indexing by key instead of number
    idx = dict(zip(keys, range(len(keys))))

    # construct pixel-widths list, then get rid of text items
    widths = []
    for i in ids:
        xleft,_,xright,_ = Canv.bbox(i)
        widths.append(xright - xleft)
        Canv.delete(i)

    # once and for all, set widths of number columns (number of characters, not pixels!)
    # won't change when toggling ADD/SUB mode
    if widths[idx['first']] > widths[idx['larger']]:
        Ctrl.label_1['width'] = len(texts[idx['first']])
        n1_wid = widths[idx['first']]
    else:
        Ctrl.label_1['width'] = len(texts[idx['larger']])
        n1_wid = widths[idx['larger']]

    if widths[idx['second']] > widths[idx['smaller']]:
        Ctrl.label_2['width'] = len(texts[idx['second']])
        n2_wid = widths[idx['second']]
    else:
        Ctrl.label_2['width'] = len(texts[idx['smaller']])
        n2_wid = widths[idx['smaller']]

    nA_wid = widths[idx['answer']]

    #RootWin.update()

    # once and for all, set widths of spacer Frames
    Ctrl.spacer_0['width'] = Ctrl.spacer_1['width'] = SpacerWidth(n1_wid)
    Ctrl.spacer_2['width'] = Ctrl.spacer_3['width'] = SpacerWidth(n2_wid)
    Ctrl.spacer_4['width'] = SpacerWidth(nA_wid, True)
    # we don't need much width to right of Answer column, can overlap buttons at right
    Ctrl.spacer_5['width'] = 8

def HelpCmd():
    """
    display help text
    """
    if not G.HELP_WINDOW:
        G.HELP_WINDOW = HelpWindow()
    G.HELP_WINDOW.Update()

####################
#################### main routine
####################

if __name__ == '__main__':

    # set up TK app and top-level window
    RootWin = T.Tk()
    RootWin.option_add('*font', G.FONT)
    RootWin.title("BlockHead")

    # window geometry (TODO: make it smarter!)
    if G.ShowMeDo_800_600:
        RootWin.geometry('%dx%d+%d+%d' % G.SHOWMEDO_GEOM)
    else:
        pass
        RootWin.minsize(None, 2*G.BASE*G.UNIT_HGT + G.WINDOW_HGT_ADJ)

    # initialize operating mode (ADD/SUB)
    Mode = T.IntVar()
    Mode.set(G.ADD_MODE)

    # create canvas and control panel

    Canv = BlockHeadCanvas(RootWin)
    Canv['height'] = 2 * G.BASE * G.UNIT_HGT + 75
    Canv.pack(side=T.TOP, expand=True, fill=T.BOTH)

    Ctrl = BlockHeadControlPanel(RootWin)
    Ctrl.pack(side=T.TOP, fill=T.X)

    # compute widths of strings to be displayed
    SetWidths()

    # initialize control panel
    NewCmd()

    # carry/borrow images
    # must wait to create; must be global to avoid Tkinter garbage-collection idiosynsracy
    LEFT_ARROW = T.PhotoImage(file="left_arrow_btn.gif")
    RIGHT_ARROW = T.PhotoImage(file="right_arrow_btn.gif")

    # for debugging: seed the input fields
    #Ctrl.number_1.set('1256')
    #Ctrl.number_2.set('9847')
    #Ctrl.drawbtn['state'] = T.NORMAL

    # splash screen
    RootWin.update()
    if G.SPLASH_ENABLE:
        splash_id = Canv.create_text(RootWin.winfo_width()*0.5, RootWin.winfo_height()*0.4,
                                     text = "BlockHead\n\nAddition/Subtraction\nCalculator",
                                     justify=T.CENTER, font=G.SPLASHFONT)
        RootWin.after(2500, ClearSplash)

    # freeze current geometry, and don't allow window resizing
    RootWin.geometry(RootWin.geometry())
    RootWin.resizable(0,0)

    # enable debugging
    RootWin.bind('<Button-2>', Debug)

    # go
    RootWin.mainloop()
    sys.exit(0)
