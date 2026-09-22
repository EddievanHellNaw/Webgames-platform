from roleplay.models import RolePlaySituation, RoleCard


situation, situation_created = RolePlaySituation.objects.update_or_create(
    slug="the-campus-connection-mixer",
    defaults={
        "title": "The Campus Connection Mixer",
        "summary": (
            "Students attend a university social mixer where they must meet new people, "
            "make small talk, share life experiences, and discuss possible or imaginary situations."
        ),
        "student_briefing": (
            "You are at a university social mixer. Your goal is to meet different people "
            "and have short, friendly conversations. Start with small talk, ask about life "
            "experiences, and ask at least one 'What if...?' question. Try to find someone "
            "who connects with the objective in your role. Remember to end conversations politely."
        ),
        "teacher_notes": (
            "Allow students to interact freely for about 12–15 minutes. Encourage them to "
            "speak to at least three classmates. Students should begin conversations naturally "
            "using small talk, then use Present Perfect to ask about experiences and Simple Past "
            "for follow-up details. They should also use at least one First or Second Conditional "
            "question. Encourage discourse markers such as 'So...', 'Well...', 'Anyway...', "
            "'I mean...', and polite closing expressions."
        ),
        "language_target": (
            "Small talk, initiating and closing conversations, discourse markers, "
            "Present Perfect and Simple Past for experiences, First Conditional for real "
            "future possibilities, Second Conditional for hypothetical situations"
        ),
        "is_active": True,
    },
)


roles = [
    (
        "The Adventure Seeker",
        "You enjoy exciting activities and talking about adventures.",
        "You have tried an extreme sport once. You went zip-lining and were very nervous at first.",
        "Find someone who has done something scary or exciting and compare your experiences.",
        "You would love to try skydiving if you had the opportunity.",
        (
            "Hi, how's it going? Have you ever done something scary? "
            "When did it happen? If you could try any extreme sport, what would you try? "
            "Anyway, it was nice talking to you."
        ),
    ),

    (
        "The World Traveler",
        "You enjoy talking about places, cultures, and travel.",
        "You have been abroad once with your family.",
        "Find someone who has traveled or would like to visit another country.",
        "You got lost for about twenty minutes during your trip.",
        (
            "Have you ever been abroad? Where did you go? What happened there? "
            "If you travel abroad next year, where will you go? "
            "What would you do if you could travel anywhere?"
        ),
    ),

    (
        "The Food Explorer",
        "You love talking about food and trying new dishes.",
        "You have tried exotic food at a food festival.",
        "Find someone who has had an unusual or memorable food experience.",
        "You tried insects and actually liked them.",
        (
            "Have you ever tried exotic food? What did you eat? Did you like it? "
            "If you see something unusual on a menu, will you try it? "
            "What would you eat if you could try any food in the world?"
        ),
    ),

    (
        "The Competition Winner",
        "You enjoy challenges and talking about achievements.",
        "You have won a competition at school.",
        "Find someone who has achieved something they are proud of.",
        "You entered the competition at the last minute and did not expect to win.",
        (
            "Have you ever won a competition? What was it? How did you feel? "
            "If you enter another competition, will you prepare differently? "
            "What would you compete in if you could choose anything?"
        ),
    ),

    (
        "The Forgetful Friend",
        "You are friendly, but sometimes you forget important things.",
        "You once forgot an important date.",
        "Find someone who has made an embarrassing or funny mistake.",
        "You forgot your best friend's birthday and bought them a cake the next day.",
        (
            "Have you ever forgotten something important? What happened? "
            "How did you fix it? If you forget an important date again, what will you do? "
            "What would you do if your friend forgot your birthday?"
        ),
    ),

    (
        "The Roller Coaster Fan",
        "You enjoy amusement parks and exciting activities.",
        "You have ridden a roller coaster several times.",
        "Find someone who likes or dislikes scary activities.",
        "The first time you rode one, you screamed during the entire ride.",
        (
            "Have you ever ridden a roller coaster? Were you scared? "
            "If we go to an amusement park, will you ride one? "
            "What would you do if the biggest roller coaster was the only ride open?"
        ),
    ),

    (
        "The Part-Time Worker",
        "You like talking about jobs, university, and everyday life.",
        "You have had a part-time job at a café.",
        "Find someone who has worked before or would like to have a part-time job.",
        "You once gave a customer the wrong order.",
        (
            "So, do you work or study full-time? Have you ever had a part-time job? "
            "What did you do? If you get a part-time job, what will you do with the money? "
            "What job would you choose if you could work anywhere?"
        ),
    ),

    (
        "The Celebrity Encounter",
        "You enjoy entertainment and popular culture.",
        "You have met a famous person once.",
        "Find someone who has had an unusual public or entertainment experience.",
        "You were too nervous to ask the famous person for a photo.",
        (
            "Have you ever met someone famous? Who did you meet? "
            "What did you say? What would you do if you met your favorite celebrity? "
            "Anyway, it was great talking to you."
        ),
    ),

    (
        "The Lost Explorer",
        "You enjoy visiting new places, even though you sometimes get confused.",
        "You have gotten lost in an unfamiliar place.",
        "Find someone who has gotten lost or had a surprising travel experience.",
        "You got lost in a shopping mall and called your mother for help.",
        (
            "Have you ever gotten lost? Where did it happen? Who helped you? "
            "If you get lost in a new city, what will you do? "
            "What would you do if your phone had no battery?"
        ),
    ),

    (
        "The Theater Performer",
        "You enjoy music, theater, and creative activities.",
        "You have acted in a play.",
        "Find someone who has performed, competed, or spoken in front of other people.",
        "You forgot one line, but the audience did not notice.",
        (
            "Have you ever acted in a play? Have you ever performed in public? "
            "How did you feel? If you perform again, will you be nervous? "
            "What role would you choose if you could be in any movie?"
        ),
    ),

    (
        "The Phone Disaster",
        "You enjoy talking about technology and everyday problems.",
        "You have lost your phone before.",
        "Find someone who has lost something important or had a technology problem.",
        "You found your phone under a seat at the movie theater.",
        (
            "Have you ever lost your phone? Where did you lose it? "
            "How did you find it? If you lose your phone tomorrow, what will you do? "
            "What would you do if you couldn't use your phone for a month?"
        ),
    ),

    (
        "The Fancy Dinner Guest",
        "You enjoy restaurants and talking about food.",
        "You have eaten at a fancy restaurant.",
        "Find someone who has had an interesting restaurant or food experience.",
        "You ordered something expensive because you did not understand the menu.",
        (
            "Have you ever eaten at a fancy restaurant? What did you order? "
            "Was it good? If you go there again, what will you order? "
            "Where would you eat if money were not a problem?"
        ),
    ),

    (
        "The New City Student",
        "You enjoy meeting new people and learning about different places.",
        "You have moved to a new city before.",
        "Find someone who has experienced an important change in their life.",
        "At first you did not know anyone, but you eventually made several good friends.",
        (
            "Have you ever moved to a new city? Was it difficult? "
            "How did you meet people? If you move again, what will you do first? "
            "Where would you live if you could choose any city?"
        ),
    ),

    (
        "The Lucky Finder",
        "You like talking about surprising things that happen in everyday life.",
        "You once found money on the street.",
        "Find someone who has had a lucky or unexpected experience.",
        "You gave the money to a security guard.",
        (
            "Have you ever found money? Where did you find it? What did you do? "
            "If you find money tomorrow, what will you do? "
            "What would you do if you found a bag with a million pesos?"
        ),
    ),

    (
        "The Inventor",
        "You enjoy creative ideas and solving problems.",
        "You have invented something for a university or school project.",
        "Find someone who has created or achieved something interesting.",
        "You made a phone holder using recycled materials.",
        (
            "Have you ever invented something? What did you make? Did it work? "
            "If you have another project, what will you create? "
            "What would you invent if you had unlimited money?"
        ),
    ),

    (
        "The TV Guest",
        "You enjoy talking about media and unusual experiences.",
        "You have been on TV once.",
        "Find someone who has had an unusual public experience.",
        "A local reporter interviewed you during a university event.",
        (
            "Have you ever been on TV? What happened? Were you nervous? "
            "If someone interviews you again, what will you say? "
            "What would you talk about if you had your own TV show?"
        ),
    ),

    (
        "The Seasick Tourist",
        "You enjoy traveling, although one trip did not go very well.",
        "You have gotten seasick on a boat.",
        "Find someone who has had a bad but memorable travel experience.",
        "You spent most of the trip sitting down because you felt terrible.",
        (
            "Have you ever gotten seasick? Have you ever had a bad trip? "
            "What happened? If you travel by boat again, what will you do? "
            "Would you take a cruise if someone gave you a free ticket?"
        ),
    ),

    (
        "The Perfect Score Student",
        "You enjoy talking about university life and academic achievements.",
        "You have gotten a perfect grade on an exam.",
        "Find someone who has achieved something at school or university.",
        "You studied for three days before the exam.",
        (
            "How are your classes going? Have you ever gotten a perfect grade? "
            "What subject was it? If you have a difficult exam next week, how will you prepare? "
            "What would you study if you could choose any subject?"
        ),
    ),

    (
        "The Brave Cook",
        "You like preparing food and trying new recipes.",
        "You have cooked a vegetarian meal for your family.",
        "Find someone who enjoys cooking or has tried something new.",
        "You burned the rice, but everybody still liked the meal.",
        (
            "Do you like cooking? Have you ever cooked a vegetarian meal? "
            "What did you make? If you cook dinner tonight, what will you make? "
            "What would you cook for a famous guest?"
        ),
    ),

    (
        "The Accident Survivor",
        "You have an interesting story about an accident from your childhood.",
        "You have broken a bone.",
        "Find someone who has had a scary or painful experience.",
        "You broke your arm while learning to skateboard.",
        (
            "Have you ever broken a bone? How did it happen? "
            "How long did it take to recover? If you try that activity again, will you be more careful? "
            "What would you do if your friend got hurt?"
        ),
    ),

    (
        "The Sky Watcher",
        "You enjoy unusual stories and looking at the night sky.",
        "You have seen a shooting star, although at first you thought it was a UFO.",
        "Find someone who has seen or experienced something unusual.",
        "You made a wish when you realized it was a shooting star.",
        (
            "Have you ever seen a shooting star or a UFO? Where were you? "
            "What did you see? What would you do if you saw a real UFO? "
            "So, do you believe there is life on other planets?"
        ),
    ),

    (
        "The Big Mistake",
        "You have a funny but embarrassing story to share.",
        "You have made a terrible mistake with your phone.",
        "Find someone who has also made an embarrassing mistake.",
        "You sent a private message to the wrong group chat.",
        (
            "Have you ever made a terrible mistake? What happened? "
            "How did you fix it? If it happens again, what will you do? "
            "What would you do if you sent a message to the wrong person?"
        ),
    ),

    (
        "The Wrestling Fan",
        "You enjoy sports and live entertainment.",
        "You have been to a wrestling match.",
        "Find someone who has attended an exciting event.",
        "You met one of the wrestlers after the match.",
        (
            "What kind of sports do you like? Have you ever been to a wrestling match? "
            "Who did you go with? If there is another match this year, will you go? "
            "What event would you attend if tickets were free?"
        ),
    ),

    (
        "The Conversation Starter",
        "You are very sociable and enjoy meeting new people.",
        "You have had many interesting experiences, but today your main challenge is helping other people talk.",
        "Speak to someone who seems quiet and keep the conversation going for at least a few minutes.",
        "You once felt very shy at a university event, so you understand how uncomfortable small talk can feel.",
        (
            "Hi, mind if I join you? How are you enjoying the event? "
            "Have you ever been to an event like this before? I see what you mean. "
            "What would make an event like this more fun? It was nice talking to you."
        ),
    ),
]


created_count = 0
updated_count = 0

for sort_order, (
    name,
    public_description,
    private_briefing,
    objective,
    secret_information,
    useful_language,
) in enumerate(roles, start=1):

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


print("Campus Connection Mixer seed complete.")
print(
    f"Situation: {situation.title} "
    f"({'created' if situation_created else 'updated'})"
)
print(f"Roles created: {created_count}")
print(f"Roles updated: {updated_count}")
print(f"Total active role slots: {situation.total_role_slots}")