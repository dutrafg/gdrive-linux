"""Parse rclone --stats-one-line output without accessing credentials."""
import re

STATS = re.compile(r"Transferred:\\s*([^,]+),\\s*(\\d{1,3})%")
RATE = re.compile(r",\\s*([^,]+/s)")

def parse_progress(line):
    match = STATS.search(line)
    if not match:
        return None
    percentage = int(match.group(2))
    if not 0 <= percentage <= 100:
        return None
    rate = RATE.search(line[match.end():])
    return {"percentage": percentage, "transferred": match.group(1).strip(),
            "speed": rate.group(1).strip() if rate else ""}
