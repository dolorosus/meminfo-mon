#!/bin/python3
# -*- coding: utf-8 -*-
#
#  bufferwatch.py
#  project
#
#  Created by Dolorosus on {2023-07-11.
#  Copyright 2023. All rights reserved.
#
#  mail@dolorosus.de
#
#  shows continously selected values from /proc/meminfo
#
#  since globals are considered harmful, they are hidden hidden in the meminfoMon class ;-)
#
import curses
from curses import A_BOLD, A_REVERSE, A_NORMAL, wrapper
import locale
import socket

import argparse

from time import sleep


class meminfoMon(object):
    def __init__(
        self,
        stdscr,
        selection,
        count=3600,
        interval=1,
    ):
        self.meminfo = {}
        self.count = count
        self.interval = interval
        self.intervalOld = interval

        self.selection = selection
        self.stdscr = stdscr

        self.scrRows, self.scrCols = self.stdscr.getmaxyx()
        self.scrRowsOld = self.scrRows
        self.scrColsOld = self.scrCols

    def updScr(self):
        self.scrRowsOld = self.scrRows
        self.scrColsOld = self.scrCols
        self.scrRows, self.scrCols = self.stdscr.getmaxyx()

    def read(self):
        #
        # transform input to dict {name:[value,hwm]}
        for line in [l.strip().split() for l in open("/proc/meminfo")]:
            #
            #
            # HugePages_* comes without unit...
            if len(line) == 3:
                name, value, unit = line
                #
                # Item of interest?
                if name in self.selection:
                    value = int(value)
                    #
                    # if element exists ==> update, else create it
                    if self.meminfo.get(name):
                        self.meminfo.update({name: [value, self.meminfo[name][1]]})
                    else:
                        self.meminfo[name] = [value, value]
                    #
                    # update high water mark
                    self.meminfo[name][1] = max(self.meminfo[name][1], value)

    def show(self):
        bar = {
            "start": "[",
            "ind": "*",
            "hwmark": "|",
            "empty": " ",
            "end": "]",
            "upb": 0,
        }

        self.intervalOld = self.interval
        #
        # length of output fields
        nameLen = 14
        valLen = 12

        curses.curs_set(0)

        self.updScr()

        while self.count > 0:
            self.count -= 1

            self.read()
            #
            # compute length of bargraph and factor for stars
            bar.update({"upb": max(self.scrCols - 43, 1)})
            starFac = self.meminfo["MemTotal:"][0] // bar["upb"]

            title = f"{'meminfo monitor':^22}\t {self.count:>7}"
            header = f"{'Name':<{nameLen}}{'kb':^{valLen}} {' '*bar['upb']} {'     HWM (kb)  ':>{valLen}}"
            dRow = 2  # datalines starts from dRow

            #
            # Fits output on terminal?
            if (self.scrRows > len(self.meminfo) + 3) and (
                self.scrCols >= 48
            ):  # output fits on terminal
                #
                # build bars, hwm etc.
                self.stdscr.addstr(0, 0, f"{hostname:<{nameLen}}", A_BOLD)
                self.stdscr.addstr(0, 0 + nameLen, title)
                self.stdscr.addstr(1, 0, header, A_REVERSE)
                for name in self.meminfo:
                    #
                    #  self.meminfo {name:[value,highWaterMark]}
                    value, hwm = self.meminfo[name][0], self.meminfo[name][1]
                    #
                    # compute count of marker
                    stars = value // starFac
                    barGraph = bar["ind"] * stars + bar["empty"] * (bar["upb"] - stars)
                    #
                    # compute position of high water mark
                    # build the bar
                    barGraph = (
                        bar["start"]
                        + midstr(barGraph, hwm // starFac, bar["hwmark"])
                        + bar["end"]
                    )
                    #
                    # format number according the current locale
                    _val = locale.format_string("%d", value, grouping=True)
                    _hwm = locale.format_string("%d", hwm, grouping=True)
                    #
                    # add line to screenOutput
                    self.stdscr.addstr(
                        dRow,
                        0,
                        f"{name:<{nameLen}}{_val:>{valLen}} {barGraph} {_hwm:>{valLen}}",
                    )
                    dRow += 1
                #
                # stacked bar
                #
                sDirty = self.meminfo["Dirty:"][0] // starFac
                sCached = self.meminfo["Cached:"][0] // starFac
                sAva = self.meminfo["MemAvailable:"][0] // starFac
                barGraph = (
                    "D" * sDirty
                    + "c" * (sCached - sDirty)
                    + " " * (sAva - sCached)
                    + "u" * (bar["upb"] - sAva)
                )
                #
                # compute position of high water mark
                # build the bar
                barGraph = (
                    bar["start"]
                    + midstr(
                        barGraph, self.meminfo["Cached:"][1] // starFac, bar["hwmark"]
                    )
                    + bar["end"]
                )
                out = f"{'Dirty/cached/ava/used:':<{nameLen+valLen}} {barGraph}"
                self.stdscr.addstr(dRow, 0, out, A_BOLD)
            else:
                self.stdscr.clear()
                self.stdscr.addstr(
                    self.scrRows // 2,
                    0,
                    f"{'Termsize too small!':^{self.scrCols}}",
                    A_BOLD,
                )

            self.stdscr.refresh()
            #
            # even if interval=0 check for pressed keys
            #self.keycheck()
            #
            # Max. latency for reacting of a pressed key is 0.3 seconds
            if self.interval:
                for _ in range(int(self.interval) * 3):
                    sleep(0.33)
                    if self.keycheck():
                        break
            else:
                self.keycheck()

    def showHelp(self):
        help = {
            "MemTotal:": " total usable RAM",
            "MemFree:": " free RAM, the memory which is not used for anything at all",
            "MemAvailable:": " available RAM, the amount of memory available for allocation to any process",
            "Buffers:": " temporary storage element in memory, which doesn’t generally exceed 20 MB",
            "Cached:": " page cache size (cache for files read from the disk), which also includes tmpfs and shmem but excludes SwapCached",
            "SwapCached:": " recently used swap memory, which increases the speed of I/O",
            "SwapTotal:": " the total amount of swap space available in the system",
            "SwapFree:": " unused swap space, the memory that has been transferred from RAM to the disk temporarily",
            "Active:": " memory that has been used more recently, not very suitable to reclaim for new applications",
            "Inactive:": " memory that hasn’t been used recently, more suitable to reclaim for new applications",
            "Dirty:": " memory that currently waits to be written back to the disk",
            "Writeback:": " memory that is being written back at the moment",
            "WritebackTmp:": " temporary buffer for writebacks used by the FUSE module",
            "AnonPages:": " anon (non-file) pages mapped into the page tables",
            "Mapped:": " files that have been mapped into memory with mmap",
            "DirectMap4k:": " the total amount of memory mapped by the kernel in 4 kB pages",
            "DirectMap2M:": " the total amount of memory mapped by the kernel in 2 MB pages",
            "Shmem:": " the amount used by shared memory and the tmpfs filesystem",
            "ShmemHugePages:": " the amount used by shared memory and the tmpfs filesystem with huge pages",
            "ShmemPmdMapped:": " userspace-mapped shared memory with huge pages",
            "KReclaimable:": " kernel allocated memory, reclaimable under memory pressure (includes SReclaimable)",
            "Slab:": " kernel-level data structures cache, allocation of contiguous pages for caches by the slab allocator",
            "SReclaimable:": " reclaimable parts of Slab, e.g., caches",
            "SUnreclaim:": " unreclaimable parts of Slab",
            "CommitLimit:": " amount currently available for allocation on the system",
            "Committed_AS:": " amount already allocated on the system",
            "PageTables:": " the amount of memory consumed by page tables used by the virtual memory system",
            "VmallocTotal:": " total size of vmalloc memory space to allocate virtually contiguous memory",
            "VmallocUsed:": " the size of the used vmalloc memory space",
            "VmallocChunk:": " largest free contiguous block of vmalloc memory",
            "AnonHugePages:": " anon (non-file) huge pages mapped into the page tables",
            "FileHugePages:": " memory consumed by page cache allocated with huge pages",
            "FilePmdMapped:": " mapped page cache in the userspace allocated with huge pages",
            "HugePages_Total:": " total size of the huge pages pool",
            "HugePages_Free:": " amount of unallocated huge pages",
            "HugePages_Rsvd:": " number of reserved huge pages for allocation from the pool, which guarantees the allocation for processes when undesired behavior occurs",
            "HugePages_Surp:": " number of surplus huge pages above a specific base value in /proc/sys/vm/nr_hugepages",
            "Hugepagesize:": " the default size of huge pages",
            "Hugetlb:": " the total amount of memory allocated for huge pages of all sizes",
            "Unevictable:": " unreclaimable memory consumed by userspace like mlock-locke, ramfs backing, and anonymous memfd pages",
            "Mlocked:": " amount of memory locked with mlock",
            "NFS_Unstable:": " Network File System pages that have been written to the disk but not yet committed to stable storage, always zero",
            "Bounce:": " amount of memory for bounce buffers, which are low-level memory areas that enable devices to copy and write data",
            "Percpu:": " memory used for the percpu interface allocations",
            "HardwareCorrupted:": " memory that the kernel spots as corrupted",
        }

        self.stdscr.clear()
        row = 0
        self.stdscr.addstr(
            row,
            0,
            f"{'h,F1,F10=help, q=quit a,A=additional 600/6000 passes, n=speedup, c=clear HWM':^{self.scrCols}}",
            A_BOLD + A_REVERSE,
        )
        row += 2

        for i in self.selection:
            self.stdscr.addstr(row, 0, i, A_BOLD)
            self.stdscr.addstr(row, 20, help[i])
            row += 1
        self.stdscr.addstr(
            row, 0, f"{'Hit any key':^{self.scrCols}}", A_NORMAL + A_REVERSE
        )
        row += 1

        self.stdscr.refresh()
        #
        # wait for anykey
        self.getch(True)
        self.stdscr.clear()
        self.stdscr.refresh()

    def keycheck(self):
        #
        # key pressed?
        key = self.getch(False)
        if key != -1:
            #
            # Wich key was it?
            # self.stdscr.addstr(0,50,f'  {key}  ')
            #        "q","Q"
            if key in [27, 113, 81]:
                exit(0)
            #          "H","h", F10,F1
            elif key in [72, 104, 274, 265]:
                self.showHelp()
            #            a
            elif key in [97]:
                self.count += 600
            #            A
            elif key in [65]:
                self.count += 6000

            elif key in [110, 78]:
                if self.interval == 0:
                    self.interval = self.intervalOld
                else:
                    self.intervalOld = self.interval
                    self.interval = 0

            elif key in [67, 99]:
                for i in self.meminfo:
                    self.meminfo[i][1] = self.meminfo[i][0]

            elif key == curses.KEY_RESIZE:
                self.updScr()
                self.stdscr.clear()

            return True

        return False

    def getch(self, blocking=True):
        self.stdscr.nodelay(not blocking)
        c = self.stdscr.getch()
        self.stdscr.nodelay(blocking)
        curses.flushinp()
        return c


def midstr(str, pos, repl):
    """replace a part of string with repl, starting at pos
       never retuns a string longer than the length of 'str'
    """
    
    if not str:
        return repl
    
    if not repl:
        return str
    
    rLen = len(repl)
    vLen = len(str)

    if pos >= vLen:
        return str
    else:
        return (str[:pos] + repl + str[pos + rLen :])[:vLen]


def parsearg():
    parser = argparse.ArgumentParser(
        description="shows continuously elements \
            from /proc/meminfo adding a bargraph with high water marks.\n\n\
            press 'q' or 'F10' to stop.",
        epilog="",
    )
    parser.add_argument(
        "-c",
        "--count",
        required=False,
        help="Number of passes.",
        type=int,
        default=3600,
    )
    parser.add_argument(
        "-i",
        "--interval",
        required=False,
        help="seconds to wait between updates (fractional values allowed).",
        type=float,
        default=1,
    )
    args = parser.parse_args()
    return args.count, args.interval


def main(stdscr):
    count, interval = parsearg()

    sel = [
        "MemTotal:",
        "MemFree:",
        "MemAvailable:",
        "Buffers:",
        "Cached:",
        "Dirty:",
        "Writeback:",
    ]

    meminfo = meminfoMon(
        stdscr,
        sel,
        int(count),
        interval,
    )

    meminfo.show()


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")

    global hostname
    hostname = socket.gethostname()

    wrapper(main)
