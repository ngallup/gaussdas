
import sys
from processor import Processor

parser = Processor()
print(parser.get_df(sys.argv[1]))
