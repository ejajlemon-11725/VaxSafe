"""
=================================================================
 send_due_reminders.py  —  VaxSafe Auto Reminder Command
=================================================================

কী কাজ করে?
-----------
যেসব Scheduled Vaccine এর date_administered (নির্ধারিত তারিখ) আজ,
অথবা সামনের `--days` দিনের মধ্যে, তাদের জন্য User কে
in-app Notification + Email পাঠায়।

ফলে — Admin ১ম ডোজ select করার পর `_auto_schedule_next_dose()`
যে ২য় ডোজ-টা Scheduled তৈরি করে দেয়, সেই ২য় ডোজের তারিখ
যখন কাছাকাছি এসে যায়, তখন User কে আর ম্যানুয়ালি কিছু না করেই
স্বয়ংক্রিয়ভাবে Reminder চলে যাবে।

কীভাবে চালাবে?
--------------
    # আজকের যেসব vaccine এর তারিখ — তাদের কে reminder পাঠাও
    python manage.py send_due_reminders

    # আজ থেকে আগামী ৩ দিনের মধ্যে যাদের তারিখ
    python manage.py send_due_reminders --days 3

    # শুধু dry-run — কাকে কাকে পাঠাবে দেখাবে, পাঠাবে না
    python manage.py send_due_reminders --days 3 --dry-run

প্রতিদিন cron / Task Scheduler দিয়ে একবার চালালেই হবে।
উদাহরণ Linux cron (প্রতিদিন সকাল ৯টায়):
    0 9 * * *  cd /path/to/VaxSafe && python manage.py send_due_reminders --days 2

Duplicate ঠেকানো হয়:
--------------------
একই vaccine record এর জন্য একই দিনে দু-বার reminder যাবে না।
Notification এ একটা unique title-key check করি।
=================================================================
"""

from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from vaxsafe.models import Vaccine, Notification


# একটা special marker — Notification.message এর শুরুতে রাখব
# যাতে পরে identify করতে পারি "এটা auto due-reminder ছিল"।
DUE_REMINDER_MARKER = "[AUTO_DUE_REMINDER]"


class Command(BaseCommand):
    help = (
        "Scheduled Vaccine গুলোর তারিখ কাছে এলে User কে Notification + Email "
        "পাঠায়। প্রতিদিন একবার চালানো যায় (cron / Task Scheduler)।"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help='আজ থেকে কতদিন সামনের vaccine পর্যন্ত cover করবে। ডিফল্ট 0 (শুধু আজকের)।',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='কিছু পাঠাবে না, শুধু কাকে কাকে পাঠাত তা print করবে।',
        )

    # ---------------------------------------------------------------
    def handle(self, *args, **options):
        days_ahead = options['days']
        dry_run    = options['dry_run']

        today      = timezone.now().date()
        end_date   = today + timedelta(days=days_ahead)

        # যেসব vaccine এখনো Scheduled আর তারিখ আজ থেকে end_date এর মধ্যে
        due_vaccines = Vaccine.objects.filter(
            status='Scheduled',
            date_administered__gte=today,
            date_administered__lte=end_date,
        ).select_related('user', 'family_member')

        self.stdout.write(
            self.style.NOTICE(
                f"🔍 খুঁজে পেয়েছি {due_vaccines.count()} টি due/upcoming vaccine "
                f"(আজ {today} থেকে {end_date} পর্যন্ত)।"
            )
        )

        sent_count    = 0
        skipped_count = 0
        email_errors  = 0

        for vaccine in due_vaccines:
            target_user = vaccine.user
            if not target_user:
                continue

            # Duplicate ঠেকানো: একই দিনে এই specific vaccine record এর জন্য
            # আগে auto due-reminder পাঠানো হয়েছে কিনা দেখো
            unique_tag = f"{DUE_REMINDER_MARKER}#vid={vaccine.id}#date={today.isoformat()}"
            already_sent = Notification.objects.filter(
                user=target_user,
                message__contains=unique_tag,
            ).exists()

            if already_sent:
                skipped_count += 1
                self.stdout.write(
                    f"  ⏭️  Skip (আজকে আগেই পাঠানো): {target_user.username} — "
                    f"{vaccine.name} {vaccine.dose_number}"
                )
                continue

            # ---- Notification বানাও ----
            recipient = vaccine.get_recipient_name()
            days_left = (vaccine.date_administered - today).days

            if days_left == 0:
                when_text = "আজই"
            elif days_left == 1:
                when_text = "আগামীকাল"
            else:
                when_text = f"{days_left} দিন পর"

            title = (
                f"⏰ Reminder: {recipient} এর {vaccine.name} "
                f"({vaccine.dose_number}) — {when_text}"
            )

            msg_lines = [
                f"আপনার / {recipient} এর '{vaccine.name}' টিকার",
                f"{vaccine.dose_number} দেওয়ার তারিখ {when_text}।",
                "",
                f"📅 নির্ধারিত তারিখ: {vaccine.date_administered.strftime('%d %B %Y')}",
            ]
            if vaccine.location:
                msg_lines.append(f"📍 স্থান: {vaccine.location}")
            if vaccine.healthcare_provider:
                msg_lines.append(f"🏥 প্রদানকারী: {vaccine.healthcare_provider}")
            msg_lines.append("")
            msg_lines.append("⚠️ নির্ধারিত সময়ে টিকা নিতে ভুলবেন না।")
            msg_lines.append("")
            # সবার শেষে unique tag — যাতে duplicate detect করা যায়
            msg_lines.append(unique_tag)

            full_msg = "\n".join(msg_lines)

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [DRY] → {target_user.username} ({target_user.email or 'no-email'}) "
                        f": {vaccine.name} {vaccine.dose_number} — {when_text}"
                    )
                )
                sent_count += 1
                continue

            # ---- In-app Notification ----
            Notification.objects.create(
                user       = target_user,
                title      = title,
                message    = full_msg,
                notif_type = 'reminder',
            )

            # ---- Email ----
            if target_user.email:
                try:
                    send_mail(
                        subject=f"VaxSafe — {vaccine.name} ({vaccine.dose_number}) Reminder",
                        message=f"{title}\n\n{full_msg}\n\n---\nVaxSafe Auto Reminder",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[target_user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    email_errors += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"  ✉️  Email error for {target_user.email}: {e}"
                        )
                    )

            sent_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✅ Sent → {target_user.username}: "
                    f"{vaccine.name} {vaccine.dose_number} ({when_text})"
                )
            )

        # ---- Summary ----
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 55))
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"🧪 DRY-RUN: {sent_count} টি reminder পাঠানো হত। "
                f"কিছুই পাঠানো হয়নি।"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"🎉 মোট {sent_count} টি reminder পাঠানো হয়েছে। "
                f"Skipped: {skipped_count}। Email error: {email_errors}।"
            ))
        self.stdout.write(self.style.SUCCESS("=" * 55))