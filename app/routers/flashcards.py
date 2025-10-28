from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.flashcard import Flashcard
from app.schemas.flashcard import FlashcardResponse, FlashcardUpdate

router = APIRouter()

@router.get("/group/{group_id}", response_model=List[FlashcardResponse])
async def get_flashcards_by_group(group_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Flashcard).where(Flashcard.group_id == group_id, Flashcard.user_id == current_user.id)
    result = await db.execute(q)
    return result.scalars().all()

@router.delete("/{card_id}")
async def delete_flashcard(card_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Flashcard).where(Flashcard.id == card_id)
    res = await db.execute(q)
    card = res.scalars().first()
    if not card or card.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Card not found")
    await db.execute(delete(Flashcard).where(Flashcard.id == card_id))
    await db.commit()
    return {"detail": "Card deleted"}

@router.put("/{card_id}", response_model=FlashcardResponse)
async def update_flashcard(card_id: str, updated_data: FlashcardUpdate, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Flashcard).where(Flashcard.id == card_id)
    res = await db.execute(q)
    card = res.scalars().first()
    if not card or card.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Card not found")
    if updated_data.question is not None:
        card.question = updated_data.question
    if updated_data.answer is not None:
        card.answer = updated_data.answer
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card
