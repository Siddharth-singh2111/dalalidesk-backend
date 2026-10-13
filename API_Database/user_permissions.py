"""
Per-user feature permissions, managed from the admin panel.

The catalog below is the list of features shown in the admin UI. Each is a
`resource` matching the backend @permission_required(resource, action) guards,
with a human label. get/set operate on the user_permissions table.
"""
from psql import execute_query

# (resource, friendly label). Order controls the admin grid order.
RESOURCE_CATALOG = [
    ('register_entry', 'Bills (Register)'),
    ('memo_entry', 'Memos'),
    ('order_form', 'Order Forms'),
    ('dalali_entry', 'Dalali'),
    ('supplier', 'Suppliers'),
    ('party', 'Buyers (Parties)'),
    ('bank', 'Banks'),
    ('transport', 'Transport'),
    ('firm', 'Firms'),
    ('firm_bank', 'Firm Banks'),
    ('item', 'Items'),
    ('item_entry', 'Item Entries'),
    ('users', 'User Management'),
    ('audit_log', 'Audit Log'),
]

_ACTION_COLS = ('can_create', 'can_read', 'can_update', 'can_delete')


def get_user_permissions_matrix(user_id):
    """Return the full catalog with this user's current CRUD flags, defaulting a
    feature to all-false when the user has no row for it yet."""
    res = execute_query(
        "SELECT resource, can_create, can_read, can_update, can_delete "
        "FROM user_permissions WHERE user_id = {}".format(int(user_id))
    )
    stored = {}
    if res.get('status') == 'okay':
        for row in res['result']:
            stored[row['resource']] = row

    matrix = []
    for resource, label in RESOURCE_CATALOG:
        row = stored.get(resource)
        matrix.append({
            'resource': resource,
            'label': label,
            'can_create': bool(row['can_create']) if row else False,
            'can_read': bool(row['can_read']) if row else False,
            'can_update': bool(row['can_update']) if row else False,
            'can_delete': bool(row['can_delete']) if row else False,
        })
    return matrix


def set_user_permissions(user_id, permissions, updated_by=None):
    """Upsert the given per-user permissions.

    `permissions` is a list of {resource, can_create, can_read, can_update,
    can_delete}. Only resources in the catalog are accepted. Returns the saved
    matrix.
    """
    user_id = int(user_id)
    valid_resources = {r for r, _ in RESOURCE_CATALOG}
    updated_by_sql = int(updated_by) if updated_by not in (None, '') else 'NULL'

    for perm in permissions or []:
        resource = perm.get('resource')
        if resource not in valid_resources:
            continue
        vals = {col: bool(perm.get(col, False)) for col in _ACTION_COLS}
        # Note: created_by is listed explicitly so execute_query's audit layer
        # (which would otherwise inject created_by/last_updated_by) leaves this
        # query untouched.
        query = (
            "INSERT INTO user_permissions "
            "(user_id, resource, can_create, can_read, can_update, can_delete, created_by, last_updated, last_updated_by) "
            "VALUES ({uid}, '{res}', {c}, {r}, {u}, {d}, {by}, CURRENT_TIMESTAMP, {by}) "
            "ON CONFLICT (user_id, resource) DO UPDATE SET "
            "can_create = EXCLUDED.can_create, can_read = EXCLUDED.can_read, "
            "can_update = EXCLUDED.can_update, can_delete = EXCLUDED.can_delete, "
            "last_updated = CURRENT_TIMESTAMP, last_updated_by = EXCLUDED.last_updated_by"
        ).format(
            uid=user_id, res=resource,
            c=str(vals['can_create']).lower(), r=str(vals['can_read']).lower(),
            u=str(vals['can_update']).lower(), d=str(vals['can_delete']).lower(),
            by=updated_by_sql,
        )
        execute_query(query)
    return get_user_permissions_matrix(user_id)


def get_effective_permissions_matrix(user):
    """The user's EFFECTIVE permissions, matching User.has_permission's logic, for
    driving UI menu visibility: admin => everything; else the user's own rows when
    they have any; else the role template. Keeps the menu in sync with enforcement.
    """
    role = getattr(user, 'role', None)
    if role == 'admin':
        return [{
            'resource': r, 'label': l,
            'can_create': True, 'can_read': True, 'can_update': True, 'can_delete': True,
        } for r, l in RESOURCE_CATALOG]

    res = execute_query(
        "SELECT resource, can_create, can_read, can_update, can_delete "
        "FROM user_permissions WHERE user_id = {}".format(int(user.id))
    )
    rows = {}
    if res.get('status') == 'okay' and res['result']:
        rows = {row['resource']: row for row in res['result']}
    else:
        # No per-user rows: fall back to the role matrix.
        role_safe = str(role or '').replace("'", "''")
        rres = execute_query(
            "SELECT resource, can_create, can_read, can_update, can_delete "
            "FROM permissions WHERE role = '{}'".format(role_safe)
        )
        if rres.get('status') == 'okay':
            rows = {row['resource']: row for row in rres['result']}

    matrix = []
    for resource, label in RESOURCE_CATALOG:
        row = rows.get(resource)
        matrix.append({
            'resource': resource, 'label': label,
            'can_create': bool(row['can_create']) if row else False,
            'can_read': bool(row['can_read']) if row else False,
            'can_update': bool(row['can_update']) if row else False,
            'can_delete': bool(row['can_delete']) if row else False,
        })
    return matrix


def seed_default_user_permissions(user_id):
    """Give a brand-new user the standard 'user' role template so they are usable
    immediately; the admin can then adjust each checkbox."""
    user_id = int(user_id)
    query = (
        "INSERT INTO user_permissions (user_id, resource, can_create, can_read, can_update, can_delete) "
        "SELECT {uid}, resource, can_create, can_read, can_update, can_delete "
        "FROM permissions WHERE role = 'user' "
        "ON CONFLICT (user_id, resource) DO NOTHING"
    ).format(uid=user_id)
    return execute_query(query)
