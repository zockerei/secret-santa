from typing import Annotated
from fastapi import Depends
from sqlmodel import SQLModel, create_engine, Session

engine = create_engine("sqlite:///database.db")


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    with Session(engine) as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]
