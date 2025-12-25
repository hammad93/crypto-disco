# Please try to keep only basic data structures in this file
app_width = 700
app_height = 400
table_width = app_width * (4/7)
window_title = "Crypto Disco"
total_size_prefix = "Total Size:"
table_cols = ["File Size", "ECC", "Clone", "File Name"]
file_size_col_w = 80
ecc_col_w = 45
clone_col_w = 45
disc_types = ["4.7 GB M-DISC DVD+R",
              "25 GB M-DISC BD-R",
              "50 GB M-DISC BD-R",
              "100 GB M-DISC BDXL"]
default_disc_type = "25 GB M-DISC BD-R"
default_files = [":/assets/README.md", ":/assets/crypto-disco.zip"]
disc_icon = ":/assets/disc-drive-reshot.png"
wand_icon = ":/assets/fix-reshot.png"
iso9660_overhead_approx = 8 # percent, pycdlib utilizes the ISO9660 filesystem
donut_chart = {
    "slices_colors": ["#7e7e7e", "#9b9b9b", "#bdbdbd"],
    "remaining_color": "#5abd5a",
    "exceeding_color": "#bd5a5a",
    "update_timer": 1250 # in milliseconds
}
unzip_err = {
    "multiple_single_zip": "If you are extracting single ZIP files, please do them one at a time. Multipart ZIP "
                               "files are combined into one and have the expected file extension of .partX_of_Y",
    "missing_parts": "All parts from a multipart or split ZIP file need to be in the same directory. The following "
                         "files were missing from the directory:",
}