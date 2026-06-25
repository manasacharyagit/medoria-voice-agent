from tools.sms_tool import send_appointment_sms

result = send_appointment_sms(
    patient_name="Test Patient",
    patient_phone="+918709252948",
    doctor_name="Dr. Arjun Mehta",
    service_name="ECG",
    date_str="2026-06-25",
    time_str="11:00",
    clinic_name="Mehta Heart Clinic",
    clinic_address="201, Second Floor, City Centre Mall, Rohini, New Delhi 110085"
)
print(result)