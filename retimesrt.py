#!/usr/bin/env python3

import re
import argparse
import os.path
from datetime import timedelta

STAGE_SPACE, STAGE_PREAMBLE, STAGE_TIMING, STAGE_BODY = 0, 1, 2, 3


def convert_delta(time: timedelta):
    total_sec = time.total_seconds()
    return f"{int(total_sec//3600):02}:{int((total_sec%3600)//60):02}:{time.seconds%60:02},{int(time.microseconds/1000):03}"


if __name__=="__main__":
    args = argparse.ArgumentParser()
    args.add_argument("infile")
    args.add_argument("outfile")
    args.add_argument("-o", "--offset-seconds", type=float, default=0.0, help="Offset in seconds")
    args.add_argument("-e", "--source-encoding", help="Set source encoding (output will always be UTF8)", default=None)
    rate_group = args.add_mutually_exclusive_group(required=False)
    rate_group.add_argument("--ntsc", action="store_const", const=1.040959040959041)
    rate_group.add_argument("--pal", action="store_const", const=0.959040959040959)
    args = args.parse_args()

    rate_modifier = args.pal or args.ntsc or 1

    # Check only input, we'll handle output purely through error handling
    if not os.path.exists(args.infile):
        exit("Input file does not exist")

    with open(args.infile, encoding=args.source_encoding) as f:
        lines = f.read().split("\n")

    lines.append("")

    out_lines = []

    stage = STAGE_SPACE
    pre, start, end, body = [], None, None, []
    re_timing = re.compile(r"(\d+):(\d{2}):(\d{2}),?(\d*)")

    for index, line in enumerate(lines):
        if not line:
            stage = STAGE_SPACE
        elif line and stage == STAGE_SPACE:
            stage = STAGE_PREAMBLE
        elif stage in [STAGE_PREAMBLE, STAGE_TIMING] and "-->" in line:
            stage = STAGE_TIMING
        elif stage == STAGE_TIMING:
            stage = STAGE_BODY

        if stage == STAGE_SPACE:
            if not all((start, end, body)):
                print(f"Line {index} - no time or no body")
            else:
                out_lines.append((pre, start, end, body))
            pre, start, end, body = [], None, None, []
        elif stage == STAGE_PREAMBLE:
            pre.append(line)
        elif stage == STAGE_TIMING:
            matches = re_timing.findall(line)
            if len(matches) != 2:
                print(f"Line {index} - malformed time string")
            else:
                times = []
                for match in matches:
                    hours, minutes, seconds, milliseconds = match
                    times.append(
                        timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds), milliseconds=int(milliseconds or 0)) *
                            rate_modifier + timedelta(seconds=args.offset_seconds))
                start, end = times
        elif stage == STAGE_BODY:
            body.append(line)

    with open(args.outfile, "w") as f:
        for pre, start, end, body in out_lines:
            # Write line number if any
            f.write("\n".join(pre))
            f.write("\n"*bool(pre))

            # Write times
            f.write(convert_delta(start) + " --> " + convert_delta(end) + "\n")

            # Write body
            f.write("\n".join(body))

            # Final spaces
            f.write("\n\n")