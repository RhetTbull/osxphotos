<%def name="photoshop_sidecar_for_extension(extension)">
    % if extension is None:
        <photoshop:SidecarForExtension></photoshop:SidecarForExtension>
    % else:
        <photoshop:SidecarForExtension>${extension}</photoshop:SidecarForExtension>
    % endif
</%def>

<%def name="dc_description(desc)">
    % if desc is None:
        <dc:description>
         <rdf:Alt>
          <rdf:li xml:lang='x-default'/>
         </rdf:Alt>
        </dc:description>
    % else:
        <dc:description>
        <rdf:Alt>
         <rdf:li xml:lang='x-default'>${desc | x}</rdf:li>
        </rdf:Alt>
        </dc:description>
    % endif
</%def>

<%def name="dc_title(title)">
    % if title is None:
        <dc:title>
         <rdf:Alt>
          <rdf:li xml:lang='x-default'/>
         </rdf:Alt>
        </dc:title>
    % else:
        <dc:title>
         <rdf:Alt>
          <rdf:li xml:lang='x-default'>${title | x}</rdf:li>
         </rdf:Alt>
        </dc:title>
    % endif
</%def>

<%def name="dc_subject(subject)">
    % if subject:
        <dc:subject>
         <rdf:Bag>
         % for subj in subject:
          <rdf:li>${subj | x}</rdf:li>
         % endfor
         </rdf:Bag>
        </dc:subject>
    % endif
</%def>

<%def name="dc_datecreated(date)">
    % if date is not None:
        <photoshop:DateCreated>${date.isoformat()}</photoshop:DateCreated>
    % endif
</%def>

<%def name="iptc_personinimage(persons)">
    % if persons:
        <Iptc4xmpExt:PersonInImage>
        <rdf:Bag>
         % for person in persons:
         <rdf:li>${person | x}</rdf:li>
         % endfor
        </rdf:Bag>
        </Iptc4xmpExt:PersonInImage>
    % endif 
</%def>

<%def name="dk_tagslist(keywords)">
    % if keywords:
        <digiKam:TagsList>
        <rdf:Seq>
         % for keyword in keywords:
          <rdf:li>${keyword | x}</rdf:li>
         % endfor
        </rdf:Seq>
        </digiKam:TagsList>
    % endif
</%def>

<%def name="adobe_createdate(date)">
    % if date is not None:
        <xmp:CreateDate>${date.strftime("%Y-%m-%dT%H:%M:%S")}</xmp:CreateDate>
    % endif
</%def>

<%def name="adobe_modifydate(date)">
    % if date is not None:
        <xmp:ModifyDate>${date.strftime("%Y-%m-%dT%H:%M:%S")}</xmp:ModifyDate>
    % endif
</%def>

<%def name="gps_info(latitude, longitude)">
    % if latitude is not None and longitude is not None:
        <exif:GPSLongitude>${int(abs(longitude))},${(abs(longitude) % 1) * 60}${"E" if longitude >= 0 else "W"}</exif:GPSLongitude>
        <exif:GPSLatitude>${int(abs(latitude))},${(abs(latitude) % 1) * 60}${"N" if latitude >= 0 else "S"}</exif:GPSLatitude>
    % endif
</%def>

<%def name="mwg_face_regions(photo)">
    % if photo.face_info:
    <mwg-rs:Regions rdf:parseType="Resource">
    <mwg-rs:AppliedToDimensions rdf:parseType="Resource">
    <stDim:unit>pixel</stDim:unit>
    </mwg-rs:AppliedToDimensions>
    <mwg-rs:RegionList>
    <rdf:Bag>
    % for face in photo.face_info:
     <rdf:li rdf:parseType="Resource">
      <mwg-rs:Area rdf:parseType="Resource">
      <stArea:h>${'{0:.6f}'.format(face.mwg_rs_area.h)}</stArea:h>
      <stArea:w>${'{0:.6f}'.format(face.mwg_rs_area.w)}</stArea:w>
      <stArea:x>${'{0:.6f}'.format(face.mwg_rs_area.x)}</stArea:x>
      <stArea:y>${'{0:.6f}'.format(face.mwg_rs_area.y)}</stArea:y>
      <stArea:unit>normalized</stArea:unit>
      </mwg-rs:Area>
      <mwg-rs:Name>${face.name}</mwg-rs:Name>
      <mwg-rs:Rotation>${face.roll}</mwg-rs:Rotation>
      <mwg-rs:Type>Face</mwg-rs:Type>
     </rdf:li>
    % endfor
    </rdf:Bag>
    </mwg-rs:RegionList>
    </mwg-rs:Regions>
    % endif
</%def>

<%def name="mpri_face_regions(photo)">
    % if photo.face_info:
    <MP:RegionInfo rdf:parseType="Resource">
     <MPRI:Regions>
      <rdf:Bag>
      % for face in photo.face_info:
       <rdf:li rdf:parseType="Resource">
       <MPReg:PersonDisplayName>${face.name}</MPReg:PersonDisplayName>
       <MPReg:Rectangle>${'{0:.6f}'.format(face.mpri_reg_rect.x)}, ${'{0:.6f}'.format(face.mpri_reg_rect.y)}, ${'{0:.6f}'.format(face.mpri_reg_rect.h)}, ${'{0:.6f}'.format(face.mpri_reg_rect.w)}</MPReg:Rectangle>
       </rdf:li>
      % endfor
      </rdf:Bag>
     </MPRI:Regions>
    </MP:RegionInfo>
    % endif
</%def>


<?xpacket begin="${"\uFEFF"}" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="osxphotos">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description rdf:about="" 
 xmlns:dc="http://purl.org/dc/elements/1.1/" 
 xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
 ${photoshop_sidecar_for_extension(extension)}
 ${dc_description(description)}
 ${dc_title(photo.title)}
 ${dc_subject(subjects)}
 ${dc_datecreated(photo.date)}
</rdf:Description>

<rdf:Description rdf:about=""  
 xmlns:Iptc4xmpExt='http://iptc.org/std/Iptc4xmpExt/2008-02-29/'>
 ${iptc_personinimage(persons)}
</rdf:Description>

<rdf:Description rdf:about="" 
 xmlns:digiKam='http://www.digikam.org/ns/1.0/'>
 ${dk_tagslist(keywords)}
</rdf:Description>

<rdf:Description rdf:about="" 
 xmlns:xmp='http://ns.adobe.com/xap/1.0/'>
 ${adobe_createdate(photo.date)}
 ${adobe_modifydate(photo.date)}
</rdf:Description>

<rdf:Description rdf:about=""
 xmlns:exif='http://ns.adobe.com/exif/1.0/'>
 ${gps_info(*location)}
</rdf:Description>

<rdf:Description rdf:about=""
 xmlns:mwg-rs="http://www.metadataworkinggroup.com/schemas/regions/"
 xmlns:stArea="http://ns.adobe.com/xmp/sType/Area#"
 xmlns:stDim="http://ns.adobe.com/xap/1.0/sType/Dimensions#">
 ${mwg_face_regions(photo)}
</rdf:Description>


<rdf:Description rdf:about=""
 xmlns:MP="http://ns.microsoft.com/photo/1.2/"
 xmlns:MPRI="http://ns.microsoft.com/photo/1.2/t/RegionInfo#"
 xmlns:MPReg="http://ns.microsoft.com/photo/1.2/t/Region#">
 ${mpri_face_regions(photo)}
</rdf:Description>

</rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>