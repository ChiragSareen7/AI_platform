import uuid


def new_query_id() -> str:
    return str(uuid.uuid4())

