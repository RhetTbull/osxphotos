-- Get the owner name of person who owns a photo in a shared album
WITH case1 AS
(
    -- Case where someone has invited you to a shared album
    -- Need to get the owner of the shared album
    SELECT ZGENERICALBUM.ZCLOUDOWNERFULLNAME as OWNER_FULLNAME
    FROM ZGENERICALBUM
    JOIN ${asset_table} ON ${asset_table}.ZCLOUDOWNERHASHEDPERSONID = ZGENERICALBUM.ZCLOUDOWNERHASHEDPERSONID
    WHERE ${asset_table}.ZUUID = "${uuid}"
),
case2 AS
(
    -- Case where you have invited someone to a shared album
    -- Need to get the data for person who was invited to the album
    SELECT
    ZCLOUDSHAREDALBUMINVITATIONRECORD.ZINVITEEFULLNAME AS OWNER_FULLNAME
    FROM ZCLOUDSHAREDALBUMINVITATIONRECORD 
    JOIN ${asset_table} ON ${asset_table}.ZCLOUDOWNERHASHEDPERSONID = ZCLOUDSHAREDALBUMINVITATIONRECORD.ZINVITEEHASHEDPERSONID
    WHERE ${asset_table}.ZUUID = "${uuid}"
    ORDER BY ZCLOUDSHAREDALBUMINVITATIONRECORD.Z_PK
    LIMIT 1
)
SELECT * FROM case1
UNION
SELECT * FROM case2 WHERE NOT EXISTS (SELECT * FROM case1)
