from tools.email_tool import send_appointment_email

result = send_appointment_email(
    patient_name="Test Patient",
    patient_email="manasacharya1702@gmail.com",  # ← put your own email here
    doctor_name="Dr. Test Doctor",
    doctor_email="manas.acharya@medoria.ai",  # ← same
    service_name="Test Consultation",
    date_str="2026-05-30",
    time_str="10:00",
    clinic_name="Test Clinic",
    clinic_address="Test Address"
)

print(result)