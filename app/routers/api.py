from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import Userbot, Group, Member
from app.services.session_service import SessionService
from app.services.group_service import GroupService
from typing import List
from pydantic import BaseModel
from uuid import UUID

router = APIRouter(prefix="/api", tags=["api"])
session_service = SessionService()
group_service = GroupService()


class UserbotResponse(BaseModel):
    id: str
    name: str | None
    phone_number: str | None
    username: str | None
    created_at: str

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_userbots: int
    total_sessions: int
    total_groups: int


class UpdateDataResponse(BaseModel):
    added: int
    skipped: int
    total_sessions: int


class CreateGroupRequest(BaseModel):
    name: str
    admin_id: str
    member_ids: List[str]


class CreateGroupResponse(BaseModel):
    group_id: str
    telegram_id: int
    name: str
    message: str


@router.get("/userbots")
async def get_userbots(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Userbot).order_by(Userbot.created_at.desc()))
    userbots = result.scalars().all()

    return {
        "userbots": [
            {
                "id": str(bot.id),
                "name": bot.name,
                "phone_number": bot.phone_number,
                "username": bot.username,
                "created_at": bot.created_at.isoformat()
            }
            for bot in userbots
        ]
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    userbots_count = await db.scalar(select(func.count(Userbot.id)))

    groups_count = await db.scalar(select(func.count(Group.id)))

    session_files = session_service.get_session_files()
    sessions_count = len(session_files)

    return {
        "total_userbots": userbots_count or 0,
        "total_sessions": sessions_count,
        "total_groups": groups_count or 0
    }


@router.post("/update-data", response_model=UpdateDataResponse)
async def update_data(db: AsyncSession = Depends(get_db)):
    try:
        sessions_info = await session_service.get_all_sessions_info_via_telethon()

        if not sessions_info:
            return {
                "added": 0,
                "skipped": 0,
                "total_sessions": 0
            }

        added = 0
        skipped = 0

        for session_info in sessions_info:
            name = session_info.get('name')
            phone = session_info.get('phone_number')
            username = session_info.get('username')

            query = select(Userbot)

            if phone:
                query = query.where(Userbot.phone_number == phone)
            elif username:
                query = query.where(Userbot.username == username)
            else:
                skipped += 1
                continue

            result = await db.execute(query)
            existing_bot = result.scalar_one_or_none()

            if existing_bot:
                skipped += 1
                continue

            new_bot = Userbot(
                name=name,
                phone_number=phone,
                username=username
            )
            db.add(new_bot)
            added += 1

        await db.commit()

        return {
            "added": added,
            "skipped": skipped,
            "total_sessions": len(sessions_info)
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating data: {str(e)}")


@router.post("/groups/create", response_model=CreateGroupResponse)
async def create_group(request: CreateGroupRequest, db: AsyncSession = Depends(get_db)):
    """
    Створити групу в Telegram та додати учасників
    """
    try:
        # Отримати адміна з БД
        admin_result = await db.execute(
            select(Userbot).where(Userbot.id == UUID(request.admin_id))
        )
        admin = admin_result.scalar_one_or_none()

        if not admin:
            raise HTTPException(status_code=404, detail="Admin userbot not found")

        if not admin.phone_number:
            raise HTTPException(
                status_code=400,
                detail="Admin userbot does not have a phone number"
            )

        # Отримати учасників з БД
        members_info = []
        for member_id in request.member_ids:
            member_result = await db.execute(
                select(Userbot).where(Userbot.id == UUID(member_id))
            )
            member = member_result.scalar_one_or_none()

            if member and member.phone_number:
                members_info.append({
                    'phone': member.phone_number,
                    'name': member.name or member.username or 'User'
                })

        if not members_info:
            raise HTTPException(
                status_code=400,
                detail="No valid members found with phone numbers"
            )

        # Створити групу через Telethon
        telegram_chat_id = await group_service.create_group_with_members(
            admin_phone=admin.phone_number,
            group_name=request.name,
            members_info=members_info
        )

        # Зберегти групу в БД
        new_group = Group(
            name=request.name,
            telegram_id=telegram_chat_id,
            admin_id=UUID(request.admin_id)
        )
        db.add(new_group)
        await db.flush()

        # Додати учасників до БД
        for member_id in request.member_ids:
            member = Member(
                userbot_id=UUID(member_id),
                group_id=new_group.id
            )
            db.add(member)

        await db.commit()

        return {
            "group_id": str(new_group.id),
            "telegram_id": telegram_chat_id,
            "name": request.name,
            "message": f"Group '{request.name}' created successfully with {len(members_info)} members"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating group: {str(e)}")
