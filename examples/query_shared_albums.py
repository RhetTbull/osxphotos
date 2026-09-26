#!/usr/bin/env python3
"""
Query script to test shared album queries on macOS Tahoe (26.x).

This script tests different hypotheses for how shared albums and their assets
are stored in the Photos database on macOS 26.x. It attempts to list all shared
albums with their asset counts and sample filenames to verify the queries work.

Run with: osxphotos run query_shared_albums.py

Related issue: https://github.com/RhetTbull/osxphotos/issues/2003
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def get_photos_library_path() -> Path:
    """Get the default Photos library path."""
    return Path.home() / "Pictures" / "Photos Library.photoslibrary"


def get_db_path(library_path: Path) -> Path:
    """Get the Photos database path."""
    return library_path / "database" / "Photos.sqlite"


def run_query(cursor: sqlite3.Cursor, query: str) -> list | None:
    """Run a query with error handling."""
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"    Query failed: {e}")
        return None


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print("=" * 70)


def test_shared_album_queries(db_path: Path) -> None:
    """Test various queries to find shared albums and their assets."""
    print(f"\nAnalyzing database: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cursor = conn.cursor()

    # First, check which tables and columns exist
    print_section("CHECKING AVAILABLE COLUMNS")

    # Check ZASSET columns
    result = run_query(cursor, "PRAGMA table_info(ZASSET)")
    zasset_cols = {row[1] for row in result} if result else set()
    share_cols = [c for c in zasset_cols if "SHARE" in c.upper()]
    print(f"  ZASSET share-related columns: {share_cols}")

    # Check ZCLOUDMASTER columns
    result = run_query(cursor, "PRAGMA table_info(ZCLOUDMASTER)")
    zcloudmaster_cols = {row[1] for row in result} if result else set()
    share_cols_cm = [c for c in zcloudmaster_cols if "SHARE" in c.upper()]
    print(f"  ZCLOUDMASTER share-related columns: {share_cols_cm}")

    # =========================================================================
    # HYPOTHESIS 1: ZASSET.ZCOLLECTIONSHARE -> ZSHARE.Z_PK
    # This is the most likely relationship based on schema analysis
    # =========================================================================
    print_section("HYPOTHESIS 1: ZASSET.ZCOLLECTIONSHARE -> ZSHARE")
    print("  Query: Join ZASSET to ZSHARE via ZCOLLECTIONSHARE column\n")

    if "ZCOLLECTIONSHARE" in zasset_cols:
        query = """
            SELECT
                s.Z_PK as share_pk,
                s.ZTITLE as album_name,
                COUNT(a.Z_PK) as asset_count,
                (SELECT ZFILENAME
                 FROM ZASSET a2
                 WHERE a2.ZCOLLECTIONSHARE = s.Z_PK
                 LIMIT 1) as sample_filename
            FROM ZSHARE s
            LEFT JOIN ZASSET a ON a.ZCOLLECTIONSHARE = s.Z_PK
            WHERE s.Z_ENT = 67  -- CollectionShare entity type
              AND s.ZTRASHEDSTATE = 0
            GROUP BY s.Z_PK, s.ZTITLE
            ORDER BY s.ZTITLE
        """
        result = run_query(cursor, query)
        if result is None:
            print("  Query failed (see error above)")
        elif len(result) == 0:
            print(
                "  No shared albums found (ZSHARE table is empty or has no CollectionShare records)"
            )
        else:
            print(f"  {'Album Name':<40} {'Assets':<10} {'Sample Filename'}")
            print(f"  {'-' * 40} {'-' * 10} {'-' * 30}")
            total_with_assets = 0
            for row in result:
                album_name = (row[1] or "(no title)")[:40]
                asset_count = row[2]
                sample = row[3] or "(none)"
                print(f"  {album_name:<40} {asset_count:<10} {sample}")
                if asset_count > 0:
                    total_with_assets += 1
            print(f"\n  Total shared albums: {len(result)}")
            print(f"  Albums with assets: {total_with_assets}")
            if total_with_assets > 0:
                print(
                    "\n  *** SUCCESS: This query found shared albums with assets! ***"
                )
    else:
        print("  ZCOLLECTIONSHARE column not found in ZASSET table")

    # =========================================================================
    # HYPOTHESIS 2: ZASSET.ZMOMENTSHARE -> ZSHARE.Z_PK
    # MomentShare is another type of sharing
    # =========================================================================
    print_section("HYPOTHESIS 2: ZASSET.ZMOMENTSHARE -> ZSHARE")
    print("  Query: Join ZASSET to ZSHARE via ZMOMENTSHARE column\n")

    if "ZMOMENTSHARE" in zasset_cols:
        query = """
            SELECT
                s.Z_PK as share_pk,
                s.ZTITLE as album_name,
                COUNT(a.Z_PK) as asset_count,
                (SELECT ZFILENAME
                 FROM ZASSET a2
                 WHERE a2.ZMOMENTSHARE = s.Z_PK
                 LIMIT 1) as sample_filename
            FROM ZSHARE s
            LEFT JOIN ZASSET a ON a.ZMOMENTSHARE = s.Z_PK
            WHERE s.Z_ENT = 69  -- MomentShare entity type
              AND s.ZTRASHEDSTATE = 0
            GROUP BY s.Z_PK, s.ZTITLE
            ORDER BY s.ZTITLE
        """
        result = run_query(cursor, query)
        if result is None:
            print("  Query failed (see error above)")
        elif len(result) == 0:
            print("  No moment shares found")
        else:
            print(f"  {'Album Name':<40} {'Assets':<10} {'Sample Filename'}")
            print(f"  {'-' * 40} {'-' * 10} {'-' * 30}")
            for row in result:
                album_name = (row[1] or "(no title)")[:40]
                asset_count = row[2]
                sample = row[3] or "(none)"
                print(f"  {album_name:<40} {asset_count:<10} {sample}")
            print(f"\n  Total moment shares: {len(result)}")
    else:
        print("  ZMOMENTSHARE column not found in ZASSET table")

    # =========================================================================
    # HYPOTHESIS 3: ZCLOUDMASTER -> ZSHARE relationship
    # Assets might link through ZCLOUDMASTER
    # =========================================================================
    print_section("HYPOTHESIS 3: ZCLOUDMASTER.ZCOLLECTIONSHARE -> ZSHARE")
    print("  Query: Join assets via ZCLOUDMASTER to ZSHARE\n")

    if "ZCOLLECTIONSHARE" in zcloudmaster_cols:
        query = """
            SELECT
                s.Z_PK as share_pk,
                s.ZTITLE as album_name,
                COUNT(DISTINCT cm.Z_PK) as cloudmaster_count,
                (SELECT cm2.ZORIGINALFILENAME
                 FROM ZCLOUDMASTER cm2
                 WHERE cm2.ZCOLLECTIONSHARE = s.Z_PK
                 LIMIT 1) as sample_filename
            FROM ZSHARE s
            LEFT JOIN ZCLOUDMASTER cm ON cm.ZCOLLECTIONSHARE = s.Z_PK
            WHERE s.Z_ENT = 67
              AND s.ZTRASHEDSTATE = 0
            GROUP BY s.Z_PK, s.ZTITLE
            ORDER BY s.ZTITLE
        """
        result = run_query(cursor, query)
        if result is None:
            print("  Query failed (see error above)")
        elif len(result) == 0:
            print("  No shared albums found via ZCLOUDMASTER")
        else:
            print(f"  {'Album Name':<40} {'CloudMasters':<12} {'Sample Filename'}")
            print(f"  {'-' * 40} {'-' * 12} {'-' * 30}")
            total_with_assets = 0
            for row in result:
                album_name = (row[1] or "(no title)")[:40]
                count = row[2]
                sample = row[3] or "(none)"
                print(f"  {album_name:<40} {count:<12} {sample}")
                if count > 0:
                    total_with_assets += 1
            print(f"\n  Total shared albums: {len(result)}")
            print(f"  Albums with cloudmasters: {total_with_assets}")
            if total_with_assets > 0:
                print(
                    "\n  *** SUCCESS: This query found shared albums via ZCLOUDMASTER! ***"
                )
    else:
        print("  ZCOLLECTIONSHARE column not found in ZCLOUDMASTER table")

    # =========================================================================
    # HYPOTHESIS 4: Check if there's a scope-based relationship
    # ZSHARE.ZSCOPEIDENTIFIER might match something
    # =========================================================================
    print_section("HYPOTHESIS 4: ZSHARE.ZSCOPEIDENTIFIER relationships")
    print("  Checking if ZSCOPEIDENTIFIER matches any asset UUIDs\n")

    query = """
        SELECT
            s.Z_PK,
            s.ZTITLE,
            s.ZSCOPEIDENTIFIER,
            (SELECT COUNT(*) FROM ZASSET a WHERE a.ZUUID = s.ZSCOPEIDENTIFIER) as uuid_matches,
            (SELECT COUNT(*) FROM ZCLOUDMASTER cm WHERE cm.ZCLOUDMASTERGUID = s.ZSCOPEIDENTIFIER) as guid_matches
        FROM ZSHARE s
        WHERE s.Z_ENT = 67
          AND s.ZTRASHEDSTATE = 0
        LIMIT 10
    """
    result = run_query(cursor, query)
    if result:
        print(
            f"  {'Album Name':<30} {'Scope ID':<40} {'UUID Match':<12} {'GUID Match'}"
        )
        print(f"  {'-' * 30} {'-' * 40} {'-' * 12} {'-' * 10}")
        for row in result:
            album_name = (row[1] or "(no title)")[:30]
            scope_id = (row[2] or "")[:40]
            uuid_match = row[3]
            guid_match = row[4]
            print(f"  {album_name:<30} {scope_id:<40} {uuid_match:<12} {guid_match}")

    # =========================================================================
    # HYPOTHESIS 5: Check cached counts in ZSHARE table
    # ZSHARE might have its own cached asset counts
    # =========================================================================
    print_section("HYPOTHESIS 5: ZSHARE cached counts")
    print("  Checking ZSHARE's own asset count columns\n")

    query = """
        SELECT
            s.ZTITLE,
            s.ZASSETCOUNT,
            s.ZCLOUDITEMCOUNT,
            s.ZCLOUDPHOTOCOUNT,
            s.ZCLOUDVIDEOCOUNT,
            s.ZPHOTOSCOUNT,
            s.ZVIDEOSCOUNT
        FROM ZSHARE s
        WHERE s.Z_ENT = 67
          AND s.ZTRASHEDSTATE = 0
        ORDER BY s.ZTITLE
    """
    result = run_query(cursor, query)
    if result:
        print(
            f"  {'Album Name':<30} {'Assets':<8} {'Cloud':<8} {'Photos':<8} {'Videos':<8} {'Photos2':<8} {'Videos2'}"
        )
        print(
            f"  {'-' * 30} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8}"
        )
        for row in result:
            album_name = (row[0] or "(no title)")[:30]
            print(
                f"  {album_name:<30} {row[1] or 0:<8} {row[2] or 0:<8} {row[3] or 0:<8} {row[4] or 0:<8} {row[5] or 0:<8} {row[6] or 0:<8}"
            )

    # =========================================================================
    # HYPOTHESIS 6: Check ZADDITIONALASSETATTRIBUTES for share info
    # =========================================================================
    print_section("HYPOTHESIS 6: ZADDITIONALASSETATTRIBUTES share columns")
    print("  Checking if assets have share info in additional attributes\n")

    result = run_query(cursor, "PRAGMA table_info(ZADDITIONALASSETATTRIBUTES)")
    if result:
        share_cols_attr = [row[1] for row in result if "SHARE" in row[1].upper()]
        print(f"  Share-related columns: {share_cols_attr}")

        if "ZPENDINGSHARECOUNT" in [r[1] for r in result]:
            query = """
                SELECT COUNT(*) FROM ZADDITIONALASSETATTRIBUTES
                WHERE ZPENDINGSHARECOUNT > 0
            """
            count_result = run_query(cursor, query)
            if count_result:
                print(f"  Assets with pending share count > 0: {count_result[0][0]}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_section("SUMMARY")

    # Get total shares
    result = run_query(
        cursor, "SELECT COUNT(*) FROM ZSHARE WHERE Z_ENT = 67 AND ZTRASHEDSTATE = 0"
    )
    total_shares = result[0][0] if result else 0

    # Get shares with assets via ZASSET.ZCOLLECTIONSHARE
    if "ZCOLLECTIONSHARE" in zasset_cols:
        result = run_query(
            cursor,
            """
            SELECT COUNT(DISTINCT s.Z_PK)
            FROM ZSHARE s
            JOIN ZASSET a ON a.ZCOLLECTIONSHARE = s.Z_PK
            WHERE s.Z_ENT = 67 AND s.ZTRASHEDSTATE = 0
        """,
        )
        shares_with_assets = result[0][0] if result else 0
    else:
        shares_with_assets = 0

    print(
        f"""
  Total CollectionShare records (Z_ENT=67): {total_shares}
  Shares with assets via ZASSET.ZCOLLECTIONSHARE: {shares_with_assets}
"""
    )

    if shares_with_assets > 0:
        print(
            """  RECOMMENDATION: Use HYPOTHESIS 1 query

  The correct query to get shared albums on macOS 26.x appears to be:

  SELECT
      s.Z_PK,
      s.ZTITLE,
      COUNT(a.Z_PK) as asset_count
  FROM ZSHARE s
  LEFT JOIN ZASSET a ON a.ZCOLLECTIONSHARE = s.Z_PK
  WHERE s.Z_ENT = 67  -- CollectionShare
    AND s.ZTRASHEDSTATE = 0
  GROUP BY s.Z_PK
"""
        )
    elif total_shares > 0 and shares_with_assets == 0:
        print(
            """  NOTE: Shared albums exist but no assets are linked via ZCOLLECTIONSHARE.

  This could mean:
  1. The assets are stored elsewhere (different Photos library section)
  2. The assets need to be synced from iCloud first
  3. There's a different relationship we haven't discovered yet

  Please check the HYPOTHESIS 5 cached counts - if ZSHARE.ZASSETCOUNT
  shows assets but our joins don't find them, there may be another
  join path we need to discover.
"""
        )

    conn.close()


def main():
    """Main entry point."""
    print("=" * 70)
    print(" osxphotos Shared Album Query Tester")
    print(" Issue: https://github.com/RhetTbull/osxphotos/issues/2003")
    print("=" * 70)

    # Check for custom library path
    if len(sys.argv) > 1:
        library_path = Path(sys.argv[1])
    else:
        library_path = get_photos_library_path()

    if not library_path.exists():
        print(f"\nError: Photos library not found at {library_path}")
        print("Usage: osxphotos run query_shared_albums.py [library_path]")
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
        test_shared_album_queries(db_path)
    except Exception as e:
        print(f"\nError during query testing: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 70)
    print(" Query testing complete!")
    print(" Please share this output in GitHub issue #2003")
    print("=" * 70)


if __name__ == "__main__":
    main()
