from mcp.server.fastmcp import Context
from osxphotos import PhotosDB

def caption_from_context(uuid: str, style: str = "plain", ctx: Context = None) -> str:
    """
    Generates a prompt for an AI to create a caption for a photo based on its context.
    
    :param uuid: The UUID of the photo.
    :param style: The desired style of the caption (e.g., 'plain', 'travel', 'journal').
    :return: A string containing the generated prompt.
    """
    db = PhotosDB()
    photo = db.get_photo(uuid)

    if not photo:
        return f"Error: Photo with UUID {uuid} not found."

    context = []
    if photo.title:
        context.append(f"- Title: {photo.title}")
    if photo.description:
        context.append(f"- Description: {photo.description}")
    if photo.persons:
        context.append(f"- People: {', '.join(photo.persons)}")
    if photo.place:
        context.append(f"- Location: {photo.place.name}")
    if photo.keywords:
        context.append(f"- Keywords: {', '.join(photo.keywords)}")
    
    try:
        detected_text = photo.detected_text()
        if detected_text:
            text = [item[0] for item in detected_text]
            context.append(f"- Detected Text: {', '.join(text)}")
    except Exception as e:
        # Ignore errors if text detection is not available
        pass

    prompt = f"Generate a {style} caption for a photo with the following context:\n"
    prompt += "\n".join(context)
    
    return prompt

def smart_album_query(description: str, ctx: Context = None) -> str:
    """
    (Not Implemented) Helps the AI compose a QueryOptions spec based on natural language.
    """
    raise NotImplementedError("smart_album_query is not yet implemented.")

def duplicate_review(uuids: list[str], ctx: Context = None) -> str:
    """
    (Not Implemented) Guides the AI to evaluate candidates using PhotoInfo.duplicates.
    """
    raise NotImplementedError("duplicate_review is not yet implemented.")