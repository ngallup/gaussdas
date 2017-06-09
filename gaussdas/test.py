
import sys
from processor import Processor

parser = Processor()
df = parser.get_df(sys.argv[1])

print('Test output')
print(df)
print(df.info())
