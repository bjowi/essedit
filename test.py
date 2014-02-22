import io
import essedit5

#data = io.BytesIO(bytes.fromhex("91 01"))
#print(essedit5.parse_vsval_r(data))

with open('SkyCells', 'rb') as fh:
    data = fh.read()
    print(essedit5.parse_skycells(io.BytesIO(data), len(data), 'SkyCells'))

with open('Interface', 'rb') as fh:
   data = fh.read()
   print(essedit5.parse_interface(io.BytesIO(data), len(data), 'Interface'))
