"""
This file defines the database models
"""

from .common import db, Field, auth
from py4web import URL
from pydal.validators import IS_NOT_EMPTY
import datetime
from . import settings

# Define your table below
#
# db.define_table('thing', Field('name'))
#
# always commit your models to avoid problems later
#
# db.commit()
#


def get_time():
    return datetime.datetime.utcnow()


def get_download_url(picture):
    return f"images/{picture}"


def get_user():
    return auth.current_user.get("id") if auth.current_user else None


db.define_table(
    "post",
    Field("title", "string", requires=IS_NOT_EMPTY()),
    Field("content", "text", requires=IS_NOT_EMPTY()),
    Field("date_posted", "datetime", default=get_time, readable=False, writable=False),
    Field(
        "author",
        "reference auth_user",
        default=get_user,
        readable=False,
        writable=False,
    ),
)

db.define_table(
    "profile",
    Field("user", "reference auth_user", readable=False, writable=False),
    Field(
        "image",
        "upload",
        default="default.jpg",
        uploadfolder=settings.UPLOAD_PATH,
        download_url=get_download_url, label="Profile Picture",
    ),
)
# We do not want these fields to appear in forms by default.
db.post.id.readable = False
db.post.id.writable = False
db.profile.id.readable = False
db.profile.id.writable = False


db.commit()
