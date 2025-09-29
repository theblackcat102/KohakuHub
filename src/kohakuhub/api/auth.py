from fastapi import Depends
from ..db import db, User


def get_db():
    try:
        db.connect(reuse_if_open=True)
        yield db
    finally:
        if not db.is_closed():
            db.close()


def get_current_user():
    # TODO: 真正 auth，這裡先 mock
    class _U:
        username = "me"

    return _U()
