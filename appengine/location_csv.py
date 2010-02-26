import csv,sys
from datetime import datetime

def str_or_none(x):
  if str(x) == '':
    return None
  else:
    return str(x)

def float_or_none(x):
  try:
      if float(x) >= 0.0:
          return float(x)
  except:
       pass
  return None

loader = [
           ('loc', str),
           ('date', lambda x: datetime.fromtimestamp(float(x))),
           ('accuracy', float),
           ('woeid', str_or_none),
           ('url', str),
           ('speed', float_or_none),
         ]

def main():
    if len(sys.argv) < 2:
        print >> sys.stderr, "Usage: %s <location.csv>" % sys.argv[0]
        exit(1)
    fin = open(sys.argv[1], 'r')
    r = csv.reader(fin)
    for row in r:
        e = {}
        for i in range(len(loader)):
            e[loader[i][0]] = loader[i][1](row[i])
        print e   

if __name__ == "__main__":
    main()
