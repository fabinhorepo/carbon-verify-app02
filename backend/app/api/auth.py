"""Endpoints de autenticação, usuários e organização."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.auth import verify_password, get_password_hash, create_access_token, create_api_key, get_current_user
from app.models.models import User, Organization, UserRole, AuditLog
from app.models.schemas import (
    LoginRequest, TokenResponse, RegisterRequest, UserResponse,
    ChangePasswordRequest, UserUpdate, OrganizationResponse, MemberInvite,
)

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    slug = data.organization_name.lower().replace(" ", "-")[:100]
    org_result = await db.execute(select(Organization).where(Organization.slug == slug))
    org = org_result.scalar_one_or_none()

    if not org:
        org = Organization(name=data.organization_name, slug=slug)
        db.add(org)
        await db.flush()
        org.api_key = create_api_key(org.id)

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        role=UserRole.ADMIN,
        organization_id=org.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Conta desativada")

    db.add(AuditLog(user_id=user.id, action="login", resource_type="auth"))
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    current_user.hashed_password = get_password_hash(data.new_password)
    db.add(AuditLog(user_id=current_user.id, action="change_password", resource_type="auth"))
    await db.commit()
    return {"message": "Senha alterada com sucesso"}


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Sem permissão")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if data.full_name:
        user.full_name = data.full_name
    if data.role and current_user.role == UserRole.ADMIN:
        user.role = data.role
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


# ─── Organization Endpoints ─────────────────────────────────────────────

org_router = APIRouter(prefix="/organizations", tags=["Organização"])


@org_router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organização não encontrada")
    return OrganizationResponse.model_validate(org)


@org_router.get("/me/members")
async def list_members(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(User).where(User.organization_id == current_user.organization_id)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@org_router.post("/me/members", response_model=UserResponse, status_code=201)
async def invite_member(
    data: MemberInvite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas admins podem convidar")
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        role=data.role,
        organization_id=current_user.organization_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@org_router.post("/me/api-keys")
async def generate_api_key(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas admins")
    result = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = result.scalar_one_or_none()
    org.api_key = create_api_key(org.id)
    await db.commit()
    return {"api_key": org.api_key}


@org_router.get("/me/audit-log")
async def get_audit_log(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AuditLog, User.full_name)
        .join(User, AuditLog.user_id == User.id)
        .where(User.organization_id == current_user.organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )
    return [
        {
            "id": log.id, "action": log.action,
            "resource_type": log.resource_type, "resource_id": log.resource_id,
            "details": log.details, "user_name": name,
            "created_at": log.created_at,
        }
        for log, name in result.all()
    ]
