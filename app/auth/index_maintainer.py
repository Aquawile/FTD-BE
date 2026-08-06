from __future__ import annotations

from app.db import execute, query, query_dict


def rebuild_user_permissions_index() -> None:
    execute("TRUNCATE TABLE user_permissions_index")
    query(
        """
        INSERT INTO user_permissions_index (user_id, permission_name)
        SELECT up.user_id, p.name
        FROM user_permissions up
        JOIN permissions p ON up.permission_id = p.id
        """
    )
    rows = query("SELECT COUNT(*) AS count FROM user_permissions_index")[0][0]
    print(f"rebuild_user_permissions_index: {rows} rows rebuilt")


def sync_user_permissions_index(user_id: int) -> None:
    execute("DELETE FROM user_permissions_index WHERE user_id = %s", (user_id,))
    execute(
        """
        INSERT INTO user_permissions_index (user_id, permission_name)
        SELECT up.user_id, p.name
        FROM user_permissions up
        JOIN permissions p ON up.permission_id = p.id
        WHERE up.user_id = %s
        """,
        (user_id,),
    )
    rows = query("SELECT COUNT(*) AS count FROM user_permissions_index WHERE user_id = %s", (user_id,))
    count = rows[0][0] if rows else 0
    print(f"sync_user_permissions_index({user_id}): {count} rows synced")


if __name__ == "__main__":
    rebuild_user_permissions_index()
