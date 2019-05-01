import string
from difflib import SequenceMatcher
from typing import List


def similar(a: string, b: string) -> float:
    return SequenceMatcher(None, a, b).ratio()


# dataFilePath = '/Users/Jonathan/Downloads/artists.txt'
dataFilePath = '/Users/Jonathan/Downloads/albums.txt'

print('======================================')
print(' Analyzing Strings...')
print(' Config file: ' + str(dataFilePath))
print('======================================')

# Load file
with open(dataFilePath) as f:
    lines: List[str] = f.read().splitlines()

# Clean/Format data -- [PLACEHOLDER]

# Parse data
# freqData: Counter[str] = collections.Counter(lines)
numLines = len(lines)
for jj in range(0,numLines-1):
    line0 = lines[jj]
    for kk in range(jj+1,numLines):
        line1 = lines[kk]
        ratio: float = similar(line0, line1)
        if 0.9 < ratio:
            print("[MATCH]: " + line0 + " <--> " + line1)

# Analyze data
print('Done.')
