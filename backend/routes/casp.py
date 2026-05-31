"""CASP admin routes — REST API consumed by the /admin frontend console.

Grouping convention:
  /api/casp/dashboard           -> KPI summary
  /api/casp/kyc, /kyb, /risk    -> Block 1
  /api/casp/aml, /travel-rule, /sar -> Block 2
  /api/casp/wallets, /reconciliation, /por -> Block 3
  /api/casp/otc                 -> Block 4
  /api/casp/reports, /capital   -> Block 5
  /api/casp/complaints, /disclosures -> Block 6
  /api/casp/governance          -> Block 7
  /api/casp/audit               -> WORM log
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from middleware.casp_rbac import (
    require_any_admin, require_compliance, require_mlro,
    require_risk, require_treasury, require_otc_trader, require_otc_approver,
)
from services.casp_service import CaspService
from services.audit_log_service import AuditLogService

router = APIRouter(prefix="/casp", tags=["CASP"])

# Service handles wired by server.py
_casp: Optional[CaspService] = None
_audit: Optional[AuditLogService] = None


def set_services(casp: CaspService, audit: AuditLogService) -> None:
    global _casp, _audit
    _casp = casp
    _audit = audit


# ── Dashboard ───────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(actor: dict = Depends(require_any_admin)) -> Dict[str, Any]:
    return await _casp.kpi_summary()


# ── BLOCK 1: KYC / KYB / Risk / Sanctions ───────────────────────────────────

class KycStartReq(BaseModel):
    user_id: str
    email: EmailStr


@router.post("/kyc/start")
async def kyc_start(body: KycStartReq, actor: dict = Depends(require_compliance)):
    return await _casp.kyc_start(body.user_id, body.email, actor)


class KycDecisionReq(BaseModel):
    decision: str  # APPROVE | REJECT | HOLD
    reason: Optional[str] = None


@router.post("/kyc/{kyc_id}/decision")
async def kyc_decision(kyc_id: str, body: KycDecisionReq, actor: dict = Depends(require_compliance)):
    if body.decision not in ("APPROVE", "REJECT", "HOLD"):
        raise HTTPException(status_code=400, detail="Invalid decision")
    return await _casp.kyc_decision(kyc_id, body.decision, body.reason, actor)


@router.get("/kyc")
async def kyc_list(status: Optional[str] = None, limit: int = 100,
                   actor: dict = Depends(require_compliance)):
    return await _casp.kyc_list(status, limit)


@router.get("/kyb")
async def kyb_list(status: Optional[str] = None, limit: int = 100,
                   actor: dict = Depends(require_compliance)):
    return await _casp.kyb_list(status, limit)


class RiskRatingReq(BaseModel):
    user_id: str
    rating: str  # LOW | MEDIUM | HIGH | PROHIBITED
    score: float = Field(ge=0, le=100)
    factors: Dict[str, Any] = Field(default_factory=dict)


@router.post("/risk-rating")
async def upsert_risk_rating(body: RiskRatingReq, actor: dict = Depends(require_risk)):
    return await _casp.upsert_risk_rating(body.user_id, body.rating, body.score, body.factors, actor)


@router.get("/risk-rating")
async def list_risk_ratings(limit: int = 100, actor: dict = Depends(require_risk)):
    return await _casp.list_risk_ratings(limit)


@router.get("/sanctions")
async def list_sanctions(status: Optional[str] = None, limit: int = 100,
                         actor: dict = Depends(require_compliance)):
    return await _casp.list_sanctions_hits(status, limit)


# ── BLOCK 2: AML / Travel Rule / SAR ────────────────────────────────────────

class ScreenAddressReq(BaseModel):
    address: str
    asset: str
    chain: str


@router.post("/aml/screen-address")
async def screen_address(body: ScreenAddressReq, actor: dict = Depends(require_compliance)):
    return await _casp.evaluate_address(body.address, body.asset, body.chain, actor)


@router.get("/aml/alerts")
async def list_aml_alerts(status: Optional[str] = None, severity: Optional[str] = None,
                          limit: int = 100, actor: dict = Depends(require_compliance)):
    return await _casp.list_aml_alerts(status, severity, limit)


class ResolveAlertReq(BaseModel):
    status: str  # CLOSED_FALSE_POSITIVE | CLOSED_TRUE_POSITIVE | ESCALATED
    notes: Optional[str] = None


@router.post("/aml/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, body: ResolveAlertReq, actor: dict = Depends(require_mlro)):
    return await _casp.resolve_aml_alert(alert_id, body.status, body.notes, actor)


class TravelRuleReq(BaseModel):
    transaction_id: Optional[str] = None
    asset: str
    amount: float
    amount_eur: float
    originator_name: str
    originator_wallet: str
    beneficiary_name: str
    beneficiary_wallet: str
    chain: str


@router.post("/travel-rule")
async def create_travel_rule(body: TravelRuleReq, actor: dict = Depends(require_compliance)):
    return await _casp.create_travel_rule_transfer(
        transaction_id=body.transaction_id, asset=body.asset, amount=body.amount,
        amount_eur=body.amount_eur, originator_name=body.originator_name,
        originator_wallet=body.originator_wallet, beneficiary_name=body.beneficiary_name,
        beneficiary_wallet=body.beneficiary_wallet, chain=body.chain, actor=actor,
    )


@router.get("/travel-rule")
async def list_travel_rule(direction: Optional[str] = None, limit: int = 100,
                          actor: dict = Depends(require_compliance)):
    return await _casp.list_travel_rule(direction, limit)


class SarDraftReq(BaseModel):
    user_id: str
    alert_ids: List[str]
    narrative: str
    total_amount_eur: float


@router.post("/sar")
async def draft_sar(body: SarDraftReq, actor: dict = Depends(require_mlro)):
    return await _casp.draft_sar(body.user_id, body.alert_ids, body.narrative,
                                 body.total_amount_eur, actor)


@router.get("/sar")
async def list_sars(limit: int = 100, actor: dict = Depends(require_mlro)):
    return await _casp.list_sars(limit)


# ── BLOCK 3: Custody / Reconciliation / PoR ─────────────────────────────────

class ProvisionWalletReq(BaseModel):
    user_id: str
    asset: str
    chain: str


@router.post("/wallets/provision")
async def provision_wallet(body: ProvisionWalletReq, actor: dict = Depends(require_treasury)):
    return await _casp.provision_segregated_wallet(body.user_id, body.asset, body.chain, actor)


@router.get("/wallets")
async def list_wallets(kind: Optional[str] = None, purpose: Optional[str] = None,
                      limit: int = 200, actor: dict = Depends(require_treasury)):
    return await _casp.list_wallets(kind, purpose, limit)


@router.post("/wallets/{wallet_id}/freeze")
async def freeze_wallet(wallet_id: str, actor: dict = Depends(require_treasury)):
    return await _casp.freeze_wallet(wallet_id, actor)


@router.post("/wallets/{wallet_id}/reconcile")
async def reconcile(wallet_id: str, actor: dict = Depends(require_treasury)):
    return await _casp.run_reconciliation(wallet_id, actor)


@router.get("/proof-of-reserves")
async def latest_por(actor: dict = Depends(require_any_admin)):
    return await _casp.latest_proof_of_reserves()


@router.post("/proof-of-reserves/generate")
async def generate_por(actor: dict = Depends(require_treasury)):
    return await _casp.generate_proof_of_reserves(actor)


# ── BLOCK 4: B2B OTC desk ───────────────────────────────────────────────────

class OtcQuoteReq(BaseModel):
    client_user_id: str
    side: str  # BUY | SELL
    asset: str
    quantity: float
    price_eur: float
    fee_bps: int = 25
    settlement_method: str = "SEPA"
    settlement_account: Optional[str] = None
    settlement_wallet: Optional[str] = None


@router.post("/otc/quote")
async def create_otc(body: OtcQuoteReq, actor: dict = Depends(require_otc_trader)):
    if body.side not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")
    return await _casp.create_otc_quote(
        client_user_id=body.client_user_id, side=body.side, asset=body.asset,
        quantity=body.quantity, price_eur=body.price_eur, fee_bps=body.fee_bps,
        settlement_method=body.settlement_method,
        settlement_account=body.settlement_account,
        settlement_wallet=body.settlement_wallet,
        actor=actor,
    )


class OtcApproveReq(BaseModel):
    decision: str  # APPROVE | REJECT
    notes: Optional[str] = None


@router.post("/otc/{quote_id}/approve")
async def approve_otc(quote_id: str, body: OtcApproveReq, actor: dict = Depends(require_otc_approver)):
    result = await _casp.approve_otc(quote_id, body.decision, body.notes, actor)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/otc/{quote_id}/execute")
async def execute_otc(quote_id: str, actor: dict = Depends(require_otc_trader)):
    result = await _casp.execute_otc(quote_id, actor)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/otc")
async def list_otc(status: Optional[str] = None, limit: int = 100,
                  actor: dict = Depends(require_any_admin)):
    return await _casp.list_otc(status, limit)


# ── BLOCK 5: Reporting & Capital ────────────────────────────────────────────

class ReportReq(BaseModel):
    period_start: datetime
    period_end: datetime


@router.post("/reports/micar")
async def generate_micar(body: ReportReq, actor: dict = Depends(require_compliance)):
    return await _casp.generate_micar_report(body.period_start, body.period_end, actor)


@router.get("/reports")
async def list_reports(limit: int = 100, actor: dict = Depends(require_any_admin)):
    return await _casp.list_regulatory_reports(limit)


class CapitalReq(BaseModel):
    own_funds_eur: float
    casp_class: int = 2
    notes: Optional[str] = None


@router.post("/capital")
async def upsert_capital(body: CapitalReq, actor: dict = Depends(require_treasury)):
    return await _casp.upsert_capital_snapshot(body.own_funds_eur, body.casp_class, body.notes, actor)


# ── BLOCK 6: Complaints & disclosures ───────────────────────────────────────

class ComplaintReq(BaseModel):
    user_id: str
    category: str
    subject: str
    description: str


@router.post("/complaints")
async def create_complaint(body: ComplaintReq, actor: dict = Depends(require_compliance)):
    return await _casp.create_complaint(body.user_id, body.category, body.subject, body.description, actor)


@router.get("/complaints")
async def list_complaints(status: Optional[str] = None, limit: int = 100,
                         actor: dict = Depends(require_compliance)):
    return await _casp.list_complaints(status, limit)


@router.get("/disclosures")
async def list_disclosures(actor: dict = Depends(require_any_admin)):
    return await _casp.list_disclosures()


# ── BLOCK 7: Governance ─────────────────────────────────────────────────────

class AdminUserReq(BaseModel):
    user_id: str
    email: EmailStr
    casp_roles: List[str]
    department: Optional[str] = None


@router.post("/governance/admins")
async def add_admin(body: AdminUserReq, actor: dict = Depends(require_any_admin)):
    # Only super-admins can create admin users
    if actor.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Only ADMIN can manage admin users")
    return await _casp.ensure_admin_user(body.user_id, body.email, body.casp_roles, body.department)


@router.get("/governance/admins")
async def list_admins(actor: dict = Depends(require_any_admin)):
    return await _casp.list_admin_users()


@router.get("/governance/incidents")
async def list_incidents(status: Optional[str] = None, limit: int = 100,
                        actor: dict = Depends(require_risk)):
    return await _casp.list_incidents(status, limit)


@router.get("/governance/conflicts")
async def list_conflicts(actor: dict = Depends(require_any_admin)):
    return await _casp.list_conflicts()


# ── Audit log ──────────────────────────────────────────────────────────────

@router.get("/audit")
async def list_audit(limit: int = Query(100, le=500), skip: int = 0,
                     entity_id: Optional[str] = None,
                     actor: dict = Depends(require_any_admin)):
    return await _audit.list(limit=limit, skip=skip, entity_id=entity_id)


@router.get("/audit/verify")
async def verify_audit(limit: int = Query(1000, le=10000),
                       actor: dict = Depends(require_any_admin)):
    return await _audit.verify_chain(limit=limit)
