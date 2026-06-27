from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import User, get_current_user, require_site_access
from app.config import get_settings
from app.db import get_db
from app.models import GeneratedReportRow

router = APIRouter(tags=["reports"])


@router.get("/reports")
def list_reports(week: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """List generated reports the current user may download."""
    q = db.query(GeneratedReportRow)
    if week:
        q = q.filter(GeneratedReportRow.week == week)
    rows = q.order_by(GeneratedReportRow.created_at.desc()).all()

    visible = []
    for r in rows:
        if r.report_type == "digest" and user.role != "admin":
            continue
        if r.report_type == "site" and user.role == "manager" and r.site_id != user.site_id:
            continue
        visible.append(
            {
                "id": r.id,
                "week": r.week,
                "report_type": r.report_type,
                "site_id": r.site_id,
                "title": r.title,
                "recipient_email": r.recipient_email,
                "file_name": r.file_name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return {"reports": visible}


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.query(GeneratedReportRow).filter(GeneratedReportRow.id == report_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    if row.report_type == "digest" and user.role != "admin":
        raise HTTPException(status_code=403, detail="Executive digest is for HQ only")
    if row.report_type == "site" and row.site_id:
        require_site_access(user, row.site_id)

    settings = get_settings()
    path = settings.resolved_reports_path / row.week / row.file_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file missing — re-run the pipeline")

    return FileResponse(
        path,
        media_type="text/html",
        filename=row.file_name,
        headers={"Content-Disposition": f'attachment; filename="{row.file_name}"'},
    )
