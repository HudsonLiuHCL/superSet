#
# The Python Imaging Library
# $Id$
#
# base class for raster font file parsers
#
# history:
# 1997-06-05 fl   created
# 1997-08-19 fl   restrict image width
#
# Copyright (c) 1997-1998 by Secret Labs AB
# Copyright (c) 1997-1998 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import os
from typing import BinaryIO

from . import Image, _binary

WIDTH = 800


def puti16(
    fp: BinaryIO, values: tuple[int, int, int, int, int, int, int, int, int, int]
) -> None:
    """Write network order (big-endian) 16-bit sequence"""
    for v in values:
        if v < 0:
            v += 65536
        fp.write(_binary.o16be(v))


class FontFile:
    """Base class for raster font file handlers."""

    bitmap: Image.Image | None = None

    def __init__(self) -> None:
        self.info: dict[bytes, bytes | int] = {}
        self.glyph: list[
            tuple[
                tuple[int, int],
                tuple[int, int, int, int],
                tuple[int, int, int, int],
                Image.Image,
            ]
            | None
        ] = [None] * 256

    def __getitem__(
        self, ix: int
    ) -> (
        tuple[
            tuple[int, int],
            tuple[int, int, int, int],
            tuple[int, int, int, int],
            Image.Image,
        ]
        | None
    ):
        return self.glyph[ix]

    def compile(self) -> None:
        """Create metrics and bitmap"""

        if self.bitmap:
            return

        # create bitmap large enough to hold all data
        h = w = maxwidth = 0
        lines = 1
        for glyph in self.glyph:
            if glyph:
                d, dst, src, im = glyph
                h = max(h, src[3] - src[1])
                w = w + (src[2] - src[0])
                if w > WIDTH:
                    lines += 1
                    w = src[2] - src[0]
                maxwidth = max(maxwidth, w)

        xsize = maxwidth
        ysize = lines * h

        if xsize == 0 and ysize == 0:
            return

        self.ysize = h

        # paste glyphs into bitmap
        self.bitmap = Image.new("1", (xsize, ysize))
        self.metrics: list[
            tuple[tuple[int, int], tuple[int, int, int, int], tuple[int, int, int, int]]
            | None
        ] = [None] * 256
        x = y = 0
        for i in range(256):
            glyph = self[i]
            if glyph:
                d, dst, src, im = glyph
                xx = src[2] - src[0]
                x0, y0 = x, y
                x = x + xx
                if x > WIDTH:
                    x, y = 0, y + h
                    x0, y0 = x, y
                    x = xx
                s = src[0] + x0, src[1] + y0, src[2] + x0, src[3] + y0
                self.bitmap.paste(im.crop(src), s)
                self.metrics[i] = d, dst, s

    def save(self, filename: str) -> None:
        """Save font"""

        self.compile()

        # font data
        if not self.bitmap:
            msg = "No bitmap created"
            raise ValueError(msg)
        self.bitmap.save(os.path.splitext(filename)[0] + ".pbm", "PNG")

        # font metrics
        with open(os.path.splitext(filename)[0] + ".pil", "wb") as fp:
            fp.write(b"PILfont\n")
            fp.write(f";;;;;;{self.ysize};\n".encode("ascii"))  # HACK!!!
            fp.write(b"DATA\n")
            for id in range(256):
                m = self.metrics[id]
                if not m:
                    puti16(fp, (0,) * 10)
                else:
                    puti16(fp, m[0] + m[1] + m[2])
