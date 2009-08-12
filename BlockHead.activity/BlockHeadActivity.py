#!/usr/bin/env python
# BlockHeadActivity.py -- visual calculator for addition and subtraction of whole numbers
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
BlockHeadActivity -- visual calculator

add or subtract two multiple-digit numbers,
with number base <= 10
"""

__date__ = '12-Aug-2009'
__version__ = 2055

SUGAR_ACTIVITY = True

import pygtk
pygtk.require('2.0')
import gtk
import pango
if SUGAR_ACTIVITY:
    from sugar.activity import activity
    import logging
import os
import sys
from time import sleep

SnapX = SnapY = ClickX = ClickY = TargetColumn = None
CarryCount = 0
DropOk = False

class P():
    """
    overall parameters
    """
    # debug flag
    DEBUG = False

    # show help button and help window?
    HELP_ENABLE = False

    # show exit button?
    EXIT_ENABLE = False if SUGAR_ACTIVITY else True

    # number of columns
    COL_COUNT = 3

    # number base
    BASE = 10
    VALID_DIGITS = map(str, range(BASE))

    # animation times
    IN_COL = 0.10
    COL_TO_COL = 0.20
    SHRINK_EXPAND_DELAY = 0.07
    PAUSE = 0.25

    ###
    ### sizes
    ###

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
    ARROW_OFFSET = (-10, 10)
    # distance between carry/borrow arrow and digit
    ANSR_OFFSET = ARROW_OFFSET[1] + 25
    # height adjustment for control panel, to ensure display of carry/borrow blocks
    WINDOW_HGT_ADJ = 100

    # operations,  modes
    ADD_MODE, SUBTRACT_MODE, CARRY, BORROW = range(4)

    # fonts
    FONTNAME = "Sans Bold"
    FONT = pango.FontDescription("%s 12" % FONTNAME)
    EQUAL_SIGN_FONT = pango.FontDescription("%s 24" % FONTNAME)
    HELP_FONT = pango.FontDescription("%s 11" % FONTNAME)

    ###
    ### colors
    ###
    
    ANSW_COLOR = '#00CCFF'
    CAN_DROP_COLOR = 0x00FF0000
    CANNOT_DROP_COLOR = 0x22222200

    # colors repeat every N columns
    COLUMN_PIXEL_COLORS = [0xA6E2F400, 0xFFD5D700, 0xD3FFD300, 0xFEEDB100, 0xD1B5F300, 0xD8C3C100,
                        0xA6E2F400, 0xFFD5D700, 0xD3FFD300, 0xFEEDB100,
                        ]

    # get rid of unneeded column colors
    assert(len(COLUMN_PIXEL_COLORS) >= COL_COUNT)
    del COLUMN_PIXEL_COLORS[COL_COUNT:]
    
    # gray column for final carry
    COLUMN_PIXEL_COLORS.append(0xE8E8E800)

    BLOCK_PIXEL_COLORS = [0x3280EA00, 0xE35BA000, 0x6FD48A00, 0xF2BC0200, 0xCB00FF00, 0x99667600,
                          0x3280EA00, 0xE35BA000, 0x6FD48A00, 0xF2BC0200,
                          ]

    # get rid of unneeded block colors
    del BLOCK_PIXEL_COLORS[COL_COUNT:]
    # gray color for block created by final carry
    BLOCK_PIXEL_COLORS.append(0xC0C0C000)

    # texts and strings
    # widths set to None, will be populated by SetDisplayStringWidths()
    DISPLAY_STR = {
        'first': ["First Number", None],
        'second': ["Second Number", None],
        'larger': ["Larger Number", None],
        'smaller': ["Smaller Number", None],
        'answer': ["Answer", None],
    }

class HelpWindow(gtk.Window):
    """
    window to display help text for ADD mode or SUB mode
    """
    WID = 470
    HGT = 250
    FONT_STRING = "Sans Bold 11"
    BG_COLOR = '#EEEAFA'
    HEAD_COLOR = 'red'

    # help texts
    HELP_ADD = """ADD TWO NUMBERS
Enter two numbers to be added, then click "Draw Blocks".
Drag each block that appears to the corresponding (same-color) answer column.
If an answer column's total is 10 or more, click the "carry" arrow that appears below the answer column.
Click the "+" operator between the numbers to change it to "-".
"""

    HELP_SUB = """SUBTRACT TWO NUMBERS
Enter the larger and smaller numbers, then click "Draw Blocks".
Drag the blocks for the smaller number to the corresponding columns of the larger number.
In the larger number, you may need to click one or more "borrow" arrows -- they appear below columns whose blocks are too short to subtract from.
Click the "-" operator between the numbers to change it to "+".
"""

    def __init__(self):
        gtk.Window.__init__(self)
        self.set_title("BlockHead Help")
        self.set_transient_for(MainWin)
        self.connect('destroy', lambda _: self.Cleanup())
        self.set_size_request(self.WID, self.HGT)
        self.move(10,10)

        # buffer
        self.tbuf = gtk.TextBuffer()

        # view
        tv = gtk.TextView(self.tbuf)
        tv.modify_base(gtk.STATE_NORMAL, tv.get_colormap().alloc_color(self.BG_COLOR))
        tv.set_left_margin(10)
        tv.set_pixels_above_lines(10)
        tv.set_wrap_mode(gtk.WRAP_WORD)
        tv.set_cursor_visible(False)
        self.add(tv)

        # format tags
        self.heading_tag = self.tbuf.create_tag(None, font=self.FONT_STRING, foreground=self.HEAD_COLOR)
        self.text_tag = self.tbuf.create_tag(None, font=self.FONT_STRING)

    def Update(self):
        """
        get rid of old text, display new text
        """
        help_text = self.HELP_ADD if Mode == P.ADD_MODE else self.HELP_SUB
        self.tbuf.set_text(help_text)

        start = self.tbuf.get_start_iter()
        end = self.tbuf.get_end_iter()
        # heading is first text line
        end_of_hd = self.tbuf.get_iter_at_offset(help_text.index("\n"))

        self.tbuf.apply_tag(self.heading_tag, start, end_of_hd)
        self.tbuf.apply_tag(self.text_tag, end_of_hd, end)

        # show help, but main window always gets focus back
        self.show_all()
        MainWin.present()

    def Cleanup(self):
        """
        remove help window
        """
        global HelpWin

        self.destroy()
        HelpWin = None

class AnswerLabel(gtk.EventBox):
    """
    widget that implements a background for a gtk.Label
    """

    # standard bg color (in NORMAL state), to make label seem transparent
    std_bgcolor = tuple(gtk.Fixed().get_style().bg)[gtk.STATE_NORMAL]

    def __init__(self):
        gtk.EventBox.__init__(self)
        # add a label that displays its text centered NSEW
        lab = gtk.Label()
        lab.set_alignment(0.5, 0.5)
        self.add(lab)

        self.Reset()

    def Reset(self):
        """
        empty the label
        """
        lab = self.child
        lab.set_text("")
        SetBgColor(self, self.std_bgcolor)

    def set_text(self, textstr):
        """
        like gtk.Label.set_text()
        """
        self.child.set_text(textstr)
        SetBgColor(self, P.ANSW_COLOR)

    def set_sensitive(self, arg):
        """
        like gtk.Widget.set_sensitive()

        enables AnswerLabel to be process in a list of gtk.Entry objects
        """
        pass

    def modify_font(self, font):
        self.child.modify_font(font)

class BlockPanel(object):
    """
    canvas on which columns and blocks are drawn by program
    and dragged by user
    """
    def __init__(self, wid, hgt):
        self.canv = gtk.Fixed()
        self.canv.set_size_request(wid, hgt)

class CtrlPanel(gtk.Frame):
    """
    input fields, labels, and buttons at bottom of BlockHead window
    """
    # offsets into buttons list
    DRAW, NEW, HELP, EXIT = range(4)
    # offsets into entries/labels lists
    N1, N2, ANS = range(3)

    def __init__(self, wid, hgt):
        gtk.Frame.__init__(self)
        
        ###
        ### create control widgets
        ###

        # entry fields and labels (includes answer field, too)
        self.entries = [gtk.Entry(max=P.COL_COUNT), gtk.Entry(max=P.COL_COUNT), AnswerLabel()]
        self.entry_labels = [gtk.Label(P.DISPLAY_STR["first"][0]),
                             gtk.Label(P.DISPLAY_STR["second"][0]),
                             gtk.Label(P.DISPLAY_STR["answer"][0]),
                             ]

        for i in self.N1, self.N2:
            self.entries[i].set_width_chars(P.COL_COUNT)
            self.entries[i].connect("key_release_event", self.ValidateInput)
            self.entries[i].set_alignment(0.5)

        self.entries[self.ANS].child.set_width_chars(P.COL_COUNT+1)
        self.entries[self.ANS].child.set_alignment(0.5, 0.5)

        # operator button (toggles "+" and "-")
        self.opbtn = gtk.Button()
        self.opbtn.connect("clicked", self.ChangeSign)
        self.algn_op = gtk.Alignment(0.5, 0.5)
        self.algn_op.add(self.opbtn)

        # equals sign
        equ = gtk.Label("=")
        self.algn_equ = gtk.Alignment(0.5, 0.5)
        self.algn_equ.add(equ)

        # control buttons
        self.ctrlbtns = [None, None, None, None]
        self.ctrlbtns[self.DRAW] = gtk.Button("Draw Blocks")
        self.ctrlbtns[self.DRAW].connect("clicked", self.DrawBlocksCmd)
        self.ctrlbtns[self.NEW] = gtk.Button("New")
        self.ctrlbtns[self.NEW].connect("clicked", self.NewCmd)
        if P.EXIT_ENABLE:
            self.ctrlbtns[self.EXIT] = gtk.Button("Exit")
            self.ctrlbtns[self.EXIT].connect("clicked", gtk.main_quit)
        else:
            del self.ctrlbtns[self.EXIT]
        if P.HELP_ENABLE:
            self.ctrlbtns[self.HELP] = gtk.Button("Help")
            self.ctrlbtns[self.HELP].connect("clicked", self.HelpCmd)
        else:
            del self.ctrlbtns[self.HELP]

        # font settings
        for wgt in (self.entries + self.entry_labels):
            wgt.modify_font(P.FONT)
        for wgt in self.ctrlbtns:
            # gtk.Label is the "child" of gtk.Button
            wgt.child.modify_font(P.FONT)
        equ.modify_font(P.EQUAL_SIGN_FONT)

        ###
        ### lay out widgets
        ###

        # top level: HBox with lots of columns, each one a VBox
        SA, COL_1, SB, COL_OP, SC, COL_2, SD, COL_EQ, SE, COL_ANS, SF = range(11)
        
        overall_box = gtk.HBox()
        self.cols = []
        for i in range(11):
            onecol = gtk.VBox()
            self.cols.append(onecol)
            overall_box.pack_start(onecol)

        ##
        ## process the "real" columns
        ##
        
        self.cols[COL_1].pack_start(self.entries[self.N1])
        # fixed-width spacer prevents jitter when switching ADD/SUB modes
        fx1 = gtk.Fixed()
        fx1.set_size_request(max(P.DISPLAY_STR['first'][1], P.DISPLAY_STR['larger'][1]), 5)
        self.cols[COL_1].pack_start(fx1)
        self.cols[COL_1].pack_start(self.entry_labels[self.N1])

        self.cols[COL_OP].pack_start(self.algn_op)

        self.cols[COL_2].pack_start(self.entries[self.N2])
        # fixed-width spacer prevents jitter when switched ADD/SUB modes
        fx2 = gtk.Fixed()
        fx2.set_size_request(max(P.DISPLAY_STR['second'][1], P.DISPLAY_STR['smaller'][1]), 5)
        self.cols[COL_2].pack_start(fx2)
        self.cols[COL_2].pack_start(self.entry_labels[self.N2])

        self.cols[COL_EQ].pack_start(self.algn_equ)

        self.cols[COL_ANS].pack_start(self.entries[self.ANS])
        self.cols[COL_ANS].pack_start(self.entry_labels[self.ANS])

        ##
        ## process the spacer columns
        ##
        
        # use gtk.Fixed objects to set widths
        self.spacer_wgts = {}
        for key in [SA, SB, SC, SD, SE, SF]:
            self.spacer_wgts[key] = gtk.Fixed()
            self.cols[key].pack_start(self.spacer_wgts[key])

        # use largest width of enclosed "real" column to determine proper width
        for i in [SA, SB]:
            self.spacer_wgts[i].set_size_request(SpacerWidth(('first', 'larger')), 13)
        for i in [SC, SD]:
            self.spacer_wgts[i].set_size_request(SpacerWidth(('second', 'smaller')), 13)

        # to left of answer: flag indicates need for extra space, for carry column
        self.spacer_wgts[SE].set_size_request(SpacerWidth(('answer',), True), 13)
        # to right of answer: not much space needed, can overlap buttons at right
        self.spacer_wgts[SF].set_size_request(25, 13)

        # box of buttons goes into the horizontal box flush-right, with padding
        ctrlbtns_box = gtk.HBox(spacing=2)
        for btn in self.ctrlbtns:
            ctrlbtns_box.pack_start(btn)

        # ... gtk.Alignment keeps buttons from filling vertical space
        buttons_box_algn = gtk.Alignment(0.5, 0.5)
        buttons_box_algn.add(ctrlbtns_box)
        overall_box.pack_end(buttons_box_algn, padding=5)

        # place horizontal box into control panel frame
        self.add(overall_box)
        self.show_all()

    def ChangeSign(self, btn):
        """
        toggle between ADD/SUB modes
        """
        global Mode

        if Mode == P.ADD_MODE:
            Mode = P.SUBTRACT_MODE
        elif Mode == P.SUBTRACT_MODE:
            Mode = P.ADD_MODE

        InitializeMode()

        if HelpWin:
            HelpWin.Update()

        # might need to enable/disable "Draw Blocks" button
        self.ValidateInput(None, None)

    def HelpCmd(self, _btn="not used"):
        """
        display help text in top-level window
        """
        global HelpWin

        if not HelpWin:
            HelpWin = HelpWindow()

        HelpWin.Update()

    def NewCmd(self, _btn="not used"):
        """
        start over
        """
        # empty the canvas
        for obj in Bpnl.canv.get_children():
            try:
                obj.destroy()
            except Exception, exc_data: # ?? what kinds of exceptions can be raised?
                print "exception in NewCmd():", exc_data
                pass

        # reinit entry fields, reset focus
        for ent in self.entries:
            ent.set_text("")
            ent.set_sensitive(True)
        self.entries[Cpnl.N1].grab_focus()

        # reinit buttons
        for btn in self.ctrlbtns + [self.opbtn]:
            btn.set_sensitive(True)
        self.ctrlbtns[self.DRAW].set_sensitive(False)

        # reinit answer label
        self.entries[Cpnl.ANS].Reset()

        # continue with mode-specific initialization
        InitializeMode()

    def DrawBlocksCmd(self, _btn="not used"):
        """
        get values from Entry fields
        draw columns
        draw a block to represent each digit
        """
        global Num1, Num2, NumA

        # these are STRINGs, not INTs, normalize to P.COL_COUNT width
        digits = [None, None]
        for i in range(2):
            digits[i] = Cpnl.entries[i].get_text().zfill(P.COL_COUNT)

        # base y-coordinate for columns
        bottomY = 2 * P.COL_HGT

        # get allocations of entry fields and answer field
        allocs = [ ent.allocation for ent in Cpnl.entries]

        if Mode == P.ADD_MODE:
            # center column block over first input number
            Num1 = Number("n1", digits[0], allocs[0].x + allocs[0].width // 2, bottomY)
            # center column block over second input number
            Num2 = Number("n2", digits[1], allocs[1].x + allocs[1].width // 2, bottomY)
            # center column block over first answer number
            NumA = AnswerNumber("nA", None, allocs[2].x + allocs[2].width // 2, bottomY)

        elif Mode == P.SUBTRACT_MODE:
            # Answer in SUB mode is a little higher
            NumA = AnswerNumber("nA", digits[0], allocs[0].x + allocs[0].width // 2, bottomY - P.ANSR_OFFSET)
            Num2 = Number("n2", digits[1], allocs[1].x + allocs[1].width // 2, bottomY)

            # enable borrow buttons (maybe)
            DrawBorrowButtons()

        # disable button and entry fields
        for obj in [self.ctrlbtns[self.DRAW], self.opbtn] + self.entries:
            obj.set_sensitive(False)

        # update panel
        Bpnl.canv.show_all()

    def ValidateInput(self, fld, event):
        """
        after a keystroke, determine whether the two input fields have valid numbers
        """
        if event:
            # remove invalid characters
            char = event.string
            if (char
                and
                char not in P.VALID_DIGITS
                and
                # is the offending character still there?
                # it might have been deleted already by field's max-length property
                char in fld.get_text()
                ):
                cur = fld.get_position()
                fld.delete_text(cur-1, cur)

        # input values are STRINGs not INTs, to support non-decimal arithmetic
        entry_strings = [None, None]
        for i in [0,1]:
            entry_strings[i] = self.entries[i].get_text()

        # enable Draw button if entries are valid
        # cannot enable if one or both of the input fields is blank
        if (all(entry_strings)
            and
            (Mode == P.ADD_MODE
             or
             (Mode == P.SUBTRACT_MODE and int(entry_strings[0]) >= int(entry_strings[1]))
             )
            ):
            self.ctrlbtns[self.DRAW].set_sensitive(True)
        else:
            self.ctrlbtns[self.DRAW].set_sensitive(False)

class Number(object):
    """
    one number, to be added or subtracted
    (the answer number is subtype: AnswerNumber)
    """
    def __init__(self, id, digits, x, y):
        self.id = id
        # STRING of digits, not INT
        self.digits = digits
        # X-coordinate of center of column-set
        self.centerX = x
        # Y-coordinate of bottom of column-set
        self.bottomY = y
        self.columns = self.InitColumns(P.COL_COUNT)
        self.InitBlocks()

    def InitColumns(self, count):
        """
        create Column objects in self.columns list

        determine proper location for the entire "column set",
        then invoke Draw() to draw each column
        """
        # all X-coordinates are offsets from the middle column's position

        if count % 2 == 1:
            # odd number of columns
            middle_idx = count // 2 # which is the middle column?
            offset = -P.COL_WID / 2 # middle column does not start at center of column-set
        else:
            # even number of columns
            middle_idx = count / 2 - 1
            offset = 0 # middle column DOES start at center of column-set

        # create columns
        col_list = [Column(i) for i in range(count)]

        # configure column locations
        for idx,col in enumerate(col_list):
            col.number_obj = self

            # (x,y) of column lower-left corner
            col.x = self.centerX + (middle_idx - idx) * P.COL_WID + offset
            col.y = self.bottomY

            col.Draw()

            # column total
            Bpnl.canv.put(col.total_label,
                          col.x + P.COL_WID/2,
                          col.y + P.ANSR_OFFSET)

        # record list in attribute
        return col_list

    def InitBlocks(self):
        """
        create Block objects in each Column of self.columns list,
        using self.digits
        """
        if isinstance(self, AnswerNumber) and Mode == P.ADD_MODE:
            return

        assert(len(self.columns) == len(self.digits))

        # convert STRING to list of INTs
        digit_list = map(int, list(self.digits))
        # we will process digits starting at the ONES column
        digit_list.reverse()

        # draw a block in each column
        for col in self.columns:
            # block size is corresponding digit in digit_list
            val = digit_list[col.Index()]

            # nothing to do if size is ZERO
            if val == 0:
                continue

            # create block, and place it in column
            # block's color is determined by column's position
            blk = Block(val, col)
            #DbgPrint("before initial add:", tuple(blk.drag_wgt.allocation))

            # do not enable dragging in the answer column (occurs in SUB mode only)
            if not isinstance(self, AnswerNumber):
                blk.EnableDrag()

            #DbgPrint("before initial show", tuple(blk.drag_wgt.allocation))
            col.Show()
            #DbgPrint("after initial show", tuple(blk.drag_wgt.allocation))

class AnswerNumber(Number):
    """
    a Number object to be used as the answer
    """
    def __init__(self, id, digits, x, y):
        self.id = id
        # STRING of digits, not INT
        self.digits = digits
        # X-coordinate of center of column-set
        self.centerX = x
        # Y-coordinate of bottom of column-set
        self.bottomY = y
        self.columns = (self.InitColumns(P.COL_COUNT+1)
                        if Mode == P.ADD_MODE else
                        self.InitColumns(P.COL_COUNT))

        if Mode == P.SUBTRACT_MODE:
            self.InitBlocks()

class Column():
    """
    represents one column (ones, tens, hundreds)
    """
    def __init__(self, colnumber):
        """
        initialize a column, either input or answer
        """
        self.color = P.COLUMN_PIXEL_COLORS[colnumber]

        # list of Block objects in this column
        self.blocks = []

        # will be created later
        self.carryarrow = self.borrowarrow = None

        # will be filled in by Column.Draw()
        self.image = None

        self.total_label = gtk.Label()
        self.total_label.modify_font(P.FONT)
        self.total_label.show()

    def Index(self):
        """
        return index within Number.columns
        (to indicate ones column, tens column, etc.)
        """
        return self.number_obj.columns.index(self)

    def UpperLeft(self):
        """
        return (x,y) of the column's upper-left corner
        i.e. corner of its Image (self.image)
        """
        return self.x, self.y - P.COL_HGT

    def Draw(self):
        """
        draw a column, starting at lower left corner (x,y)
        """
        """
        Image -> Pixbuf
        """
        # (width, height) of column
        mysize = (P.COL_WID, P.COL_HGT)

        # sized image
        img = gtk.Image()
        img.set_size_request(*mysize)

        # color it in
        PixelFill(img, self.color)

        pbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, *mysize)
        pbuf.fill(self.color)
        img.set_from_pixbuf(pbuf)

        # place column on canvas (gtk.Fixed)
        Bpnl.canv.put(img, *self.UpperLeft())

        # cross-register gtk.Image and app's Column object
        self.image = img
        img.column = self

    def ColumnToRight(self):
        """
        return Column to right of this column
        """
        return self.number_obj.columns[self.Index() - 1]

    def ColumnToLeft(self):
        """
        return Column to left of this column
        """
        return self.number_obj.columns[self.Index() + 1]

    def Remove(self, blk):
        """
        remove the specified block from this column
        """
        self.blocks.remove(blk)

    def Add(self, blk, carry_button_suppress=False):
        """
        send an existing block to this column
        """
        # carry_button_suppress is needed when creating a P.BASE-size ("filled") block
        # during execution of Carry() method

        global CarryCount

        # save current column total, before adding new block
        old_total = self.Total()

        # cross-register Block and Column objects
        self.blocks.append(blk)
        blk.column = self

        # SUB: maybe we're done
        if Mode == P.SUBTRACT_MODE or blk.value == 0:
            return

        # ADD maybe create carry arrow
        if self.Total() >= P.BASE and not carry_button_suppress and not self.carryarrow:
            self.carryarrow = gtk.Button()
            self.carryarrow.set_property("image", gtk.image_new_from_pixbuf(Pix[P.CARRY]))
            Bpnl.canv.put(self.carryarrow,
                           self.x + P.ARROW_OFFSET[0],
                           self.y + P.ARROW_OFFSET[1])
            self.carryarrow.connect("clicked", self.Carry)
            self.carryarrow.hide_all()
            CarryCount += 1
            DbgPrint("Created carry arrow:", self.carryarrow)

    def Show(self):
        """
        display the column's blocks
        display the total of the blocks in a label below the column
        """

        # calculation of total is always performed in base-10
        total = 0

        for blk in self.blocks:
            Bpnl.canv.move(blk.drag_wgt,
               self.x + P.BLOCK_PAD,
               # first, adjust upward by height of block
               # second, adjust upward to account for earlier blocks in this column
               self.y - (blk.value * P.UNIT_HGT) - (total * P.UNIT_HGT))

            #blk.drag_wgt.show()

            # update column total
            total += blk.value

        # maybe: carry arrow
        if self.carryarrow:
            self.carryarrow.show_all()

        # convert total value to string, using P.BASE, and display it

        ## single digit
        if total < P.BASE:
            strval = str(total)
        ## two digits
        else:
            digit_list = map(str, list(divmod(total, P.BASE)))
            strval = "".join(digit_list)

        self.total_label.set_text(strval)
        self.total_label.show()

        # display new column configuration: blocks, carry arrow, and total label
        UpdateScreen()

    def Total(self):
        """
        base-10 total of column's blocks
        """
        values = [blk.value for blk in self.blocks]
        return sum(values)

    def Carry(self, event):
        """
        calculate carry for specified column
        btn = ID of dynamically-created carry button, to be deleted
        """
        global CarryCount

        srccol = self
        destcol = srccol.ColumnToLeft()

        # delete carry arrow
        srccol.carryarrow.destroy()
        srccol.carryarrow = None
        CarryCount -= 1

        # save total value of blocks, for creation of new blocks
        total = srccol.Total()

        # clear out all the blocks in this column
        for blk in srccol.blocks:
            blk.DisableDrag()
            blk.drag_wgt.destroy()
        srccol.blocks = []

        # block of P.BASE units
        fillblk = Block(P.BASE, srccol, True)
        #DbgPrint("before carry add:", tuple(fillblk.drag_wgt.allocation))
        #DbgPrint("after carry add:", tuple(fillblk.drag_wgt.allocation))

        # "excess block" (1+ units)
        excessblk = None
        if total > P.BASE:
            excessblk = Block(total - P.BASE, srccol, True)

        srccol.Show()
        sleep(P.PAUSE)

        # collapse the block of P.BASE units into a single unit
        # TBD: change the color to that of the "carry-to" column
        pbufs = fillblk.GenScaledPixbufs(P.ADD_MODE)

        for smaller_pbuf in pbufs:
            eventbox = fillblk.drag_wgt
            # get rid of old image, add new one
            eventbox.remove(eventbox.get_child())
            eventbox.add(gtk.image_new_from_pixbuf(smaller_pbuf))
            # show animatation step
            UpdateScreen()
            sleep(P.SHRINK_EXPAND_DELAY)

        # move the shrunken (1-unit-high) block to the next column
        sleep(P.PAUSE)
        AniMove(fillblk.drag_wgt,
                destcol.x + P.BLOCK_PAD,
                destcol.y - destcol.Total()*P.UNIT_HGT - 1*P.UNIT_HGT)

        # dest column: replace shrunken P.BASE-unit block with 1-unit "carry block"
        carryblk = Block(1, destcol)
        destcol.Show()

        # drop the "excess block" into position
        if excessblk:
            AniMove(excessblk.drag_wgt,
                    srccol.x + P.BLOCK_PAD,
                    srccol.y - excessblk.value * P.UNIT_HGT)

        # source column: delete the "fill block", and update column total
        fillblk.drag_wgt.destroy()
        srccol.Remove(fillblk)
        srccol.Show()

        # are we done?
        CalcAnswer()

    def Borrow(self, event):
        """
        borrow 1 unit FROM this column:
        send P.BASE units to the column to the right
        """
        # can we borrow from this column?
        # if not, first borrow from column to the left
        if self.Total() == 0:
            self.ColumnToLeft().Borrow(event)
            sleep(P.PAUSE)

        srccol = self
        destcol = srccol.ColumnToRight()
        srccol_index = srccol.Index()

        # decompose last block in this column (ex: 8 --> 7+1)
        borrow_orig_blk = srccol.blocks[-1]
        borrow_val = borrow_orig_blk.value

        # delete the topmost block from this column
        borrow_orig_blk.drag_wgt.destroy()
        srccol.Remove(borrow_orig_blk)

        # delete the borrow arrow
        if srccol.borrowarrow:
            srccol.borrowarrow.destroy()
            srccol.borrowarrow = None

        # create block of size N-1, to be left behind in this column
        if borrow_val > 1:
            remaining_blk = Block(borrow_val-1, srccol)
            srccol.Show()

        # create block of size 1, which will get borrowed
        borrow_from_blk = Block(1, srccol)
        srccol.Show()

        # at GTK level, move the unexpanded (1-unit-high) block to next column
        top_of_destblock_Y = destcol.y - destcol.Total()*P.UNIT_HGT
        AniMove(borrow_from_blk.drag_wgt,
                destcol.x + P.BLOCK_PAD,
                top_of_destblock_Y - 1*P.UNIT_HGT)

        # expand vertically from 1 unit to P.BASE units
        sleep(P.PAUSE)
        eventbox = borrow_from_blk.drag_wgt
        for i in range(1, P.BASE+1):
            eventbox.remove(eventbox.get_child())
            img, _ = CreateBlockImage(i, P.BLOCK_PIXEL_COLORS[self.Index()-1], True)
            eventbox.add(img)
            Bpnl.canv.move(eventbox,
                eventbox.allocation.x,
                top_of_destblock_Y - i*P.UNIT_HGT)
            # show animation step
            UpdateScreen()
            sleep(P.SHRINK_EXPAND_DELAY)

        # at application level, replace "borrow from" block in source column
        # with "borrow to" block in destination column
        borrow_from_blk.drag_wgt.destroy()
        srccol.Remove(borrow_from_blk)
        srccol.Show()
        borrow_to_block = Block(P.BASE, destcol)
        destcol.Show()

        # recalc the borrow buttons
        DrawBorrowButtons()

class Block(object):
    """
    represents one digit of a multipsrccol_indexigit number
    """
    def __init__(self, value, colobj, carry_button_suppress=False):
        self.value = value
        self.color = P.BLOCK_PIXEL_COLORS[colobj.Index()]
        # will be filled in by Column.Add()
        self.column = None

        # create rectangle image for the block
        # EventBox -> Image -> Pixmap -> Pixbuf
        # draw unit-lines on Pixmap

        # no image for zero value
        if self.value == 0:
            return

        # event box with sized image
        ebox = gtk.EventBox()
        img, self.pmap = CreateBlockImage(self.value, self.color)
        ebox.add(img)

        # cross-link draggable gtk.EventBox widget and app's Block object
        ebox.block = self
        ebox.set_double_buffered(False)
        self.drag_wgt = ebox

        # put the image in upper left corner, but make it invisible
        Bpnl.canv.put(self.drag_wgt, 0, 0)
        self.drag_wgt.hide_all()

        # allocate list for dragging callback IDs
        self.callback_ids = []

        # add the Block to the specified Column
        colobj.Add(self, carry_button_suppress)

    def UpperLeft(self):
        """
        return (x,y) of the block's upper-left corner
        i.e. corner of its EventBox (self.drag_wgt) which contains an Image
        """
        alloc = self.drag_wgt.allocation
        return (alloc.x, alloc.y)

    def GenScaledPixbufs(self, mode):
        """
        generate a set of scaled Pixbufs for this block,
        in decreasing size
        """
        # set the target vertical scaling factor
        start = 1.0
        end = 1.0/P.BASE if mode == P.ADD_MODE else 1.0*P.BASE

        mysize = (P.BLOCK_WID, self.value * P.UNIT_HGT)
        img = gtk.Image()
        img.set_size_request(*mysize)
        orig_pbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, *mysize)
        # initialize Pixbuf to original image, which was stored as a Pixmap
        orig_pbuf.get_from_drawable(self.pmap, img.get_colormap(), 0, 0, 0, 0, *mysize)

        # generator loop: yield a series of Pixbufs, of decreasing size
        x0, y0 = mysize
        count = 12
        for sf in (end*(1.0*i/count) + start*(1-1.0*i/count) for i in range(1, count+1)):
            # scale vertically, but not horizontally
            y = int(sf * y0)
            newpbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, x0, y)
            orig_pbuf.scale(newpbuf, 0,0, x0,y, 0,0, 1.0,sf, gtk.gdk.INTERP_BILINEAR)
            yield newpbuf

    def EnableDrag(self):
        """
        make block draggable
        """
        self.callback_ids.append(self.drag_wgt.connect("button_press_event", WidgetClicked))
        self.callback_ids.append(self.drag_wgt.connect("motion_notify_event", MoveWidget))
        self.callback_ids.append(self.drag_wgt.connect("button_release_event", PlaceWidget))

    def DisableDrag(self):
        """
        make block undraggable
        """
        for id in self.callback_ids:
            self.drag_wgt.disconnect(id)
        self.callback_ids = []

###
### functions
###

def WidgetClicked(widget, context):
    global SnapX, SnapY, ClickX, ClickY, TargetColumn

    alloc = widget.allocation
    # global (SnapX, SnapY) is location of widget when first clicked
    SnapX = alloc.x
    SnapY = alloc.y
    ClickX = context.x
    ClickY = context.y

    # raise widget to top of stack
    widget.window.raise_()

    # set the corresponding answer column as the drag-drop target
    TargetColumn = SetTargetColumn(widget)

    DbgPrint("widget allocation: (%d,%d) width=%d, height=%d" % (SnapX, SnapY, alloc.width, alloc.height))
    DbgPrint("offset within widget: (%d,%d)" % (ClickX, ClickY))

def SetTargetColumn(widget):
    """
    return the Column (i.e. gtk.EventBox) that is
    the target of the selected Block (i.e. gtk.EventBox)
    """
    col_number = widget.block.column.Index()
    target_obj = NumA.columns[col_number]
    return target_obj

def MoveWidget(widget, context):
    global DropOk

    blk = widget.block

    # in calculating offset, take into account position of mouse click
    # within the widget: (ClickX, ClickY)
    parentX, parentY = widget.translate_coordinates(Bpnl.canv, int(context.x), int(context.y))
    Bpnl.canv.move(widget, parentX - int(ClickX), parentY - int(ClickY))

    if InTargetColumn(widget):
        if Mode == P.ADD_MODE:
            PixelFill(TargetColumn.image, P.CAN_DROP_COLOR)
            DropOk = True
        elif Mode == P.SUBTRACT_MODE:
            if blk.value <= TargetColumn.Total():
                # can subtract now, without borrowing
                PixelFill(TargetColumn.image, P.CAN_DROP_COLOR)
                DropOk = True
            else:
                # cannot subtract now, need to borrow
                PixelFill(TargetColumn.image, P.CANNOT_DROP_COLOR)
                DropOk = False
    else:
        # reset target column background
        PixelFill(TargetColumn.image, TargetColumn.color)
        DropOk = False

def PlaceWidget(widget, context):

    global DropOk

    if Mode == P.ADD_MODE:
        PlaceWidget_Add(widget)
    elif Mode == P.SUBTRACT_MODE:
        PlaceWidget_Sub(widget)

    CalcAnswer()
    DropOk = False
    TargetColumn = None

def PlaceWidget_Sub(widget):
    """
    handle a mouse-up event in SUB mode
    """
    global DropOk

    blk = widget.block
    origcol = blk.column

    if DropOk:
        # superimpose block to be subtracted at top of current set of blocks

        current_value = TargetColumn.Total()
        sub_value = blk.value

        endX, endY = TargetColumn.blocks[-1].UpperLeft()

        # move the block to be subtracted
        AniMove(widget, endX, endY)
        sleep(P.PAUSE)

        # delete block from original column
        blk.drag_wgt.destroy()
        origcol.Remove(blk)
        origcol.Show()

        ##
        ## process result
        ##
        result = current_value - sub_value

        # clear target column
        for blk in TargetColumn.blocks:
            blk.DisableDrag()
            blk.drag_wgt.destroy()
        TargetColumn.blocks = []

        # create result block (maybe) and show value
        if result > 0:
            blk = Block(result, TargetColumn)
        TargetColumn.Show()

        # recalc the borrow buttons
        DrawBorrowButtons()

    else:
        # snap back
        AniMove(widget,
                origcol.x + P.BLOCK_PAD,
                origcol.y - blk.value*P.UNIT_HGT)

    # in all cases, reset flag and target column background
    PixelFill(TargetColumn.image, TargetColumn.color)
    DropOk = False

def PlaceWidget_Add(widget):
    """
    handle a mouse-up event in ADD mode
    """
    global DropOk, TargetColumn

    if DropOk:
        blk = widget.block
        origcol = blk.column
        destcolX, destcolY = TargetColumn.UpperLeft()

        # place block at target location
        endX = destcolX + P.BLOCK_PAD
        # y-coord takes into account column's existing blocks,
        # and reflects "offset downward from top of column" calculation
        endY = destcolY + P.UNIT_HGT * (P.BASE - TargetColumn.Total() - blk.value)

        # perform the move at GUI level
        AniMove(widget, endX, endY)

        # perform the move at object level, disable further interactions
        TargetColumn.Add(blk)
        origcol.Remove(blk)
        blk.DisableDrag()

        # reset target column background
        PixelFill(TargetColumn.image, TargetColumn.color)

        # show results
        origcol.Show()
        TargetColumn.Show()

    else:
        # snap back
        AniMove(widget, SnapX, SnapY)

def AniMove(widget, endX, endY):
    """
    animate the move of a widget from current position to (endX,endY)
    """
    origX = widget.allocation.x
    origY = widget.allocation.y
    count = 15
    for i in range(1, count+1):
        # set progress factor, and move a little
        pf = i * 1.0 / count
        widget.parent.move(widget,
                           int(pf*endX + (1-pf)*origX),
                           int(pf*endY + (1-pf)*origY))
        # show animation step
        UpdateScreen()
        sleep(P.IN_COL/count)

    # final move, to take care of roundoff errors
    widget.parent.move(widget, endX, endY)

def InTargetColumn(widget):
    """
    is the mouse in the drag-and-drop target column?
    """
    sect_tuple = tuple(widget.allocation.intersect(TargetColumn.image.allocation))
    return True if any(sect_tuple) else False

def PixelFill(image, color_int, wid=P.COL_WID, hgt=P.COL_HGT):
    """
    fill in a background image (for a column) with a color, specd as integer
    """
    pbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, wid, hgt)
    pbuf.fill(color_int)
    image.set_from_pixbuf(pbuf)

def DbgPrint(*arglist):
    """
    display debug data
    """
    if P.DEBUG:
        for arg in arglist:
            print arg,
        print

def InitializeMode():
    """
    adjust labels on entry fields for ADD/SUB mode
    display help text
    """
    # adjust labels
    if Mode == P.ADD_MODE:
        Cpnl.entry_labels[0].set_text(P.DISPLAY_STR['first'][0])
        Cpnl.entry_labels[1].set_text(P.DISPLAY_STR['second'][0])
    else:
        Cpnl.entry_labels[0].set_text(P.DISPLAY_STR['larger'][0])
        Cpnl.entry_labels[1].set_text(P.DISPLAY_STR['smaller'][0])

    Cpnl.opbtn.set_property("image", Pix[Mode])

def DrawBorrowButtons():
    """
    reconfigure borrow buttons for all columns
    """
    # "-1" because largest column cannot be the "to" of a borrow operation
    for idx in range(P.COL_COUNT-1):
        srccol = NumA.columns[idx+1]
        destcol = NumA.columns[idx]

        # as appropriate, create borrow image and set binding
        if destcol.Total() <  Num2.columns[idx].Total() and not srccol.borrowarrow:
            srccol.borrowarrow = gtk.Button()
            srccol.borrowarrow.set_property("image", gtk.image_new_from_pixbuf(Pix[P.BORROW]))
            srccol.borrowarrow.show_all()
            Bpnl.canv.put(srccol.borrowarrow,
                          destcol.x + P.ARROW_OFFSET[0],
                          destcol.y + P.ARROW_OFFSET[1])

            srccol.borrowarrow.connect("clicked", srccol.Borrow)
            DbgPrint("Created borrow arrow:", srccol.borrowarrow)

def CalcAnswer():
    """
    show the final answer, if all original blocks have been "played"
    and no more carrying/borrowing needs to be done
    """
    # are we ready to calculate?
    if Mode == P.ADD_MODE:
        if any([col.Total() for col in Num1.columns + Num2.columns]) or CarryCount > 0:
            return
    elif Mode == P.SUBTRACT_MODE: # note: there is no 'BorrowCount' to check
        if any([col.Total() for col in Num2.columns]):
            return

    # transcribe column totals
    digit_list = [col.Total() for col in NumA.columns]

    # special case: ZERO answer
    if sum(digit_list) == 0:
        strval = "0"

    # std case: INT list -> STRING
    else:
        # get rid of leading ZEROs (which are at the end of the list)
        while digit_list[-1] == 0:
            del digit_list[-1]
        # reverse digit list, and construct string value
        strval = "".join(map(str, reversed(digit_list)))

    # show and bell
    Cpnl.entries[2].set_text(strval)
    gtk.gdk.beep()

def SetBgColor(widget, colorstr):
    """
    set background color of a widget
    """
    widget.modify_bg(gtk.STATE_NORMAL, widget.get_colormap().alloc_color(colorstr))

def SetLabelColor(widget, colorstr):
    """
    set foreground color of a gtk.Label
    """
    widget.modify_fg(gtk.STATE_INSENSITIVE, widget.get_colormap().alloc_color(colorstr))

def UpdateScreen():
    """
    update the display screen
    """
    MainWin.show_all()
    while gtk.events_pending():
        gtk.main_iteration(False)

def CreateBlockImage(value, pixelcolor, borrow_block_flag=False):
    img = gtk.Image()
    wid, hgt = P.BLOCK_WID, value * P.UNIT_HGT
    img.set_size_request(wid, hgt)

    # color it in
    pbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, wid, hgt)
    pbuf.fill(pixelcolor)
    pmap = gtk.gdk.Pixmap(MyDrawable, wid, hgt, -1)
    pmap.set_colormap(img.get_colormap())
    pmap.draw_pixbuf(None, pbuf, 0, 0, 0, 0)

    # get ready to lines on pixmap, in black
    gc = gtk.gdk.GC(pmap)
    gc.set_rgb_fg_color(gtk.gdk.Color(0,0,0))

    # draw unit-lines
    if borrow_block_flag:
        line_count = P.BASE
        segment_hgt = value * P.UNIT_HGT // P.BASE
    else:
        line_count = value
        segment_hgt = P.UNIT_HGT

    for i in range(1, line_count):
        line_y = i * segment_hgt
        pmap.draw_line(gc,
                       0, line_y,
                       P.BLOCK_WID, line_y)

    # draw overall outline
    pmap.draw_rectangle(gc, False, 0,0, P.BLOCK_WID - 1,
                        value * P.UNIT_HGT -1)

    # set final image
    img.set_from_pixmap(pmap, None)

    # return both final image and the pixmap
    return img, pmap

def SetDisplayStringWidths():
    """
    determine, and save, the pixel widths of the control
    panel labels
    """
    # create layout for setting text in a font
    lay = gtk.TextView().create_pango_layout("")
    lay.set_font_description(P.FONT)

    # store string widths
    for k in P.DISPLAY_STR.keys():
        lay.set_text(P.DISPLAY_STR[k][0])
        P.DISPLAY_STR[k][1] = lay.get_pixel_size()[0]

def LoadImages():
    """
    create images/pixbufs from XPM data
    """
    LEFT_ARROW = [
        "30 12 2 1",
        "  c black",
        ". c None",
        "..    ........................",
        "..      ......................",
        "..        .................   ",
        ".        .................    ",
        ".       .................     ",
        "        .................    .",
        "  ..    .................    .",
        ".....   .............  .......",
        "..........     ....     ......",
        ".........       ..      ......",
        "..........      ..     .......",
        "............   ....  ........."
    ]

    RIGHT_ARROW = [
        "30 12 2 1",
        "  c black",
        ". c None",
        "........................    ..",
        "......................      ..",
        "   .................        ..",
        "    .................        .",
        "     .................       .",
        ".    .................        ",
        ".    .................    ..  ",
        ".......  .............   .....",
        "......     ....     ..........",
        "......      ..       .........",
        ".......     ..      ..........",
        ".........  ....   ............"        
    ]

    PLUS = [
        "26 20 2 1",
        "  c black",
        ". c None",
        "..........................",
        "...........    ...........",
        "...........    ...........",
        "...........    ...........",
        "...........    ...........",
        "...........    ...........",
        "...........    ...........",
        "...........    ...........",
        "....                  ....",
        "....                  ....",
        "....                  ....",
        "....                  ....",
        "...........    ...........",
        "...........    ...........",
        "...........    ...........",
        "...........    ...........",
        "...........    ...........",
        "...........    ...........",
        "...........    ...........",
        ".........................."
    ]

    MINUS = [
        "26 20 2 1",
        "  c black",
        ". c None",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        "....                  ....",
        "....                  ....",
        "....                  ....",
        "....                  ....",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        ".........................."
    ]
    
    def _image_new_from_xpm_data(datalist):
        """
        create image using XPM data list
        (missing from standard GTK/GDK library)
        """
        pbuf = gtk.gdk.pixbuf_new_from_xpm_data(datalist)
        return gtk.image_new_from_pixbuf(pbuf)

    # operator images (Image and Pixbuf objects)
    pix = {
        P.ADD_MODE:      _image_new_from_xpm_data(PLUS),
        P.SUBTRACT_MODE: _image_new_from_xpm_data(MINUS),
        P.CARRY:         gtk.gdk.pixbuf_new_from_xpm_data(LEFT_ARROW),
        P.BORROW:        gtk.gdk.pixbuf_new_from_xpm_data(RIGHT_ARROW),
    }
    return pix

def SpacerWidth(label_keys, answ_col_flag=False):
    """
    determine width for spacer Frame for a specified label-width
    flag indicates this is answer column (needs wider spacer in ADD mode, for carry column)
    """
    # width of column set; extra answer column for carry in ADD mode
    col_set_width = ((P.COL_COUNT + 1) * P.COL_WID
                     if answ_col_flag else
                     P.COL_COUNT * P.COL_WID)
    half_col = P.COL_WID // 2

    # calculate max width of label that appears in this column
    max_label_wid = max(P.DISPLAY_STR[key][1] for key in label_keys)
    
    # spacer width depends on whether label width exceeds column-set width
    return (half_col
            if max_label_wid > col_set_width else
            (col_set_width - max_label_wid) // 2 + half_col)

###
### main routine
###

mytype = activity.Activity if SUGAR_ACTIVITY else object
  
class BlockHeadActivity(mytype):

    def __init__(self, handle=None):
        global Mode, HelpWin, MyDrawable, Pix, MainWin, Bpnl, Cpnl
        if SUGAR_ACTIVITY:
            activity.Activity.__init__(self, handle)
        
        Mode = P.ADD_MODE
        HelpWin = None
    
        # we need an invisible Drawable, for use by SetDisplayStringWidths()
        # also, CreateBlockImage() needs it to establish pixel-depth of a Pixmap
        _tempwin = gtk.Window()
        _tempwin.realize()
        MyDrawable = _tempwin.window
    
        # establish string widths
        SetDisplayStringWidths()
    
        # load images for operator button and carry/borrow buttons
        Pix = LoadImages()
    
        # set up main window
        if SUGAR_ACTIVITY:
            MainWin = gtk.Frame()
            MainWin.set_shadow_type(gtk.SHADOW_NONE)
        else:
            MainWin = gtk.Window(gtk.WINDOW_TOPLEVEL)
            MainWin.set_title("BlockHead")
            MainWin.set_resizable(False)
            MainWin.set_position(gtk.WIN_POS_CENTER)
            MainWin.connect('destroy', lambda _: gtk.main_quit())
     
        # vertical box holds block canvas (BlockPanel) and control panel (CtrlPanel)
        vb = gtk.VBox()
        MainWin.add(vb)
    
        # canvas where columns/blocks appear, at top
        Bpnl = BlockPanel(111, 2 * P.BASE * P.UNIT_HGT + P.WINDOW_HGT_ADJ)
        vb.pack_start(Bpnl.canv, expand=True, fill=True)
    
        # control panel, at bottom
        Cpnl = CtrlPanel(111, 75)
        Cpnl.NewCmd(None)
        vb.pack_start(Cpnl, expand=False, fill=False)
    
        # go
        MainWin.show_all()

        if SUGAR_ACTIVITY:
            toolbox = activity.ActivityToolbox(self)
            self.set_toolbox(toolbox)
            toolbox.show()
            self.set_canvas(MainWin)

if __name__ == "__main__":
    BlockHeadActivity()
    gtk.main()
    sys.exit(0)
