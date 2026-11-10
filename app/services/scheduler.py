import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("apscheduler")

scheduler = BackgroundScheduler()


def job_expire_reservations():
    """APScheduler periodic job running every 5 minutes to expire overdue reservations."""
    from app.db.session import SessionLocal
    from app.services.enrollment_service import enrollment_service

    db = SessionLocal()
    try:
        count = enrollment_service.expire_pending_reservations(db)
        if count > 0:
            logger.info(f"[APScheduler] Expired {count} overdue reservations.")
    except Exception as e:
        logger.error(f"[APScheduler] Error in job_expire_reservations: {e}")
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            job_expire_reservations,
            trigger=IntervalTrigger(minutes=5),
            id="job_expire_reservations",
            name="Expire overdue enrollment reservations",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("[APScheduler] Background scheduler started.")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[APScheduler] Background scheduler stopped.")

