from tools.calendar_tool import check_slot_availability

result = check_slot_availability(
    calendar_id="manas.acharya@medoria.ai",
    date_str="2026-05-28",
    time_str="10:30"
)
print("Available:", result)