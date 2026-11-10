from typing import Optional
from fastapi import Request

MESSAGES = {
    # Auth & Permissions
    "auth_invalid_credentials": {
        "en": "Invalid email or password.",
        "ar": "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
    },
    "auth_inactive_account": {
        "en": "Account is suspended or inactive.",
        "ar": "الحساب معطل أو غير نشط.",
    },
    "auth_token_expired": {
        "en": "Token has expired.",
        "ar": "انتهت صلاحية الرمز.",
    },
    "auth_token_invalid": {
        "en": "Invalid authentication token.",
        "ar": "رمز المصادقة غير صالح.",
    },
    "permission_denied": {
        "en": "Permission denied. You do not have access to this resource or action.",
        "ar": "تم رفض الإذن. ليس لديك صلاحية للوصول إلى هذا المورد أو الإجراء.",
    },
    "branch_access_denied": {
        "en": "Access to this branch is restricted.",
        "ar": "الوصول إلى هذا الفرع مقيد وغير مصرح به.",
    },
    "teacher_forbidden_resource": {
        "en": "Teachers can only access attendance and their assigned groups/sessions.",
        "ar": "يُسمح للأساتذة فقط بالوصول إلى الحضور ومجموعاتهم وحصصهم المسندة إليهم.",
    },

    # Groups & Capacity
    "group_not_found": {
        "en": "Group not found.",
        "ar": "المجموعة غير موجودة.",
    },
    "group_capacity_exceeded": {
        "en": "Group capacity reached. No available spots left.",
        "ar": "تم بلوغ الطاقة الاستيعابية للمجموعة. لا توجد مقاعد شاغرة.",
    },
    "group_capacity_reduction_forbidden": {
        "en": "Cannot reduce group capacity below current occupied spots (confirmed + active reservations).",
        "ar": "لا يمكن تخفيض طاقة المجموعة إلى أقل من عدد المقاعد المشغولة حالياً.",
    },
    "group_over_capacity_unauthorized": {
        "en": "Only General Director or Branch Director can allow over-capacity with a mandatory reason.",
        "ar": "فقط المدير العام أو مدير الفرع يمكنه تجاوز الطاقة الاستيعابية مع تبرير إلزامي.",
    },
    "room_capacity_insufficient": {
        "en": "Room capacity is smaller than group capacity.",
        "ar": "سعة القاعة أصغر من طاقة المجموعة.",
    },

    # Reservations & Enrollments
    "enrollment_not_found": {
        "en": "Enrollment record not found.",
        "ar": "ملف التسجيل غير موجود.",
    },
    "reservation_expired": {
        "en": "Reservation has expired.",
        "ar": "انتهت مدة الحجز المؤقت.",
    },
    "enrollment_already_confirmed": {
        "en": "Enrollment is already confirmed.",
        "ar": "التسجيل مؤكد بالفعل.",
    },
    "enrollment_deposit_insufficient": {
        "en": "Cannot confirm enrollment without meeting minimum deposit payment.",
        "ar": "لا يمكن تأكيد التسجيل دون دفع الحد الأدنى من الدفعة الأولى.",
    },
    "student_schedule_conflict": {
        "en": "Student already has an overlapping active enrollment schedule.",
        "ar": "لدى الطالب تعارض في جدول التوقيت مع مجموعة أخرى مسجل بها.",
    },

    # Schedules & Sessions
    "room_schedule_conflict": {
        "en": "Room is already booked for another session in this time window.",
        "ar": "القاعة محجوزة بالفعل لحصة أخرى في هذه الفترة الزمنية.",
    },
    "teacher_schedule_conflict": {
        "en": "Teacher is already scheduled for another session in this time window.",
        "ar": "الأستاذ مرتبط بحصة أخرى في هذه الفترة الزمنية.",
    },
    "closure_day_conflict": {
        "en": "Date falls on a registered school closure day or vacation.",
        "ar": "التاريخ يوافق يوم عطلة أو إغلاق مدرسي مسجل.",
    },
    "session_already_held": {
        "en": "Cannot cancel or modify a session that has already been held.",
        "ar": "لا يمكن إلغاء أو تعديل حصة تم إجراؤها بالفعل.",
    },
    "session_cancelled": {
        "en": "This session has been cancelled. Attendance cannot be recorded.",
        "ar": "هذه الحصة ملغاة، لا يمكن تسجيل الحضور عليها.",
    },
    "attendance_window_expired": {
        "en": "The allowed time window for teacher attendance modification has passed.",
        "ar": "انتهت المهلة الزمنية المسموحة للأستاذ لتعديل الحضور.",
    },

    # Financial & Fund Transfers
    "payment_not_found": {
        "en": "Payment not found.",
        "ar": "سجل الدفع غير موجود.",
    },
    "payment_already_cancelled": {
        "en": "Payment has already been cancelled.",
        "ar": "تم إلغاء عملية الدفع بالفعل.",
    },
    "transfer_not_found": {
        "en": "Fund transfer not found.",
        "ar": "عملية تحويل الأموال غير موجودة.",
    },
    "transfer_status_invalid": {
        "en": "Fund transfer is not in pending status.",
        "ar": "عملية تحويل الأموال ليست في حالة الانتظار.",
    },
    "cash_register_insufficient_funds": {
        "en": "Cash register has insufficient balance for this operation.",
        "ar": "رصيد الصندوق غير كافٍ لإتمام هذه العملية.",
    },

    # General
    "resource_not_found": {
        "en": "Requested resource was not found.",
        "ar": "المورد المطلوب غير موجود.",
    },
    "conflict_error": {
        "en": "A conflicting record already exists.",
        "ar": "يوجد سجل متعارض بالفعل.",
    },
    "validation_error": {
        "en": "Input validation error.",
        "ar": "خطأ في التحقق من صحة البيانات المدخلة.",
    },
}


def get_preferred_language(request: Optional[Request] = None, user_lang: Optional[str] = None) -> str:
    """Detect language between 'ar' and 'en'. Default is 'en'."""
    if user_lang in ("ar", "en"):
        return user_lang
    if request:
        accept = request.headers.get("accept-language", "").lower()
        if "ar" in accept:
            return "ar"
    return "en"


def t(key: str, lang: str = "en", **kwargs) -> str:
    """Translate message key to requested language ('ar' or 'en')."""
    entry = MESSAGES.get(key)
    if not entry:
        return key
    msg = entry.get(lang) or entry.get("en") or key
    if kwargs:
        try:
            return msg.format(**kwargs)
        except Exception:
            return msg
    return msg
