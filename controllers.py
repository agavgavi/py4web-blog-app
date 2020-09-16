"""
This file defines actions, i.e. functions the URLs are mapped into
The @action(path) decorator exposed the function at URL:

    http://127.0.0.1:8000/{app_name}/{path}

If app_name == '_default' then simply

    http://127.0.0.1:8000/{path}

If path == 'index' it can be omitted:

    http://127.0.0.1:8000/

The path follows the bottlepy syntax.

@action.uses('generic.html')  indicates that the action uses the generic.html template
@action.uses(session)         indicates that the action uses the session
@action.uses(db)              indicates that the action uses the db
@action.uses(T)               indicates that the action uses the i18n & pluralization
@action.uses(auth.user)       indicates that the action requires a logged in user
@action.uses(auth)            indicates that the action requires the auth object

session, db, T, auth, and tempates are examples of Fixtures.
Warning: Fixtures MUST be declared with @action.uses({fixtures}) else your app will result in undefined behavior
"""
from py4web import action, request, redirect, URL, Field, HTTP
from py4web.utils.form import Form, FormStyleBootstrap4
from py4web.utils.grid import Grid
from .common import db, authenticated, unauthenticated, flash, auth, session

from .models import get_download_url
from .import settings

from pydal.validators import (
    IS_EMAIL,
    IS_NOT_EMPTY,
    IS_NOT_IN_DB
)

import os
from PIL import Image

# Routes that don't require sign in

#  Users can view all of the posts from here


@unauthenticated('index', 'index.html')
def index():
    posts = db().select(db.post.ALL, db.profile.ALL, left=db.post.on(
        db.post.author == db.profile.user), orderby=~db.post.date_posted)
    return dict(posts=posts)

#  When clicking on an individual post you will get a direct link to that
#  article, useful for longer form articles and comments (If you so choose to implement that)


@unauthenticated('post/<pk:int>', 'post_detail.html')
def postDetail(pk=None):
    if pk is None:
        redirect(URL('index'))
    post = db.post[pk]
    if post is None:
        redirect(URL('index'))
    profile = db.auth_user(post.author).profile.select().first()
    post.author_icon = f"images/{profile.image}"
    return dict(post=post)

#  In addition to seeing all the posts, you can filter
#  the posts to only show those by a specific user.
#  If the user doesn't exist, it will redirect to the home page


@unauthenticated('user/<user_id>', 'user_posts.html')
def userPosts(user_id=None):
    if user_id is None:
        redirect(URL('index'))

    author = db.auth_user[user_id]
    if author == None:
        redirect(URL('index'))

    posts = db(db.post.author == user_id).select(db.post.ALL, db.profile.ALL, left=db.post.on(
        db.post.author == db.profile.user),
        orderby=~db.post.date_posted)
    return dict(posts=posts)

# The about page gives information about the project and it's possible future


@unauthenticated('about', 'about.html')
def about():
    return dict(title="About")


# Routes that require sign in


#  Utilizing py4web's built in form utility, we can
#  create posts simply with a few lines. However, we want
#  to make sure only logged in users can post
@authenticated('post/new', 'post_create.html')
def postCreate():

    form = Form(db.post, csrf_session=session, formstyle=FormStyleBootstrap4)

    if form.accepted:
        # We always want POST requests to be redirected as GETs.
        redirect(URL('post', form.vars['id']))

    return dict(form=form)

#  The same form utility that allows us to create posts also
#  allows us to edit them. However, in addition to wanting to
#  restrict editing to logged in users, we want to also restrict
#  editing to the post's author


@authenticated('post/<pk:int>/update', 'post_update.html')
def postUpdate(pk=None):

    post = db.post[pk]

    if post is None or post.author != auth.current_user.get('id'):
        redirect(URL('index'))

    form = Form(db.post, record=post, deletable=False,
                csrf_session=session, formstyle=FormStyleBootstrap4)

    if form.accepted:
        # We always want POST requests to be redirected as GETs.
        redirect(URL('index'))
    return dict(form=form)

#  We can delete the post using pydal but we want to
#  restrict deleting to only the post owner


@authenticated('post/delete/<pk:int>')
def _postDelete(pk=None):
    post = db.post[pk]

    if post is None or post.author != auth.current_user.get('id'):
        redirect(URL('index'))

    db(db.post.id == pk).delete()
    redirect(URL('index'))

#  If we want to show a warning screen before deleting, we need to pass
#  the post to the page


@authenticated('post/<pk:int>/delete', 'post_delete.html')
def postDelete(pk=None):
    post = db.post[pk]
    if post is None or post.author != auth.current_user.get('id'):
        redirect(URL('index'))
    return dict(post=post)

#  The user can edit their profile through this page. Here they can edit
#  the following attributes:
#  Their profile pic
#  Username
#  Email
#  First name and Last name
#
#  For all profile pics uploaded, they are resized to a max of 300x300 to
#  save space and renamed to remove conflicts. Everyone starts with the default.jpg pic
#  When the old profile pic is no longer in use, it is deleted


@authenticated('profile', 'profile.html')
def profile():
    user = auth.get_user()
    profile = db.auth_user(user['id']).profile.select().first()

    icon = f"images/{profile.image}"
    # Append the user profile icon to the dict so it prepopulates it with current data
    user.update({"icon": profile.image})

    form_list = [
        Field("username", requires=[IS_NOT_EMPTY(), IS_NOT_IN_DB(
            db, "auth_user.username")], unique=True,),
        Field("email", requires=(IS_EMAIL(), IS_NOT_IN_DB(
            db, "auth_user.email")), unique=True,),
        Field("first_name", requires=IS_NOT_EMPTY()),
        Field("last_name", requires=IS_NOT_EMPTY()),
        Field('icon', 'upload', default='default.jpg',
                      uploadfolder=settings.UPLOAD_PATH, download_url=get_download_url),
    ]
    aform = Form(form_list, record=user,
                 csrf_session=session,
                 deletable=False,
                 formstyle=FormStyleBootstrap4)
    if aform.accepted:
        user_db = db.auth_user[user['id']]
        user_db.update_record(username=aform.vars['username'],
                              email=aform.vars['email'],
                              first_name=aform.vars['first_name'],
                              last_name=aform.vars['last_name'])
        if aform.vars['icon'] == None and aform.vars['icon'] != profile.image:
            temp_image = profile.image
            if temp_image == 'default.jpg':
                redirect(URL('profile'))
            cleanup_image(temp_image)
            profile.update_record(image='default.jpg')

        if aform.vars['icon'] and aform.vars['icon'] != profile.image:
            if profile.image != 'default.jpg':
                cleanup_image(profile.image)
            profile.update_record(image=aform.vars['icon'])
            resize_image(profile.image)

        redirect(URL('profile'))
    return dict(icon=icon, aform=aform)


def resize_image(image_path):
    total_path = os.path.join(settings.UPLOAD_PATH, image_path)

    img = Image.open(total_path)
    if img.height > 300 or img.width > 300:
        output_size = (300, 300)
        img.thumbnail(output_size)
        img.save(total_path)


def cleanup_image(image_path):
    total_path = os.path.join(settings.UPLOAD_PATH, image_path)
    os.remove(total_path, dir_fd=None)
