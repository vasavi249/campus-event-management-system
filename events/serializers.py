from rest_framework import serializers
from django.utils import timezone
from .models import Department, Category, Club, Venue, CustomUser, Event, Registration, Attendance, Feedback, Certificate, Notification

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ClubSerializer(serializers.ModelSerializer):
    department_detail = DepartmentSerializer(source='department', read_only=True)

    class Meta:
        model = Club
        fields = '__all__'

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'

class CustomUserSerializer(serializers.ModelSerializer):
    department_detail = DepartmentSerializer(source='department', read_only=True)
    club_detail = ClubSerializer(source='club', read_only=True)
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'role', 'phone', 'roll_number', 'department', 'club', 'department_detail', 'club_detail']

class EventSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
    venue_detail = VenueSerializer(source='venue', read_only=True)
    organizer_detail = CustomUserSerializer(source='organizer', read_only=True)
    registered_count = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    banner_image_url = serializers.SerializerMethodField()
    certificate_template_url = serializers.SerializerMethodField()
    payment_scanner_url = serializers.SerializerMethodField()
    skills_list = serializers.ReadOnlyField()

    class Meta:
        model = Event
        fields = '__all__'

    def get_banner_image_url(self, obj):
        if obj.banner_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.banner_image.url)
            return obj.banner_image.url
        return None

    def get_certificate_template_url(self, obj):
        if obj.certificate_template:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.certificate_template.url)
            return obj.certificate_template.url
        return None

    def get_payment_scanner_url(self, obj):
        if obj.payment_scanner:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.payment_scanner.url)
            return obj.payment_scanner.url
        return None

    def get_registered_count(self, obj):
        from django.db.models import Sum
        total = obj.registrations.filter(status='Confirmed').aggregate(total_members=Sum('num_members'))['total_members']
        return total or 0

    def get_is_full(self, obj):
        return self.get_registered_count(obj) >= obj.max_participants

    def validate(self, data):
        venue = data.get('venue')
        date = data.get('date', getattr(self.instance, 'date', None))
        time_val = data.get('time', getattr(self.instance, 'time', None))
        deadline = data.get('deadline', getattr(self.instance, 'deadline', None))
        approval_status = data.get('approval_status', getattr(self.instance, 'approval_status', 'pending'))

        if deadline and date and time_val:
            dt_combined = timezone.datetime.combine(date, time_val)
            if timezone.is_aware(deadline):
                event_datetime = timezone.make_aware(dt_combined, timezone.get_current_timezone())
            else:
                event_datetime = dt_combined

            deadline_dt = deadline
            if timezone.is_aware(event_datetime) and timezone.is_naive(deadline_dt):
                deadline_dt = timezone.make_aware(deadline_dt, timezone.get_current_timezone())
            elif timezone.is_naive(event_datetime) and timezone.is_aware(deadline_dt):
                event_datetime = timezone.make_aware(event_datetime, timezone.get_current_timezone())

            if deadline_dt > event_datetime:
                raise serializers.ValidationError({"deadline": "Registration deadline must be before the event date and time."})

        if venue and approval_status == 'approved':
            qs = Event.objects.filter(venue=venue, date=date, approval_status='approved')
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"venue": f"Venue '{venue.venue_name}' is already booked for another approved event on {date}."})

        return data

class RegistrationSerializer(serializers.ModelSerializer):
    student_detail = CustomUserSerializer(source='student', read_only=True)
    event_detail = EventSerializer(source='event', read_only=True)
    approved_by_detail = CustomUserSerializer(source='approved_by', read_only=True)
    payment_screenshot_url = serializers.SerializerMethodField()

    class Meta:
        model = Registration
        fields = '__all__'
        read_only_fields = ['ticket_code', 'registration_date']

    def get_payment_screenshot_url(self, obj):
        if obj.payment_screenshot:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.payment_screenshot.url)
            return obj.payment_screenshot.url
        return None

class AttendanceSerializer(serializers.ModelSerializer):
    registration_detail = RegistrationSerializer(source='registration', read_only=True)
    verified_by_detail = CustomUserSerializer(source='verified_by', read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'

class FeedbackSerializer(serializers.ModelSerializer):
    student_detail = CustomUserSerializer(source='student', read_only=True)
    event_detail = EventSerializer(source='event', read_only=True)

    class Meta:
        model = Feedback
        fields = '__all__'

class CertificateSerializer(serializers.ModelSerializer):
    student_detail = CustomUserSerializer(source='student', read_only=True)
    event_detail = EventSerializer(source='event', read_only=True)

    class Meta:
        model = Certificate
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
