import json
newlist=[
    {'name':'CVL','url':'https://cvl.massive.org.au/cvl_flavours.json'},
    {'name':'MASSIVE','url':'http://cvl.massive.org.au/massive_flavours.json'},
    {'name':'CQU','url':'http://cvl.massive.org.au/massive_flavours.json'}
]

s=json.dumps(newlist,sort_keys=True, indent=4, separators=(',', ': '))
print s
