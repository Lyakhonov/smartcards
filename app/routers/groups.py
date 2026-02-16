from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import require_role
from app.core.security import get_current_user
from app.core.utils import generate_uuid
from app.models.flashcard import Flashcard
from app.models.group import Group
from app.models.user import User, UserRole
from app.schemas.group import FileUploadResponse, GroupResponse
from app.services.llm import generate_flashcards
from app.services.pdf import extract_text_from_pdf

router = APIRouter()


@router.get("/", response_model=List[GroupResponse])
async def get_user_groups(
    current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    q = select(Group).where(Group.user_id == current_user.id)
    result = await db.execute(q)
    groups = result.scalars().all()
    return groups


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group_id = generate_uuid()
    new_group = Group(
        id=group_id,
        filename=file.filename,
        user_id=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_group)
    contents = await file.read()
    text = extract_text_from_pdf(contents)

    flashcards = await generate_flashcards(text)

    for card in flashcards:
        db.add(
            Flashcard(
                id=generate_uuid(),
                question=card["question"],
                answer=card["answer"],
                user_id=current_user.id,
                group_id=group_id,
            )
        )
    await db.commit()
    return {
        "group_id": group_id,
        "filename": file.filename,
        "message": "File processed successfully",
    }


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
    db: AsyncSession = Depends(get_db),
):
    q = select(Group).where(Group.id == group_id)
    res = await db.execute(q)
    group = res.scalars().first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    await db.execute(delete(Flashcard).where(Flashcard.group_id == group_id))
    await db.execute(delete(Group).where(Group.id == group_id))
    await db.commit()

    return {"detail": "Group deleted"}
