from tools.transcript_manager import TranscriptManager

# Create transcript manager
transcript = TranscriptManager()

# Simulate a call
transcript.set_phone_number("+918709252948")

# Simulate conversation
transcript.add_agent("Hello! Thank you for calling Medoria. I'm Aria, your virtual assistant. Are you looking for a specific doctor?")
transcript.add_user("Yes I am looking for a dentist")
transcript.add_agent("We have Dr. Priya Sharma available. Would you like to know more about her?")
transcript.add_user("Yes please tell me about her")
transcript.add_agent("Dr. Priya Sharma is a dentist with 10 years of experience.")
transcript.add_user("Can I book an appointment?")
transcript.add_agent("Sure! May I have your full name please?")
transcript.add_user("My name is Manas Acharya")
transcript.add_agent("Thank you for calling Medoria. Have a great day!")

# Save transcript
transcript.save()
print("Done! Check transcripts/ folder")