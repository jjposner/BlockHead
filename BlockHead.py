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
visual calculator, for adding or subtracting two 3-digit numbers
"""

import os
import sys
from time import sleep
import Tkinter as T

__date__ = '16-Jun-2009'
__version__ = 1049

####################
#################### global variables
####################

# configure for 800x600 display screen, required for ShowMeDo videos
ShowMeDo_800_600 = False

# operation modes
ADD_MODE = 1
SUB_MODE = 2

# help texts
HELP_ADD = """
ADD TWO NUMBERS

Enter two numbers to
be added, then click
"Draw Blocks"

Drag each of the
blocks you've drawn
to the corresponding
(same-color)
answer column

If an answer column's
total is 10 or more,
click the "carry" arrow
that appears below the
answer column

Click the "+" operator
between the numbers
to change it to "-"
"""

HELP_SUB = """
SUBTRACT TWO NUMBERS

Enter the larger and
smaller numbers, then
click "Draw Blocks"

Drag the blocks for
the smaller number to
the corresponding columns
of the larger number

In the larger number,
you may need to click one
or more "borrow" arrows --
they appear below columns
whose blocks are too short
to subtract from

Click the "-" operator
between the numbers
to change it to "+"
"""

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

# help text positions
HELP_ADD_OFFSET = -95
HELP_SUB_OFFSET = -105
TEXT_FONT = FONT

# colors
BGND_COLOR = '#D8D8D8'
INPT_COLOR = '#00FF00'
ANSW_COLOR = '#00CCFF'
TGT_COLOR = '#00FF00'
CARRY_COLOR = '#008000'
BORROWBLK_COLOR = '#f0f000'
SUBTRACT_COLOR = '#CCCCCC'
COLORS = {'hb': '#FF7D7D', # hundreds block
          'tb': '#32bfe8',
          'ob': '#F2BC02',
          'xc': BGND_COLOR, # thousands column (invisible)
          'hc': '#ffd7d7', # hundreds column
          'tc': '#a6e2f4',
          'oc': '#feedb1'}

# block specs
WID = 18     # block width
PAD = 8      # padding between block and column edge
UNIT = WID   # height of one unit

# column specs
COL_OFFSET = WID + 2*PAD # make the columns contiguous
HGT = 10*UNIT # height of column
ANSR_OFFSET = 30 # distance between bottom of column and digit; leave room for carry/borrow arrows!
CARRY_ARROW_HGT = 12 # height of carry/borrow arrow

# dictionaries of columns and blocks
# an object's dict key is same as its Tkinter "create_rectangle" tag
ANSW_COLTAGS = ['xA_col', 'hA_col', 'tA_col', 'oA_col']

# suffixes to be appended to "tag root" name,
# to make a column tag or block tag or text anno
COLSUFFIX = "_col"
BLOCKSUFFIX = "_block"
TEXTSUFFIX = "_text"
CARRYSUFFIX = "_carry"

# non-constant globals 
Cols = {}
Blocks = {}
MouseLastX = MouseLastY = MouseStartX = MouseStartY = CarryCount = 0
SelectedBlockTag = DropOk = AnswerColTag = SelectableBlockTags = None

####################
#################### classes
####################

class Block():
    """
    represents one digit of a multiple-digit number
    """

    def __init__(self, tag, value, color=None):
        self.value = value
        self.tag = tag
        # maybe: assign color using first letter of tag
        if color:
            self.color = color
        else:
            self.color = StdColor(self)

        # id of Tkinter widget; will be set to integer ID by Canvas create_rectangle()
        self.id = 0

        # register the block in the global list
        Blocks[self.tag] = self

        # will be filled in by Column's Draw()
        self.startloc = None

class Column():
    """
    represents one column (ones, tens, hundreds)
    """

    def __init__(self, tag, leftedge, bottomedge, color=None):
        """
        initialize a column, either input or answer
        """
        self.tag = tag        
        self.x = leftedge
        self.y = bottomedge
        # list of Block objects in this column
        self.blocks = []

        # maybe: StdColor() assigns color using first letter of tag
        if color:
            self.color = color
        else:
            self.color = StdColor(self)

        self.id = Canv.create_rectangle(self.x, self.y, self.x+WID+2*PAD, self.y-HGT,
                                        tags=self.tag, outline=self.color, fill=self.color)
        # carry button id will be created by Add()
        self.carryarrow = None

        # register the column in the global list
        Cols[self.tag] = self

    def ColumnToRight(self):
        """
        return Column to right of this column
        """
        assert(self.tag in ANSW_COLTAGS)
        idx = ANSW_COLTAGS.index(self.tag)
        try:
            return Cols[ANSW_COLTAGS[idx+1]]
        except IndexError:
            print "ERROR: no column to right"
            sys.exit(1)

    def ColumnToLeft(self):
        """
        return Column to left of this column
        """
        assert(self.tag in ANSW_COLTAGS)
        idx = ANSW_COLTAGS.index(self.tag)
        try:
            return Cols[ANSW_COLTAGS[idx-1]]
        except IndexError:
            print "ERROR: no column to left"
            sys.exit(1)

    def Draw(self, blk, offset=0):
        """
        draw a block in this Column
        """
        # no block to draw for zero value
        if blk.value == 0:
            return

        startx = self.x + PAD
        height = blk.value*UNIT

        # might need to draw this block on top of others
        hgt_offset = offset*UNIT

        # create Tkinter rectangle widget for block
        # note: Y-axis is reversed!
        blk.id = Canv.create_rectangle(startx, self.y-hgt_offset,
                                       startx+WID, self.y-height-hgt_offset,
                                       fill=blk.color, tags=blk.tag)

        # save location of rectangle widget, for "snap back" in cancelled move operation
        blk.startloc = Canv.coords(blk.id)

        # create horizontal lines to show individual units
        for i in range(1, blk.value):
            Canv.create_line(startx, self.y-i*UNIT-hgt_offset,
                             startx+WID, self.y-i*UNIT-hgt_offset,
                             fill='black', tags=blk.tag)

    def Add(self, blk, carry_button_suppress=False):
        """
        send a block to this column
        """
        # carry_button_suppress is needed when creating a ten-block during execution
        # of Carry() method

        global mode, CarryCount

        # save current column total, before adding new block
        old_total = self.Total()

        self.blocks.append(blk)
        self.Draw(blk, old_total)

        # update numeric value display
        self.ShowValue(self.Total())

        # maybe: create carry button below column
        if mode.get() == SUB_MODE or blk.value == 0:
            return

        # maybe: display carry arrow
        carrytag = self.tag + CARRYSUFFIX
        if self.Total() >= 10 and not carry_button_suppress and not Canv.find_withtag(carrytag):
            startx, starty = LowerLeft(self.id)
            self.carryarrow = Canv.create_image(startx, starty+10,
                                                image=LEFT_ARROW, tags=carrytag)
            
            # activate the carry arrow            
            Canv.tag_bind(carrytag, "<Button-1>", self.Carry)
            CarryCount += 1

    def ShowValue(self, value=None):
        """
        display a block's value below this column
        """
        if value is None:
            value = self.Total()
        elif value == -1:
            value = ""

        texttag = self.tag + TEXTSUFFIX

        # delete previous value, if necessary
        Canv.delete(texttag)

        # create new text widget
        Canv.create_text(self.x + (WID+2*PAD)/2, self.y+ANSR_OFFSET,
                         tag = texttag, text=str(value), font=FONT, justify=T.CENTER)

    def Total(self):
        """
        total of column's blocks
        """
        total = 0
        for blk in self.blocks:
            total += blk.value
        return total

    def Carry(self, event):
        """
        calculate carry for specified column
        btn = ID of dynamically-created carry button, to be deleted
        """
        global CarryCount

        # carry destination
        destcol = self.ColumnToLeft()

        # delete carry button
        Canv.tag_unbind(self.carryarrow, "<Button-1>")
        Canv.delete(self.carryarrow)
        CarryCount -= 1

        # save total value of blocks, for creation of new blocks
        total = self.Total()

        # create some block tags, specific to this column
        tenblk_tag = self.tag + "_ten_xformblock"
        carryblk_tag = self.tag + "_carry_xformblock"
        excessblk_tag = self.tag + "_excess_xformblock"

        # save color, might be needed for "excess" block
        block_color = StdColor(self.blocks[0])

        # clear out all the blocks in this column
        for blk in self.blocks:
            Canv.delete(blk.tag)
        self.blocks = []

        # block of 10 units
        Block(tenblk_tag, 10, block_color)
        self.Add(Blocks[tenblk_tag], True)

        # create carry block (1 unit), but don't draw it yet
        Block(carryblk_tag, 1, block_color)

        # "excess" block (1+ units)
        if total > 10:
            excess = total - 10
            Block(excessblk_tag, excess, block_color)
            self.Add(Blocks[excessblk_tag], True)

        sleep(0.25)

        # transform 10 units into 1 unit of the next column
        startx, starty = UpperLeft(tenblk_tag)

        Canv.lift(tenblk_tag)
        count = 20
        for i in range(count):
            sleep(1.0/count)
            Canv.scale(tenblk_tag, startx, starty, 1.0, 0.1 ** (1.0/count))
            Canv.update()
        sleep(0.25)

        # move the shrunken blocks to the next column
        startx, starty, = LowerLeft(tenblk_tag)
        endx = Canv.coords(destcol.tag)[0]+PAD
        endy = self.y - destcol.Total()*UNIT

        count = 20
        for i in range(count):
            Canv.move(tenblk_tag, (endx-startx)/count, (endy-starty)/count)
            Canv.update()
            sleep(1.0/count)

        # replace shrunken 10-unit block with already created "carry block"
        Canv.delete(tenblk_tag)
        destcol.Add(Blocks[carryblk_tag])

        # delete the block from this column, and update column total
        del self.blocks[0]
        self.ShowValue()

        # did we create an "excess" block? if so, drop it down
        if total > 10:
            sleep(0.25)
            count = 20
            for i in range(count):
                sleep(1.0/count)
                Canv.move(excessblk_tag, 0, 10.0*UNIT/count)
                Canv.update()

        # are we done?
        CalcAnswer()

    def Borrow(self, event):
        """
        borrow 1 unit from this column:
        send 10 units to the column to the right
        """
        # can we borrow fromn this column?
        # if not, first borrow from column to the left
        if self.Total() == 0:
            self.ColumnToLeft().Borrow(event)
            Canv.update()
            sleep(0.5)

        # decompose last block in this column (ex: 8 --> 7+1)
        borrow_blk = self.blocks[-1]
        borrow_val = borrow_blk.value
        borrow_tag = borrow_blk.tag
        borrow_newblk_tag = borrow_tag + "_borrowfrom"

        # delete the borrow arrow and the topmost block from this column
        Canv.delete(borrow_tag)
        del self.blocks[-1]

        # replace with block of size N-1, if value is greater than 1
        if borrow_val > 1:
            self.Add( Block(borrow_tag, borrow_val-1, StdColor(borrow_blk)) )

        # create block of size 1, which will get borrowed
        self.Add( Block(borrow_newblk_tag, 1, BORROWBLK_COLOR) )

        startx, starty = LowerLeft(borrow_newblk_tag)
        for i in range(1,10):
            Canv.create_line(startx,     starty-i/10.0*UNIT,
                             startx+WID, starty-i/10.0*UNIT, tags=borrow_newblk_tag)
        Canv.update()

        # scale borrow block vertically from 1 unit to 10 units
        count = 20
        for i in range(count):
            Canv.scale(borrow_newblk_tag, startx, starty, 1.0, (10.0 ** (1.0/count)))
            sleep(1.0/count)
            Canv.update()

        sleep(0.25)

        # move the scaled borrow block to the next column
        destcol = self.ColumnToRight()

        try:
            # there's a block in the dest column
            tgtblk = destcol.blocks[-1]
            endx, endy = UpperLeft(tgtblk.tag)
        except IndexError:
            # there's no block in the dest column
            endx = Canv.coords(destcol.tag)[0] + PAD
            endy = self.y

        count = 20
        for i in range(count):
            Canv.move(borrow_newblk_tag, (endx-startx)/count, (endy-starty)/count)
            Canv.update()
            sleep(1.0/count)

        # remove the borrow block from this column
        del self.blocks[-1]
        self.ShowValue()

        # destination column: replace stretched block (value=1) with new block (value=10)
        Canv.delete(borrow_newblk_tag)
        destcol.Add( Block(destcol.tag+"_borrowto", 10) )

        # recalc the borrow buttons
        BorrowButtons()

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
    try:
        SelectedBlockTag = Canv.gettags(Canv.find_closest(MouseStartX, MouseStartY))[0]
    except IndexError:
        SelectedBlockTag = None
        return

    # only certain block widgets are selectable
    if SelectedBlockTag not in SelectableBlockTags:
        SelectedBlockTag = None
        return

    AnswerColTag = AnswerColumnTag(SelectedBlockTag)
    Canv.lift(SelectedBlockTag)

def MouseMotion(event):
    """
    move a block, and determine whether it can be dropped
    """
    global MouseLastX, MouseLastY, MouseStartX, MouseStartY, SelectedBlockTag, AnswerColTag, DropOk
    if not SelectedBlockTag:
        return
    cx = Canv.canvasx(event.x)
    cy = Canv.canvasy(event.y)
    Canv.move(SelectedBlockTag, cx-MouseLastX, cy-MouseLastY)
    MouseLastX = cx
    MouseLastY = cy

    if InAnswerColumn():
        if mode.get() == ADD_MODE:
            Canv.itemconfig(AnswerColTag, outline=TGT_COLOR, fill=TGT_COLOR)
            DropOk = True
        elif mode.get() == SUB_MODE:
            if Blocks[SelectedBlockTag].value <= Cols[AnswerColTag].Total():
                # can subtract now, without borrowing
                Canv.itemconfig(AnswerColTag, outline=TGT_COLOR, fill=TGT_COLOR)
                DropOk = True
            else:
                # cannot subtract now, need to borrow
                Canv.itemconfig(AnswerColTag, outline='black', fill='black')
                DropOk = False
    else:
        # reset target column background
        clr = Cols[AnswerColTag].color
        Canv.itemconfig(AnswerColTag, outline=clr, fill=clr)
        DropOk = False

def MouseUp(event):
    """
    dispatch a mouse-up event, depending on the ADD/SUB mode
    """
    global MouseLastX, MouseLastY, mode

    if not SelectedBlockTag:
        return

    # make sure that an original block is selected
    try:
        widgetlist = Canv.gettags(T.CURRENT)
    except:
        return
    if len(widgetlist) == 0 or not widgetlist[0].endswith(BLOCKSUFFIX):
        return

    # update global vars
    MouseLastX = Canv.canvasx(event.x)
    MouseLastY = Canv.canvasy(event.y)

    # dispatch ADD/SUB
    if mode.get() == ADD_MODE or len(Cols[AnswerColTag].blocks) == 0:
        MouseUp_Add(event)
    elif mode.get() == SUB_MODE:
        MouseUp_Sub(event)

    CalcAnswer()

def MouseUp_Sub(event):
    """
    handle a mouse-up event in SUB mode
    """
    global MouseLastX, MouseLastY, MouseStartX, MouseStartY, SelectedBlockTag, AnswerColTag, DropOk, CarryData

    if DropOk:
        # superimpose block to be subtracted at top of current set of blocks

        sub_offset = 10

        current_value = Cols[AnswerColTag].Total()
        sub_value = Blocks[SelectedBlockTag].value

        startx, starty = UpperLeft(SelectedBlockTag)
        endx, endy = UpperLeft(Cols[AnswerColTag].blocks[-1].tag)

        # adjust destination rightward a bit
        endx += sub_offset

        # move the block to be subtracted
        count = 10
        for i in range(count):
            Canv.move(SelectedBlockTag, (endx-startx)/count, (endy-starty)/count)
            Canv.update()
            sleep(0.15/count)
        sleep(0.25)

        # gradually migrate start color (s) toward end color (e),
        # while also sliding the block leftward into place
        s = HexString2List(Blocks[SelectedBlockTag].color)
        e = HexString2List(SUBTRACT_COLOR)

        for i in range(10):
            color = '#'
            for n in range(3):
                level = s[n] + i*((e[n] - s[n])/count)
                # make sure roundoff error doesn't take us out-of-bounds
                if level > 255: level = 255
                if level < 0: level = 0
                color += '%02x' % level
                Canv.update()

            Canv.itemconfig(SelectedBlockTag, fill=color)
            Canv.move(SelectedBlockTag, -sub_offset/count, 0)
            Canv.update()
            sleep(1.0/count)

        Canv.itemconfig(SelectedBlockTag, fill=SUBTRACT_COLOR)
        Canv.update()
        sleep(0.75)

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
        for blk in Cols[AnswerColTag].blocks:
            Canv.delete(blk.tag)
        Cols[AnswerColTag].blocks = []

        # create result block (maybe) and show value
        if result > 0:
            Cols[AnswerColTag].Add( Block(AnswerColTag+"_result", result) )
        Cols[AnswerColTag].ShowValue()

        # recalc the borrow buttons
        BorrowButtons()

        # reset target column background
        Canv.itemconfig(AnswerColTag, outline=Cols[AnswerColTag].color, fill=Cols[AnswerColTag].color)

        # a block can be moved only once
        SelectableBlockTags.remove(SelectedBlockTag)

        # maybe show answer
        CalcAnswer()

    else:
        # snap-back: return the block to its original position
        # where is block now?
        newX, newY = UpperLeft(SelectedBlockTag)
        # what is original position?
        origX, origY = Blocks[SelectedBlockTag].startloc[:2]

        # perform the move
        count = 10
        for i in range(count):
            Canv.move(SelectedBlockTag, (origX-newX)/count, (origY-newY)/count)
            Canv.update()
            sleep(0.5/count)

        # reset target column background
        clr = Cols[AnswerColTag].color
        Canv.itemconfig(AnswerColTag, outline=clr, fill=clr)

    # in all cases, reset flag
    DropOk = False

def MouseUp_Add(event):
    """
    handle a mouse-up event in ADD mode
    """
    global SelectedBlockTag, AnswerColTag, DropOk, CarryData

    if DropOk:
        # move block toward target location
        # where is block now?
        startx, starty = LowerLeft(SelectedBlockTag)
        destcol = Cols[AnswerColTag]
        # where should block go?
        endx, endy = LowerLeft(destcol.tag)
        endx += PAD
        endy -= destcol.Total()*UNIT

        # perform the move
        count = 10
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
        Cols[AnswerColTag].Add(Blocks[SelectedBlockTag])

        # reset target column background, and drop flag
        clr = Cols[AnswerColTag].color
        Canv.itemconfig(AnswerColTag, outline=clr, fill=clr)

        # a block can be moved only once
        SelectableBlockTags.remove(SelectedBlockTag)

    else:
        # snap-back: return the block to its original position
        # where is block now?
        newX, newY = UpperLeft(SelectedBlockTag)
        # what is original position?
        origX, origY = Blocks[SelectedBlockTag].startloc[:2]

        # perform the move
        count = 10
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
    rectID = Canv.find_withtag(blktag)[0]
    return Canv.coords(rectID)

def OrigColumn(blktag):
    """
    return the column object where the block with a specified tag originated
    """
    coltag = blktag.replace("block", "col")
    return Cols[coltag]

def AnswerColumnTag(blktag):
    """
    return the tag of the "answer" column that corresponds to the selected block,
    using the first letter of the tags: 'h' or 't' or 'o'
    """
    return blktag[0] + "A_col"

def InAnswerColumn():
    """
    is the mouse in the bounding box of the target column? (ID'd by global: AnswerColTag)
    """
    leftx, topy, rightx, boty = Canv.bbox(AnswerColTag)
    return (MouseLastX > leftx and MouseLastX < rightx and MouseLastY > topy and MouseLastY < boty)

def StdColor(arg):
    """
    return standard color for a column or block,
    based on the first letter of its tag
    """
    if isinstance(arg, Block):
        return COLORS[arg.tag[0] + 'b']
    elif isinstance(arg, Column):
        return COLORS[arg.tag[0] + 'c']

def ValidateKey(event=None):
    """
    after a keystroke, determine whether the two input fields have valid numbers
    """
    # if not a digit, delete it
    if event and event.char not in '0123456789':
        event.widget.delete( len(event.widget.get()) - 1 )
        return

    # Draw button disabled by default
    drawbtn['state'] = T.DISABLED

    a1 = a2 = 0
    try:
        a1 = Canv.input_1.get()
        a2 = Canv.input_2.get()
    except:
        # this code path if one or both of the input fields is blank
        return

    # enable Draw button if entries are valid
    if (a1 < 1000 and
        a2 < 1000 and
        (mode.get()==ADD_MODE or (mode.get()==SUB_MODE and a2 <= a1))):
        drawbtn['state'] = T.NORMAL

def DrawBlocks():
    """
    get inputs from Entry fields, and draw blocks to represent numbers
    """
    # NOTE: this should always succeed, given ValidateKey()

    arg1 = Canv.input_1.get()
    arg2 = Canv.input_2.get()

    # derive each digit: should always succeed
    try:
        h1 = arg1 // 100
        t1 = (arg1 % 100) // 10
        o1 = arg1 - h1*100 - t1*10

        h2 = arg2 // 100
        t2 = (arg2 % 100) // 10
        o2 = arg2 - h2*100 - t2*10
    except:
        print "bad args"
        sys.exit(1)

    # disable button and entry fields
    for obj in (signbtn, drawbtn, entry_1, entry_2):
        obj['state'] = T.DISABLED

    # configure and draw columns and blocks
    DrawColumnsAndBlocks(h1, t1, o1, h2, t2, o2)

    # maybe: enable some borrow buttons
    if mode.get() == SUB_MODE:
        BorrowButtons()

def DrawColumnsAndBlocks(h1_val, t1_val, o1_val, h2_val, t2_val, o2_val):
    """
    draw columns and blocks, using specified values
    """
    global SelectableBlockTags

    # configure column locations, based on positions of entry/answer fields
    #
    # must take into account both:
    # * offset of numbers_grid frame within numbers_frm frame
    # * offset of entry_N field within numbers_grid frame
    if mode.get() == ADD_MODE:
        # first set of columns
        center = int(numbers_grid.winfo_x() + entry_1.winfo_x() + 0.5*entry_1.winfo_width())
        huns_1 = center - COL_OFFSET*1.5
        tens_1 = huns_1 + COL_OFFSET
        ones_1 = huns_1 + COL_OFFSET*2
        # second set of columns
        center = int(numbers_grid.winfo_x() + entry_2.winfo_x() + 0.5*entry_2.winfo_width())
        huns_2 = center - COL_OFFSET*1.5
        tens_2 = huns_2 + COL_OFFSET
        ones_2 = huns_2 + COL_OFFSET*2
        # answer columns
        center = int(numbers_grid.winfo_x() + answ.winfo_x() + 0.5*answ.winfo_width())
        huns_A = center - COL_OFFSET*1.5
        tens_A = huns_A + COL_OFFSET
        ones_A = huns_A + COL_OFFSET*2
        thou_A = huns_A - COL_OFFSET
    elif mode.get() == SUB_MODE:
        # answer columns are at left, above first number
        center = int(numbers_grid.winfo_x() + entry_1.winfo_x() + 0.5*entry_1.winfo_width())
        huns_A = center - COL_OFFSET*1.5
        tens_A = huns_A + COL_OFFSET
        ones_A = huns_A + COL_OFFSET*2
        # second set of columns
        center = int(numbers_grid.winfo_x() + entry_2.winfo_x() + 0.5*entry_2.winfo_width())
        huns_2 = center - COL_OFFSET*1.5
        tens_2 = huns_2 + COL_OFFSET
        ones_2 = huns_2 + COL_OFFSET*2

    # determine y-coordinate of bottom of a column:
    # allow room for carry/borrow arrows (which are 12 pixels high) and current-value digits
    baselvl = Ctrl.winfo_y() - ANSR_OFFSET - 20

    # create the columns
    if mode.get() == ADD_MODE:
        Column('h1_col', huns_1, baselvl)
        Column('t1_col', tens_1, baselvl)
        Column('o1_col', ones_1, baselvl)
        Column('h2_col', huns_2, baselvl)
        Column('t2_col', tens_2, baselvl)
        Column('o2_col', ones_2, baselvl)
        Column('xA_col', thou_A, baselvl)
        Column('hA_col', huns_A, baselvl)
        Column('tA_col', tens_A, baselvl)
        Column('oA_col', ones_A, baselvl)
    elif mode.get() == SUB_MODE:
        # raise first columns up a bit
        yoffset = 25
        Column('hA_col', huns_A, baselvl-yoffset)
        Column('tA_col', tens_A, baselvl-yoffset)
        Column('oA_col', ones_A, baselvl-yoffset)
        Column('h2_col', huns_2, baselvl)
        Column('t2_col', tens_2, baselvl)
        Column('o2_col', ones_2, baselvl)

    # create blocks and place them in columns
    if mode.get() == ADD_MODE:
        Cols['h1_col'].Add( Block('h1_block', h1_val) )
        Cols['t1_col'].Add( Block('t1_block', t1_val) )
        Cols['o1_col'].Add( Block('o1_block', o1_val) )

        Cols['h2_col'].Add( Block('h2_block', h2_val) )
        Cols['t2_col'].Add( Block('t2_block', t2_val) )
        Cols['o2_col'].Add( Block('o2_block', o2_val) )

        SelectableBlockTags = ['h1_block', 't1_block', 'o1_block', 'h2_block', 't2_block', 'o2_block']

        # answer columns get zeros
        for coltag in ['hA_col', 'tA_col', 'oA_col']:
            Cols[coltag].ShowValue(0)

    elif mode.get() == SUB_MODE:
        Cols['hA_col'].Add( Block('hA_block', h1_val) )
        Cols['tA_col'].Add( Block('tA_block', t1_val) )
        Cols['oA_col'].Add( Block('oA_block', o1_val) )

        Cols['h2_col'].Add( Block('h2_block', h2_val) )
        Cols['t2_col'].Add( Block('t2_block', t2_val) )
        Cols['o2_col'].Add( Block('o2_block', o2_val) )

        SelectableBlockTags = ['h2_block', 't2_block', 'o2_block']

def BorrowButtons():
    """
    reconfigure borrow buttons for multiple columns
    """
    for colchar in ('t', 'o'):
        to_tag = AnswerColumnTag(colchar)
        to_col = Cols[to_tag]
        from_col = to_col.ColumnToLeft()
        from_tag = from_col.tag

        current_val = to_col.Total()
        subtract_val = Cols['%s2_col' % colchar].Total()
        borrow_tag = '%s_borrow' % colchar

        # remove any existing borrow image(s)
        Canv.delete(borrow_tag)

        # as appropariate, create borrow image and set binding
        if current_val < subtract_val:
            startx, starty = LowerLeft(to_tag)
            Canv.create_image(startx, starty+10,
                              image=RIGHT_ARROW, tags=borrow_tag)
            Canv.tag_bind(borrow_tag, "<Button-1>", from_col.Borrow)

def CalcAnswer():
    """
    show the final answer, if all original blocks have been "played"
    and no more carrying/borrowing needs to be done
    """
    if mode.get() == ADD_MODE:
        input_tags = ['h1_col', 't1_col', 'o1_col', 'h2_col', 't2_col', 'o2_col']
        answ_tags = ['xA_col', 'hA_col', 'tA_col', 'oA_col']
    elif mode.get() == SUB_MODE:
        input_tags = ['h2_col', 't2_col', 'o2_col']
        answ_tags = ['hA_col', 'tA_col', 'oA_col']

    col_totals = [Cols[tag].Total() for tag in input_tags]
    remaining_input = sum(col_totals)

    # ready to show the answer? (note: there is no 'BorrowCount' to check)

    if remaining_input == 0 and CarryCount == 0:
        anslist = [Cols[tag].Total() for tag in answ_tags]
        if mode.get() == ADD_MODE:
            answ['text'] = "%d" % (1000*anslist[0] + 100*anslist[1] + 10*anslist[2] + anslist[3])
        elif mode.get() == SUB_MODE:
            answ['text'] = "%d" % (100*anslist[0] + 10*anslist[1] + anslist[2])
        answ['bg'] = ANSW_COLOR
        Canv.bell()

def SetMode():
    """
    adjust labels on entry fields for ADD/SUB mode
    """
    if mode.get() == ADD_MODE:
        label_1['text'] = "First number"
        label_2['text'] = "Second number"
        signbtn['bitmap'] = "@plus.xbm"
        # display appropriate help text
        Canv.delete('help_sub')
        Canv.create_text(RootWin.winfo_width()+HELP_ADD_OFFSET, 20,
                         font=TEXT_FONT, text=HELP_ADD, tags='help_add',
                         anchor=T.N, justify=T.RIGHT)

    else:
        label_1['text'] = "Larger number"
        label_2['text'] = "Smaller number"
        signbtn['bitmap'] = "@minus.xbm"
        # display appropriate help text
        Canv.delete('help_add')
        Canv.create_text(RootWin.winfo_width()+HELP_SUB_OFFSET, 20,
                         font=TEXT_FONT, text=HELP_SUB, tags='help_sub',
                         anchor=T.N, justify=T.RIGHT)

    ValidateKey()
    Canv.update()

def Debug(evt):
    _=1

def NewCmd():
    """
    start over
    """
    # empty the canvas
    for obj in Canv.find_all():
        Canv.delete(obj)

    # reinit entry fields
    Canv.input_1.set("")
    Canv.input_2.set("")
    for obj in (signbtn, entry_1, entry_2):
        obj['state'] = T.NORMAL
    drawbtn['state'] = T.DISABLED
    entry_1.focus()
    answ['bg'] = BGND_COLOR
    answ['text'] = ""

    SetMode()

def ExitCmd():
    sys.exit(0)

def ClearSplash():
    Canv.delete(splash_id)

def HexString2List(hexstr):
    """
    convert a hex string: e.g. "#00FF03"
    to a list: [0, 255, 3]
    """
    rtn = []
    rtn.append(eval('0x' + hexstr[1:3]))
    rtn.append(eval('0x' + hexstr[3:5]))
    rtn.append(eval('0x' + hexstr[5:]))

    return rtn

def ChangeSign():
    """
    change between add/sub modes
    """
    global mode
    if mode.get() == ADD_MODE:
        mode.set(SUB_MODE)
        SetMode()
    elif mode.get() == SUB_MODE:
        mode.set(ADD_MODE)
        SetMode()

####################
#################### main routine
####################

if __name__ == '__main__':
    ##
    ## set up TK window
    ##
    RootWin = T.Tk()

    # window geometry handling needs to be smarter!
    if ShowMeDo_800_600:
        RootWin.geometry('%dx%d+%d+%d' % (760, 520, 20, 20))
    else:
        RootWin.geometry('%dx%d+%d+%d' % (820, 520, 50, 50))

    RootWin.option_add('*font', FONT)
    RootWin.title("BlockHead")
    # don't allow window resizing
    RootWin.resizable(0,0)

    ##
    ## canvas
    ##

    Canv = T.Canvas(RootWin)
    Canv.pack(side=T.TOP, expand=True, fill=T.BOTH)
    Canv['bg'] = BGND_COLOR

    # set up mouse bindings
    Canv.bind('<Button-1>', MouseDown)
    Canv.bind('<Button1-Motion>', MouseMotion)
    Canv.bind('<Button1-ButtonRelease>', MouseUp)

    # variables for entry fields
    Canv.input_1 = T.IntVar()
    Canv.input_2 = T.IntVar()

    ##
    ## control panel
    ##

    Ctrl = T.Frame(RootWin)
    Ctrl.pack(side=T.TOP, fill=T.X)
    Ctrl.option_add("*Entry*width", 5)
    Ctrl.option_add("*Label*width", 13)
    Ctrl.option_add("*Button*borderWidth", 2)

    ##
    ## GRID subframe containing numbers, their labels, and operators
    ##
    numbers_frm = T.Frame(Ctrl)
    numbers_frm.pack(side=T.LEFT, expand=True, fill=T.X)
    numbers_grid = T.Frame(numbers_frm)
    numbers_grid.pack(anchor=T.CENTER)

    # first number
    entry_1 = T.Entry(numbers_grid, justify=T.CENTER, textvariable=Canv.input_1)
    label_1 = T.Label(numbers_grid, text="?")
    entry_1.grid(row=0, column=0)
    label_1.grid(row=1, column=0)

    # sign (+ or -)
    signbtn = T.Button(numbers_grid, width=26, bitmap="@plus.xbm", command=ChangeSign)
    signbtn.grid(row=0, column=1)

    # second number
    entry_2 = T.Entry(numbers_grid, justify=T.CENTER, textvariable=Canv.input_2)
    label_2 = T.Label(numbers_grid, text="?")
    entry_2.grid(row=0, column=2)
    label_2.grid(row=1, column=2)

    # equals
    T.Label(numbers_grid, text="  =  ", width=4, font=(FONTNAME, 20, 'bold')).grid(row=0, column=3)

    # answer
    # use standard width for Entry, not Label
    answ = T.Label(numbers_grid, justify=T.CENTER, width=5, text="")
    answ.grid(row=0, column=4)
    # pad to make more room for thousands column
    T.Label(numbers_grid, text="Answer", width=6).grid(row=1, column=4, padx=25)

    ##
    ## PACK subframe containing control buttons
    ##
    mode = T.IntVar()
    btns_frm = T.Frame(Ctrl)
    btns_frm.pack(side=T.LEFT, padx=15)

    T.Button(btns_frm, text="Exit", command=ExitCmd).pack(side=T.RIGHT)
    T.Button(btns_frm, text="New" , command=NewCmd).pack(side=T.RIGHT)
    drawbtn = T.Button(btns_frm, text="Draw Blocks", command=DrawBlocks)
    drawbtn.pack(side=T.RIGHT, padx=10)

    # initialize control panel
    mode.set(ADD_MODE)    

    Canv.input_1.set("")
    Canv.input_2.set("")
    entry_1.bind('<KeyRelease>', ValidateKey)
    entry_2.bind('<KeyRelease>', ValidateKey)
    answ['bg'] = BGND_COLOR
    entry_1['bg'] = INPT_COLOR
    entry_2['bg'] = INPT_COLOR

    # carry/borrow images (must wait to create)
    LEFT_ARROW = T.BitmapImage(file="left_arrow.xbm", foreground=CARRY_COLOR)
    RIGHT_ARROW = T.BitmapImage(file="right_arrow.xbm", foreground=CARRY_COLOR)

    # splash screen
    Canv.update()
    splash_id = Canv.create_text(RootWin.winfo_width()*0.5, RootWin.winfo_height()*0.4,
                                 text = "BlockHead\n\nAddition/Subtraction\nCalculator",
                                 justify=T.CENTER, font=SPLASHFONT)
    # remove splash screen after pause
    RootWin.after(2500, ClearSplash)
    SetMode()

    # enable debugging
    RootWin.bind('<Button-3>', Debug)

    # go
    RootWin.mainloop()
    sys.exit(0)
