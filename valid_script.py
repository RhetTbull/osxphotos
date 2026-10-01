import pathlib
import sys

pathlib.Path(sys.argv[1]).write_text("ran")

print(f"{len(sys.argv)}")

for i in sys.argv:
    print(i)
