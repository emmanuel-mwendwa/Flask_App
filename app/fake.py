from random import randint
from sqlalchemy.exc import IntegrityError
from faker import Faker
from . import db
from .models import User, Post, Comment, Follow

fake = Faker() 

def users(count=100):
    i = 0
    while i < count:
        u = User(email=fake.email(),
                 username=fake.user_name(),
                 password='password',
                 confirmed=True,
                 name=fake.name(),
                 location=fake.city(),
                 about_me=fake.text(),
                 member_since=fake.past_date())
        db.session.add(u)
        i += 1
    with db.session.no_autoflush:
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

def posts(count=100):
    user_count = User.query.count()
    for i in range(count):
        u = User.query.offset(randint(0, user_count - 1)).first()
        p = Post(body=fake.text(),
                 timestamp=fake.past_date(),
                 author=u)
        db.session.add(p)
    db.session.commit()

def add_followers(num_followers):
    # create a list of users to follow
    users = User.query.all()

    # loop through users to add followers and followed users
    for i in range(num_followers):
        follower = fake.random_element(elements=users)
        followed = fake.random_element(elements=users)

        # make sure follower is not already following followed user
        while follower.is_following(followed):
            followed = fake.random_element(elements=users)

        # create a Follow object adn add to database
        follow = Follow(follower=follower, followed=followed)
        db.session.add(follow)
        db.session.commit()

def comments(count=100):
    user_count = User.query.count()
    post_count = Post.query.count()
    for i in range(count):
        u = User.query.offset(randint(0, user_count - 1)).first()
        p = Post.query.offset(randint(0, post_count - 1)).first()
        c = Comment(body=fake.text(),
                    timestamp=fake.past_date(),
                    disabled=False,
                    author_id=u,
                    post=p)
        db.session.add(c)
        u.comments.append(c)
    db.session.commit()

def generate_comments():
    posts = Post.query.all()
    for post in posts:
        for _ in range(5):
            comment = Comment(body=fake.text(),
                              timestamp=fake.past_date(),
                              disabled=False,
                              author_id=fake.random_int(min=1, max=11),
                              post=post)
            db.session.add(comment)
    db.session.commit()