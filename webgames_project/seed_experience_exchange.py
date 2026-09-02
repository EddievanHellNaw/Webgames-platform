from roleplay.models import RolePlaySituation, RoleCard

situation, situation_created = RolePlaySituation.objects.update_or_create(
    slug="the-experience-exchange",
    defaults={
        "title": "The Experience Exchange",
        "summary": "Students meet at a university event where everyone is sharing memorable life experiences. Students must interview each other, compare stories, and find classmates with interesting, funny, scary, or unusual experiences.",
        "student_briefing": "You are at a university social event called ‘The Experience Exchange.’ Your goal is to talk to different classmates and ask about their life experiences. Find people who have done something exciting, scary, embarrassing, or surprising. Ask follow-up questions to learn when, where, and how it happened.",
        "teacher_notes": "Allow students to interact freely for 10–15 minutes. Encourage students to begin with present perfect questions such as ‘Have you ever…?’ and continue with simple past follow-up questions such as ‘When did it happen?’ ‘Where did you go?’ and ‘How did you feel?’ Use Unit 1.1 vocabulary such as try an extreme sport, be abroad, meet a famous person, get lost, win a competition, break a bone, lose your phone, try exotic food, and do something scary.",
        "language_target": "Present perfect, simple past, asking about experiences, giving details, asking follow-up questions, Unit 1.1 life experience vocabulary",
        "is_active": True,
    },
)

roles = [
    ("The Theater Performer", "You are a student who enjoys creative activities and school events.", "You acted in a play last semester, but you were very nervous before going on stage.", "Share your acting experience and ask others about scary or exciting things they have done.", "You forgot one line during the play, but the audience didn’t notice.", "Have you ever acted in a play? When did it happen? How did you feel? Did anything go wrong?"),
    ("The World Traveler", "You are a student who loves learning about other countries and cultures.", "You have been abroad once. You traveled with your family during vacation.", "Talk about your travel experience and find someone else who has had an adventure.", "You got lost for 20 minutes in another country, but a kind person helped you.", "Have you ever been abroad? Where did you go? Who did you travel with? What did you do there?"),
    ("The TV Guest", "You are a student with an interesting media experience.", "You have been on TV once during a local news interview.", "Tell people about your TV experience and ask if they have had a surprising public moment.", "You were very embarrassed because you said the wrong word during the interview.", "Have you ever been on TV? Why were you on TV? What did you say? Were you nervous?"),
    ("The Wrestling Fan", "You are a student who enjoys exciting live events.", "You have been to a wrestling match with your cousins.", "Find classmates who have been to unusual or exciting events.", "At the wrestling match, you met one of the wrestlers and took a picture.", "Have you ever been to a wrestling match? When did you go? Who did you go with? Did you enjoy it?"),
    ("The Accident Survivor", "You are a student who has had an unforgettable accident.", "You broke a bone when you were younger.", "Talk about your accident and ask classmates about scary or painful experiences.", "You broke your arm because you fell while trying to ride a skateboard.", "Have you ever broken a bone? What bone did you break? How did it happen? Did you go to the hospital?"),
    ("The Guilty Student", "You are a student who learned an important lesson at school.", "You cheated on a test once, but you felt terrible afterward.", "Talk carefully about school mistakes and ask others about lessons they have learned.", "You confessed to the teacher the next day and accepted the consequences.", "Have you ever cheated on a test? Why did it happen? What did you do after that? Did you learn anything?"),
    ("The Vegetarian Chef", "You are a student who likes trying new things in the kitchen.", "You cooked a vegetarian meal for your family.", "Ask others about food experiences and share your cooking story.", "Your family liked the food, but you accidentally burned the rice.", "Have you ever cooked a vegetarian meal? What did you cook? Who ate it? Did they like it?"),
    ("The Brave Friend", "You are a student who once did something very scary.", "You did something scary because your friends encouraged you.", "Find classmates who have also done scary or adventurous things.", "You entered a dark abandoned house for only two minutes, then ran out.", "Have you ever done something scary? What did you do? Who were you with? Were you afraid?"),
    ("The Fancy Dinner Guest", "You are a student who has had a special restaurant experience.", "You ate at a fancy restaurant for a birthday celebration.", "Talk about your fancy restaurant experience and ask others about special meals.", "You didn’t understand the menu and ordered something you didn’t like.", "Have you ever eaten at a fancy restaurant? What did you order? Did you like the food? Was it expensive?"),
    ("The Lucky Finder", "You are a student who once found something valuable.", "You found money on the street near the university.", "Ask others about lucky or surprising experiences and decide what people usually do.", "You gave the money to a security guard because you didn’t know who lost it.", "Have you ever found money? Where did you find it? How much was it? What did you do with it?"),
    ("The Forgetful Friend", "You are a student who sometimes forgets important things.", "You forgot an important date and someone got upset.", "Ask classmates about mistakes and find people who have had embarrassing moments.", "You forgot your best friend’s birthday, so you bought a cake the next day.", "Have you ever forgotten an important date? What date did you forget? Who was upset? How did you fix it?"),
    ("The Unpaid Bill Student", "You are a student who learned to be more responsible with payments.", "You forgot to pay a bill and had a problem at home.", "Share your mistake and ask others about everyday problems they have had.", "You forgot to pay the internet bill, so you had no internet during an online class.", "Have you ever forgotten to pay a bill? What bill was it? What happened? How did you solve it?"),
    ("The Perfect Score Student", "You are a student who had a great academic achievement.", "You got a perfect grade on an exam.", "Ask classmates about school achievements and study experiences.", "You studied for three days because you really wanted to improve your grade.", "Have you ever gotten a perfect grade on an exam? What subject was it? How did you study? How did you feel?"),
    ("The Lost Explorer", "You are a student who has a funny story about getting lost.", "You got lost in a new place.", "Talk about your experience and find someone else who has gotten lost before.", "You got lost inside a mall and called your mom for help.", "Have you ever gotten lost? Where did you get lost? Who helped you? How long were you lost?"),
    ("The Seasick Tourist", "You are a student who likes traveling, but not all trips are perfect.", "You got seasick during a boat trip.", "Share your bad travel experience and ask others about uncomfortable trips.", "You felt sick for most of the trip and couldn’t enjoy the view.", "Have you ever gotten seasick? Where were you going? How did you feel? Did you travel by boat again?"),
    ("The Part-Time Worker", "You are a student who has some work experience.", "You had a part-time job during vacation.", "Find classmates who have worked before and compare experiences.", "You worked at a café, but you once gave a customer the wrong order.", "Have you ever had a part-time job? Where did you work? What did you do? Did you like it?"),
    ("The Young Inventor", "You are a creative student who likes solving problems.", "You invented something for a school project.", "Talk about your invention and ask others about competitions or creative achievements.", "Your invention was a phone holder made from recycled materials.", "Have you ever invented something? What did you invent? Why did you make it? Did it work?"),
    ("The Phone Disaster", "You are a student who has had bad luck with technology.", "You lost your phone once in a public place.", "Ask classmates about losing important things and how they solved the problem.", "You found your phone later under a seat in the movie theater.", "Have you ever lost your phone? Where did you lose it? Did you find it? What did you do?"),
    ("The Big Mistake", "You are a student who has learned from an embarrassing mistake.", "You made a terrible mistake during an important moment.", "Share your experience and ask others about mistakes they have learned from.", "You sent a private message to the wrong group chat.", "Have you ever made a terrible mistake? What happened? Who was there? How did you fix it?"),
    ("The Celebrity Encounter", "You are a student who has an exciting story about a famous person.", "You met a famous person once.", "Ask classmates about famous people, public events, and exciting experiences.", "You were too nervous to ask for a photo.", "Have you ever met a famous person? Who did you meet? Where did you meet them? What did you say?"),
    ("The New City Student", "You are a student who has lived in more than one city.", "You moved to a new city and had to adapt to a different place.", "Talk about moving and ask classmates about changes in their lives.", "At first, you didn’t know anyone, but later you made good friends.", "Have you ever moved to a new city? Where did you move? Was it difficult? How did you make friends?"),
    ("The Roller Coaster Survivor", "You are a student who has had an exciting amusement park experience.", "You rode a roller coaster for the first time.", "Find classmates who have tried exciting or scary activities.", "You screamed the whole time, but after that you wanted to ride it again.", "Have you ever ridden a roller coaster? When did you ride it? Were you scared? Did you like it?"),
    ("The Sky Watcher", "You are a student who has seen something unusual in the sky.", "You saw a shooting star or maybe a UFO. You are not completely sure.", "Ask classmates about strange or beautiful things they have seen.", "You made a wish when you saw the shooting star.", "Have you ever seen a shooting star or a UFO? When did you see it? Where were you? What did it look like?"),
    ("The Exotic Food Taster", "You are a student who likes trying unusual food.", "You tried exotic food during a trip or festival.", "Ask classmates about food experiences and compare opinions.", "You tried insects, and you actually liked them.", "Have you ever tried exotic food? What did you try? Where did you eat it? Did you like it?"),
    ("The Extreme Sport Fan", "You are a student who enjoys adventure and strong emotions.", "You tried an extreme sport once.", "Talk about adventure experiences and ask others what they have tried.", "You tried zip-lining, but you almost didn’t jump because you were scared.", "Have you ever tried an extreme sport? What sport did you try? Where did you do it? Were you afraid?"),
    ("The Competition Champion", "You are a student who has competed and won something.", "You won a competition at school.", "Ask others about competitions, contests, and achievements.", "You didn’t expect to win because you joined the competition at the last minute.", "Have you ever won a competition? What competition did you win? When did it happen? How did you feel?"),
    ("The Contest Winner", "You are a student who participated in a contest and had a surprising result.", "You won a contest, but it was not academic.", "Ask classmates about contests, awards, and unusual achievements.", "You won a singing contest, but you were very nervous before performing.", "Have you ever won a contest? What kind of contest was it? Did you practice a lot? Who watched you?"),
]

created_count = 0
updated_count = 0

for sort_order, (name, public_description, private_briefing, objective, secret_information, useful_language) in enumerate(roles, start=1):
    _, created = RoleCard.objects.update_or_create(
        situation=situation,
        name=name,
        defaults={
            "character_name": "",
            "public_description": public_description,
            "private_briefing": private_briefing,
            "objective": objective,
            "secret_information": secret_information,
            "useful_language": useful_language,
            "copies_available": 1,
            "sort_order": sort_order,
            "is_active": True,
        },
    )
    if created:
        created_count += 1
    else:
        updated_count += 1

print("Experience Exchange seed complete.")
print(f"Situation: {situation.title} ({'created' if situation_created else 'updated'})")
print(f"Roles created: {created_count}")
print(f"Roles updated: {updated_count}")
print(f"Total active role slots: {situation.total_role_slots}")
