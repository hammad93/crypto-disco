'''
Credits to PyFileFixity
'''
import sys
import hashlib
from base64 import b64encode
import codecs
import os
import random

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
    Class to provide a hasher object with various hashing algorithms. What's important is to provide the __len__ so that
    we can easily compute the block size of ecc entries. Must only use fixed size hashers for the rest of the script to\
    work properly.
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

def tamper_file(filepath, mode='e', proba=0.03, block_proba=None, blocksize=65535, burst_length=None, header=None):
    """
    Credit to PyFileFixity
    Randomly tamper a file's content
    """
    if header and header > 0:
        blocksize = header

    tamper_count = 0 # total number of characters tampered in the file
    total_size = 0 # total buffer size, NOT necessarily the total file size (depends if you set header or not)
    # 'r+' allows to read AND overwrite characters. Else any other option won't allow
    with open(filepath, "r+b") as fh:
        # normalizing probability if it's an integer (ie: the number of characters to flip on average)
        if proba >= 1:
            proba = 1.0/os.fstat(fh.fileno()).st_size * proba
        # We process blocks by blocks because it's a lot faster (IO is the slowest operation in any computing system)
        buf = fh.read(blocksize)
        while len(buf) > 0:
            total_size += len(buf)
            # If block tampering is enabled, process only if this block is selected by probability
            if not block_proba or (random.random() < block_proba):
                pos2tamper = []
                # if burst is enabled and corruption probability is triggered, then we will here store the remaining
                # number of characters to corrupt (the length is uniformly sampled over the range specified in arguments)
                burst_remain = 0
                # Create the list of bits to tamper (it's a lot more efficient to precompute the list of characters to
                # corrupt, and then modify in the file the characters all at once)
                for i in range(len(buf)):
                    # Corruption probability: corrupt only if below the bit-flip proba
                    if burst_remain > 0 or (random.random() < proba):
                        pos2tamper.append(i) # keep this character's position in the to-be-corrupted list
                        # if we're already in a burst, we minus one and continue onto the next character
                        if burst_remain > 0:
                            burst_remain -= 1
                        # else we're not in a burst, we create one (triggered by corruption probability: as soon as one
                        # character triggers the corruption probability, then we do a burst)
                        elif burst_length:
                            # if burst is enabled, then we randomly (uniformly) pick a random length for the burst
                            # between the range specified, and since we already tampered one character, we minus 1
                            burst_remain = random.randint(burst_length[0], burst_length[1]) - 1
                # If there's any character to tamper in the list, we tamper the string
                if pos2tamper:
                    tamper_count = tamper_count + len(pos2tamper)
                    #print("Before: %s" % buf)
                    buf = bytearray(buf) # Strings in Python are immutable, thus we need to convert to a bytearray
                    for pos in pos2tamper:
                        if mode == 'e' or mode == 'erasure': # Erase the character (set a null byte)
                            buf[pos] = 0
                        elif mode == 'n' or mode == 'noise': # Noising the character (set a random ASCII character)
                            buf[pos] = random.randint(0,255)
                    #print("After: %s" % buf)
                    # Overwriting the string into the file
                    # need to store and place back the seek cursor because after the write, if it's the end of the file,
                    # the next read may be buggy (getting characters that are not part of the file)
                    prevpos = fh.tell()
                    fh.seek(fh.tell()-len(buf)) # Move the cursor at the beginning of the string we just read
                    fh.write(buf) # Overwrite it
                    fh.seek(prevpos) # Restore the previous position after the string
            # If we only tamper the header, we stop here by setting the buffer to an empty string
            if header and header > 0:
                buf = ''
            # Else we continue to the next data block
            else:
                # Load the next characters from file
                buf = fh.read(blocksize)
    return [tamper_count, total_size]

def md5_file_hash(path):
    with open(path, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)
    return file_hash.hexdigest()