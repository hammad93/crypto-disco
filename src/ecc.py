from io import BytesIO
import struct
import math
import time
import os
from utils import feature_scaling, Hasher, _bytes, b

import creedsolo as reedsolo
from unireedsolomon import rs as brownanrs

def generate_ecc(input_path, output_path, progress_function=lambda x,y,z: None):
    '''
    Credit to PyFileFixity
    Parameters
    ----------
    input_path str
    output_path str
    progress_function function (optional)
        There are 3 inputs: x, y, z . Progress in bytes is x, the total estimate is z, and elapse time in seconds is y
    References
    ----------
    - https://github.com/lrq3000/pyFileFixity/blob/master/pyFileFixity/structural_adaptive_ecc.py
    - https://github.com/lrq3000/pyFileFixity/blob/master/pyFileFixity/__init__.py
    - https://github.com/lrq3000/pyFileFixity/blob/496b0518ebd51cdcd594fcd63a85066a13d1921c/pyFileFixity/structural_adaptive_ecc.py#L541
    '''
    print("Generating ECC file. Credit to PyFileFixity.")
    base_path = os.path.join(output_path, os.path.basename(input_path)) + ".txt"
    total_estimate = estimate_total_size(input_path)
    with open(base_path, 'wb') as db, open(base_path + ".idx", 'wb') as dbidx:
        # Write ECC file header identifier (unique string + version)
        db.write(b("**PYSTRUCTADAPTECCv%s**\n" % (''.join([x * 3 for x in
                                                           "3.1.4"]))))  # each character in the version will be repeated 3 times, so that in case of tampering, a majority vote can try to disambiguate)
        # Write the parameters (they are NOT reloaded automatically! It's the user role to memorize those parameters (using any means: own brain memory, keep a copy on paper, on email, etc.), so that the parameters are NEVER tampered. The parameters MUST be ultra reliable so that errors in the ECC file can be more efficiently recovered.
        for i in range(3): db.write(("** Parameters: " + " ".join(
            parameters) + "\n").encode())  # copy them 3 times just to be redundant in case of ecc file corruption
        db.write(b("** Generated under %s\n" % ecc_manager_variable.description()))
        # Processing ecc on files
        rootfolderpath = os.path.dirname(input_path)
        dirpath = os.path.dirname(input_path)
        filename = os.path.basename(input_path)
        # Get full absolute filepath
        filepath = os.path.join(dirpath, filename)
        # Get database relative path (from scanning root folder)
        relfilepath = os.path.relpath(filepath, rootfolderpath)
        # Get file size
        filesize = os.stat(filepath).st_size
        # Opening the input file's to read its header and compute the ecc/hash blocks
        print("\n- Processing file %s" % relfilepath)
        with open(os.path.join(rootfolderpath, filepath), 'rb') as file:
            entrymarker_pos = db.tell()  # backup the position of the start of this ecc entry
            # -- Intra-ecc generation: Compute an ecc for the filepath, to avoid a critical spot here (so that we don't care that the filepath gets corrupted, we have an ecc to fix it!)
            relfilepath_ecc = compute_ecc_hash_from_string(relfilepath, ecc_manager_intra, hasher_intra,
                                                           parameters["max_block_size"], parameters["resilience_rate_intra"])
            filesize_ecc = compute_ecc_hash_from_string(b(str(filesize)), ecc_manager_intra, hasher_intra,
                                                        parameters["max_block_size"], parameters["resilience_rate_intra"])
            db.write(b''.join([b(parameters["entrymarker"]), b(relfilepath), b(parameters["field_delim"]), b(str(filesize)), b(parameters["field_delim"]),
                               b(relfilepath_ecc), b(parameters["field_delim"]), b(filesize_ecc),
                               b(parameters["field_delim"])]))  # first save the file's metadata (filename, filesize, ecc for filename, ...), separated with field_delim
            # -- External indexes backup: calculate the position of the entrymarker and of each field delimiter, and compute their ecc, and save into the index backup file. This will allow later to retrieve the position of each marker in the ecc file, and repair them if necessary, while just incurring a very cheap storage cost.
            # Also, the index backup file is fixed delimited fields sizes, which means that each field has a very specifically delimited size, so that we don't need any marker: we can just compute the total size for each entry, and thus find all entries independently even if one or several are corrupted beyond repair, so that this won't affect other index entries.
            # Make the list of all markers positions for this ecc entry. The first and last indexes are the most important (first is the entrymarker, the last is the field_delim just before the ecc track start)
            markers_pos = [
                entrymarker_pos,
                entrymarker_pos + len(parameters["entrymarker"]) + len(relfilepath),
                entrymarker_pos + len(parameters["entrymarker"]) + len(relfilepath) + len(parameters["field_delim"]) + len(str(filesize)),
                entrymarker_pos + len(parameters["entrymarker"]) + len(relfilepath) + len(parameters["field_delim"]) + len(str(filesize)) + len(
                    parameters["field_delim"]) + len(relfilepath_ecc),
                db.tell() - len(parameters["field_delim"])
            ]
            # Convert to a binary representation in 8 bytes using unsigned long long (up to 16 EB, this should be more than sufficient)
            markers_pos = [struct.pack('>Q', x) for x in markers_pos]
            markers_types = [b'1', b'2', b'2', b'2', b'2']
            # compute the ecc for each number
            markers_pos_ecc = [ecc_manager_idx.encode(x + y) for x, y in zip(markers_types, markers_pos)]
            # Couple each marker's position with its type and with its ecc, and write them all consecutively into the index backup file
            for items in zip(markers_types, markers_pos, markers_pos_ecc):
                for item in items:
                    dbidx.write(b(item))
            # -- Hash/Ecc encoding of file's content (everything is managed inside stream_compute_ecc_hash)
            start = time.time()
            # then compute the ecc/hash entry for this file's header (each value will be a block, a string of hash+ecc per block of data, because Reed-Solomon is limited to a maximum of 255 bytes, including the original_message+ecc! And in addition we want to use a variable rate for RS that is decreasing along the file)
            progress = 0
            for ecc_entry in stream_compute_ecc_hash(ecc_manager_variable, hasher, file, parameters["max_block_size"], parameters["header_size"], parameters["resilience_rates"]):
                # note that there's no separator between consecutive blocks, but by calculating the ecc parameters, we will know when decoding the size of each block!
                db.write(b''.join([b(ecc_entry[0]), b(ecc_entry[1])]))
                progress += ecc_entry[2]['message_size']
                elapsed = int(time.time() - start)
                if elapsed % 2 == 0: # every 2 seconds, update progress
                    progress_function(progress, total_estimate, elapsed)

    print("All done! Total number of files processed: %i, skipped: %i" % (1, 0))
    return 0

class ECCMan(object):
    '''Error correction code manager, which provides a facade API to use different kinds of ecc algorithms or libraries/codecs.'''
    def __init__(self, n, k, algo=1):
        self.c_exp = 8 # we stay in GF(2^8) for this software
        self.field_charac = int((2**self.c_exp) - 1)

        if algo == 1 or algo == 2: # brownanrs library implementations: fully correct base 3 implementation, and mode 2 is for fast encoding
            self.gen_nb = 3
            self.prim = 0x11b
            self.fcr = 1

            self.ecc_manager = brownanrs.RSCoder(n, k, generator=self.gen_nb, prim=self.prim, fcr=self.fcr)
        elif algo == 3: # reedsolo fast implementation, compatible with brownanrs in base 3
            self.gen_nb = 3
            self.prim = 0x11b
            self.fcr = 1

            reedsolo.init_tables(generator=self.gen_nb, prim=self.prim)
            self.g = reedsolo.rs_generator_poly_all(n, fcr=self.fcr, generator=self.gen_nb)
            #self.gf_mul_arr, self.gf_add_arr = reedsolo.gf_precomp_tables()
        elif algo == 4: # reedsolo fast implementation, incompatible with any other implementation
            self.gen_nb = 2
            self.prim = 0x187
            self.fcr = 120

            reedsolo.init_tables(self.prim) # parameters for US FAA ADSB UAT RS FEC
            self.g = reedsolo.rs_generator_poly_all(n, fcr=self.fcr, generator=self.gen_nb)
        else:
            raise Exception("Specified algorithm %i is not supported!" % algo)

        self.algo = algo
        self.n = n
        self.k = k

    def encode(self, message, k=None):
        '''Encode one message block (up to 255) into an ecc'''
        if not k: k = self.k
        if self.algo == 1:
            message, _ = self.pad(b(message), k=k)
            mesecc = self.ecc_manager.encode(message, k=k)
        elif self.algo == 2:
            message, _ = self.pad(b(message), k=k)
            mesecc = self.ecc_manager.encode_fast(message, k=k)
        elif self.algo == 3 or self.algo == 4:
            message, _ = self.pad(bytearray(b(message)), k=k)  # TODO: need to use bytearray to be fully compatible with cythonized extension (the fastest!)
            mesecc = rs_encode_msg(message, self.n-k, fcr=self.fcr, gen=self.g[self.n-k])
            #mesecc = rs_encode_msg_precomp(message, self.n-k, fcr=self.fcr, gen=self.g[self.n-k])

        ecc = mesecc[len(message):]
        return _bytes(ecc)

    def decode(self, message, ecc, k=None, enable_erasures=False, erasures_char="\x00", only_erasures=False):
        '''Repair a message and its ecc also, given the message and its ecc (both can be corrupted, we will still try to fix both of them)'''
        if not k: k = self.k

        # Optimization, use bytearray
        if isinstance(message, str):
            message = bytearray([ord(x) for x in message])
        if isinstance(ecc, str):
            ecc = bytearray([ord(x) for x in ecc])

        # Detect erasures positions and replace with null bytes (replacing erasures with null bytes is necessary for correct syndrome computation)
        # Note that this must be done before padding, else we risk counting the padded null bytes as erasures!
        erasures_pos = None
        if enable_erasures:
            # Concatenate to find erasures in the whole codeword
            mesecc = message + ecc
            # Convert char to a int (because we use a bytearray)
            if isinstance(erasures_char, str): erasures_char = ord(erasures_char)
            # Find the positions of the erased characters
            erasures_pos = bytearray([i for i in range(len(mesecc)) if mesecc[i] == erasures_char])
            # Failing case: no erasures could be found and we want to only correct erasures, then we return the message as-is
            if only_erasures and not erasures_pos: return message, ecc

        # Pad with null bytes if necessary
        message, pad = self.pad(message, k=k)
        ecc, _ = self.rpad(ecc, k=k) # fill ecc with null bytes if too small (maybe the field delimiters were misdetected and this truncated the ecc? But we maybe still can correct if the truncation is less than the resilience rate)

        # If the message was left padded, then we need to update the positions of the erasures
        if erasures_pos and pad:
            len_pad = len(pad)
            erasures_pos = bytearray([x+len_pad for x in erasures_pos])

        # Decoding
        if self.algo == 1:
            msg_repaired, ecc_repaired = self.ecc_manager.decode(message + ecc, nostrip=True, k=k, erasures_pos=erasures_pos, only_erasures=only_erasures) # Avoid automatic stripping because we are working with binary streams, thus we should manually strip padding only when we know we padded
        elif self.algo == 2:
            msg_repaired, ecc_repaired = self.ecc_manager.decode_fast(message + ecc, nostrip=True, k=k, erasures_pos=erasures_pos, only_erasures=only_erasures)
        elif self.algo == 3:
            #msg_repaired, ecc_repaired = self.ecc_manager.decode_fast(message + ecc, nostrip=True, k=k, erasures_pos=erasures_pos, only_erasures=only_erasures)
            msg_repaired, ecc_repaired, _ = reedsolo.rs_correct_msg_nofsynd(bytearray(message + ecc), self.n-k, fcr=self.fcr, generator=self.gen_nb, erase_pos=erasures_pos, only_erasures=only_erasures)
            msg_repaired = bytearray(msg_repaired)
            ecc_repaired = bytearray(ecc_repaired)
        elif self.algo == 4:
            msg_repaired, ecc_repaired, _ = reedsolo.rs_correct_msg(bytearray(message + ecc), self.n-k, fcr=self.fcr, generator=self.gen_nb, erase_pos=erasures_pos, only_erasures=only_erasures)
            msg_repaired = bytearray(msg_repaired)
            ecc_repaired = bytearray(ecc_repaired)

        if pad: # Strip the null bytes if we padded the message before decoding
            msg_repaired = msg_repaired[len(pad):len(msg_repaired)]
        return _bytes(msg_repaired), _bytes(ecc_repaired)

    def pad(self, message, k=None):
        '''Automatically left pad with null bytes a message if too small, or leave unchanged if not necessary. This allows to keep track of padding and strip the null bytes after decoding reliably with binary data. Equivalent to shortening (shortened reed-solomon code).'''
        if not k: k = self.k
        pad = None
        if len(message) < k:
            #pad = "\x00" * (k-len(message))
            pad = bytearray(k-len(message))
            message = pad + bytearray(b(message))
        return [message, pad]

    def rpad(self, ecc, k=None):
        '''Automatically right pad with null bytes an ecc to fill for missing bytes if too small, or leave unchanged if not necessary. This can be used as a workaround for field delimiter misdetection. Equivalent to puncturing (punctured reed-solomon code).'''
        if not k: k = self.k
        pad = None
        if len(ecc) < self.n-k:
            print("Warning: the ecc field may have been truncated (entrymarker or field_delim misdetection?).")
            #pad = "\x00" * (self.n-k-len(ecc))
            pad = bytearray(self.n-k-len(ecc))
            ecc = bytearray(ecc) + pad
        return [ecc, pad]

    def check(self, message, ecc, k=None):
        '''Check if there's any error in a message+ecc. Can be used before decoding, in addition to hashes to detect if the message was tampered, or after decoding to check that the message was fully recovered.'''
        if not k: k = self.k
        message, _ = self.pad(message, k=k)
        ecc, _ = self.rpad(ecc, k=k)
        if self.algo == 1 or self.algo == 2:
            return self.ecc_manager.check_fast(message + ecc, k=k)
        elif self.algo == 3 or self.algo == 4:
            return reedsolo.rs_check(bytearray(message + ecc), self.n-k, fcr=self.fcr, generator=self.gen_nb)

    def description(self):
        '''Provide a description for each algorithm available, useful to print in ecc file'''
        if 0 < self.algo <= 3:
            return "Reed-Solomon with polynomials in Galois field of characteristic %i (2^%i) with generator=%s, prime poly=%s and first consecutive root=%s." % (self.field_charac, self.c_exp, self.gen_nb, hex(self.prim), self.fcr)
        elif self.algo == 4:
            return "Reed-Solomon with polynomials in Galois field of characteristic %i (2^%i) under US FAA ADSB UAT RS FEC standard with generator=%s, prime poly=%s and first consecutive root=%s." % (self.field_charac, self.c_exp, self.gen_nb, hex(self.prim), self.fcr)
        else:
            return "No description for this ECC algorithm."

def compute_ecc_params(max_block_size, rate, hasher):
    '''
    Compute the ecc parameters (size of the message, size of the hash, size of the ecc). This is an helper function to easily compute the parameters from a resilience rate to instanciate an ECCMan object.
    https://github.com/lrq3000/pyFileFixity/blob/496b0518ebd51cdcd594fcd63a85066a13d1921c/pyFileFixity/lib/eccman.py#L55
    '''
    #message_size = max_block_size - int(round(max_block_size * rate * 2, 0)) # old way to compute, wasn't really correct because we applied the rate on the total message+ecc size, when we should apply the rate to the message size only (that is not known beforehand, but we want the ecc size (k) = 2*rate*message_size or in other words that k + k * 2 * rate = n)
    message_size = int(round(float(max_block_size) / (1 + 2*rate), 0))
    ecc_size = max_block_size - message_size
    hash_size = len(hasher) # 32 when we use MD5
    return {"message_size": message_size, "ecc_size": ecc_size, "hash_size": hash_size}

def compute_ecc_hash_from_string(string, ecc_manager, hasher, max_block_size, resilience_rate):
    '''Generate a concatenated string of ecc stream of hash/ecc blocks, of constant encoding rate, given a string.
    NOTE: resilience_rate here is constant, you need to supply only one rate, between 0.0 and 1.0. The encoding rate will then be constant, like in header_ecc.py.'''
    fpfile = BytesIO(b(string))
    ecc_stream = b''.join( [b(x[1]) for x in stream_compute_ecc_hash(ecc_manager, hasher, fpfile, max_block_size, len(string), [resilience_rate])] ) # "hack" the function by tricking it to always use a constant rate, by setting the header_size=len(relfilepath), and supplying the resilience_rate_intra instead of resilience_rate_s1 (the one for header)
    return ecc_stream

def stream_compute_ecc_hash(ecc_manager, hasher, file, max_block_size, header_size, resilience_rates):
    '''Generate a stream of hash/ecc blocks, of variable encoding rate and size, given a file.'''
    curpos = file.tell() # init the reading cursor at the beginning of the file
    # Find the total size to know when to stop
    #size = os.fstat(file.fileno()).st_size # old way of doing it, doesn't work with _StringIO objects
    file.seek(0, os.SEEK_END) # alternative way of finding the total size: go to the end of the file
    size = file.tell()
    file.seek(0, curpos) # place the reading cursor back at the beginning of the file
    # Main encoding loop
    while curpos < size: # Continue encoding while we do not reach the end of the file
        # Calculating the encoding rate
        if curpos < header_size: # if we are still reading the file's header, we use a constant rate
            rate = resilience_rates[0]
        else: # else we use a progressive rate for the rest of the file the we calculate on-the-fly depending on our current reading cursor position in the file
            rate = feature_scaling(curpos, header_size, size, resilience_rates[1], resilience_rates[2]) # find the rate for the current stream of data (interpolate between stage 2 and stage 3 rates depending on the cursor position in the file)

        # Compute the ecc parameters given the calculated rate
        ecc_params = compute_ecc_params(max_block_size, rate, hasher)
        #ecc_manager = ECCMan(max_block_size, ecc_params["message_size"]) # not necessary to create an ecc manager anymore, as it is very costly. Now we can specify a value for k on the fly (tables for all possible values of k are pre-generated in the reed-solomon libraries)

        # Compute the ecc and hash for the current message block
        mes = file.read(ecc_params["message_size"])
        hash = hasher.hash(mes)
        ecc = ecc_manager.encode(mes, k=ecc_params["message_size"])
        #print("mes %i (%i) - ecc %i (%i) - hash %i (%i)" % (len(mes), message_size, len(ecc), ecc_params["ecc_size"], len(hash), ecc_params["hash_size"])) # DEBUGLINE

        # Return the result
        yield [b(hash), b(ecc), ecc_params]
        # Prepare for next iteration
        curpos = file.tell()

def estimate_total_size(input_path):
    size = os.stat(input_path).st_size
    # Compute predicted size of their headers
    if size >= parameters["header_size"]:  # for big files, we limit the size to the header size
        filesize_header = parameters["header_size"]
        filesize_content = size - parameters["header_size"]
    else:  # else for size smaller than the defined header size, it will just be the size of the file
        filesize_header = size
        filesize_content = 0
    # Size of the ecc entry for this file will be: entrymarker-bytes + field_delim-bytes*occurrence + size of the ecc per block for all blocks in file header + size of the hash per block for all blocks in file header.
    # Compute the total number of bytes we will add with ecc + hash (accounting for the padding of the remaining characters at the end of the sequence in case it doesn't fit with the message_size, by using ceil() )
    result = (len(parameters["entrymarker"]) + len(parameters["field_delim"]) * 3) + (
                    int(math.ceil(float(filesize_header) / ecc_params_header["message_size"])) *
                    (ecc_params_header["ecc_size"] + ecc_params_header["hash_size"])
                ) + (int(math.ceil(float(filesize_content) / ecc_params_variable_average["message_size"])) * (
                    ecc_params_variable_average["ecc_size"] + ecc_params_variable_average["hash_size"])
                )
    return result

parameters = {
    # main_parser.add_argument('--ecc_algo', type=int, default=3, required=False,
    #                         help='What algorithm use to generate and verify the ECC? Values possible: 1-4. 1 is the formal, fully verified Reed-Solomon in base 3 ; 2 is a faster implementation but still based on the formal base 3 ; 3 is an even faster implementation but based on another library which may not be correct ; 4 is the fastest implementation supporting US FAA ADSB UAT RS FEC standard but is totally incompatible with the other three (a text encoded with any of 1-3 modes will be decodable with any one of them).', **widget_text)
    "ecc_algo": 3,
    # marker that will signal the beginning of an ecc entry - use an alternating pattern of several characters, this avoids confusion (eg: if you use "AAA" as a pattern, if the ecc block of the previous file ends with "EGA" for example, then the full string for example will be "EGAAAAC:\yourfolder\filea.jpg" and then the entry reader will detect the first "AAA" occurrence as the entry start - this should not make the next entry bug because there is an automatic trim - but the previous ecc block will miss one character that could be used to repair the block because it will be "EG" instead of "EGA"!)
    "entrymarker": "\xFE\xFF\xFE\xFF\xFE\xFF\xFE\xFF\xFE\xFF",
    "field_delim": "\xFA\xFF\xFA\xFF\xFA",  # delimiter between fields (filepath, filesize, hash+ecc blocks) inside an ecc entry
    #main_parser.add_argument('--max_block_size', type=int, default=255, required=False,
    #                        help='Reed-Solomon max block size (maximum = 255). It is advised to keep it at the maximum for more resilience (see comments at the top of the script for more info). However, if encoding it too slow, using a smaller value will speed things up greatly, at the expense of more storage space (because hash will relatively take more space - you can use --hash "shortmd5" or --hash "minimd5" to counter balance).', **widget_text)
    "max_block_size": 255,
    #main_parser.add_argument('-ri', '--resilience_rate_intra', type=float, default=0.5, required=False,
    #                        help='Resilience rate for intra-ecc (ecc on meta-data, such as filepath, thus this defines the ecc for the critical spots!).', **widget_text)
    "resilience_rate_intra": 0.5,
    #main_parser.add_argument('-s', '--size', type=int, default=1024, required=False,
    #                        help='Headers block size to protect with resilience rate stage 1 (eg: 1024 meants that the first 1k of each file will be protected by stage 1).', **widget_text)
    "header_size": 1024,
    # resilience_rate_s1 Resilience rate for files headers (eg: 0.3 = 30%% of errors can be recovered but size of codeword will be 60%% of the data block).
    # resilience_rate_s2 Resilience rate for stage 2 (after headers, this is the starting rate applied to the rest of the file, which will be gradually lessened towards the end of the file to the stage 3 rate).
    # resilience_rate_s3 Resilience rate for stage 3 (rate that will be applied towards the end of the files).
    "resilience_rates": [0.3, 0.2, 0.1]
}
hasher = Hasher("md5") # md5 is default hash algorithm
hasher_intra = Hasher('none')
ecc_params_idx = compute_ecc_params(27, 1, hasher_intra)
ecc_params_intra = compute_ecc_params(parameters["max_block_size"], parameters["resilience_rate_intra"], hasher_intra)
ecc_manager_variable = ECCMan(parameters["max_block_size"], 1, algo=parameters["ecc_algo"])
ecc_manager_intra = ECCMan(parameters["max_block_size"], ecc_params_intra["message_size"], algo=parameters["ecc_algo"])
ecc_manager_intra = ECCMan(parameters["max_block_size"], ecc_params_intra["message_size"], algo=parameters["ecc_algo"])
ecc_manager_idx = ECCMan(27, ecc_params_idx["message_size"], algo=parameters["ecc_algo"])
rs_encode_msg = reedsolo.rs_encode_msg # local reference for small speed boost
ecc_params_header = compute_ecc_params(parameters["max_block_size"], parameters["resilience_rates"][0], hasher)
ecc_params_variable_average = compute_ecc_params(parameters["max_block_size"], (parameters["resilience_rates"][1] + parameters["resilience_rates"][2])/2, hasher) # compute the average variable rate to compute statistics
