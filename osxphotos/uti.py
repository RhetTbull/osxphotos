""" get UTI for a given file extension and the preferred extension for a given UTI """

""" Implementation note: runs only on macOS

    On macOS <= 11 (Big Sur), uses objective C CoreServices methods 
    UTTypeCopyPreferredTagWithClass and UTTypeCreatePreferredIdentifierForTag to retrieve the 
    UTI and the extension.  These are deprecated in 10.15 (Catalina) and no longer supported on Monterey.

    On Monterey, these calls are replaced with Swift methods that I can't call from python so 
    this code uses a cached dict of UTI values.  The code first checks to see if the extension or UTI 
    is available in the cache and if so, returns it. If not, it performs a subprocess call to `mdls` to 
    retrieve the UTI (by creating a temp file with the correct extension) and returns the UTI.  This only 
    works for the extension -> UTI lookup. On Monterey, if there is no cached value for UTI -> extension lookup, 
    returns None.

    It's a bit hacky but best I can think of to make this robust on different versions of macOS.  PRs welcome.
"""

import csv
import re
import subprocess
import tempfile

import CoreServices
import objc

from .utils import _get_os_version

# cached values of all the UTIs (< 6 chars long) known to my Mac running macOS 10.15.7
UTI_CSV = """extension,UTI,preferred_extension,MIME_type
c,public.c-source,c,None
f,public.fortran-source,f,None
h,public.c-header,h,None
i,public.c-source.preprocessed,i,None
l,public.lex-source,l,None
m,public.objective-c-source,m,None
o,public.object-code,o,None
r,com.apple.rez-source,r,None
s,public.assembly-source,s,None
y,public.yacc-source,y,None
z,public.z-archive,z,application/x-compress
aa,com.audible.aa-audiobook,aa,audio/audible
ai,com.adobe.illustrator.ai-image,ai,None
as,com.apple.applesingle-archive,as,None
au,public.au-audio,au,audio/basic
bz,public.bzip2-archive,bz2,application/x-bzip2
cc,public.c-plus-plus-source,cp,None
cp,public.c-plus-plus-source,cp,None
dv,public.dv-movie,dv,video/x-dv
gz,org.gnu.gnu-zip-archive,gz,application/x-gzip
hh,public.c-plus-plus-header,hh,None
hp,public.c-plus-plus-header,hh,None
ii,public.c-plus-plus-source.preprocessed,ii,None
js,com.netscape.javascript-source,js,text/javascript
lm,public.lex-source,l,None
mi,public.objective-c-source.preprocessed,mi,None
mm,public.objective-c-plus-plus-source,mm,None
pf,com.apple.colorsync-profile,icc,None
pl,public.perl-script,pl,text/x-perl-script
pm,public.perl-script,pl,text/x-perl-script
ps,com.adobe.postscript,ps,application/postscript
py,public.python-script,py,text/x-python-script
qt,com.apple.quicktime-movie,mov,video/quicktime
ra,com.real.realaudio,ram,audio/vnd.rn-realaudio
rb,public.ruby-script,rb,text/x-ruby-script
rm,com.real.realmedia,rm,application/vnd.rn-realmedia
sh,public.shell-script,sh,None
ts,public.mpeg-2-transport-stream,ts,None
ul,public.ulaw-audio,ul,None
uu,public.uuencoded-archive,uu,text/x-uuencode
wm,com.microsoft.windows-media-wm,wm,video/x-ms-wm
ym,public.yacc-source,y,None
aac,public.aac-audio,aac,audio/aac
aae,com.apple.photos.apple-adjustment-envelope,aae,None
aaf,org.aafassociation.advanced-authoring-format,aaf,None
aax,com.audible.aax-audiobook,aax,audio/vnd.audible.aax
abc,public.alembic,abc,None
ac3,public.ac3-audio,ac3,audio/ac3
ada,public.ada-source,ada,None
adb,public.ada-source,ada,None
ads,public.ada-source,ada,None
aif,public.aifc-audio,aifc,audio/aiff
amr,org.3gpp.adaptive-multi-rate-audio,amr,audio/amr
app,com.apple.application-bundle,app,None
arw,com.sony.arw-raw-image,arw,None
asf,com.microsoft.advanced-systems-format,asf,video/x-ms-asf
asx,com.microsoft.advanced-stream-redirector,asx,video/x-ms-asx
avi,public.avi,avi,video/avi
bdm,public.avchd-content,bdm,None
bin,com.apple.macbinary-archive,bin,application/macbinary
bmp,com.microsoft.bmp,bmp,image/bmp
bwf,com.microsoft.waveform-audio,wav,audio/vnd.wave
bz2,public.bzip2-archive,bz2,application/x-bzip2
caf,com.apple.coreaudio-format,caf,None
cdr,com.apple.disk-image-cdr,dvdr,None
cel,public.flc-animation,flc,video/flc
cer,public.x509-certificate,cer,application/x-x509-ca-cert
cpp,public.c-plus-plus-source,cp,None
crt,public.x509-certificate,cer,application/x-x509-ca-cert
crw,com.canon.crw-raw-image,crw,image/x-canon-crw
cr2,com.canon.cr2-raw-image,cr2,None
cr3,com.canon.cr3-raw-image,cr3,None
csh,public.csh-script,csh,None
css,public.css,css,text/css
csv,public.comma-separated-values-text,csv,text/csv
cxx,public.c-plus-plus-source,cp,None
dae,org.khronos.collada.digital-asset-exchange,dae,None
dcm,org.nema.dicom,dcm,application/dicom
dcr,com.kodak.raw-image,dcr,None
dds,com.microsoft.dds,dds,None
der,public.x509-certificate,cer,application/x-x509-ca-cert
dif,public.dv-movie,dv,video/x-dv
dll,com.microsoft.windows-dynamic-link-library,dll,application/x-msdownload
dls,public.downloadable-sound,dls,audio/dls
dmg,com.apple.disk-image-udif,dmg,None
dng,com.adobe.raw-image,dng,image/x-adobe-dng
doc,com.microsoft.word.doc,doc,application/msword
dot,com.microsoft.word.dot,dot,application/msword
dxo,com.dxo.raw-image,dxo,image/x-dxo-dxo
ec3,public.enhanced-ac3-audio,eac3,audio/eac3
edn,com.adobe.edn,edn,None
efx,com.j2.efx-fax,efx,image/efax
eml,com.apple.mail.email,eml,message/rfc822
eps,com.adobe.encapsulated-postscript,eps,None
erf,com.epson.raw-image,erf,image/x-epson-erf
etd,com.adobe.etd,etd,None
exe,com.microsoft.windows-executable,exe,application/x-msdownload
exp,com.apple.symbol-export,exp,None
exr,com.ilm.openexr-image,exr,None
fdf,com.adobe.fdf,fdf,None
fff,com.hasselblad.fff-raw-image,fff,None
flc,public.flc-animation,flc,video/flc
fli,public.flc-animation,flc,video/flc
flv,com.adobe.flash.video,flv,video/x-flv
for,public.fortran-source,f,None
fpx,com.kodak.flashpix-image,fpx,image/fpx
f4a,com.adobe.flash.video,flv,video/x-flv
f4b,com.adobe.flash.video,flv,video/x-flv
f4p,com.adobe.flash.video,flv,video/x-flv
f4v,com.adobe.flash.video,flv,video/x-flv
f77,public.fortran-77-source,f77,None
f90,public.fortran-90-source,f90,None
f95,public.fortran-95-source,f95,None
gif,com.compuserve.gif,gif,image/gif
hdr,public.radiance,pic,None
hpp,public.c-plus-plus-header,hh,None
hqx,com.apple.binhex-archive,hqx,application/mac-binhex40
htm,public.html,html,text/html
hxx,public.c-plus-plus-header,hh,None
iba,com.apple.ibooksauthor.pkgbook,iba,None
icc,com.apple.colorsync-profile,icc,None
icm,com.apple.colorsync-profile,icc,None
ico,com.microsoft.ico,ico,image/vnd.microsoft.icon
ics,com.apple.ical.ics,ics,text/calendar
iig,com.apple.iig-source,iig,None
iiq,com.phaseone.raw-image,iiq,None
img,com.apple.disk-image-ndif,ndif,None
inl,public.c-plus-plus-inline-header,inl,None
ipa,com.apple.itunes.ipa,ipa,None
ipp,public.c-plus-plus-header,hh,None
ips,com.apple.ips,ips,None
iso,public.iso-image,iso,None
ite,com.apple.tv.ite,ite,None
itl,com.apple.itunes.db,itl,None
jar,com.sun.java-archive,jar,application/java-archive
jav,com.sun.java-source,java,None
jfx,com.j2.jfx-fax,jfx,None
jpe,public.jpeg,jpeg,image/jpeg
jpf,public.jpeg-2000,jp2,image/jp2
jpg,public.jpeg,jpeg,image/jpeg
jpx,public.jpeg-2000,jp2,image/jp2
jp2,public.jpeg-2000,jp2,image/jp2
j2c,public.jpeg-2000,jp2,image/jp2
j2k,public.jpeg-2000,jp2,image/jp2
kar,public.midi-audio,midi,audio/midi
key,com.apple.iwork.keynote.key,key,None
ksh,public.ksh-script,ksh,None
kth,com.apple.iwork.keynote.kth,kth,None
ktx,org.khronos.ktx,ktx,None
lid,public.dylan-source,dlyan,None
lmm,public.lex-source,l,None
log,com.apple.log,log,None
lpp,public.lex-source,l,None
lxx,public.lex-source,l,None
mid,public.midi-audio,midi,audio/midi
mig,public.mig-source,defs,None
mii,public.objective-c-plus-plus-source.preprocessed,mii,None
mjs,com.netscape.javascript-source,js,text/javascript
mnc,ca.mcgill.mni.bic.mnc,mnc,None
mos,com.leafamerica.raw-image,mos,None
mov,com.apple.quicktime-movie,mov,video/quicktime
mpe,public.mpeg,mpg,video/mpeg
mpg,public.mpeg,mpg,video/mpeg
mpo,public.mpo-image,mpo,None
mp2,public.mp2,mp2,None
mp3,public.mp3,mp3,audio/mpeg
mp4,public.mpeg-4,mp4,video/mp4
mrw,com.konicaminolta.raw-image,mrw,None
mts,public.avchd-mpeg-2-transport-stream,mts,None
mxf,org.smpte.mxf,mxf,application/mxf
m15,public.mpeg,mpg,video/mpeg
m2v,public.mpeg-2-video,m2v,video/mpeg2
m3u,public.m3u-playlist,m3u,audio/mpegurl
m4a,com.apple.m4a-audio,m4a,audio/x-m4a
m4b,com.apple.protected-mpeg-4-audio-b,m4b,None
m4p,com.apple.protected-mpeg-4-audio,m4p,None
m4r,com.apple.mpeg-4-ringtone,m4r,audio/x-m4r
m4v,com.apple.m4v-video,m4v,video/x-m4v
m75,public.mpeg,mpg,video/mpeg
nef,com.nikon.raw-image,nef,None
nii,gov.nih.nifti-1,nii,None
nrw,com.nikon.nrw-raw-image,nrw,image/x-nikon-nrw
obj,public.geometry-definition-format,obj,None
odb,org.oasis-open.opendocument.database,odb,application/vnd.oasis.opendocument.database
odc,org.oasis-open.opendocument.chart,odc,application/vnd.oasis.opendocument.chart
odf,org.oasis-open.opendocument.formula,odf,application/vnd.oasis.opendocument.formula
odg,org.oasis-open.opendocument.graphics,odg,application/vnd.oasis.opendocument.graphics
odi,org.oasis-open.opendocument.image,odi,application/vnd.oasis.opendocument.image
odm,org.oasis-open.opendocument.text-master,odm,application/vnd.oasis.opendocument.text-master
odp,org.oasis-open.opendocument.presentation,odp,application/vnd.oasis.opendocument.presentation
ods,org.oasis-open.opendocument.spreadsheet,ods,application/vnd.oasis.opendocument.spreadsheet
odt,org.oasis-open.opendocument.text,odt,application/vnd.oasis.opendocument.text
omf,com.avid.open-media-framework,omf,None
orf,com.olympus.raw-image,orf,None
otc,public.opentype-collection-font,otc,None
otf,public.opentype-font,otf,None
otg,org.oasis-open.opendocument.graphics-template,otg,application/vnd.oasis.opendocument.graphics-template
oth,org.oasis-open.opendocument.text-web,oth,application/vnd.oasis.opendocument.text-web
oti,org.oasis-open.opendocument.image-template,oti,application/vnd.oasis.opendocument.image-template
otp,org.oasis-open.opendocument.presentation-template,otp,application/vnd.oasis.opendocument.presentation-template
ots,org.oasis-open.opendocument.spreadsheet-template,ots,application/vnd.oasis.opendocument.spreadsheet-template
ott,org.oasis-open.opendocument.text-template,ott,application/vnd.oasis.opendocument.text-template
pas,public.pascal-source,pas,None
pax,public.cpio-archive,cpio,None
pbm,public.pbm,pbm,None
pch,public.precompiled-c-header,pch,None
pct,com.apple.pict,pict,image/pict
pdf,com.adobe.pdf,pdf,application/pdf
pef,com.pentax.raw-image,pef,None
pem,public.x509-certificate,cer,application/x-x509-ca-cert
pfa,com.adobe.postscript-pfa-font,pfa,None
pfb,com.adobe.postscript-pfb-font,pfb,None
pfm,public.pbm,pbm,None
pfx,com.rsa.pkcs-12,p12,application/x-pkcs12
pgm,public.pbm,pbm,None
pgn,com.apple.chess.pgn,pgn,None
php,public.php-script,php,text/php
ph3,public.php-script,php,text/php
ph4,public.php-script,php,text/php
pic,com.apple.pict,pict,image/pict
pkg,com.apple.installer-package-archive,pkg,None
pls,public.pls-playlist,pls,audio/x-scpls
ply,public.polygon-file-format,ply,None
png,public.png,png,image/png
pot,com.microsoft.powerpoint.pot,pot,application/vnd.ms-powerpoint
ppm,public.pbm,pbm,None
pps,com.microsoft.powerpoint.pps,pps,application/vnd.ms-powerpoint
ppt,com.microsoft.powerpoint.ppt,ppt,application/vnd.ms-powerpoint
psb,com.adobe.photoshop-large-image,psb,None
psd,com.adobe.photoshop-image,psd,image/vnd.adobe.photoshop
pvr,public.pvr,pvr,None
pvt,com.apple.private.live-photo-bundle,pvt,None
pwl,com.leica.pwl-raw-image,pwl,image/x-leica-pwl
p12,com.rsa.pkcs-12,p12,application/x-pkcs12
qti,com.apple.quicktime-image,qtif,image/x-quicktime
qtz,com.apple.quartz-composer-composition,qtz,application/x-quartzcomposer
raf,com.fuji.raw-image,raf,None
ram,com.real.realaudio,ram,audio/vnd.rn-realaudio
raw,com.panasonic.raw-image,raw,None
rbw,public.ruby-script,rb,text/x-ruby-script
rmp,com.apple.music.rmp-playlist,rmp,application/vnd.rn-rn_music_package
rss,public.rss,rss,application/rss+xml
rtf,public.rtf,rtf,text/rtf
rwl,com.leica.rwl-raw-image,rwl,None
rw2,com.panasonic.rw2-raw-image,rw2,None
scc,com.scenarist.closed-caption,scc,None
scn,com.apple.scenekit.scene,scn,None
sda,org.openoffice.graphics,sxd,application/vnd.sun.xml.draw
sdc,org.openoffice.spreadsheet,sxc,application/vnd.sun.xml.calc
sdd,org.openoffice.presentation,sxi,application/vnd.sun.xml.impress
sdp,org.openoffice.presentation,sxi,application/vnd.sun.xml.impress
sdv,public.3gpp,3gp,video/3gpp
sdw,org.openoffice.text,sxw,application/vnd.sun.xml.writer
sd2,com.digidesign.sd2-audio,sd2,None
sea,com.stuffit.archive.sit,sit,application/x-stuffit
sf2,com.soundblaster.soundfont,sf2,None
sgi,com.sgi.sgi-image,sgi,image/sgi
sit,com.stuffit.archive.sit,sit,application/x-stuffit
slm,com.apple.photos.slow-motion-video-sidecar,slm,None
smf,public.midi-audio,midi,audio/midi
smi,com.apple.disk-image-smi,smi,None
snd,public.au-audio,au,audio/basic
spx,com.apple.systemprofiler.document,spx,None
srf,com.sony.raw-image,srf,None
srw,com.samsung.raw-image,srw,None
sr2,com.sony.sr2-raw-image,sr2,image/x-sony-sr2
stc,org.openoffice.spreadsheet-template,stc,application/vnd.sun.xml.calc.template
std,org.openoffice.graphics-template,std,application/vnd.sun.xml.draw.template
sti,org.openoffice.presentation-template,sti,application/vnd.sun.xml.impress.template
stl,public.standard-tesselated-geometry-format,stl,None
stw,org.openoffice.text-template,stw,application/vnd.sun.xml.writer.template
svg,public.svg-image,svg,image/svg+xml
sxc,org.openoffice.spreadsheet,sxc,application/vnd.sun.xml.calc
sxd,org.openoffice.graphics,sxd,application/vnd.sun.xml.draw
sxg,org.openoffice.text-master,sxg,application/vnd.sun.xml.writer.global
sxi,org.openoffice.presentation,sxi,application/vnd.sun.xml.impress
sxm,org.openoffice.formula,sxm,application/vnd.sun.xml.math
sxw,org.openoffice.text,sxw,application/vnd.sun.xml.writer
tar,public.tar-archive,tar,application/x-tar
tbz,public.tar-bzip2-archive,tbz2,None
tga,com.truevision.tga-image,tga,image/targa
tgz,org.gnu.gnu-zip-tar-archive,tgz,None
tif,public.tiff,tiff,image/tiff
tsv,public.tab-separated-values-text,tsv,text/tab-separated-values
ttc,public.truetype-collection-font,ttc,None
ttf,public.truetype-ttf-font,ttf,None
txt,public.plain-text,txt,text/plain
ulw,public.ulaw-audio,ul,None
url,com.microsoft.internet-shortcut,url,None
usd,com.pixar.universal-scene-description,usd,None
vcf,public.vcard,vcf,text/directory
vcs,com.apple.ical.vcs,vcs,text/x-vcalendar
vfw,public.avi,avi,video/avi
vtt,org.w3.webvtt,vtt,text/vtt
war,com.sun.web-application-archive,war,None
wav,com.microsoft.waveform-audio,wav,audio/vnd.wave
wax,com.microsoft.windows-media-wax,wax,video/x-ms-wax
web,com.getdropbox.dropbox.shortcut,web,None
wma,com.microsoft.windows-media-wma,wma,video/x-ms-wma
wmp,com.microsoft.windows-media-wmp,wmp,video/x-ms-wmp
wmv,com.microsoft.windows-media-wmv,wmv,video/x-ms-wmv
wmx,com.microsoft.windows-media-wmx,wmx,video/x-ms-wmx
wvx,com.microsoft.windows-media-wvx,wvx,video/x-ms-wvx
xar,com.apple.xar-archive,xar,None
xbm,public.xbitmap-image,xbm,image/x-xbitmap
xfd,public.xfd,xfd,None
xht,public.xhtml,xhtml,application/xhtml+xml
xip,com.apple.xip-archive,xip,None
xla,com.microsoft.excel.xla,xla,None
xls,com.microsoft.excel.xls,xls,application/vnd.ms-excel
xlt,com.microsoft.excel.xlt,xlt,application/vnd.ms-excel
xlw,com.microsoft.excel.xlw,xlw,application/vnd.ms-excel
xml,public.xml,xml,application/xml
xmp,com.seriflabs.xmp,xmp,application/rdf+xml
xpc,com.apple.xpc-service,xpc,None
yml,public.yaml,yml,application/x-yaml
ymm,public.yacc-source,y,None
ypp,public.yacc-source,y,None
yxx,public.yacc-source,y,None
zip,public.zip-archive,zip,application/zip
zsh,public.zsh-script,zsh,None
3fr,com.hasselblad.3fr-raw-image,3fr,None
3gp,public.3gpp,3gp,video/3gpp
3g2,public.3gpp2,3g2,video/3gpp2
adts,public.aac-audio,aac,audio/aac
ahap,com.apple.haptics.ahap,ahap,None
aifc,public.aifc-audio,aifc,audio/aiff
aiff,public.aifc-audio,aifc,audio/aiff
astc,org.khronos.astc,astc,None
avci,public.avci,avci,image/avci
avcs,public.avcs,avcs,image/avcs
band,com.apple.garageband.project,band,None
bash,public.bash-script,bash,None
bdmv,public.avchd-content,bdm,None
book,com.apple.ibooksauthor.pkgbook,iba,None
cdda,public.aifc-audio,aifc,audio/aiff
chat,com.apple.ichat.transcript,ichat,None
cpgz,com.apple.bom-compressed-cpio,cpgz,None
cpio,public.cpio-archive,cpio,None
dart,com.apple.disk-image-dart,dart,None
dc42,com.apple.disk-image-dc42,dc42,None
defs,public.mig-source,defs,None
dext,com.apple.driver-extension,dext,None
diff,public.patch-file,patch,None
dist,com.apple.installer-distribution-package,dist,None
docm,org.openxmlformats.wordprocessingml.document.macroenabled,docm,application/vnd.ms-word.document.macroenabled.12
docx,org.openxmlformats.wordprocessingml.document,docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document
dotm,org.openxmlformats.wordprocessingml.template.macroenabled,dotm,application/vnd.ms-word.template.macroenabled.12
dotx,org.openxmlformats.wordprocessingml.template,dotx,application/vnd.openxmlformats-officedocument.wordprocessingml.template
dsym,com.apple.xcode.dsym,dsym,None
dvdr,com.apple.disk-image-cdr,dvdr,None
eac3,public.enhanced-ac3-audio,eac3,audio/eac3
emlx,com.apple.mail.emlx,emlx,None
enex,com.evernote.enex,enex,None
epub,org.idpf.epub-container,epub,application/epub+zip
fh10,com.seriflabs.affinity,fh10,None
fh11,com.seriflabs.affinity,fh10,None
flac,org.xiph.flac,flac,audio/flac
fpbf,com.apple.finder.burn-folder,fpbf,None
game,com.apple.chess.game,game,None
gdoc,com.google.gdoc,gdoc,None
gtar,org.gnu.gnu-tar-archive,gtar,application/x-gtar
gzip,org.gnu.gnu-zip-archive,gz,application/x-gzip
hang,com.apple.hangreport,hang,None
heic,public.heic,heic,image/heic
heif,public.heif,heif,image/heif
html,public.html,html,text/html
hvpl,com.apple.music.visual,hvpl,None
icbu,com.apple.ical.backup,icbu,None
icns,com.apple.icns,icns,None
ipsw,com.apple.itunes.ipsw,ipsw,None
itlp,com.apple.music.itlp,itlp,None
itms,com.apple.itunes.store-url,itms,None
java,com.sun.java-source,java,None
jnlp,com.sun.java-web-start,jnlp,application/x-java-jnlp-file
jpeg,public.jpeg,jpeg,image/jpeg
json,public.json,json,application/json
latm,public.mp4a-loas,loas,None
loas,public.mp4a-loas,loas,None
lpdf,com.apple.localized-pdf-bundle,lpdf,None
mbox,com.apple.mail.mbox,mbox,None
menu,com.apple.menu-extra,menu,None
midi,public.midi-audio,midi,audio/midi
minc,ca.mcgill.mni.bic.mnc,mnc,None
mpeg,public.mpeg,mpg,video/mpeg
mpga,public.mp3,mp3,audio/mpeg
mpg4,public.mpeg-4,mp4,video/mp4
mpkg,com.apple.installer-package-archive,pkg,None
m2ts,public.avchd-mpeg-2-transport-stream,mts,None
m3u8,public.m3u-playlist,m3u,audio/mpegurl
ndif,com.apple.disk-image-ndif,ndif,None
note,com.apple.notes.note,note,None
php3,public.php-script,php,text/php
php4,public.php-script,php,text/php
pict,com.apple.pict,pict,image/pict
pntg,com.apple.macpaint-image,pntg,None
potm,org.openxmlformats.presentationml.template.macroenabled,potm,application/vnd.ms-powerpoint.template.macroenabled.12
potx,org.openxmlformats.presentationml.template,potx,application/vnd.openxmlformats-officedocument.presentationml.template
ppsm,org.openxmlformats.presentationml.slideshow.macroenabled,ppsm,application/vnd.ms-powerpoint.slideshow.macroenabled.12
ppsx,org.openxmlformats.presentationml.slideshow,ppsx,application/vnd.openxmlformats-officedocument.presentationml.slideshow
pptm,org.openxmlformats.presentationml.presentation.macroenabled,pptm,application/vnd.ms-powerpoint.presentation.macroenabled.12
pptx,org.openxmlformats.presentationml.presentation,pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation
pset,com.apple.pdf-printer-settings,pset,None
qtif,com.apple.quicktime-image,qtif,image/x-quicktime
rmvb,com.real.realmedia-vbr,rmvb,application/vnd.rn-realmedia-vbr
rtfd,com.apple.rtfd,rtfd,None
scnz,com.apple.scenekit.scene,scn,None
scpt,com.apple.applescript.script,scpt,None
shtm,public.html,html,text/html
sidx,com.stuffit.archive.sidx,sidx,application/x-stuffitx-index
sitx,com.stuffit.archive.sitx,sitx,application/x-stuffitx
spin,com.apple.spinreport,spin,None
suit,com.apple.font-suitcase,suit,None
svgz,public.svg-image,svg,image/svg+xml
tbz2,public.tar-bzip2-archive,tbz2,None
tcsh,public.tcsh-script,tcsh,None
term,com.apple.terminal.session,term,None
text,public.plain-text,txt,text/plain
tiff,public.tiff,tiff,image/tiff
tool,com.apple.terminal.shell-script,command,None
udif,com.apple.disk-image-udif,dmg,None
ulaw,public.ulaw-audio,ul,None
usda,com.pixar.universal-scene-description,usd,None
usdc,com.pixar.universal-scene-description,usd,None
usdz,com.pixar.universal-scene-description-mobile,usdz,model/vnd.usdz+zip
vcal,com.apple.ical.vcs,vcs,text/x-vcalendar
wave,com.microsoft.waveform-audio,wav,audio/vnd.wave
wdgt,com.apple.dashboard-widget,wdgt,None
webp,public.webp,webp,None
xfdf,com.adobe.xfdf,xfdf,None
xhtm,public.xhtml,xhtml,application/xhtml+xml
xlsb,com.microsoft.excel.sheet.binary.macroenabled,xlsb,application/vnd.ms-excel.sheet.binary.macroenabled.12
xlsm,org.openxmlformats.spreadsheetml.sheet.macroenabled,xlsm,application/vnd.ms-excel.sheet.macroenabled.12
xlsx,org.openxmlformats.spreadsheetml.sheet,xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
xltm,org.openxmlformats.spreadsheetml.template.macroenabled,xltm,application/vnd.ms-excel.template.macroenabled.12
xltx,org.openxmlformats.spreadsheetml.template,xltx,application/vnd.openxmlformats-officedocument.spreadsheetml.template
yaml,public.yaml,yml,application/x-yaml
3gpp,public.3gpp,3gp,video/3gpp
3gp2,public.3gpp2,3g2,video/3gpp2
abcdg,com.apple.addressbook.group,abcdg,None
abcdp,com.apple.addressbook.person,abcdp,None
afpub,com.seriflabs.affinitypublisher.document,afpub,None
appex,com.apple.application-and-system-extension,appex,None
avchd,public.avchd-collection,avchd,None
blank,com.apple.preview.blank,blank,None
class,com.sun.java-class,class,None
crash,com.apple.crashreport,crash,None
dfont,com.apple.truetype-datafork-suitcase-font,dfont,None
dicom,org.nema.dicom,dcm,application/dicom
distz,com.apple.installer-distribution-package,dist,None
dlyan,public.dylan-source,dlyan,None
dylib,com.apple.mach-o-dylib,dylib,None
heics,public.heics,heics,image/heic-sequence
heifs,public.heifs,heifs,image/heif-sequence
ichat,com.apple.ichat.transcript,ichat,None
pages,com.apple.iwork.pages.pages,pages,None
panic,com.apple.panicreport,panic,None
paper,com.getdropbox.dropbox.paper,paper,None
patch,public.patch-file,patch,None
phtml,public.php-script,php,text/php
plist,com.apple.property-list,plist,None
saver,com.apple.systempreference.screen-saver,saver,None
scptd,com.apple.applescript.script-bundle,scptd,None
sfont,com.apple.cfr-font,sfont,None
shtml,public.html,html,text/html
swift,public.swift-source,swift,None
toast,com.roxio.disk-image-toast,toast,None
vcard,public.vcard,vcf,text/directory
wdmon,com.apple.wireless-diagnostics.wdmon,wdmon,None
xhtml,public.xhtml,xhtml,application/xhtml+xml
action,com.apple.automator-action,action,None
afploc,com.apple.afp-internet-location,afploc,None
"""

# load CSV separated uti data into dictionaries with key of extension and UTI
EXT_UTI_DICT = {}
UTI_EXT_DICT = {}


def _load_uti_dict():
    """load an initialize the cached UTI and extension dicts"""
    _reader = csv.DictReader(UTI_CSV.split("\n"), delimiter=",")
    for row in _reader:
        EXT_UTI_DICT[row["extension"]] = row["UTI"]
        UTI_EXT_DICT[row["UTI"]] = row["preferred_extension"]


_load_uti_dict()

# OS version for determining which methods can be used
OS_VER, OS_MAJOR, _ = (int(x) for x in _get_os_version())


def _get_uti_from_mdls(extension):
    """use mdls to get the UTI for a given extension on systems that don't support UTTypeCreatePreferredIdentifierForTag
    Returns: UTI or None if UTI cannot be determined"""

    # mdls -name kMDItemContentType foo.3fr
    # kMDItemContentType = "com.hasselblad.3fr-raw-image"

    with tempfile.NamedTemporaryFile(suffix="." + extension) as temp:
        output = subprocess.check_output(
            [
                "/usr/bin/mdls",
                "-name",
                "kMDItemContentType",
                temp.name,
            ]
        ).splitlines()
        output = output[0].decode("UTF-8") if output else None
        if not output:
            return None

        match = re.match(r'kMDItemContentType\s+\=\s+"(.*)"', output)
        if match:
            return match.group(1)
        return None


def _get_uti_from_ext_dict(ext):
    try:
        return EXT_UTI_DICT[ext]
    except KeyError:
        return None


def _get_ext_from_uti_dict(uti):
    try:
        return UTI_EXT_DICT[uti]
    except KeyError:
        return None


def get_preferred_uti_extension(uti):
    """get preferred extension for a UTI type
    uti: UTI str, e.g. 'public.jpeg'
    returns: preferred extension as str or None if cannot be determined"""

    if (OS_VER, OS_MAJOR) <= (10, 16):
        # reference: https://developer.apple.com/documentation/coreservices/1442744-uttypecopypreferredtagwithclass?language=objc
        # deprecated in Catalina+, likely won't work at all on macOS 12
        with objc.autorelease_pool():
            extension = CoreServices.UTTypeCopyPreferredTagWithClass(
                uti, CoreServices.kUTTagClassFilenameExtension
            )
            if extension:
                return extension

            # on MacOS 10.12, HEIC files are not supported and UTTypeCopyPreferredTagWithClass will return None for HEIC
            if uti == "public.heic":
                return "HEIC"

            return None

    return _get_ext_from_uti_dict(uti)


def get_uti_for_extension(extension):
    """get UTI for a given file extension"""

    # accepts extension with or without leading 0
    if extension[0] == ".":
        extension = extension[1:]

    if (OS_VER, OS_MAJOR) <= (10, 16):
        # https://developer.apple.com/documentation/coreservices/1448939-uttypecreatepreferredidentifierf
        with objc.autorelease_pool():
            uti = CoreServices.UTTypeCreatePreferredIdentifierForTag(
                CoreServices.kUTTagClassFilenameExtension, extension, None
            )
            if uti:
                return uti

            # on MacOS 10.12, HEIC files are not supported and UTTypeCopyPreferredTagWithClass will return None for HEIC
            if extension.lower() == "heic":
                return "public.heic"

            return None

    uti = _get_uti_from_ext_dict(extension)
    if uti:
        return uti

    uti = _get_uti_from_mdls(extension)
    if uti:
        # cache the UTI
        EXT_UTI_DICT[extension.lower()] = uti
        UTI_EXT_DICT[uti] = extension.lower()
        return uti

    return None
