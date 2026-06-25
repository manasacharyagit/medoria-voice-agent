from tools.transcript_manager import TranscriptManager


transcript = TranscriptManager()

transcript.set_phone_number("+918709252948")


transcript.add_agent("Hello! Thank you for calling Medoria. I'm Aria, your virtual assistant. Are you looking for a specific doctor, or can I help you find the right specialist for your concern?")
transcript.add_user("Yes I am looking for a dentist")
transcript.add_agent("We have Dr. Priya Sharma available. Would you like to know more about her?")
transcript.add_user("Yes please tell me about her")
transcript.add_agent("Dr. Priya Sharma is a dentist with 10 years of experience. She offers dental checkups, teeth whitening, braces and more.")
transcript.add_user("Can I book with her for tomorrow at 11am?")
transcript.add_agent("Sure! May I have your full name please?")
transcript.add_user("My name is Manas Acharya")
transcript.add_agent("Could you share your email address?")
transcript.add_user("manasacharya1702 at gmail dot com")
transcript.add_agent("Done! Your appointment is confirmed. You will receive a confirmation email shortly.")
transcript.add_user("Thank you so much")
transcript.add_agent("Thank you for calling Medoria. Have a great day, take care!")

transcript.save()

print("Done")