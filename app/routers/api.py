from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import Userbot, Group, Member
from app.services.session_service import SessionService
from app.services.group_service import GroupService
from app.services.contact_service import ContactService
from database.managers.contacts_manager import ContactsManager
from typing import List
from pydantic import BaseModel
from uuid import UUID
import json

router = APIRouter(prefix="/api", tags=["api"])
session_service = SessionService()
group_service = GroupService()
contact_service = ContactService()
contacts_manager = ContactsManager()


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
    global_prompt: str = ""


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
            admin_id=UUID(request.admin_id),
            global_prompt=request.global_prompt
        )
        db.add(new_group)
        await db.flush()

        # Додати адміна до members з is_admin=True
        admin_member = Member(
            userbot_id=UUID(request.admin_id),
            group_id=new_group.id,
            is_admin=True
        )
        db.add(admin_member)

        # Додати інших учасників до БД з is_admin=False
        for member_id in request.member_ids:
            member = Member(
                userbot_id=UUID(member_id),
                group_id=new_group.id,
                is_admin=False
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


@router.get("/groups")
async def get_groups(db: AsyncSession = Depends(get_db)):
    """
    Отримати всі групи з мемберами
    """
    try:
        result = await db.execute(
            select(Group).order_by(Group.created_at.desc())
        )
        groups = result.scalars().all()

        groups_data = []
        for group in groups:
            # Отримати мемберів групи
            members_result = await db.execute(
                select(Member).where(Member.group_id == group.id)
            )
            members = members_result.scalars().all()

            # Отримати дані юзерботів для кожного мембера
            members_data = []
            for member in members:
                userbot_result = await db.execute(
                    select(Userbot).where(Userbot.id == member.userbot_id)
                )
                userbot = userbot_result.scalar_one_or_none()

                if userbot:
                    members_data.append({
                        "member_id": str(member.id),
                        "userbot_id": str(userbot.id),
                        "userbot_name": userbot.name or userbot.phone_number,
                        "phone_number": userbot.phone_number,
                        "is_admin": member.is_admin,
                        "additional_prompt": member.additional_prompt or ""
                    })

            # Отримати адміна
            admin_name = None
            if group.admin_id:
                admin_result = await db.execute(
                    select(Userbot).where(Userbot.id == group.admin_id)
                )
                admin = admin_result.scalar_one_or_none()
                if admin:
                    admin_name = admin.name or admin.phone_number

            groups_data.append({
                "id": str(group.id),
                "name": group.name,
                "telegram_id": group.telegram_id,
                "admin_id": str(group.admin_id) if group.admin_id else None,
                "admin_name": admin_name,
                "global_prompt": group.global_prompt or "",
                "group_settings": group.group_settings,
                "created_at": group.created_at.isoformat(),
                "members": members_data
            })

        return {"groups": groups_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching groups: {str(e)}")


@router.put("/groups/{group_id}/prompt")
async def update_group_prompt(
    group_id: str,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Оновити global_prompt групи
    """
    try:
        result = await db.execute(
            select(Group).where(Group.id == UUID(group_id))
        )
        group = result.scalar_one_or_none()

        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        group.global_prompt = request.get("global_prompt", "")
        await db.commit()

        return {
            "success": True,
            "message": "Group prompt updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating group prompt: {str(e)}")


@router.put("/members/{member_id}/prompt")
async def update_member_prompt(
    member_id: str,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Оновити additional_prompt мембера
    """
    try:
        result = await db.execute(
            select(Member).where(Member.id == UUID(member_id))
        )
        member = result.scalar_one_or_none()

        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        member.additional_prompt = request.get("additional_prompt", "")
        await db.commit()

        return {
            "success": True,
            "message": "Member prompt updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating member prompt: {str(e)}")


@router.get("/contacts/add-all")
async def contact_all(db: AsyncSession = Depends(get_db)):
    """
    Add all userbots to each other's contacts
    Uses Server-Sent Events for real-time progress
    """
    async def event_generator():
        try:
            result = await db.execute(
                select(Userbot)
                .where(Userbot.phone_number.isnot(None))
                .order_by(Userbot.created_at)
            )
            userbots = result.scalars().all()

            if not userbots:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No userbots found'})}\n\n"
                return

            userbots_data = [
                {
                    'id': str(bot.id),
                    'phone_number': bot.phone_number,
                    'name': bot.name or bot.phone_number
                }
                for bot in userbots
            ]

            async for progress in contact_service.contact_all_userbots(userbots_data):
                if progress['type'] == 'userbot_completed':
                    userbot_id = UUID(userbots_data[progress['current'] - 1]['id'])

                    other_ids = [
                        UUID(bot['id']) for bot in userbots_data
                        if bot['id'] != str(userbot_id)
                    ]

                    try:
                        await contacts_manager.bulk_create_contacts(
                            db, userbot_id, other_ids
                        )
                        await db.commit()
                    except Exception as e:
                        await db.rollback()
                        print(f"Error saving contacts for {userbot_id}: {e}")

                yield f"data: {json.dumps(progress)}\n\n"

        except Exception as e:
            error_msg = {
                'type': 'error',
                'message': f'Server error: {str(e)}'
            }
            yield f"data: {json.dumps(error_msg)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
