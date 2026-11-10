from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.fund_transfer import FundTransfer
from app.schemas.fund_transfer import (
    FundTransferContestRequest,
    FundTransferCreate,
    FundTransferResponse,
)
from app.services.fund_transfer_service import fund_transfer_service
from app.services.receipt_service import receipt_service

router = APIRouter(prefix="/fund-transfers", tags=["Fund Transfers"])


@router.get("", response_model=List[FundTransferResponse])
def list_fund_transfers(
    status: Optional[str] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("fund_transfers", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(FundTransfer)
    query = scope.apply_query_filter(query, FundTransfer)
    if status:
        query = query.filter(FundTransfer.status == status)

    transfers = query.order_by(FundTransfer.id.desc()).all()
    results = []
    for t in transfers:
        results.append(
            FundTransferResponse(
                id=t.id,
                reference=t.reference,
                branch_id=t.branch_id,
                from_user_id=t.from_user_id,
                from_user_name=t.sender.full_name if t.sender else None,
                to_user_id=t.to_user_id,
                to_user_name=t.recipient.full_name if t.recipient else None,
                amount=t.amount,
                reason=t.reason,
                status=t.status,
                contested_reason=t.contested_reason,
                cancelled_by=t.cancelled_by,
                confirmed_at=t.confirmed_at,
                cancelled_at=t.cancelled_at,
                created_at=t.created_at,
            )
        )
    return results


@router.post("", response_model=FundTransferResponse)
def create_fund_transfer(
    data: FundTransferCreate,
    request: Request,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("fund_transfers", Action.CREATE)),
    db: Session = Depends(get_db),
):
    scope.ensure_access(data.branch_id)
    ip = request.client.host if request.client else None
    t = fund_transfer_service.create_transfer(
        db=db,
        data=data,
        sender_id=int(current_user["sub"]),
        ip_address=ip,
    )
    return FundTransferResponse(
        id=t.id,
        reference=t.reference,
        branch_id=t.branch_id,
        from_user_id=t.from_user_id,
        from_user_name=t.sender.full_name if t.sender else None,
        to_user_id=t.to_user_id,
        to_user_name=t.recipient.full_name if t.recipient else None,
        amount=t.amount,
        reason=t.reason,
        status=t.status,
        contested_reason=t.contested_reason,
        cancelled_by=t.cancelled_by,
        confirmed_at=t.confirmed_at,
        cancelled_at=t.cancelled_at,
        created_at=t.created_at,
    )


@router.post("/{id}/confirm", response_model=FundTransferResponse)
def confirm_fund_transfer(
    id: int,
    request: Request,
    current_user: dict = Depends(require_permission("fund_transfers", Action.VALIDATE)),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    t = fund_transfer_service.confirm_transfer(
        db=db,
        transfer_id=id,
        recipient_id=int(current_user["sub"]),
        ip_address=ip,
    )
    return FundTransferResponse(
        id=t.id,
        reference=t.reference,
        branch_id=t.branch_id,
        from_user_id=t.from_user_id,
        from_user_name=t.sender.full_name if t.sender else None,
        to_user_id=t.to_user_id,
        to_user_name=t.recipient.full_name if t.recipient else None,
        amount=t.amount,
        reason=t.reason,
        status=t.status,
        contested_reason=t.contested_reason,
        cancelled_by=t.cancelled_by,
        confirmed_at=t.confirmed_at,
        cancelled_at=t.cancelled_at,
        created_at=t.created_at,
    )


@router.post("/{id}/contest", response_model=FundTransferResponse)
def contest_fund_transfer(
    id: int,
    data: FundTransferContestRequest,
    request: Request,
    current_user: dict = Depends(require_permission("fund_transfers", Action.VALIDATE)),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    t = fund_transfer_service.contest_transfer(
        db=db,
        transfer_id=id,
        reason=data.reason,
        recipient_id=int(current_user["sub"]),
        ip_address=ip,
    )
    return FundTransferResponse(
        id=t.id,
        reference=t.reference,
        branch_id=t.branch_id,
        from_user_id=t.from_user_id,
        from_user_name=t.sender.full_name if t.sender else None,
        to_user_id=t.to_user_id,
        to_user_name=t.recipient.full_name if t.recipient else None,
        amount=t.amount,
        reason=t.reason,
        status=t.status,
        contested_reason=t.contested_reason,
        cancelled_by=t.cancelled_by,
        confirmed_at=t.confirmed_at,
        cancelled_at=t.cancelled_at,
        created_at=t.created_at,
    )


@router.post("/{id}/cancel", response_model=FundTransferResponse)
def cancel_fund_transfer(
    id: int,
    request: Request,
    current_user: dict = Depends(require_permission("fund_transfers", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    t = fund_transfer_service.cancel_transfer(
        db=db,
        transfer_id=id,
        canceller_id=int(current_user["sub"]),
        ip_address=ip,
    )
    return FundTransferResponse(
        id=t.id,
        reference=t.reference,
        branch_id=t.branch_id,
        from_user_id=t.from_user_id,
        from_user_name=t.sender.full_name if t.sender else None,
        to_user_id=t.to_user_id,
        to_user_name=t.recipient.full_name if t.recipient else None,
        amount=t.amount,
        reason=t.reason,
        status=t.status,
        contested_reason=t.contested_reason,
        cancelled_by=t.cancelled_by,
        confirmed_at=t.confirmed_at,
        cancelled_at=t.cancelled_at,
        created_at=t.created_at,
    )


@router.get("/{id}/receipt")
def get_transfer_receipt(
    id: int,
    current_user: dict = Depends(require_permission("fund_transfers", Action.VIEW)),
    db: Session = Depends(get_db),
):
    transfer = db.query(FundTransfer).filter(FundTransfer.id == id).first()
    if not transfer:
        raise NotFoundError(message_key="transfer_not_found")

    from_name = transfer.sender.full_name if transfer.sender else "Émetteur"
    to_name = transfer.recipient.full_name if transfer.recipient else "Récepteur"
    b_name = transfer.branch.name if transfer.branch else "Établissement"

    pdf_buffer = receipt_service.generate_transfer_receipt_pdf(
        transfer=transfer,
        from_user_name=from_name,
        to_user_name=to_name,
        branch_name=b_name,
    )

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="transfer_{transfer.reference}.pdf"'},
    )

