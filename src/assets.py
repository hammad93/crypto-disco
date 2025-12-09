# Resource object code (Python 3)
# Created by: object code
# Created by: The Resource Compiler for Qt version 6.10.1
# WARNING! All changes made in this file will be lost!

from PySide6 import QtCore

qt_resource_data = b"\
\x00\x00\x04\xef\
<\
svg xmlns=\x22http:\
//www.w3.org/200\
0/svg\x22 width=\x2212\
8\x22 height=\x22128\x22 \
viewBox=\x220 0 128\
 128\x22>\x0d\x0a  <title\
>DISC</title>\x0d\x0a \
 <g>\x0d\x0a    <path \
d=\x22M64,6.306A57.\
694,57.694,0,1,0\
,121.694,64,57.6\
95,57.695,0,0,0,\
64,6.306Zm0,68.7\
5A11.056,11.056,\
0,1,1,75.056,64,\
11.056,11.056,0,\
0,1,64,75.056Z\x22 \
fill=\x22#e5e5e5\x22/>\
\x0d\x0a    <path d=\x22M\
64,37.052A26.948\
,26.948,0,1,0,90\
.948,64,26.948,2\
6.948,0,0,0,64,3\
7.052Zm0,38A11.0\
56,11.056,0,1,1,\
75.056,64,11.056\
,11.056,0,0,1,64\
,75.056Z\x22 fill=\x22\
#f7b82d\x22/>\x0d\x0a    \
<path d=\x22M43.223\
,25.129a1.75,1.7\
5,0,0,1-.8-3.308\
,47.4,47.4,0,0,1\
,5.129-2.255,1.7\
5,1.75,0,0,1,1.2\
16,3.283,43.644,\
43.644,0,0,0-4.7\
49,2.088A1.755,1\
.755,0,0,1,43.22\
3,25.129Z\x22 fill=\
\x22#707070\x22/>\x0d\x0a   \
 <path d=\x22M21.20\
8,49.912a1.753,1\
.753,0,0,1-1.642\
-2.359,47.361,47\
.361,0,0,1,15.95\
-21.4,1.75,1.75,\
0,0,1,2.107,2.8A\
43.86,43.86,0,0,\
0,22.849,48.769,\
1.752,1.752,0,0,\
1,21.208,49.912Z\
\x22 fill=\x22#707070\x22\
/>\x0d\x0a    <path d=\
\x22M79.839,108.543\
a1.751,1.751,0,0\
,1-.608-3.392,43\
.644,43.644,0,0,\
0,4.749-2.088,1.\
75,1.75,0,0,1,1.\
6,3.116,47.4,47.\
4,0,0,1-5.129,2.\
255A1.751,1.751,\
0,0,1,79.839,108\
.543Z\x22 fill=\x22#70\
7070\x22/>\x0d\x0a    <pa\
th d=\x22M91.432,10\
2.2a1.75,1.75,0,\
0,1-1.055-3.148,\
43.86,43.86,0,0,\
0,14.774-19.823,\
1.75,1.75,0,0,1,\
3.283,1.216,47.3\
61,47.361,0,0,1-\
15.95,21.4A1.742\
,1.742,0,0,1,91.\
432,102.2Z\x22 fill\
=\x22#707070\x22/>\x0d\x0a  \
</g>\x0d\x0a</svg>\x0d\x0a\
\x00\x00\x08\x1f\
#\
 crypto-disco\x0a\x0aA\
 repository cont\
aining software \
and resources fo\
r archival of da\
ta on M-Discs in\
cluding use case\
s for cryptocurr\
ency, bioinforma\
tics, artificial\
 intelligence, p\
hotos, videos, m\
usic, and emerge\
ncy planning.\x0a\x0a#\
# Installation\x0a\x0a\
### Development\x0a\
\x0aThese sets of c\
ommands on Ubunt\
u, Linux, or equ\
ivalent can be u\
tilized to insta\
ll the developme\
nt application.\x0a\
Please note that\
 _pypy_ is requi\
red instead of t\
he standard _pyt\
hon_ interpreter\
. This is becaus\
e the error corr\
ecting codes (EC\
C) have signific\
ant processing t\
ime reductions.\x0a\
\x0a```bash\x0asudo ap\
t install pypy3\x0a\
pypy3 -m venv ve\
nv\x0asource venv/b\
in/activate\x0apip \
install -r src/r\
equirements.txt\x0a\
cd src\x0apypy3 src\
/app.py\x0a```\x0a\x0a###\
# Compilation\x0a\x0aI\
n order to impor\
t various files \
to the applicati\
on for deploymen\
t, it's necessar\
y to compile the\
m into the _QRC_\
 format. [Click \
here](https://do\
c.qt.io/qtforpyt\
hon-6/tutorials/\
basictutorial/qr\
cfiles.html#tuto\
rial-qrcfiles) f\
or details on th\
is file. Verify \
that the `assets\
.qrc` XML file i\
s updated and th\
en run this comm\
and,\x0a\x0a```bash\x0apy\
side6-rcc assets\
.qrc -o src/asse\
ts.py\x0a```\x0a\x0aThere\
 is already an `\
assets.py` inclu\
ded in the repos\
itory but it mig\
ht not be update\
d. Recompile it \
for the latest c\
hanges.\x0a\x0a## Comp\
liance\x0a\x0a### Disc\
laimer\x0a\x0a_This so\
ftware is releas\
ed under the CC0\
 license, which \
means it is in t\
he public domain\
 and can be used\
 freely. Please \
review requireme\
nts.txt for any \
packaged softwar\
e that may be su\
bject to other l\
icenses. Additio\
nally, the softw\
are supports var\
ious disc format\
s including M-DI\
SC, BD-R, DVD-R,\
 and BDXL. Users\
 should ensure t\
heir hardware is\
 compatible with\
 these formats b\
efore use. For m\
ore detailed inf\
ormation about c\
ompatibility and\
 usage, please r\
efer to the user\
 documentation p\
rovided with the\
 software._\x0a\x0a###\
 Trademark Notic\
e\x0a\x0a_All other pr\
oduct names, log\
os, and brands a\
re the property \
of their respect\
ive owners and a\
re used for iden\
tification purpo\
ses only. Use of\
 these names, lo\
gos, and brands \
does not imply e\
ndorsement._\x0a\x0a##\
# Contact Inform\
ation\x0a\x0a_For inqu\
iries, please co\
ntact the virtua\
l assistant at v\
a@fluids.ai._\x0a\
"

qt_resource_name = b"\
\x00\x06\
\x06\x8a\x9c\xb3\
\x00a\
\x00s\x00s\x00e\x00t\x00s\
\x00\x15\
\x02\xe3\xff\x87\
\x00d\
\x00i\x00s\x00c\x00-\x00d\x00r\x00i\x00v\x00e\x00-\x00r\x00e\x00s\x00h\x00o\x00t\
\x00.\x00s\x00v\x00g\
\x00\x09\
\x05\x91\xe8\x14\
\x00R\
\x00E\x00A\x00D\x00M\x00E\x00.\x00m\x00d\
"

qt_resource_struct = b"\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\
\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x02\
\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x12\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\
\x00\x00\x01\x9a\xe4!8\x11\
\x00\x00\x00B\x00\x00\x00\x00\x00\x01\x00\x00\x04\xf3\
\x00\x00\x01\x9b\x04\xc6\x92b\
"

def qInitResources():
    QtCore.qRegisterResourceData(0x03, qt_resource_struct, qt_resource_name, qt_resource_data)

def qCleanupResources():
    QtCore.qUnregisterResourceData(0x03, qt_resource_struct, qt_resource_name, qt_resource_data)

qInitResources()
