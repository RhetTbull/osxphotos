"""Use osxphotos and photoscript to find text in photos and update the photo description with detected text"""

import photoscript

import osxphotos

if __name__ == "__main__":
    # get photos selected in Photos
    selection = photoscript.PhotosLibrary().selection
    photosdb = osxphotos.PhotosDB()
    photos = photosdb.photos(uuid=[s.uuid for s in selection])
    for photo in photos:
        detected_text = photo.detected_text()
        if not detected_text:
            continue
        # detected text is tuple of (text, confidence)
        for text, confidence in detected_text:
            description = photo.description or ""
            # set confidence level to whatever you like
            if confidence > 0.8 and text not in description:
                print(f"Adding {text} to {photo.original_filename} ({photo.uuid})")
                photoscript.Photo(photo.uuid).description += f" {text}"
