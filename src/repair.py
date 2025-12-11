import os
from io import BytesIO
import ecc
import utils
from utils import b
from creedsolo import ReedSolomonError
from unireedsolomon.rs import RSCodecError

def correct_errors(damaged, repair_dir, ecc_file, only_erasures=False, enable_erasures=False,
                   erasure_symbol="0", fast_check=True):
    '''
    Credit to PyFileFixity
    - Even though the file noted by the "damaged" path variable is sufficient, the ECC file has the filename included
      in the "ecc_file" path variable and it must match the filename of the "damaged" filename
    - If the "damaged" filename and the one indicated inside the "ecc_file" don't match, it can be renamed

    Parameters
    ----------
    damaged str
        The path of the damaged file to repair
    repair_dir str
        The path of the directory to place the repair
    ecc_file str
        The path of the error correcting codes file utilized for repair
    ecc_file_idx str (Optional)
        The index of the ecc file to repair
    only_erasures bool
        Enable only erasures correction (no errors)
    enable_erasures bool
        Enables errors-and-erasures correction. This can cause it to fail if there are no erasures
    erasure_symbol int or char
        Symbol that will be flagged as an erasure. When extracting corrupted data, the extraction software does this
    fast_check bool
        Checks if the hash value is the same but the value isn't (malicious intent, or extremely random occurance)
    '''
    # Read the ecc file
    database = os.path.abspath(os.path.expanduser(ecc_file))
    print(database)
    entrymarker = ecc.parameters["entrymarker"]
    field_delim = ecc.parameters["field_delim"]
    rootfolderpath = os.path.dirname(damaged)
    with open(database, 'rb') as db:
        # Counters
        files_count = 0
        files_corrupted = 0
        files_repaired_partially = 0
        files_repaired_completely = 0
        files_skipped = 0

        # Main loop: process each ecc entry
        entry = 1  # to start the while loop
        while entry:
            # -- Read the next ecc entry (extract the raw string from the ecc file)
            # if replication_rate == 1:
            entry_pos = get_next_entry(db, entrymarker)

            # No entry? Then we finished because this is the end of file (stop condition)
            if not entry_pos: break

            # -- Extract the fields from the ecc entry
            entry_p = entry_fields(db, entry_pos, b(field_delim))

            # -- Get file path, check its correctness and correct it by using intra-ecc if necessary
            relfilepath = entry_p["relfilepath"]  # Relative file path, given in the ecc fields
            print(relfilepath)
            relfilepath, fpcorrupted, fpcorrected, fperrmsg = ecc_correct_intra_stream(
                ecc.ecc_manager_intra,
                ecc.ecc_params_intra,
                ecc.hasher_intra,
                ecc.parameters["resilience_rate_intra"],
                relfilepath,
                entry_p["relfilepath_ecc"],
                entry_pos,
                enable_erasures=enable_erasures,
                erasures_char=erasure_symbol,
                only_erasures=only_erasures,
                max_block_size=ecc.parameters["max_block_size"])
            # Report errors
            if fpcorrupted:
                if fpcorrected:
                    print("\n- Fixed error in metadata field at offset %i filepath %s." % (entry_pos[0], filepath))
                else:
                    print(
                        "\n- Error in filepath, could not correct completely metadata field at offset %i with value: %s. Please fix manually by editing the ecc file or set the corrupted characters to null bytes and --enable_erasures." % (
                            entry_pos[0], filepath))
            print(fperrmsg)

            # Convert to str (so that we can use os.path funcs)
            relfilepath = relfilepath.decode('latin-1')
            # Update entry_p
            entry_p["relfilepath"] = relfilepath
            # -- End of intra-ecc on filepath

            # -- Get file size, check its correctness and correct it by using intra-ecc if necessary
            filesize = str(entry_p["filesize"])
            filesize, fscorrupted, fscorrected, fserrmsg = ecc_correct_intra_stream(
                ecc.ecc_manager_intra,
                ecc.ecc_params_intra,
                ecc.hasher_intra,
                ecc.parameters["resilience_rate_intra"],
                filesize,
                entry_p["filesize_ecc"],
                entry_pos,
                enable_erasures=enable_erasures,
                erasures_char=erasure_symbol,
                only_erasures=only_erasures,
                max_block_size=ecc.parameters["max_block_size"])

            # Report errors
            if fscorrupted:
                if fscorrected:
                    print("\n- Fixed error in metadata field at offset %i filesize %s." % (entry_pos[0], filesize))
                else:
                    print(
                        "\n- Error in filesize, could not correct completely metadata field at offset %i with value: %s. Please fix manually by editing the ecc file or set the corrupted characters to null bytes and --enable_erasures." % (
                            entry_pos[0], filesize))
            print(fserrmsg)

            # Convert filesize intra-field into an int
            filesize = int(filesize)

            # Update entry_p
            entry_p[
                "filesize"] = filesize  # need to update entry_p because various funcs will directly access filesize this way...
            # -- End of intra-ecc on filesize

            # Build the absolute file path
            # Get full absolute filepath from given input folder (because the files may be specified in any folder,
            # in the ecc file the paths are relative, so that the files can be moved around or burnt on optical discs)
            filepath = os.path.join(rootfolderpath,
                                    relfilepath)

            print("\n- Processing file %s" % relfilepath)

            # -- Check filepath
            # Check that the filepath isn't corrupted (if a silent error erase a character (not only flip a bit), then it will also be detected this way)
            if relfilepath.find("\x00") >= 0:
                print(
                    "Error: ecc entry corrupted on filepath field, please try to manually repair the filepath (filepath: %s - missing/corrupted character at %i)." % (
                        relfilepath, relfilepath.find("\x00")))
                files_skipped += 1
                continue
            # Check that file still exists before checking it
            if not os.path.isfile(filepath):
                print(
                    "Error: file %s could not be found: either file was moved or the ecc entry was corrupted (filepath is incorrect?)." % relfilepath)
                files_skipped += 1
                continue

            # -- Checking file size: if the size has changed, the blocks may not match anymore!
            real_filesize = os.stat(filepath).st_size
            if filesize != real_filesize:
                print(
                    "Error: file %s has a different size: %s (before: %s). Skipping the file correction because blocks may not match (you can set --ignore_size to still correct even if size is different, maybe just the entry was corrupted)." % (
                        relfilepath, real_filesize, filesize))
                files_skipped += 1
                continue

            files_count += 1
            # -- Check blocks and repair if necessary
            corrupted = False  # flag to signal that the file was corrupted and we need to reconstruct it afterwards
            repaired_partially = False  # flag to signal if a file was repaired only partially
            # Do a first run to check if there's any error. If yes, then we will begin back from the start of the file but this time we will streamline copy the data to an output file.
            with open(filepath, 'rb') as file:
                # For each message block, check the message with hash and repair with ecc if necessary
                # Extract and assemble each message block from the original file with its corresponding ecc and hash
                for i, e in enumerate(stream_entry_assemble(
                        ecc.hasher, file, db, entry_p, ecc.parameters["max_block_size"], ecc.parameters["header_size"],
                        ecc.parameters["resilience_rates"])):
                    # If the message block has a different hash or the message+ecc is corrupted (syndrome is not null), it was corrupted (or the hash is corrupted or one of the characters of the ecc was corrupted, or both). In any case, it's an any clause here (any potential corruption condition triggers the correction).
                    if ecc.hasher.hash(e["message"]) != e["hash"] or (
                            not fast_check and not ecc.ecc_manager_variable.check(e["message"], e["ecc"],
                                                                              k=e["ecc_params"]["message_size"])):
                        corrupted = True
                        break
            # -- Reconstruct/Copying the repaired file
            # If the first run detected a corruption, then we try to repair the file (we create an output file where good blocks will be copied as-is but bad blocks will be repaired, if it's possible)
            if corrupted:
                files_corrupted += 1
                repaired_one_block = False  # flag to check that we could repair at least one block, else we will delete the output file since we didn't do anything
                err_consecutive = True  # flag to check if the ecc track is misaligned/misdetected (we only encounter corrupted blocks that we can't fix)
                with open(filepath, 'rb') as file:
                    outfilepath = os.path.join(repair_dir, relfilepath)  # get the full path to the output file
                    outfiledir = os.path.dirname(outfilepath)
                    if not os.path.isdir(outfiledir): os.makedirs(
                        outfiledir)  # if the target directory does not exist, create it (and create recursively all parent directories too)
                    with open(outfilepath, 'wb') as outfile:
                        # TODO: optimize to copy over what we have already checked, so that we get directly to the first error that triggered the correction
                        # For each message block, check the message with hash and repair with ecc if necessary
                        # Extract and assemble each message block from the original file with its corresponding ecc and hash
                        for i, e in enumerate(
                                stream_entry_assemble(ecc.hasher, file, db, entry_p, ecc.parameters["max_block_size"],
                                                      ecc.parameters["header_size"], ecc.parameters["resilience_rates"])):
                            # If the message block has a different hash, it was corrupted (or the hash is corrupted, or both)
                            if ecc.hasher.hash(e["message"]) == e["hash"] and (
                                    fast_check or ecc.ecc_manager_variable.check(e["message"], e["ecc"],
                                                                             k=e["ecc_params"]["message_size"])):
                                outfile.write(e["message"])
                                err_consecutive = False
                            else:
                                # Try to repair the block using ECC
                                print("File %s: corruption in block %i. Trying to fix it." % (relfilepath, i))
                                try:
                                    repaired_block, repaired_ecc = ecc.ecc_manager_variable.decode(
                                        e["message"], e["ecc"], k=e["ecc_params"]["message_size"],
                                        enable_erasures=enable_erasures, erasures_char=erasure_symbol,
                                        only_erasures=only_erasures)
                                except (ReedSolomonError,
                                        RSCodecError) as exc:  # the reedsolo lib may raise an exception when it can't decode. We ensure that we can still continue to decode the rest of the file, and the other files.
                                    repaired_block = None
                                    repaired_ecc = None
                                    print("Error: file %s: block %i: %s" % (relfilepath, i, exc))
                                # Check if the repair was successful. This is an "all" condition: if all checks fail, then the correction failed. Else, we assume that the checks failed because the ecc entry was partially corrupted (it's highly improbable that any one check success by chance, it's a lot more probable that it's simply that the entry was partially corrupted, eg: the hash was corrupted and thus cannot match anymore).
                                hash_ok = False
                                ecc_ok = False
                                if repaired_block is not None:
                                    hash_ok = (ecc.hasher.hash(repaired_block) == e["hash"])
                                    ecc_ok = ecc.ecc_manager_variable.check(repaired_block, repaired_ecc,
                                                                        k=e["ecc_params"]["message_size"])
                                if repaired_block is not None and (
                                        hash_ok or ecc_ok):  # If the hash now match the repaired message block, we commit the new block
                                    outfile.write(repaired_block)  # save the repaired block
                                    # Show a precise report about the repair
                                    if hash_ok and ecc_ok:
                                        print("File %s: block %i repaired!" % (relfilepath, i))
                                    elif not hash_ok:
                                        print(
                                            "File %s: block %i probably repaired with matching ecc check but with a hash error (assume the hash was corrupted)." % (
                                                relfilepath, i))
                                    elif not ecc_ok:
                                        print(
                                            "File %s: block %i probably repaired with matching hash but with ecc check error (assume the ecc was partially corrupted)." % (
                                                relfilepath, i))
                                    # Turn on the repaired flag, to trigger the copying of the file (else it will be removed if all blocks repairs failed in this file)
                                    repaired_one_block = True
                                    err_consecutive = False
                                else:  # Else the hash does not match: the repair failed (either because the ecc is too much tampered, or because the hash is corrupted. Either way, we don't commit).
                                    outfile.write(e["message"])  # copy the bad block that we can't repair...
                                    print(
                                        "Error: file %s could not repair block %i (both hash and ecc check mismatch). If you know where the errors are, you can set the characters to a null character so that the ecc may correct twice more characters." % (
                                            relfilepath,
                                            i))  # you need to code yourself to use bit-recover, it's in perl but it should work given the hash computed by this script and the corresponding message block.
                                    repaired_partially = True
                                    # Detect if the ecc track is misaligned/misdetected (we encounter only errors that we can't fix)
                                    if err_consecutive and i >= 10:  # threshold is ten consecutive uncorrectable errors
                                        print(
                                            "Failure: Too many consecutive uncorrectable errors for %s. Most likely, the ecc track was misdetected (try to repair the entrymarkers and field delimiters). Skipping this track/file." % relfilepath)
                                        db.seek(entry_p["ecc_field_pos"][
                                                    1])  # Optimization: move the reading cursor to the beginning of the next ecc entry, this will save some iterations in get_next_entry()
                                        break
                # Copying the last access time and last modification time from the original file TODO: a more reliable way would be to use the db computed by rfigc.py, because if a software maliciously tampered the data, then the modification date may also have changed (but not if it's a silent error, in that case we're ok).
                filestats = os.stat(filepath)
                os.utime(outfilepath, (filestats.st_atime, filestats.st_mtime))
                # Check that at least one block was repaired, else we couldn't fix anything in the file and thus we should just remove the output file which is an exact copy of the original without any added value
                if not repaired_one_block:
                    os.remove(outfilepath)
                # Counters...
                elif repaired_partially:
                    files_repaired_partially += 1
                else:
                    files_repaired_completely += 1
    # All ecc entries processed for checking and potentally repairing, we're done correcting!
    print(
        "All done! Stats:\n- Total files processed: %i\n- Total files corrupted: %i\n- Total files repaired completely: %i\n- Total files repaired partially: %i\n- Total files corrupted but not repaired at all: %i\n- Total files skipped: %i" % (
            files_count, files_corrupted, files_repaired_completely, files_repaired_partially,
            files_corrupted - (files_repaired_partially + files_repaired_completely), files_skipped))
    if files_corrupted == 0 or files_repaired_completely == files_corrupted:
        return 0
    else:
        return 1

def get_next_entry(file, entrymarker, only_coord=True, blocksize=65535):
    '''
    Find or read the next ecc entry in a given ecc file.
    Call this function multiple times with the same file handle to get subsequent markers positions (this is not a generator but it works very similarly, because it will continue reading from the file's current cursor position -- this can be used advantageously if you want to read only a specific entry by seeking before supplying the file handle).
    This will read any string length between two entrymarkers.
    The reading is very tolerant, so it will always return any valid entry (but also scrambled entries if any, but the decoding will ensure everything's ok).
    `file` is a file handle, not the path to the file.
    '''
    # TODO: use mmap native module instead of manually reading using blocksize?
    entrymarker = bytearray(b(entrymarker))
    found = False
    start = None # start and end vars are the relative position of the starting/ending entrymarkers in the current buffer
    end = None
    startcursor = None # startcursor and endcursor are the absolute position of the starting/ending entrymarkers inside the database file
    endcursor = None
    buf = 1
    # Sanity check: cannot screen the file's content if the window is of the same size as the pattern to match (the marker)
    if blocksize <= len(entrymarker): blocksize = len(entrymarker) + 1
    # Continue the search as long as we did not find at least one starting marker and one ending marker (or end of file)
    while (not found and buf):
        # Read a long block at once, we will readjust the file cursor after
        buf = bytearray(file.read(blocksize))
        # Find the start marker (if not found already)
        if start is None or start == -1:
            start = buf.find(entrymarker); # relative position of the starting marker in the currently read string
            if start >= 0 and not startcursor: # assign startcursor only if it's empty (meaning that we did not find the starting entrymarker, else if found we are only looking for
                startcursor = file.tell() - len(buf) + start # absolute position of the starting marker in the file
            if start >= 0: start = start + len(entrymarker)
        # If we have a starting marker, we try to find a subsequent marker which will be the ending of our entry (if the entry is corrupted we don't care: it won't pass the entry_to_dict() decoding or subsequent steps of decoding and we will just pass to the next ecc entry). This allows to process any valid entry, no matter if previous ones were scrambled.
        if startcursor is not None and startcursor >= 0:
            end = buf.find(entrymarker, start)
            if end < 0 and len(buf) < blocksize: # Special case: we didn't find any ending marker but we reached the end of file, then we are probably in fact just reading the last entry (thus there's no ending marker for this entry)
                end = len(buf) # It's ok, we have our entry, the ending marker is just the end of file
            # If we found an ending marker (or if end of file is reached), then we compute the absolute cursor value and put the file reading cursor back in position, just before the next entry (where the ending marker is if any)
            if end >= 0:
                endcursor = file.tell() - len(buf) + end
                # Make sure we are not redetecting the same marker as the start marker
                if endcursor > startcursor:
                    file.seek(endcursor)
                    found = True
                else:
                    end = -1
                    encursor = None
        #print("Start:", start, startcursor)
        #print("End: ", end, endcursor)
        # Stop criterion to avoid infinite loop: in the case we could not find any entry in the rest of the file and we reached the EOF, we just quit now
        if len(buf) < blocksize: break
        # Did not find the full entry in one buffer? Reinit variables for next iteration, but keep in memory startcursor.
        if start > 0: start = 0 # reset the start position for the end buf find at next iteration (ie: in the arithmetic operations to compute the absolute endcursor position, the start entrymarker won't be accounted because it was discovered in a previous buffer).
        if not endcursor: file.seek(file.tell()-len(entrymarker)) # Try to fix edge case where blocksize stops the buffer exactly in the middle of the ending entrymarker. The starting marker should always be ok because it should be quite close (or generally immediately after) the previous entry, but the end depends on the end of the current entry (size of the original file), thus the buffer may miss the ending entrymarker. should offset file.seek(-len(entrymarker)) before searching for ending.

    if found: # if an entry was found, we seek to the beginning of the entry and then either read the entry from file or just return the markers positions (aka the entry bounds)
        file.seek(startcursor + len(entrymarker))
        if only_coord:
            # Return only coordinates of the start and end markers
            # Note: it is useful to just return the reading positions and not the entry itself because it can get quite huge and may overflow memory, thus we will read each ecc blocks on request using a generator.
            return [startcursor + len(entrymarker), endcursor]
        else:
            # Return the full entry's content
            return file.read(endcursor - startcursor - len(entrymarker))
    else:
        # Nothing found (or no new entry to find, we've already found them all), so we return None
        print("Entry not found")
        return None

def entry_fields(file, entry_pos, field_delim):
    '''
    From an ecc entry position (a list with starting and ending positions), extract the metadata fields
    (filename, filesize, ecc for both), and the starting/ending positions of the ecc stream (containing variably
    encoded blocks of hash and ecc per blocks of the original file's header)
    '''
    # Read the the beginning of the ecc entry
    blocksize = 65535
    file.seek(entry_pos[0])
    entry = file.read(blocksize)
    entry = entry.lstrip(field_delim) # if there was some slight adjustment error (example: the last ecc block of the last file was the field_delim, then we will start with a field_delim, and thus we need to remove the trailing field_delim which is useless and will make the field detection buggy). This is not really a big problem for the previous file's ecc block: the missing ecc characters (which were mistaken for a field_delim), will just be missing (so we will lose a bit of resiliency for the last block of the previous file, but that's not a huge issue, the correction can still rely on the other characters).
    # TODO: do in a while loop in case the filename is really big (bigger than blocksize) - or in case we add intra-ecc for filename

    # Find metadata fields delimiters positions
    # TODO: automate this part, just give in argument the number of field_delim to find, and the func will find the x field_delims (the number needs to be specified in argument because the field_delim can maybe be found wrongly inside the ecc stream, which we don't want)
    first = entry.find(field_delim)
    second = entry.find(field_delim, first+len(field_delim))
    third = entry.find(field_delim, second+len(field_delim))
    fourth = entry.find(field_delim, third+len(field_delim))
    # Note: we do not try to find all the field delimiters because we optimize here: we just walk the string to find the exact number of field_delim we are looking for, and after we stop, no need to walk through the whole string.

    # Extract the content of the fields
    # Metadata fields
    relfilepath = entry[:first]
    filesize = entry[first+len(field_delim):second]
    relfilepath_ecc = entry[second+len(field_delim):third]
    filesize_ecc = entry[third+len(field_delim):fourth]
    # Ecc stream field (aka ecc blocks)
    ecc_field_pos = [entry_pos[0]+fourth+len(field_delim), entry_pos[1]] # return the starting and ending position of the rest of the ecc track, which contains blocks of hash/ecc of the original file's content.

    # Place the cursor at the beginning of the ecc_field
    file.seek(ecc_field_pos[0])

    # Try to convert to an int, an error may happen
    try:
        filesize = int(filesize)
    except Exception as e:
        print("Exception when trying to detect the filesize in ecc field (it may be corrupted), skipping: ")
        print(e)
        #filesize = 0 # avoid setting to 0, we keep as an int so that we can try to fix using intra-ecc

    # entries = [ {"message":, "ecc":, "hash":}, etc.]
    return {"relfilepath": relfilepath, "relfilepath_ecc": relfilepath_ecc, "filesize": filesize, "filesize_ecc": filesize_ecc, "ecc_field_pos": ecc_field_pos}

def ecc_correct_intra_stream(ecc_manager_intra, ecc_params_intra, hasher_intra, resilience_rate_intra, field, ecc, entry_pos, enable_erasures=False, erasures_char="\x00", only_erasures=False, max_block_size=65535):
    """ Correct an intra-field with its corresponding intra-ecc if necessary """
    # convert strings to _StringIO object so that we can trick our ecc reading functions that normally works only on files
    fpfile = BytesIO(b(field))
    fpfile_ecc = BytesIO(b(ecc))
    fpentry_p = {"ecc_field_pos": [0, len(field)]} # create a fake entry_pos so that the ecc reading function works correctly
    # Prepare variables
    field_correct = [] # will store each block of the corrected (or already correct) filepath
    fcorrupted = False # check if field was corrupted
    fcorrected = True # check if field was corrected (if it was corrupted)
    errmsg = ''
    # Decode each block of the filepath
    for e in stream_entry_assemble(hasher_intra, fpfile, fpfile_ecc, fpentry_p, max_block_size, len(field), [resilience_rate_intra], constantmode=True):
        # Check if this block of the filepath is OK, if yes then we just copy it over
        if ecc_manager_intra.check(e["message"], e["ecc"]):
            field_correct.append(e["message"])
        else: # Else this block is corrupted, we will try to fix it using the ecc
            fcorrupted = True
            # Repair the message block and the ecc
            try:
                repaired_block, repaired_ecc = ecc_manager_intra.decode(e["message"], e["ecc"], enable_erasures=enable_erasures, erasures_char=erasures_char, only_erasures=only_erasures)
            except (ReedSolomonError, RSCodecError) as exc: # the reedsolo lib may raise an exception when it can't decode. We ensure that we can still continue to decode the rest of the file, and the other files.
                repaired_block = None
                repaired_ecc = None
                errmsg += "- Error: unrecoverable corrupted metadata field at offset %i: %s\n" % (entry_pos[0], exc)
            # Check if the block was successfully repaired: if yes then we copy the repaired block...
            if repaired_block is not None and ecc_manager_intra.check(repaired_block, repaired_ecc):
                field_correct.append(repaired_block)
            else: # ... else it failed, then we copy the original corrupted block and report an error later
                field_correct.append(e["message"])
                fcorrected = False
    # Join all the blocks into one string to build the final filepath
    field_correct = [b(x) for x in field_correct] # workaround when using --ecc_algo 3 or 4, because we get a list of bytearrays instead of str
    field = b''.join(field_correct)
    # Report errors
    return (field, fcorrupted, fcorrected, errmsg)

def stream_entry_assemble(hasher, file, eccfile, entry_fields, max_block_size, header_size, resilience_rates, constantmode=False):
    '''From an entry with its parameters (filename, filesize), assemble a list of each block from the original file along with the relative hash and ecc for easy processing later.'''
    # Cut the header and the ecc entry into blocks, and then assemble them so that we can easily process block by block
    eccfile.seek(entry_fields["ecc_field_pos"][0])
    curpos = file.tell()
    ecc_curpos = eccfile.tell()
    while (ecc_curpos < entry_fields["ecc_field_pos"][1]): # continue reading the input file until we reach the position of the previously detected ending marker
        # Compute the current rate, depending on where we are inside the input file (headers? later stage?)
        if curpos < header_size or constantmode: # header stage: constant rate
            rate = resilience_rates[0]
        else: # later stage 2 or 3: progressive rate
            rate = utils.feature_scaling(curpos, header_size, entry_fields["filesize"], resilience_rates[1], resilience_rates[2]) # find the rate for the current stream of data (interpolate between stage 2 and stage 3 rates depending on the cursor position in the file)
        # From the rate, compute the ecc parameters
        ecc_params = ecc.compute_ecc_params(max_block_size, rate, hasher)
        # Extract the message block from input file, given the computed ecc parameters
        mes = file.read(ecc_params["message_size"])
        if len(mes) == 0: return # quit if message is empty (reached end-of-file), this is a safeguard if ecc pos ending was miscalculated (we thus only need the starting position to be correct)
        buf = eccfile.read(ecc_params["hash_size"]+ecc_params["ecc_size"])
        hash = buf[:ecc_params["hash_size"]]
        ecc_result = buf[ecc_params["hash_size"]:]

        yield {"message": mes, "hash": hash, "ecc": ecc_result, "rate": rate, "ecc_params": ecc_params, "curpos": curpos, "ecc_curpos": ecc_curpos}
        # Prepare for the next iteration of the loop
        curpos = file.tell()
        ecc_curpos = eccfile.tell()
    # Just a quick safe guard against ecc ending marker misdetection
    file.seek(0, os.SEEK_END) # alternative way of finding the total size: go to the end of the file
    size = file.tell()
    if curpos < size: print("WARNING: end of ecc track reached but not the end of file! Either the ecc ending marker was misdetected, or either the file hash changed! Some blocks maybe may not have been properly checked!")
