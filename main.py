from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

# ====== JWT Config ======
SECRET_KEY = "super_secret_key_123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI(title="SmartCards Backend")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ====== Fake DB ======
fake_users_db = {}
fake_flashcards_db = {}
fake_groups_db = {}  # group_id -> {id, user_id, filename, created_at}

# ====== Schemas ======
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

def get_user_by_email(email: str):
    return fake_users_db.get(email)

def get_current_user(token: str = Depends(oauth2_scheme)):
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
    user = get_user_by_email(email)
    if user is None:
        raise credentials_exception
    return user

# ====== Auth Routes ======
@app.post("/auth/register", response_model=UserResponse)
def register_user(user: UserCreate):
    if user.email in fake_users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    user_id = str(uuid4())
    fake_users_db[user.email] = {
        "id": user_id,
        "email": user.email,
        "password": hash_password(user.password),
        "full_name": user.full_name
    }
    return {"id": user_id, "email": user.email, "full_name": user.full_name}

@app.post("/auth/login", response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": user["email"]}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

# ====== Groups & Flashcards ======
@app.get("/groups", response_model=List[GroupResponse])
def get_user_groups(current_user: dict = Depends(get_current_user)):
    return [
        group for group in fake_groups_db.values()
        if group["user_id"] == current_user["id"]
    ]

@app.get("/flashcards/group/{group_id}", response_model=List[FlashcardResponse])
def get_flashcards_by_group(group_id: str, current_user: dict = Depends(get_current_user)):
    return [
        card for card in fake_flashcards_db.values()
        if card["group_id"] == group_id and card["user_id"] == current_user["id"]
    ]

@app.delete("/groups/{group_id}")
def delete_group(group_id: str, current_user: dict = Depends(get_current_user)):
    group = fake_groups_db.get(group_id)
    if not group or group["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Group not found")
    # Удаляем карточки группы
    for card_id in list(fake_flashcards_db.keys()):
        if fake_flashcards_db[card_id]["group_id"] == group_id:
            del fake_flashcards_db[card_id]
    # Удаляем саму группу
    del fake_groups_db[group_id]
    return {"detail": "Group deleted"}


# ====== Flashcard Editing ======
@app.delete("/flashcards/{card_id}")
def delete_flashcard(card_id: str, current_user: dict = Depends(get_current_user)):
    card = fake_flashcards_db.get(card_id)
    if not card or card["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Card not found")
    del fake_flashcards_db[card_id]
    return {"detail": "Card deleted"}

@app.put("/flashcards/{card_id}", response_model=FlashcardResponse)
def update_flashcard(
    card_id: str,
    updated_data: FlashcardUpdate,
    current_user: dict = Depends(get_current_user)
):
    card = fake_flashcards_db.get(card_id)
    if not card or card["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Card not found")

    if updated_data.question is not None:
        card["question"] = updated_data.question
    if updated_data.answer is not None:
        card["answer"] = updated_data.answer

    return card


# ====== Upload PDF ======
@app.post("/upload", response_model=FileUploadResponse)
def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    group_id = str(uuid4())
    fake_groups_db[group_id] = {
        "id": group_id,
        "filename": file.filename,
        "user_id": current_user["id"],
        "created_at": datetime.now(timezone.utc)
    }

    # TODO: здесь будет обработка PDF ИИ
    # А пока — фейковая генерация карточек
    for i in range(3):
        card_id = str(uuid4())
        fake_flashcards_db[card_id] = {
            "id": card_id,
            "question": f"Вопрос {i+1} к {file.filename}",
            "answer": f"Ответ {i+1}",
            "user_id": current_user["id"],
            "group_id": group_id
        }

    return {"group_id": group_id, "filename": file.filename, "message": "File processed successfully"}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
