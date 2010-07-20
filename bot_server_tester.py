bytes = []
with open('testpacks.packs') as f:
  temp_datas = []
  for line in f:
    if line.strip() == '' and len(temp_datas):
      bytes.extend(temp_datas[54:])
      temp_datas = []
    else:
      temp_datas.extend(line.strip().split())
data = (chr(int(x, 16)) for x in bytes)

#ok listen, accept, print data, close.