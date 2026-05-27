from tools.email_tool import send_appointment_email

result = send_appointment_email(
    patient_name="Manas Acharya",
    patient_email="manasacharya1702@gmail.com",
    doctor_name="Dr. Arjun Mehta",
    doctor_email="manas.acharya@medoria.ai",
    service_name="ECG",
    date_str="2026-05-28",
    time_str="11:00",
    clinic_name="Mehta Heart Clinic",
    clinic_address="201, Second Floor, City Centre Mall, Rohini, New Delhi 110085"
)

print(result)