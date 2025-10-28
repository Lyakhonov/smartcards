# main.py
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import (Column, DateTime, ForeignKey, String, Text, delete,
                        select, update)
# SQLAlchemy async imports
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

load_dotenv()

# ====== JWT Config ======
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_key_123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI(title="SmartCards Backend")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ====== Database (async SQLAlchemy) ======
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/smartcards"
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

def generate_uuid():
    return str(uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    groups = relationship("Group", back_populates="user", cascade="all, delete-orphan")
    # flashcards relation not strictly needed here

class Group(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="groups")
    flashcards = relationship("Flashcard", back_populates="group", cascade="all, delete-orphan")

class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(String, primary_key=True, default=generate_uuid)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)

    group = relationship("Group", back_populates="flashcards")


# Create tables on startup
@app.post("/startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


# Dependency: async DB session
async def get_db():
    async with async_session_maker() as session:
        yield session


# ====== Schemas (Pydantic) ======
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str]

class Token(BaseModel):
    access_token: str
    token_type: str

class FlashcardCreate(BaseModel):
    question: str
    answer: str

class FlashcardUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None

class FlashcardResponse(BaseModel):
    id: str
    question: str
    answer: str
    user_id: str
    group_id: str

class GroupResponse(BaseModel):
    id: str
    filename: str
    created_at: datetime

class FileUploadResponse(BaseModel):
    group_id: str
    filename: str
    message: str

# ====== Auth helpers ======
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# async helper: get user by email from DB
async def get_user_by_email_async(email: str, db: AsyncSession):
    q = select(User).where(User.email == email)
    result = await db.execute(q)
    return result.scalars().first()


# get_current_user now async and uses DB
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await get_user_by_email_async(email, db)
    if user is None:
        raise credentials_exception
    return user

# ====== Auth Routes ======
@app.post("/auth/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email_async(user.email, db)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    new_user = User(
        id=generate_uuid(),
        email=user.email,
        password=hash_password(user.password),
        full_name=user.full_name
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email, "full_name": new_user.full_name}

@app.post("/auth/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email_async(form_data.username, db)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": user.email}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

# ====== Groups & Flashcards ======
@app.get("/groups", response_model=List[GroupResponse])
async def get_user_groups(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Group).where(Group.user_id == current_user.id)
    result = await db.execute(q)
    groups = result.scalars().all()
    return [
        {"id": g.id, "filename": g.filename, "created_at": g.created_at}
        for g in groups
    ]

@app.get("/flashcards/group/{group_id}", response_model=List[FlashcardResponse])
async def get_flashcards_by_group(group_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Flashcard).where(Flashcard.group_id == group_id, Flashcard.user_id == current_user.id)
    result = await db.execute(q)
    cards = result.scalars().all()
    return [
        {"id": c.id, "question": c.question, "answer": c.answer, "user_id": c.user_id, "group_id": c.group_id}
        for c in cards
    ]

@app.delete("/groups/{group_id}")
async def delete_group(group_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # check group exists and belongs to user
    q = select(Group).where(Group.id == group_id)
    res = await db.execute(q)
    group = res.scalars().first()
    if not group or group.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Group not found")

    # delete flashcards (cascade is configured but we'll delete explicitly)
    await db.execute(delete(Flashcard).where(Flashcard.group_id == group_id))
    await db.execute(delete(Group).where(Group.id == group_id))
    await db.commit()
    return {"detail": "Group deleted"}

# ====== Flashcard Editing ======
@app.delete("/flashcards/{card_id}")
async def delete_flashcard(card_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Flashcard).where(Flashcard.id == card_id)
    res = await db.execute(q)
    card = res.scalars().first()
    if not card or card.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Card not found")
    await db.execute(delete(Flashcard).where(Flashcard.id == card_id))
    await db.commit()
    return {"detail": "Card deleted"}

@app.put("/flashcards/{card_id}", response_model=FlashcardResponse)
async def update_flashcard(
    card_id: str,
    updated_data: FlashcardUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    q = select(Flashcard).where(Flashcard.id == card_id)
    res = await db.execute(q)
    card = res.scalars().first()
    if not card or card.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Card not found")

    changed = False
    if updated_data.question is not None:
        card.question = updated_data.question
        changed = True
    if updated_data.answer is not None:
        card.answer = updated_data.answer
        changed = True

    if changed:
        db.add(card)
        await db.commit()
        await db.refresh(card)

    return {"id": card.id, "question": card.question, "answer": card.answer, "user_id": card.user_id, "group_id": card.group_id}

# ====== Upload PDF ======
@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    group_id = generate_uuid()
    new_group = Group(
        id=group_id,
        filename=file.filename,
        user_id=current_user.id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_group)
    # fake generation of 3 cards (will be replaced by real AI later)
    flashcards = []
    for i in range(3):
        card = Flashcard(
            id=generate_uuid(),
            question=f"Вопрос {i+1} к {file.filename}",
            answer=f"Ответ {i+1}",
            user_id=current_user.id,
            group_id=group_id
        )
        db.add(card)
        flashcards.append(card)
    await db.commit()
    # no need to refresh everything here
    return {"group_id": group_id, "filename": file.filename, "message": "File processed successfully"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)