from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Club(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='clubs')

    def __str__(self):
        return self.name

class Venue(models.Model):
    venue_id = models.AutoField(primary_key=True)
    venue_name = models.CharField(max_length=100, unique=True)
    building = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(default=100)
    has_projector = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.venue_name} - {self.building} (Cap: {self.capacity})"

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('organizer', 'Organizer'),
        ('faculty', 'Faculty'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=15, blank=True, null=True)
    roll_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True, related_name='organizers')

    @property
    def full_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username

    def save(self, *args, **kwargs):
        if self.role == 'admin':
            self.is_staff = True
            self.is_superuser = True
        elif self.role == 'faculty':
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class Event(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    APPROVAL_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    event_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='events')
    description = models.TextField()
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    date = models.DateField()
    time = models.TimeField()
    deadline = models.DateTimeField()
    max_participants = models.PositiveIntegerField()
    banner_image = models.ImageField(upload_to='event_banners/', blank=True, null=True)
    certificate_template = models.ImageField(upload_to='certificate_templates/', blank=True, null=True)
    payment_scanner = models.ImageField(upload_to='payment_scanners/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='pending')
    organizer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='organized_events')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    registration_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    skills_learned = models.CharField(max_length=300, blank=True, null=True, help_text="Comma-separated list of skills learned e.g. Python, AI, Leadership")

    @property
    def skills_list(self):
        if self.skills_learned:
            return [s.strip() for s in self.skills_learned.split(',') if s.strip()]
        return []

    def clean(self):
        if self.deadline and self.date and self.time:
            dt_combined = timezone.datetime.combine(self.date, self.time)
            if timezone.is_aware(self.deadline):
                event_datetime = timezone.make_aware(dt_combined, timezone.get_current_timezone())
            else:
                event_datetime = dt_combined

            deadline_dt = self.deadline
            if timezone.is_aware(event_datetime) and timezone.is_naive(deadline_dt):
                deadline_dt = timezone.make_aware(deadline_dt, timezone.get_current_timezone())
            elif timezone.is_naive(event_datetime) and timezone.is_aware(deadline_dt):
                event_datetime = timezone.make_aware(event_datetime, timezone.get_current_timezone())

            if deadline_dt > event_datetime:
                raise ValidationError({'deadline': 'Registration deadline must be before the event date and time.'})
        
        if self.venue and self.approval_status == 'approved':
            conflicts = Event.objects.filter(
                venue=self.venue,
                date=self.date,
                approval_status='approved'
            ).exclude(pk=self.pk)
            if conflicts.exists():
                raise ValidationError({'venue': f"Venue '{self.venue.venue_name}' is already booked for another approved event on {self.date}."})

    def __str__(self):
        return f"{self.title} - {self.date}"

class Registration(models.Model):
    registration_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='registrations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    registration_date = models.DateTimeField(auto_now_add=True)
    ticket_code = models.CharField(max_length=30, unique=True, blank=True)
    status = models.CharField(max_length=20, default='Confirmed')
    attendance = models.CharField(max_length=10, choices=(('absent', 'Absent'), ('present', 'Present')), default='absent')
    
    # Team size & Payment tracking
    num_members = models.PositiveIntegerField(default=1)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    payment_status = models.CharField(
        max_length=10,
        choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')],
        default='pending'
    )
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_screenshot = models.ImageField(upload_to='payment_screenshots/', blank=True, null=True)

    # Department-Based Faculty Attendance Approval Workflow
    attendance_status = models.CharField(
        max_length=15,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_attendances'
    )

    class Meta:
        unique_together = ('student', 'event')

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            import uuid
            self.ticket_code = f"EVT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def clean(self):
        if self.event.registrations.filter(status='Confirmed').exclude(pk=self.pk).count() >= self.event.max_participants:
            raise ValidationError('Event is at maximum capacity.')
        if timezone.now() > self.event.deadline:
            raise ValidationError('Registration deadline for this event has passed.')

    def __str__(self):
        return f"{self.student.username} -> {self.event.title} ({self.ticket_code})"

class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    registration = models.OneToOneField(Registration, on_delete=models.CASCADE, related_name='attendance_record')
    checked_in_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_attendances')

    def __str__(self):
        return f"Attendance Log #{self.attendance_id} for Ticket {self.registration.ticket_code}"

class Feedback(models.Model):
    feedback_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='feedbacks')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comments = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'event')

    def __str__(self):
        return f"{self.rating}★ by {self.student.username} for {self.event.title}"

class Certificate(models.Model):
    certificate_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='certificates')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='certificates')
    certificate_file = models.FileField(upload_to='certificates/')
    issue_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'event')

    def __str__(self):
        return f"Cert #{self.certificate_id} - {self.student.username} ({self.event.title})"

class Notification(models.Model):
    notification_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notif to {self.user.username}: {self.title}"
