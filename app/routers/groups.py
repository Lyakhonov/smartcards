from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
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
from app.services.storage import storage
from sqlalchemy import desc, asc

router = APIRouter()


@router.get("/", response_model=List[GroupResponse])
async def get_user_groups(
    q: str | None = Query(None, description="Поиск по имени файла"),
    min_cards: int | None = Query(None, ge=0, description="Минимальное число карточек"),
    sort_by: str = Query(
        "created_at", regex="^(created_at|filename|flashcards_count)$"
    ),
    order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Ensure storage bucket exists (idempotent)
    try:
        storage.ensure_bucket()
    except Exception:
        # don't block listing if storage temporarily unavailable
        pass

    stmt = select(Group).where(Group.user_id == current_user.id)

    if q:
        stmt = stmt.where(Group.filename.ilike(f"%{q}%"))

    if min_cards is not None:
        stmt = stmt.where(Group.flashcards_count >= min_cards)

    # apply sorting
    sort_column = {
        "created_at": Group.created_at,
        "filename": Group.filename,
        "flashcards_count": Group.flashcards_count,
    }[sort_by]

    if order == "desc":
        stmt = stmt.order_by(desc(sort_column))
    else:
        stmt = stmt.order_by(asc(sort_column))

    stmt = stmt.limit(per_page).offset((page - 1) * per_page)

    result = await db.execute(stmt)
    groups = result.scalars().all()

    # attach presigned file url where possible
    out = []
    for g in groups:
        item = g
        try:
            object_name = f"groups/{g.id}/{g.filename}"
            url = storage.get_presigned_url(object_name)
            setattr(item, "file_url", url)
        except Exception:
            setattr(item, "file_url", None)
        out.append(item)

    return out


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

    # upload original file to storage
    try:
        storage.ensure_bucket()
        object_name = f"groups/{group_id}/{file.filename}"
        storage.upload_bytes(contents, object_name, content_type=file.content_type)
    except Exception:
        # if storage fails, continue but note that file_url won't be available
        pass

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
    # attempt to remove object from storage
    try:
        object_name = f"groups/{group_id}/{group.filename}"
        storage.delete_object(object_name)
    except Exception:
        # ignore storage errors but continue DB cleanup
        pass

    await db.execute(delete(Flashcard).where(Flashcard.group_id == group_id))
    await db.execute(delete(Group).where(Group.id == group_id))
    await db.commit()

    return {"detail": "Group deleted"}
