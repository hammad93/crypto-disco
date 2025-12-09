'''
Credits to PyFileFixity
'''
import sys
import hashlib
from base64 import b64encode
import codecs

def feature_scaling(x, xmin, xmax, a=0, b=1):
    '''Generalized feature scaling (useful for variable error correction rate calculation)'''
    return a + float(x - xmin) * (b - a) / (xmax - xmin)

def b(x):
    # https://github.com/lrq3000/pyFileFixity/blob/master/pyFileFixity/lib/_compat.py#L34
    if isinstance(x, str):
        return codecs.latin_1_encode(x)[0]
    else:
        return x

def _bytes(x):
    if isinstance(x, (bytes, bytearray)):
        return x
    else:
        return bytes(x, 'latin-1')

class Hasher(object):
    '''
    Credit to
    https://github.com/lrq3000/pyFileFixity/blob/master/pyFileFixity/lib/hasher.py
    Class to provide a hasher object with various hashing algorithms. What's important is to provide the __len__ so that we can easily compute the block size of ecc entries. Must only use fixed size hashers for the rest of the script to work properly.
    '''

    known_algo = ["md5", "shortmd5", "shortsha256", "minimd5", "minisha256", "none"]
    __slots__ = ['algo', 'length']

    def __init__(self, algo="md5"):
        # Store the selected hashing algo
        self.algo = algo.lower()
        # Precompute length so that it's very fast to access it later
        if self.algo == "md5":
            self.length = 32
        elif self.algo == "shortmd5" or self.algo == "shortsha256":
            self.length = 8
        elif self.algo == "minimd5" or self.algo == "minisha256":
            self.length = 4
        elif self.algo == "none":
            self.length = 0
        else:
            raise NameError('Hashing algorithm %s is unknown!' % algo)

    def hash(self, mes):
        # use hashlib.algorithms_guaranteed to list algorithms
        mes = b(mes)
        if self.algo == "md5":
            return b(hashlib.md5(mes).hexdigest())
        elif self.algo == "shortmd5":  # from: http://www.peterbe.com/plog/best-hashing-function-in-python
            return b64encode(b(hashlib.md5(mes).hexdigest()))[:8]
        elif self.algo == "shortsha256":
            return b64encode(b(hashlib.sha256(mes).hexdigest()))[:8]
        elif self.algo == "minimd5":
            return b64encode(b(hashlib.md5(mes).hexdigest()))[:4]
        elif self.algo == "minisha256":
            return b64encode(b(hashlib.sha256(mes).hexdigest()))[:4]
        elif self.algo == "none":
            return ''
        else:
            raise NameError('Hashing algorithm %s is unknown!' % self.algo)

    def __len__(self):
        return self.length