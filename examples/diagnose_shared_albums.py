#!/usr/bin/env python3
"""
Diagnostic script to investigate shared albums on macOS Tahoe (26.x).

This script helps diagnose why shared albums may not be showing up correctly
in osxphotos on macOS 26.x. It examines the Photos database schema and data
to identify how shared albums are stored.

Run with: osxphotos run diagnose_shared_albums.py

Related issue: https://github.com/RhetTbull/osxphotos/issues/2003
"""

from __future__ import annotations

import plistlib
import sqlite3
import sys
from pathlib import Path
from typing import Any


def get_photos_library_path() -> Path:
    """Get the default Photos library path."""
    return Path.home() / "Pictures" / "Photos Library.photoslibrary"


def get_db_path(library_path: Path) -> Path:
    """Get the Photos database path."""
    return library_path / "database" / "Photos.sqlite"


def run_query(cursor: sqlite3.Cursor, query: str, description: str) -> list[Any]:
    """Run a query with error handling."""
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"  Query failed: {e}")
        return []


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print("=" * 60)


def print_table(headers: list[str], rows: list[tuple], max_rows: int = 50) -> None:
    """Print a simple ASCII table."""
    if not rows:
        print("  (no results)")
        return

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows[:max_rows]:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)[:50]))

    # Print header
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(f"  {header_line}")
    print(f"  {'-' * len(header_line)}")

    # Print rows
    for row in rows[:max_rows]:
        row_line = " | ".join(str(v)[:50].ljust(widths[i]) for i, v in enumerate(row))
        print(f"  {row_line}")

    if len(rows) > max_rows:
        print(f"  ... and {len(rows) - max_rows} more rows")


def diagnose_shared_albums(db_path: Path) -> None:
    """Run diagnostic queries on the Photos database."""
    print(f"\nAnalyzing database: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cursor = conn.cursor()

    # Section 1: Database version info
    print_section("1. DATABASE VERSION INFO")

    # Get model version from Z_METADATA plist blob
    result = run_query(
        cursor,
        "SELECT MAX(Z_VERSION), Z_PLIST FROM Z_METADATA",
        "Model version",
    )
    if result and result[0][1]:
        try:
            plist = plistlib.loads(result[0][1])
            model_version = plist.get("PLModelVersion", "Unknown")
            print(f"  PLModelVersion: {model_version}")
        except Exception as e:
            print(f"  Could not parse Z_METADATA plist: {e}")
    else:
        print("  Could not retrieve Z_METADATA")

    # Section 2: Entity Types (Z_PRIMARYKEY)
    print_section("2. ENTITY TYPES (Z_PRIMARYKEY)")
    print("  Looking for album-related and share-related entity types...\n")

    result = run_query(
        cursor,
        """SELECT Z_ENT, Z_NAME FROM Z_PRIMARYKEY
           WHERE Z_NAME LIKE '%Album%' OR Z_NAME LIKE '%Share%' OR Z_NAME LIKE '%Folder%'
           ORDER BY Z_ENT""",
        "Album/Share/Folder entity types",
    )
    print_table(["Z_ENT", "Z_NAME"], result)

    # Section 3: Album ZKIND values
    print_section("3. ALBUM ZKIND VALUES (ZGENERICALBUM)")
    print("  Counting albums by ZKIND and Z_ENT...\n")

    result = run_query(
        cursor,
        """SELECT ZKIND, Z_ENT, COUNT(*) as count
           FROM ZGENERICALBUM
           GROUP BY ZKIND, Z_ENT
           ORDER BY count DESC""",
        "ZKIND/Z_ENT distribution",
    )
    print_table(["ZKIND", "Z_ENT", "COUNT"], result)

    # Section 4: Known shared album constants
    print_section("4. CHECKING KNOWN SHARED ALBUM CONSTANTS")

    # ZKIND = 1505 (traditional shared album kind)
    print("\n  a) Albums with ZKIND = 1505 (traditional shared albums):")
    result = run_query(
        cursor,
        """SELECT Z_PK, ZKIND, Z_ENT, ZTITLE, ZCLOUDOWNERHASHEDPERSONID,
                  ZCLOUDOWNERFIRSTNAME, ZCLOUDOWNERLASTNAME
           FROM ZGENERICALBUM WHERE ZKIND = 1505""",
        "ZKIND=1505 albums",
    )
    print_table(
        ["Z_PK", "ZKIND", "Z_ENT", "TITLE", "OWNER_HASH", "FIRST_NAME", "LAST_NAME"],
        result,
    )

    # Z_ENT = 34 (CloudSharedAlbum entity type in some versions)
    print("\n  b) Albums with Z_ENT = 34 (CloudSharedAlbum entity):")
    result = run_query(
        cursor,
        """SELECT Z_PK, ZKIND, Z_ENT, ZTITLE, ZCLOUDOWNERHASHEDPERSONID,
                  ZCLOUDOWNERFIRSTNAME, ZCLOUDOWNERLASTNAME
           FROM ZGENERICALBUM WHERE Z_ENT = 34""",
        "Z_ENT=34 albums",
    )
    print_table(
        ["Z_PK", "ZKIND", "Z_ENT", "TITLE", "OWNER_HASH", "FIRST_NAME", "LAST_NAME"],
        result,
    )

    # Albums with ZCLOUDOWNERHASHEDPERSONID not null
    print("\n  c) Albums with ZCLOUDOWNERHASHEDPERSONID not null:")
    result = run_query(
        cursor,
        """SELECT Z_PK, ZKIND, Z_ENT, ZTITLE, ZCLOUDOWNERHASHEDPERSONID,
                  ZCLOUDOWNERFIRSTNAME, ZCLOUDOWNERLASTNAME
           FROM ZGENERICALBUM
           WHERE ZCLOUDOWNERHASHEDPERSONID IS NOT NULL
             AND ZCLOUDOWNERHASHEDPERSONID != ''""",
        "Albums with cloud owner",
    )
    print_table(
        ["Z_PK", "ZKIND", "Z_ENT", "TITLE", "OWNER_HASH", "FIRST_NAME", "LAST_NAME"],
        result,
    )

    # Section 5: ZSHARE table
    print_section("5. ZSHARE TABLE (Share records)")

    result = run_query(cursor, "SELECT COUNT(*) FROM ZSHARE", "ZSHARE count")
    share_count = result[0][0] if result else 0
    print(f"  Total records in ZSHARE: {share_count}")

    if share_count > 0:
        print("\n  Share records:")
        result = run_query(
            cursor,
            """SELECT Z_PK, Z_ENT, ZTITLE, ZSTATUS, ZSCOPETYPE, ZSHAREURL, ZTRASHEDSTATE
               FROM ZSHARE LIMIT 20""",
            "ZSHARE records",
        )
        print_table(
            ["Z_PK", "Z_ENT", "TITLE", "STATUS", "SCOPE_TYPE", "SHARE_URL", "TRASHED"],
            result,
        )

        # Check Z_ENT values in ZSHARE
        print("\n  ZSHARE Z_ENT distribution:")
        result = run_query(
            cursor,
            "SELECT Z_ENT, COUNT(*) FROM ZSHARE GROUP BY Z_ENT",
            "ZSHARE Z_ENT distribution",
        )
        print_table(["Z_ENT", "COUNT"], result)

    # Section 6: ZCLOUDSHAREDALBUMINVITATIONRECORD
    print_section("6. ZCLOUDSHAREDALBUMINVITATIONRECORD TABLE")

    result = run_query(
        cursor,
        "SELECT COUNT(*) FROM ZCLOUDSHAREDALBUMINVITATIONRECORD",
        "Invitation record count",
    )
    inv_count = result[0][0] if result else 0
    print(f"  Total invitation records: {inv_count}")

    if inv_count > 0:
        print("\n  Invitation records:")
        result = run_query(
            cursor,
            """SELECT ZALBUM, ZINVITEEFULLNAME, ZINVITEEHASHEDPERSONID, ZALBUMGUID
               FROM ZCLOUDSHAREDALBUMINVITATIONRECORD LIMIT 20""",
            "Invitation records",
        )
        print_table(["ALBUM_PK", "INVITEE_NAME", "INVITEE_HASH", "ALBUM_GUID"], result)

    # Section 7: ZSHAREPARTICIPANT
    print_section("7. ZSHAREPARTICIPANT TABLE")

    result = run_query(
        cursor, "SELECT COUNT(*) FROM ZSHAREPARTICIPANT", "Share participant count"
    )
    part_count = result[0][0] if result else 0
    print(f"  Total share participants: {part_count}")

    if part_count > 0:
        print("\n  Share participants:")
        result = run_query(
            cursor,
            """SELECT Z_PK, ZSHARE, ZISCURRENTUSER, ZROLE, ZPERMISSION
               FROM ZSHAREPARTICIPANT LIMIT 20""",
            "Share participants",
        )
        print_table(["Z_PK", "SHARE", "IS_CURRENT_USER", "ROLE", "PERMISSION"], result)

    # Section 8: Check join tables
    print_section("8. ALBUM-ASSET JOIN TABLE DETECTION")
    print("  Looking for Z_nnASS ETS tables that join albums to assets...\n")

    result = run_query(
        cursor,
        """SELECT name FROM sqlite_master
           WHERE type='table' AND name LIKE 'Z_%ASSETS'
           ORDER BY name""",
        "Asset join tables",
    )
    print("  Found tables:")
    for row in result:
        table_name = row[0]
        # Get column names
        col_result = run_query(cursor, f"PRAGMA table_info({table_name})", "columns")
        cols = [c[1] for c in col_result]
        print(f"    {table_name}: {', '.join(cols)}")

    # Section 9: Test potential queries for shared albums
    print_section("9. TESTING POTENTIAL SHARED ALBUM QUERIES")

    # Query A: Traditional osxphotos approach (ZKIND=1505 + cloudownerhashedpersonid)
    print("\n  Query A: ZKIND=1505 AND ZCLOUDOWNERHASHEDPERSONID IS NOT NULL")
    result = run_query(
        cursor,
        """SELECT COUNT(*) FROM ZGENERICALBUM
           WHERE ZKIND = 1505 AND ZCLOUDOWNERHASHEDPERSONID IS NOT NULL""",
        "Query A",
    )
    print(f"  Result: {result[0][0] if result else 0} albums")

    # Query B: Z_ENT=34 (CloudSharedAlbum)
    print("\n  Query B: Z_ENT = 34 (CloudSharedAlbum entity)")
    result = run_query(
        cursor, "SELECT COUNT(*) FROM ZGENERICALBUM WHERE Z_ENT = 34", "Query B"
    )
    print(f"  Result: {result[0][0] if result else 0} albums")

    # Query C: Just ZKIND=1505
    print("\n  Query C: Just ZKIND = 1505")
    result = run_query(
        cursor, "SELECT COUNT(*) FROM ZGENERICALBUM WHERE ZKIND = 1505", "Query C"
    )
    print(f"  Result: {result[0][0] if result else 0} albums")

    # Query D: Albums with any cloud owner info
    print("\n  Query D: Albums with any cloud owner information")
    result = run_query(
        cursor,
        """SELECT COUNT(*) FROM ZGENERICALBUM
           WHERE (ZCLOUDOWNERHASHEDPERSONID IS NOT NULL AND ZCLOUDOWNERHASHEDPERSONID != '')
              OR (ZCLOUDOWNERFIRSTNAME IS NOT NULL AND ZCLOUDOWNERFIRSTNAME != '')
              OR (ZCLOUDPERSONID IS NOT NULL AND ZCLOUDPERSONID != '')""",
        "Query D",
    )
    print(f"  Result: {result[0][0] if result else 0} albums")

    # Query E: Albums linked to ZSHARE
    print("\n  Query E: Check if ZGENERICALBUM has relationship to ZSHARE")
    # First check if there's a column linking them
    result = run_query(cursor, "PRAGMA table_info(ZGENERICALBUM)", "ZGENERICALBUM info")
    share_cols = [c for c in result if "SHARE" in c[1].upper()]
    if share_cols:
        print(f"  Found share-related columns in ZGENERICALBUM: {share_cols}")
    else:
        print("  No direct share columns found in ZGENERICALBUM")

    # Check for relationship via ZSHARE.ZSCOPEIDENTIFIER
    print("\n  Query F: Check ZSHARE.ZSCOPEIDENTIFIER for album UUIDs")
    result = run_query(
        cursor,
        """SELECT s.Z_PK, s.ZTITLE, s.ZSCOPEIDENTIFIER, a.ZUUID, a.ZTITLE
           FROM ZSHARE s
           LEFT JOIN ZGENERICALBUM a ON s.ZSCOPEIDENTIFIER = a.ZUUID
           LIMIT 10""",
        "Share to album via scope identifier",
    )
    if result:
        print_table(
            ["SHARE_PK", "SHARE_TITLE", "SCOPE_ID", "ALBUM_UUID", "ALBUM_TITLE"], result
        )
    else:
        print("  No relationships found")

    # Section 10: Check ZCLOUDMASTER for collection share relationships
    print_section("10. ZCLOUDMASTER COLLECTION SHARE RELATIONSHIPS")

    # Check if ZCOLLECTIONSHARE column exists
    result = run_query(cursor, "PRAGMA table_info(ZCLOUDMASTER)", "ZCLOUDMASTER info")
    cols = {c[1]: c for c in result}

    if "ZCOLLECTIONSHARE" in cols:
        print("  ZCOLLECTIONSHARE column exists in ZCLOUDMASTER")
        result = run_query(
            cursor,
            """SELECT ZCOLLECTIONSHARE, COUNT(*)
               FROM ZCLOUDMASTER
               WHERE ZCOLLECTIONSHARE IS NOT NULL
               GROUP BY ZCOLLECTIONSHARE""",
            "Collection share distribution",
        )
        if result:
            print("\n  Assets by collection share:")
            print_table(["COLLECTION_SHARE_PK", "ASSET_COUNT"], result)
        else:
            print("  No assets linked to collection shares")

    if "ZMOMENTSHARE" in cols:
        print("\n  ZMOMENTSHARE column exists in ZCLOUDMASTER")
        result = run_query(
            cursor,
            """SELECT ZMOMENTSHARE, COUNT(*)
               FROM ZCLOUDMASTER
               WHERE ZMOMENTSHARE IS NOT NULL
               GROUP BY ZMOMENTSHARE""",
            "Moment share distribution",
        )
        if result:
            print("  Assets by moment share:")
            print_table(["MOMENT_SHARE_PK", "ASSET_COUNT"], result)
        else:
            print("  No assets linked to moment shares")

    # Section 11: Summary and recommendations
    print_section("11. SUMMARY AND RECOMMENDATIONS")

    # Collect summary data
    summary_data = {
        "zkind_1505": run_query(
            cursor, "SELECT COUNT(*) FROM ZGENERICALBUM WHERE ZKIND=1505", ""
        )[0][0],
        "z_ent_34": run_query(
            cursor, "SELECT COUNT(*) FROM ZGENERICALBUM WHERE Z_ENT=34", ""
        )[0][0],
        "with_owner": run_query(
            cursor,
            """SELECT COUNT(*) FROM ZGENERICALBUM
               WHERE ZCLOUDOWNERHASHEDPERSONID IS NOT NULL AND ZCLOUDOWNERHASHEDPERSONID != ''""",
            "",
        )[0][0],
        "shares": share_count,
        "invitations": inv_count,
        "participants": part_count,
    }

    print(
        f"""
  Albums with ZKIND=1505: {summary_data['zkind_1505']}
  Albums with Z_ENT=34: {summary_data['z_ent_34']}
  Albums with cloud owner: {summary_data['with_owner']}
  ZSHARE records: {summary_data['shares']}
  Invitation records: {summary_data['invitations']}
  Share participants: {summary_data['participants']}
"""
    )

    if summary_data["zkind_1505"] == 0 and summary_data["z_ent_34"] == 0:
        if summary_data["shares"] > 0 or summary_data["invitations"] > 0:
            print(
                """  FINDING: No traditional shared albums found, but share/invitation
  records exist. This suggests shared albums might be stored differently
  on this version of macOS.

  HYPOTHESIS: On macOS 26.x, shared albums might be:
  1. Using ZSHARE table directly instead of ZGENERICALBUM with ZKIND=1505
  2. Using a different Z_ENT value
  3. Requiring a join between ZGENERICALBUM and ZSHARE tables
"""
            )
        else:
            print(
                """  FINDING: No shared albums found in this library.
  This could mean:
  1. There are no shared albums in this Photos library
  2. Shared albums are stored in a different location on this macOS version

  If you have shared albums visible in Photos.app, please report this
  diagnostic output to: https://github.com/RhetTbull/osxphotos/issues/2003
"""
            )
    else:
        if summary_data["zkind_1505"] > 0:
            print(
                """  FINDING: Found traditional shared albums (ZKIND=1505).
  The existing osxphotos query should work for these albums.
"""
            )
        if summary_data["z_ent_34"] > 0:
            print(
                """  FINDING: Found CloudSharedAlbum entities (Z_ENT=34).
  osxphotos may need to query by Z_ENT=34 instead of/in addition to ZKIND=1505.
"""
            )

    conn.close()


def main():
    """Main entry point."""
    print("=" * 60)
    print(" osxphotos Shared Albums Diagnostic Tool")
    print(" Issue: https://github.com/RhetTbull/osxphotos/issues/2003")
    print("=" * 60)

    # Check for custom library path
    if len(sys.argv) > 1:
        library_path = Path(sys.argv[1])
    else:
        library_path = get_photos_library_path()

    if not library_path.exists():
        print(f"\nError: Photos library not found at {library_path}")
        print("Usage: osxphotos run diagnose_shared_albums.py [library_path]")
        sys.exit(1)

    db_path = get_db_path(library_path)
    if not db_path.exists():
        print(f"\nError: Database not found at {db_path}")
        sys.exit(1)

    # Print system info
    import platform

    print(f"\nSystem: macOS {platform.mac_ver()[0]}")
    print(f"Library: {library_path}")

    try:
        diagnose_shared_albums(db_path)
    except Exception as e:
        print(f"\nError during diagnosis: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print(" Diagnostic complete!")
    print(" Please share this output in GitHub issue #2003")
    print("=" * 60)


if __name__ == "__main__":
    main()
