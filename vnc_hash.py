import d3des

def get_vnc_hash(password):
    passpadd = (password + '\x00'*8)[:8]
    strkey = ''.join([ chr(x) for x in d3des.vnckey ])
    ekey = d3des.deskey(strkey, False)

    hashed = d3des.desfunc(passpadd, ekey)
    return hashed.encode('hex')
    
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        print get_vnc_hash(sys.argv[1])
    else:
        print 'usage: %s ' % sys.argv[0]
