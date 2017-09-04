from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from os import remove, path
from sys import exit
from random import randint
from random_words import RandomWords, LoremIpsum
from models import Base, Item, User, Category, Vote


def makeRandomStuff():

    # set up database session
    engine = create_engine('postgresql://grader:grader@localhost/opinionated')
    # Bind the engine to the metadata of the Base class so that the
    # declaratives can be accessed through a DBSession instance

    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    # create starter data, starting with 4 users
    frank = User(
        username="Mysterious Frank",
        email="FrankMystery@provider.net",
        picture="/static/imgs/mask.jpg",
        about="Frank was here before the beginning.")

    session.add(frank)
    session.commit()
    frank_id = session.query(User).one().id

    tara = User(
        username="Green Tara",
        email="GreenTara@dharmakaya.tb",
        picture='/static/imgs/tara.JPG',
        about='A benevolent presence.')

    session.add(tara)
    session.commit()
    tara_id = session.query(User).filter_by(
        username='Green Tara').one().id

    james = User(
        username="James Jamerson",
        email="jjj@monkeybutler.org",
        picture='/static/imgs/rocks.JPG',
        about='A man who loves rocks very much')

    session.add(james)
    james_id = session.query(User).filter_by(
        username='James Jamerson').one().id
    session.commit()

    chicken = User(
        username='Chicken Elizabeth',
        email="dontcomenearmyhouse@bark.mail",
        picture='/static/imgs/dog.jpg',
        about="A fearful dog")

    session.add(chicken)
    chicken_id = session.query(User).filter_by(
        username='Chicken Elizabeth').one().id
    session.commit()

    # load random words classes
    rw = RandomWords()
    li = LoremIpsum()
    users = [frank_id, tara_id, james_id, chicken_id]

    for user_id in users:

        for w in rw.random_words(count=randint(6, 11)):
            # make a random category
            session.add(Category(name=w, created_by=user_id))
            cat_id = session.query(Category).filter_by(
                name=w).one().id
            # populate category with stuff
            for x in rw.random_words(count=randint(3, 20)):
                thing = Item(
                    name=x,
                    category_id=cat_id,
                    description=li.get_sentence(),
                    created_by=user_id)
                session.add(thing)
                session.flush()
                for user_id2 in users:
                    if randint(1, 2) > 1:
                        session.add(Vote(
                            voter=user_id2,
                            votee=user_id,
                            item=thing.id,
                            up_or_down=randint(0, 1)))
        session.commit()


if __name__ == '__main__':
    # check for pre-existing database
    makeRandomStuff()
    print("Completed building starter data")

