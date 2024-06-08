-- Get UUID from asset table given a master fingerprint
-- There may be more than one asset with the same master fingerprint
-- Takes a single parameter: the master fingerprint
SELECT ${asset_table}.ZUUID
FROM ${asset_table}
LEFT JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ${asset_table}.Z_PK
WHERE ZADDITIONALASSETATTRIBUTES.ZMASTERFINGERPRINT = ?;
